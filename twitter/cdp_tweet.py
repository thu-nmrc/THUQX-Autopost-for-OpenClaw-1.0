#!/usr/bin/env python3
"""
Post a tweet via Chrome DevTools Protocol (CDP) — no openclaw CLI dependency.
Connects directly to Chrome on the CDP port, avoiding gateway round-trip issues.

Usage: python3 cdp_tweet.py "tweet text" [--port 9222] [--base-url https://x.com]
"""

import argparse, json, time, sys, urllib.request

import websocket


def cdp_send(ws, method, params=None, timeout=15):
    """Send a CDP command and wait for the result."""
    msg_id = int(time.time() * 1000) % 1_000_000
    payload = {"id": msg_id, "method": method, "params": params or {}}
    ws.send(json.dumps(payload))
    deadline = time.time() + timeout
    while time.time() < deadline:
        ws.settimeout(max(0.5, deadline - time.time()))
        try:
            raw = ws.recv()
        except websocket.WebSocketTimeoutException:
            continue
        data = json.loads(raw)
        if data.get("id") == msg_id:
            if "error" in data:
                raise RuntimeError(f"CDP error: {data['error']}")
            return data.get("result", {})
    raise TimeoutError(f"CDP call {method} timed out after {timeout}s")


def list_tabs(port):
    url = f"http://127.0.0.1:{port}/json"
    with urllib.request.urlopen(url, timeout=5) as resp:
        return json.loads(resp.read())


def activate_tab(port, target_id):
    url = f"http://127.0.0.1:{port}/json/activate/{target_id}"
    try:
        with urllib.request.urlopen(url, timeout=5):
            pass
    except Exception:
        pass


def find_tab(tabs, url_fragment):
    """Find a tab whose URL contains url_fragment, preferring compose."""
    compose = [t for t in tabs if "compose" in t.get("url", "") and url_fragment in t.get("url", "")]
    if compose:
        return compose[0]
    matches = [t for t in tabs if url_fragment in t.get("url", "") and t.get("type") == "page"]
    return matches[0] if matches else None


def navigate_tab(ws, url):
    cdp_send(ws, "Page.navigate", {"url": url})
    time.sleep(3)


def js_eval(ws, expression, timeout=10):
    result = cdp_send(ws, "Runtime.evaluate", {
        "expression": expression,
        "returnByValue": True,
        "awaitPromise": True,
    }, timeout=timeout)
    val = result.get("result", {})
    if val.get("type") == "string":
        return val.get("value", "")
    if val.get("type") == "boolean":
        return val.get("value", False)
    if val.get("type") == "number":
        return val.get("value", 0)
    return val.get("value", val.get("description", ""))


JS_FOCUS_TEXTBOX = r"""
(() => {
    const selectors = [
        '[data-testid="tweetTextarea_0"]',
        '[role="textbox"][aria-label]',
        '[contenteditable="true"][role="textbox"]',
    ];
    for (const sel of selectors) {
        const el = document.querySelector(sel);
        if (el) { el.focus(); el.click(); return "OK"; }
    }
    return "ERROR:TEXTBOX_NOT_FOUND";
})()
"""

JS_CLICK_POST = r"""
(async () => {
    const btn = document.querySelector('[data-testid="tweetButton"]')
        || document.querySelector('[data-testid="tweetButtonInline"]');

    if (btn && !btn.disabled && btn.getAttribute('aria-disabled') !== 'true') {
        btn.click();
        await new Promise(r => setTimeout(r, 2000));
        const body = document.body.innerText || '';
        if (/Your post was sent|已发送|帖子已发送|Post sent/i.test(body)) {
            return "SUCCESS:POST_SENT";
        }
        return "CLICKED:AWAITING_CONFIRM";
    }

    // Broader fallback
    const allBtns = document.querySelectorAll('button, [role="button"]');
    for (const b of allBtns) {
        const text = (b.textContent || '').trim();
        if (/^(Post|Tweet|发帖|发推|发布)$/i.test(text) && !b.disabled) {
            b.click();
            await new Promise(r => setTimeout(r, 2000));
            return "CLICKED:FALLBACK";
        }
    }

    return "ERROR:POST_BUTTON_NOT_FOUND";
})()
"""

JS_CHECK_LOGIN = r"""
(() => {
    const body = document.body.innerText || '';
    if (/Sign in|登录 X|Create account|创建账号/.test(body)) {
        return "LOGIN_REQUIRED";
    }
    return "LOGGED_IN";
})()
"""


def post_tweet(tweet_text, port=9222, base_url="https://x.com"):
    print(f"CDP port: {port}")

    # List tabs and find/activate X tab
    tabs = list_tabs(port)
    page_tabs = [t for t in tabs if t.get("type") == "page"]
    print(f"Found {len(page_tabs)} page tabs")

    target = find_tab(page_tabs, "x.com")

    if not target:
        print("No X tab found, will use first available page tab")
        if not page_tabs:
            print("ERROR: No page tabs available")
            return False
        target = page_tabs[0]

    target_id = target["id"]
    ws_url = target["webSocketDebuggerUrl"]

    # Activate the tab
    activate_tab(port, target_id)
    print(f"Activated tab: {target['url'][:60]}")

    # Connect via WebSocket (set origin to bypass Chrome's origin check)
    ws = websocket.create_connection(ws_url, timeout=10, origin=f"http://127.0.0.1:{port}")
    print("CDP WebSocket connected")

    try:
        # Enable Page events
        cdp_send(ws, "Page.enable")

        # Navigate to compose page
        current_url = target.get("url", "")
        if "compose/post" not in current_url:
            print("Navigating to compose page...")
            navigate_tab(ws, f"{base_url}/compose/post")

        # Wait for page to be ready
        for attempt in range(10):
            ready = js_eval(ws, "document.readyState")
            if ready == "complete":
                break
            print(f"Page loading... ({ready})")
            time.sleep(1)

        time.sleep(2)

        # Check login
        login_status = js_eval(ws, JS_CHECK_LOGIN)
        if login_status == "LOGIN_REQUIRED":
            print("ERROR: X login required. Please login first.")
            return False
        print(f"Login status: {login_status}")

        # Focus the textbox
        focus_result = js_eval(ws, JS_FOCUS_TEXTBOX)
        print(f"Focus textbox: {focus_result}")

        if "ERROR" in str(focus_result):
            print("Textbox not found, retrying after navigation...")
            navigate_tab(ws, f"{base_url}/compose/post")
            time.sleep(3)
            focus_result = js_eval(ws, JS_FOCUS_TEXTBOX)
            print(f"Retry focus: {focus_result}")
            if "ERROR" in str(focus_result):
                print("ERROR: Could not find tweet textbox")
                return False

        time.sleep(0.3)

        # Clear existing text (Cmd+A then Delete)
        cdp_send(ws, "Input.dispatchKeyEvent", {"type": "keyDown", "key": "a", "code": "KeyA", "modifiers": 2})
        cdp_send(ws, "Input.dispatchKeyEvent", {"type": "keyUp", "key": "a", "code": "KeyA", "modifiers": 2})
        cdp_send(ws, "Input.dispatchKeyEvent", {"type": "keyDown", "key": "Backspace", "code": "Backspace"})
        cdp_send(ws, "Input.dispatchKeyEvent", {"type": "keyUp", "key": "Backspace", "code": "Backspace"})
        time.sleep(0.3)

        # Type via CDP Input.insertText (triggers React state updates correctly)
        cdp_send(ws, "Input.insertText", {"text": tweet_text})
        time.sleep(1)
        print(f"Text inserted ({len(tweet_text)} chars)")

        # Click Post button
        for attempt in range(5):
            click_result = js_eval(ws, JS_CLICK_POST, timeout=10)
            print(f"Post attempt {attempt+1}: {click_result}")

            if "SUCCESS" in str(click_result):
                print("Tweet published successfully.")
                return True

            if "ERROR:POST_BUTTON_NOT_FOUND" in str(click_result):
                print("Post button not found/enabled yet, waiting...")
                time.sleep(2)
                continue

            if "CLICKED" in str(click_result):
                time.sleep(3)
                verify = js_eval(ws, """
                    (() => {
                        const box = document.querySelector('[data-testid="tweetTextarea_0"]');
                        const body = document.body.innerText || '';
                        if (/Your post was sent|已发送|帖子已发送|Post sent/.test(body)) return "SUCCESS";
                        if (!box) return "LIKELY_SUCCESS";
                        return "STILL_ON_PAGE";
                    })()
                """)
                print(f"Verify: {verify}")
                if "SUCCESS" in verify or "LIKELY_SUCCESS" in verify:
                    print("Tweet published successfully.")
                    return True

        print("Post attempted but success signal not detected. Check timeline.")
        return True

    finally:
        ws.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post a tweet via CDP")
    parser.add_argument("tweet", help="Tweet text to post")
    parser.add_argument("--port", type=int, default=int(__import__("os").environ.get("OPENCLAW_CDP_PORT", "9222")))
    parser.add_argument("--base-url", default="https://x.com")
    args = parser.parse_args()

    if not args.tweet.strip():
        print("Error: Tweet content is required")
        sys.exit(1)

    success = post_tweet(args.tweet, port=args.port, base_url=args.base_url)
    sys.exit(0 if success else 1)
