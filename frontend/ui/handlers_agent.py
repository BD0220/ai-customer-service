"""人工坐席工作台回调：会话列表、消息渲染、坐席回复、接管/交还/关闭。"""

import html as html_mod

import gradio as gr

from db import (
    list_open_sessions,
    get_session_messages,
    get_session,
    set_session_mode,
)

MODE_LABEL = {"ai": "🤖 AI 应答中", "human": "🧑‍💼 人工接管中"}


def refresh_agent_sessions():
    """刷新坐席会话列表，返回（表格行, 会话缓存）——缓存供点选时按行号取 session_id。"""
    sessions = list_open_sessions()
    rows = []
    for s in sessions:
        rows.append([
            s["session_id"],
            MODE_LABEL.get(s.get("mode"), s.get("mode", "")),
            s.get("open_tickets", 0),
            (s.get("last_message") or "（暂无消息）")[:40],
            s.get("updated_at", ""),
        ])
    return rows, sessions


def render_session_html(sid):
    """把一个会话的完整消息流渲染成 HTML（工作台右侧查看区）。"""
    msgs = get_session_messages(sid)
    if not msgs:
        return '<div style="color:#94a3b8;padding:30px;text-align:center;">（该会话暂无消息）</div>'
    parts = []
    for m in msgs:
        role = m["role"]
        text = html_mod.escape(m["content"]).replace("\n", "<br>")
        time_str = (m.get("created_at") or "")[11:16]
        if role == "user":
            parts.append(
                f'<div style="text-align:right;margin:8px 0;">'
                f'<span style="display:inline-block;max-width:75%;text-align:left;background:#f97316;'
                f'color:#fff;padding:8px 12px;border-radius:12px 4px 12px 12px;font-size:14px;">{text}'
                f'<div style="font-size:10px;opacity:.7;margin-top:3px;">用户 · {time_str}</div></span></div>'
            )
        elif role == "agent":
            parts.append(
                f'<div style="margin:8px 0;">'
                f'<span style="display:inline-block;max-width:75%;background:#ecfdf5;border:1px solid #a7f3d0;'
                f'padding:8px 12px;border-radius:4px 12px 12px 12px;font-size:14px;color:#064e3b;">🧑‍💼 {text}'
                f'<div style="font-size:10px;color:#64748b;margin-top:3px;">人工坐席 · {time_str}</div></span></div>'
            )
        else:  # assistant
            parts.append(
                f'<div style="margin:8px 0;">'
                f'<span style="display:inline-block;max-width:75%;background:#fff;border:1px solid #e2e8f0;'
                f'padding:8px 12px;border-radius:4px 12px 12px 12px;font-size:14px;color:#0f172a;">{text}'
                f'<div style="font-size:10px;color:#64748b;margin-top:3px;">🤖 AI · {time_str}</div></span></div>'
            )
    return "".join(parts)


def select_session(sessions_cache, evt: gr.SelectData):
    """点选会话行 → 加载该会话的消息和模式提示。

    gr.SelectData 只对 .select() 事件有效；取行号去缓存里查 session_id，
    不取单元格值——用户点的是哪一列不可控。
    """
    row = evt.index[0] if evt.index and len(evt.index) > 0 else None
    if row is None or not sessions_cache or row >= len(sessions_cache):
        return "", "", ""
    sid = sessions_cache[row]["session_id"]
    s = get_session(sid) or {}
    mode_md = f"当前模式：{MODE_LABEL.get(s.get('mode'), s.get('mode', '未知'))} · `{sid}`"
    return sid, mode_md, render_session_html(sid)


def poll_agent_workbench(sid, sessions_cache):
    """工作台轮询：坐席列表 + 当前选中会话的对话区自动刷新。

    返回 gr.update() 保持未选会话时不动；sid 存在且模式有效时全量重渲染。
    """
    rows, new_cache = refresh_agent_sessions()
    if not sid:
        return rows, new_cache, gr.update(), gr.update()
    s = get_session(sid)
    if not s:
        return rows, new_cache, "（会话已关闭或不存在）", ""
    mode_md = f"当前模式：{MODE_LABEL.get(s.get('mode'), s.get('mode', '未知'))} · `{sid}`"
    return rows, new_cache, mode_md, render_session_html(sid)


def send_agent_reply(reply_text, sid, sessions_cache):
    """人工坐席回复：落库 role="agent"，用户侧轮询即可见。"""
    from db import save_conversation, touch_session

    if not sid:
        rows, cache = refresh_agent_sessions()
        return rows, cache, "⚠️ 请先在左侧点选一个会话", gr.update(), ""
    content = (reply_text or "").strip()
    if not content:
        rows, cache = refresh_agent_sessions()
        return rows, cache, "⚠️ 回复内容不能为空", gr.update(), ""
    save_conversation(sid, "agent", content)
    touch_session(sid)
    rows, cache = refresh_agent_sessions()
    return rows, cache, "✅ 已发送", render_session_html(sid), ""


def switch_session_mode(mode, sid, sessions_cache):
    """接管 / 交还 AI / 关闭会话。"""
    if not sid:
        rows, cache = refresh_agent_sessions()
        return rows, cache, "⚠️ 请先点选一个会话", gr.update()
    ok = set_session_mode(sid, mode)
    rows, cache = refresh_agent_sessions()
    if not ok:
        return rows, cache, "⚠️ 切换失败（会话不存在或模式无效）", gr.update()
    label = {"human": "🧑‍💼 已接管，AI 已暂停", "ai": "🤖 已交还 AI 应答",
             "closed": "✅ 会话已关闭"}[mode]
    s = get_session(sid) or {}
    mode_md = f"当前模式：{MODE_LABEL.get(s.get('mode'), mode)} · `{sid}`"
    if mode == "closed":
        return rows, cache, label, ""  # 关闭后清掉查看区
    return rows, cache, label, mode_md
