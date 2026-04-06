#!/usr/bin/env python3
"""
Weibo post via CDP (no OpenClaw CLI). Requires Chrome --remote-debugging-port + --remote-allow-origins=*.
User must be logged in; opens / publishes from home composer when possible.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

import websocket


def port() -> int:
    return int(os.environ.get("OPENCLAW_CDP_PORT", "9222"))


def list_tabs(p: int):
    with urllib.request.urlopen(f"http://127.0.0.1:{p}/json", timeout=8) as r:
        return json.loads(r.read())


def activate(p: int, tid: str):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{p}/json/activate/{tid}", timeout=5)
    except Exception:
        pass


def find_weibo(p: int):
    for t in list_tabs(p):
        if t.get("type") == "page" and "weibo.com" in t.get("url", ""):
            return t
    return None


def connect_ws(ws_url: str, p: int):
    return websocket.create_connection(ws_url, timeout=15, origin=f"http://127.0.0.1:{p}")


def cdp_send(ws, method: str, params=None, timeout=20):
    msg_id = int(time.time() * 1000) % 1_000_000_000
    ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
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
                raise RuntimeError(str(data["error"]))
            return data.get("result", {})
    raise TimeoutError(method)


def js_eval(ws, expr: str, timeout=15):
    r = cdp_send(
        ws,
        "Runtime.evaluate",
        {"expression": expr, "returnByValue": True, "awaitPromise": False},
        timeout=timeout,
    )
    res = r.get("result", {})
    if res.get("type") == "string":
        return res.get("value", "")
    if res.get("type") == "boolean":
        return res.get("value", False)
    if res.get("type") == "number":
        return res.get("value", 0)
    return res.get("value", "")


def js_escape(s: str) -> str:
    return json.dumps(s)


def main():
    if len(sys.argv) < 2:
        print("Usage: cdp_weibo_ops.py <content>", file=sys.stderr)
        sys.exit(1)

    text = sys.argv[1]
    p = port()
    tab = find_weibo(p)
    if not tab:
        print("ERROR: No weibo.com tab. Open Weibo in CDP Chrome.", file=sys.stderr)
        sys.exit(1)

    activate(p, tab["id"])
    time.sleep(0.3)
    ws = connect_ws(tab["webSocketDebuggerUrl"], p)
    try:
        cdp_send(ws, "Page.enable", {})

        # Ensure home (composer on feed)
        url = tab.get("url", "")
        if "weibo.com" in url and "/compose" not in url and "/status" not in url:
            pass
        else:
            cdp_send(ws, "Page.navigate", {"url": "https://weibo.com/"})
            time.sleep(4)

        focus_js = f"""
        (() => {{
            const sels = [
                'textarea[placeholder*="新鲜事"]',
                'textarea[placeholder*="有什么新鲜事"]',
                'textarea.Form_textarea',
                'textarea',
                '[contenteditable="true"]'
            ];
            for (const s of sels) {{
                const el = document.querySelector(s);
                if (el && el.offsetParent !== null) {{
                    el.focus();
                    el.click();
                    return "OK:" + s;
                }}
            }}
            return "ERROR:NO_COMPOSER";
        }})()
        """
        r = js_eval(ws, focus_js)
        print("Focus:", r)
        if "ERROR" in str(r):
            cdp_send(ws, "Page.navigate", {"url": "https://weibo.com/"})
            time.sleep(4)
            r = js_eval(ws, focus_js)
            print("Focus retry:", r)
            if "ERROR" in str(r):
                sys.exit(1)

        time.sleep(0.2)
        # Clear
        cdp_send(ws, "Input.dispatchKeyEvent", {"type": "keyDown", "key": "a", "code": "KeyA", "modifiers": 2})
        cdp_send(ws, "Input.dispatchKeyEvent", {"type": "keyUp", "key": "a", "code": "KeyA", "modifiers": 2})
        cdp_send(ws, "Input.dispatchKeyEvent", {"type": "keyDown", "key": "Backspace", "code": "Backspace"})
        cdp_send(ws, "Input.dispatchKeyEvent", {"type": "keyUp", "key": "Backspace", "code": "Backspace"})
        time.sleep(0.2)
        cdp_send(ws, "Input.insertText", {"text": text})
        for _ in range(15):
            time.sleep(0.3)
            ok = js_eval(
                ws,
                """(() => {
                    const sels = ['[node-type="publishBtn"]','button','a','div[role="button"]'];
                    for (const sel of sels) {
                        for (const n of document.querySelectorAll(sel)) {
                            if (!n.offsetParent) continue;
                            const t = (n.textContent || '').replace(/\\s+/g,'').trim();
                            if (t === '发布' && !n.disabled && n.getAttribute('aria-disabled') !== 'true') return 'READY';
                        }
                    }
                    return 'WAIT';
                })()""",
            )
            if ok == "READY":
                break

        click_js = """
        (() => {
            function visible(el) {
                return el && el.offsetParent !== null && getComputedStyle(el).visibility !== 'hidden';
            }
            function textOf(el) {
                return (el.textContent || '').replace(/\\s+/g, '').trim();
            }
            const sels = [
                '[node-type="publishBtn"]',
                'a[action-type="publish"]',
                'div[role="button"][aria-label*="发布"]',
                '[aria-label="发布"]',
                'button'
            ];
            const primary = [];
            const secondary = [];
            for (const sel of sels) {
                for (const n of document.querySelectorAll(sel)) {
                    if (!visible(n)) continue;
                    const t = textOf(n);
                    if (t === '发布' || t.endsWith('发布')) primary.push(n);
                    else if (/^发送$|^发博$/.test(t)) secondary.push(n);
                }
            }
            const pick = primary[0] || secondary[0];
            if (pick) {
                pick.click();
                return 'CLICK:' + textOf(pick);
            }
            for (const n of document.querySelectorAll('a, button, div[role="button"], span')) {
                if (!visible(n)) continue;
                const t = textOf(n);
                if (t === '发布' || t.endsWith('发布')) {
                    n.click();
                    return 'CLICK:发布-variant';
                }
            }
            return 'ERROR:NO_PUBLISH_BTN';
        })()
        """
        out = js_eval(ws, click_js)
        print("Ops:", out)
        time.sleep(2)
        if "ERROR" in str(out):
            sys.exit(1)
        print("Weibo Ops flow completed.")
    finally:
        ws.close()


if __name__ == "__main__":
    main()
