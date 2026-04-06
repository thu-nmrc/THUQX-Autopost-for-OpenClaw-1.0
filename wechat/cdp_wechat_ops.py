#!/usr/bin/env python3
"""
WeChat Official Account — navigate to「内容管理 → 草稿箱 → 新的创作旁的➕ → 写文章」,
fill title / author / body, then save draft only (no 群发).

Flow:
  1) Open admin home (token from current tab)
  2) Click 内容管理 → 草稿箱 → 在「新的创作」区域点击 ➕ → 再选 写文章 (with fallbacks)
  3) If UI path fails, try known cgi-bin URLs for draft list + new editor
  4) Fill title, optional author display name, body (iframe-aware)
  5) Click 保存为草稿 only

Usage:
  python3 cdp_wechat_ops.py "标题" "正文..."
  python3 cdp_wechat_ops.py "标题" "正文" --author "大可舆评"
  python3 cdp_wechat_ops.py "标题" "正文" --nav url-only
  python3 cdp_wechat_ops.py "标题" "正文" --fill-only
"""
from __future__ import annotations

import argparse
import json
import os
import re
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


def extract_token(all_tabs) -> str | None:
    for t in all_tabs:
        m = re.search(r"[\?&]token=(\d+)", t.get("url", ""))
        if m:
            return m.group(1)
    return None


def find_mp_tab(p: int):
    for t in list_tabs(p):
        if t.get("type") == "page" and "mp.weixin.qq.com" in t.get("url", ""):
            return t
    return None


def connect_ws(ws_url: str, p: int):
    return websocket.create_connection(ws_url, timeout=15, origin=f"http://127.0.0.1:{p}")


def cdp_send(ws, method: str, params=None, timeout=25):
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


def collect_frame_ids(tree: dict) -> list[str]:
    out: list[str] = []
    frame = tree.get("frame") or {}
    fid = frame.get("id")
    if fid:
        out.append(fid)
    for child in tree.get("childFrames") or []:
        out.extend(collect_frame_ids(child))
    return out


def create_ctx(ws, frame_id: str) -> int:
    r = cdp_send(
        ws,
        "Page.createIsolatedWorld",
        {
            "frameId": frame_id,
            "worldName": "__openclaw_mp__",
            "grantUniverseAccess": True,
        },
    )
    return int(r["executionContextId"])


def js_eval_ctx(ws, execution_context_id: int, expr: str, timeout=20):
    r = cdp_send(
        ws,
        "Runtime.evaluate",
        {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": False,
            "executionContextId": execution_context_id,
        },
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


def js_eval(ws, expr: str, timeout=20):
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


# --- Navigation: click visible elements whose text matches any of `labels` (first wins) ---
CLICK_BY_LABELS_JS = """
(labels) => {
  const want = labels.map(s => String(s).trim()).filter(Boolean).sort((a, b) => b.length - a.length);
  const nodes = document.querySelectorAll(
    'a,button,span,div,li,p,label,[role="menuitem"],[role="button"],[role="link"],.menu_item,.weui-desktop-menu__link'
  );
  for (const el of nodes) {
    if (!el.offsetParent) continue;
    if (el.disabled || el.getAttribute('aria-disabled') === 'true') continue;
    const raw = (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
    if (! raw || raw.length > 80) continue;
    for (const w of want) {
      if (raw === w || raw.includes(w)) {
        el.click();
        return 'CLICK:' + w + '|' + raw.substring(0, 40);
      }
    }
  }
  return 'MISS:' + want.join(',');
}
"""

# 草稿箱页：点击「新的创作」卡片 → 弹出菜单 → 点「写新文章」
CLICK_NEW_CREATION_CARD_JS = """
(() => {
  // 1) 直接点 weui-desktop-card_new 整张卡片（hover 或 click 弹出面板）
  const card = document.querySelector('.weui-desktop-card_new');
  if (card) {
    // dispatch mouseenter + mouseover so hover-menus appear
    card.dispatchEvent(new MouseEvent('mouseenter', {bubbles: true}));
    card.dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));
    card.click();
    return 'CLICK_CARD:weui-desktop-card_new';
  }
  // 2) fallback: find the add icon
  const icon = document.querySelector('.weui-desktop-card__icon-add, i[class*="icon-add"], i[class*="icon_add"]');
  if (icon) {
    const p = icon.closest('.weui-desktop-card') || icon.parentElement;
    if (p) {
      p.dispatchEvent(new MouseEvent('mouseenter', {bubbles: true}));
      p.click();
    } else {
      icon.click();
    }
    return 'CLICK_ICON:card__icon-add';
  }
  return 'MISS_CARD';
})()
"""

# 从面板提取「写新文章」链接的 href（target=_blank 不能 .click()，需 Page.navigate）
EXTRACT_WRITE_ARTICLE_HREF_JS = """
(() => {
  const panel = document.querySelector('.preview_media_add_panel');
  if (!panel) return '';
  const labels = ['写新文章', '写文章', '新建图文'];
  const links = panel.querySelectorAll('li a');
  for (const a of links) {
    const t = (a.innerText || a.textContent || '').replace(/\\s+/g, '').trim();
    for (const lb of labels) {
      if (t === lb || t.includes(lb)) {
        return a.href || '';
      }
    }
  }
  const first = panel.querySelector('li a');
  if (first) return first.href || '';
  return '';
})()
"""

EDITOR_HINT_JS = """
(() => {
  const path = location.pathname + location.search;
  const hasTitle = !!(
    document.querySelector('#title, input[name="title"], [placeholder*="标题"]') ||
    document.querySelector('textarea') ||
    document.querySelector('.js_main_title')
  );
  const hasEd = !!(
    document.querySelector('.ProseMirror[contenteditable="true"]') ||
    document.querySelector('[contenteditable="true"]') ||
    document.querySelector('iframe') ||
    document.querySelector('.edui-editor-body')
  );
  return JSON.stringify({ path, hasTitle, hasEditorHint: hasEd });
})()
"""


def click_labels(ws, labels: list[str], timeout=12) -> str:
    expr = f"(({CLICK_BY_LABELS_JS}))({json.dumps(labels, ensure_ascii=False)})"
    return str(js_eval(ws, expr, timeout=timeout))


def _navigate_to_editor(ws, url: str) -> bool:
    """Navigate to editor URL, reload for SPA init, wait for ProseMirror."""
    print("  Page.navigate →", url[:120])
    cdp_send(ws, "Page.navigate", {"url": url})
    time.sleep(3)
    cdp_send(ws, "Page.reload", {})
    time.sleep(8)
    # dismiss masks
    js_eval(ws, "(function(){var m=document.querySelectorAll('.menu-pop__mask,.weui-mask');for(var i=0;i<m.length;i++){m[i].style.display='none';}return m.length;})()")
    hint = js_eval(ws, EDITOR_HINT_JS)
    print("  editor hint:", hint)
    try:
        o = json.loads(hint)
        if o.get("hasTitle") and o.get("hasEditorHint"):
            return True
    except Exception:
        pass
    return False


def _click_card_then_write(ws, token: str) -> bool:
    """On a draft-list page, hover 新的创作 card → extract 写新文章 href → navigate."""
    card_r = str(js_eval(ws, CLICK_NEW_CREATION_CARD_JS))
    print("  ➕卡片:", card_r)
    time.sleep(1)

    href = str(js_eval(ws, EXTRACT_WRITE_ARTICLE_HREF_JS)).strip()
    print("  写新文章 href:", href[:120] if href else "(empty)")

    if href and "appmsg" in href:
        if "token=" not in href:
            sep = "&" if "?" in href else "?"
            href += f"{sep}token={token}&lang=zh_CN"
        if _navigate_to_editor(ws, href):
            return True

    editor_url = f"https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit&isNew=1&type=10&token={token}&lang=zh_CN"
    return _navigate_to_editor(ws, editor_url)


def open_editor_ui_path(ws, token: str) -> bool:
    """草稿箱 URL → 新的创作卡片 ➕ → 写新文章"""
    draft_urls = [
        f"https://mp.weixin.qq.com/cgi-bin/appmsg?begin=0&count=10&type=77&action=list_card&token={token}&lang=zh_CN",
        f"https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_list_v2&action=list&begin=0&count=10&type=77&lang=zh_CN&token={token}",
    ]
    for url in draft_urls:
        print("Nav → 草稿箱:", url[:90], "...")
        cdp_send(ws, "Page.navigate", {"url": url})
        time.sleep(4)
        if _click_card_then_write(ws, token):
            return True

    home = f"https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN&token={token}"
    print("Nav → 首页 → 内容管理 → 草稿箱 (click path)")
    cdp_send(ws, "Page.navigate", {"url": home})
    time.sleep(4)
    for labels, wait_s in [
        (["内容管理"], 3),
        (["草稿箱"], 3),
    ]:
        r = click_labels(ws, labels)
        print("  click", labels[0], "→", r)
        time.sleep(wait_s)
    if _click_card_then_write(ws, token):
        return True

    hint = js_eval(ws, EDITOR_HINT_JS)
    try:
        o = json.loads(hint)
        if o.get("hasTitle"):
            return True
    except Exception:
        pass
    return False


def open_editor_url_fallback(ws, token: str) -> bool:
    """Direct URLs when SPA menu clicks miss (backend改版常见)."""
    candidates = [
        f"https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_list&action=list&begin=0&count=10&type=10&token={token}&lang=zh_CN",
        f"https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_list&action=list_begin&begin=0&count=10&type=10&token={token}&lang=zh_CN",
    ]
    for url in candidates:
        print("Try draft list URL:", url[:80], "...")
        cdp_send(ws, "Page.navigate", {"url": url})
        time.sleep(4)
        if _click_card_then_write(ws, token):
            return True

    new_edit_urls = [
        f"https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit&isNew=1&type=10&lang=zh_CN&token={token}",
        f"https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit&action=edit&type=10&isNew=1&lang=zh_CN&token={token}",
    ]
    for url in new_edit_urls:
        print("Try new editor URL:", url[:80], "...")
        cdp_send(ws, "Page.navigate", {"url": url})
        time.sleep(5)
        hint = js_eval(ws, EDITOR_HINT_JS)
        try:
            o = json.loads(hint)
            if o.get("hasTitle"):
                return True
        except Exception:
            pass
    return False


FOCUS_BODY_IFRAME_JS = """
(() => {
    const iframes = document.querySelectorAll('iframe');
    for (const f of iframes) {
        try {
            const doc = f.contentDocument;
            if (!doc) continue;
            const body = doc.body;
            if (body) {
                body.focus();
                const ce = doc.querySelector('[contenteditable="true"]') || body;
                ce.focus();
                ce.click();
                return 'OK_SAME_ORIGIN';
            }
        } catch (e) {}
    }
    return 'ERROR_NO_IFRAME';
})()
"""

FOCUS_BODY_SUBFRAME_JS = """
(() => {
    const body = document.body;
    if (body) {
        body.focus();
        const ce = document.querySelector('[contenteditable="true"]');
        if (ce) { ce.focus(); ce.click(); }
        return 'OK';
    }
    return 'ERROR';
})()
"""

SCROLL_TO_BOTTOM_JS = """
(() => {
    window.scrollTo(0, document.body.scrollHeight);
    var container = document.querySelector('.weui-desktop-layout__main, .js_main_inner, #js_appmsg_editor');
    if (container) container.scrollTop = container.scrollHeight;
    document.documentElement.scrollTop = document.documentElement.scrollHeight;
    return 'SCROLLED:' + document.body.scrollHeight;
})()
"""

SAVE_DRAFT_JS = """
(() => {
    // Direct ID selector first (v2 editor uses #js_submit for 保存为草稿)
    var submit = document.querySelector('#js_submit');
    if (submit) {
        submit.scrollIntoView({ behavior: 'instant', block: 'center' });
        var btn = submit.querySelector('button') || submit;
        btn.click();
        return 'SAVE_ID:js_submit';
    }
    const deny = /群发|公开发布|发布\\s*$|发表\\s*$|定时发送|群发助手/;
    function tryClick(el) {
        const t = (el.textContent || '').replace(/\\s+/g, ' ').trim();
        if (!t || deny.test(t)) return null;
        if (/保存为草稿|^存草稿$|存为草稿|保存草稿/.test(t)) {
            el.scrollIntoView({ behavior: 'instant', block: 'center' });
            el.click();
            return t;
        }
        return null;
    }
    for (const el of document.querySelectorAll('a, button, span, div[role="button"], span[role="button"]')) {
        const hit = tryClick(el);
        if (hit) return 'SAVE:' + hit;
    }
    return 'ERROR:NO_SAVE_DRAFT';
})()
"""

SELECT_AUTHOR_JS_TEMPLATE = """
(authorName) => {
    const name = authorName;
    const selects = document.querySelectorAll('select');
    for (const s of selects) {
        for (let i = 0; i < s.options.length; i++) {
            const o = s.options[i];
            if ((o.text || '').includes(name)) {
                s.selectedIndex = i;
                s.dispatchEvent(new Event('input', { bubbles: true }));
                s.dispatchEvent(new Event('change', { bubbles: true }));
                return 'OK_SELECT:' + o.text;
            }
        }
    }
    for (const el of document.querySelectorAll('[class*="author"], [id*="author"], [placeholder*="作者"]')) {
        if (!el.offsetParent) continue;
        el.click();
    }
    function clickItem() {
        for (const el of document.querySelectorAll('li, div[role="option"], .weui-widget_dropdown__option')) {
            const t = (el.textContent || '').trim();
            if (t.includes(name)) {
                el.click();
                return 'OK_MENU:' + t;
            }
        }
        return 'PARTIAL';
    }
    const r = clickItem();
    if (r !== 'PARTIAL') return r;
    return 'WARN_AUTHOR_MANUAL:' + name;
}
"""


def best_body_frame(ws) -> str | None:
    cdp_send(ws, "Runtime.enable", {})
    tree = cdp_send(ws, "Page.getFrameTree", {})
    ids = collect_frame_ids(tree.get("frameTree", {}))
    best_id = None
    best_ce = -1
    for fid in ids:
        try:
            ctx = create_ctx(ws, fid)
            n = js_eval_ctx(
                ws,
                ctx,
                """(() => document.querySelectorAll('[contenteditable="true"], body').length)()""",
            )
            if isinstance(n, int) and n > best_ce:
                best_ce = n
                best_id = fid
        except Exception:
            continue
    if best_ce < 1:
        return None
    return best_id


def type_into_focused(ws, text: str):
    cdp_send(ws, "Input.dispatchKeyEvent", {"type": "keyDown", "key": "a", "code": "KeyA", "modifiers": 2})
    cdp_send(ws, "Input.dispatchKeyEvent", {"type": "keyUp", "key": "a", "code": "KeyA", "modifiers": 2})
    cdp_send(ws, "Input.dispatchKeyEvent", {"type": "keyDown", "key": "Backspace", "code": "Backspace"})
    cdp_send(ws, "Input.dispatchKeyEvent", {"type": "keyUp", "key": "Backspace", "code": "Backspace"})
    time.sleep(0.12)
    cdp_send(ws, "Input.insertText", {"text": text})


def fill_title_author_body(ws, title: str, body: str, author: str | None):
    # --- Title ---
    fill_title = """
    (() => {
        const sels = [
            'textarea[placeholder*="标题"]', 'textarea',
            '#title', 'input[name="title"]', 'input[placeholder*="标题"]',
            '.editor_title input', '.js_main_title'
        ];
        for (const s of sels) {
            const el = document.querySelector(s);
            if (el && el.offsetParent !== null) {
                el.focus();
                el.click();
                return 'OK:' + s;
            }
        }
        return 'ERROR:NO_TITLE';
    })()
    """
    r = js_eval(ws, fill_title)
    print("Title field:", r)
    if "OK" in str(r):
        type_into_focused(ws, title)

    time.sleep(0.35)

    # --- Author ---
    if author and author.strip():
        auth_name = author.strip()
        fill_author = (
            "(function(name){"
            "  var el = document.querySelector('input#author, input.js_author, input[placeholder*=\"作者\"]');"
            "  if (el && el.offsetParent !== null) {"
            "    el.focus(); el.click(); el.value = '';"
            "    el.dispatchEvent(new Event('input', {bubbles: true}));"
            "    return 'OK_INPUT';"
            "  }"
            "  return 'MISS_INPUT';"
            "})(" + json.dumps(auth_name, ensure_ascii=False) + ")"
        )
        ar = js_eval(ws, fill_author)
        print("Author field:", ar)
        if "OK" in str(ar):
            type_into_focused(ws, auth_name)
        else:
            auth_js = (
                "("
                + SELECT_AUTHOR_JS_TEMPLATE.strip()
                + ")("
                + json.dumps(auth_name, ensure_ascii=False)
                + ")"
            )
            ar2 = js_eval(ws, auth_js)
            print("Author (select fallback):", ar2)
        time.sleep(0.4)

    # --- Body ---
    fill_body = """
    (() => {
        const pm = document.querySelector('.ProseMirror[contenteditable="true"]');
        if (pm) { pm.focus(); pm.click(); return 'OK_PM'; }
        const ce = document.querySelector('[contenteditable="true"]');
        if (ce) { ce.focus(); ce.click(); return 'OK_CE'; }
        return 'MISS_MAIN_CE';
    })()
    """
    r2 = js_eval(ws, fill_body)
    print("Body (ProseMirror/CE):", r2)
    filled = "OK" in str(r2)
    if filled:
        type_into_focused(ws, body)
    if not filled:
        r3 = js_eval(ws, FOCUS_BODY_IFRAME_JS)
        print("Body (iframe):", r3)
        if "OK" in str(r3):
            type_into_focused(ws, body)
            filled = True
    if not filled:
        bf = best_body_frame(ws)
        if bf:
            print("Body via subframe:", bf[:16], "...")
            ctx = create_ctx(ws, bf)
            out = js_eval_ctx(ws, ctx, FOCUS_BODY_SUBFRAME_JS)
            print("Body focus subframe:", out)
            if "OK" in str(out):
                type_into_focused(ws, body)
                filled = True
    if not filled:
        print("WARN: Body may be empty — check editor.", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="WeChat MP: draft box path + save draft")
    ap.add_argument("title")
    ap.add_argument("body")
    ap.add_argument(
        "--author",
        default=os.environ.get("WECHAT_MP_AUTHOR", "大可舆评"),
        help="Author display name in editor (default: 大可舆评 or WECHAT_MP_AUTHOR)",
    )
    ap.add_argument(
        "--nav",
        choices=("auto", "ui", "url"),
        default="auto",
        help="auto: UI then URL fallbacks | ui: clicks only | url: URL fallbacks only",
    )
    ap.add_argument("--fill-only", action="store_true", help="Fill only; do not save draft")
    ap.add_argument("--no-author", action="store_true", help="Skip author picker")
    args = ap.parse_args()

    title = args.title
    body = args.body
    author = "" if args.no_author else (args.author or "")

    p = port()
    tabs = list_tabs(p)
    token = extract_token(tabs)
    tab = find_mp_tab(p)
    if not tab:
        print("ERROR: No mp.weixin.qq.com tab. Open 公众号后台 in CDP Chrome.", file=sys.stderr)
        sys.exit(1)
    if not token:
        print("ERROR: No token= in any open mp URL. Open 后台首页 once.", file=sys.stderr)
        sys.exit(1)

    activate(p, tab["id"])
    time.sleep(0.3)
    ws = connect_ws(tab["webSocketDebuggerUrl"], p)
    try:
        cdp_send(ws, "Page.enable", {})

        ok = False
        if args.nav in ("auto", "ui"):
            ok = open_editor_ui_path(ws, token)
        if not ok and args.nav in ("auto", "url"):
            ok = open_editor_url_fallback(ws, token)

        if not ok:
            print(
                "ERROR: Could not reach article editor. Check login, or run with visible backend and retry.",
                file=sys.stderr,
            )
            sys.exit(1)

        fill_title_author_body(ws, title, body, author)

        time.sleep(0.5)

        if args.fill_only:
            print("WeChat: --fill-only; no save click.")
        else:
            scroll_r = js_eval(ws, SCROLL_TO_BOTTOM_JS)
            print("Scroll to bottom:", scroll_r)
            time.sleep(1)
            save_result = js_eval(ws, SAVE_DRAFT_JS)
            print("Save draft:", save_result)
            if "ERROR" in str(save_result):
                print(
                    "WARN: 未自动点到「保存为草稿」— 请在页面手动保存（脚本不会点群发）。",
                    file=sys.stderr,
                )
        print("WeChat Ops (draft) flow completed.")
    finally:
        ws.close()


if __name__ == "__main__":
    main()
