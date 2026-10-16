"""客服对话页回调：接管提示、消息应答、用户侧轮询。"""

import gradio as gr

from customer_service_agent import chat
from db import get_session, get_session_messages


def get_mode_banner(sid):
    """用户侧顶部的应答方提示条文本（空串 = 不显示）。"""
    if not sid:
        return ""
    s = get_session(sid)
    if s and s.get("mode") == "human":
        return "🧑‍💼 **人工客服正在为您服务**，AI 已暂停应答。"
    return ""


def respond(message, history, session_id):
    """发送一条用户消息，驱动 Agent 应答并渲染到气泡。

    人工接管期间（human_handling）Agent 闭嘴：撤掉空气泡，
    消息由后端落库转达坐席工作台，用户侧靠轮询刷出坐席回复。
    """
    if not message or not message.strip():
        yield history, session_id, "", get_mode_banner(session_id)
        return

    # Gradio 6.x 中 messages 已是唯一消息格式，无需传 type；
    # respond() 使用的 [{"role", "content"}] 结构即为其标准输入。
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": ""},
    ]
    yield history, session_id, "", get_mode_banner(session_id)

    result = chat(message.strip(), session_id=session_id or None)
    session_id = result["session_id"]

    if result.get("human_handling"):
        history = history[:-1]
        yield history, session_id, "", get_mode_banner(session_id)
        return

    reply = result["reply"]

    if result.get("tool_trace"):
        trace_text = "\n\n---\n🔧 **Agent 工具调用过程：**\n"
        for t in result["tool_trace"]:
            args_str = ", ".join(f"{k}={v}" for k, v in t.get("arguments", {}).items())
            trace_text += f"- 第{t.get('round', '-')}轮：`{t['tool']}({args_str})`\n"
        reply += trace_text

    if result["need_human"] and result.get("ticket_id"):
        p = "🔴 紧急" if result["priority"] == "urgent" else "🟡 普通"
        reply += f"\n\n🎫 **工单号：** #{result['ticket_id']} | **级别：** {p}"

    history[-1]["content"] = reply
    yield history, session_id, "", get_mode_banner(session_id)


def poll_user_chat(history, session_id):
    """用户侧轮询：人工接管期间从数据库刷出坐席的回复。

    只在 human 模式下覆写气泡——AI 应答时界面气泡由 respond() 管理
    （含工具调用轨迹等 UI 专属内容），不能被数据库版本覆盖。
    """
    if not session_id:
        return gr.update(), ""
    s = get_session(session_id)
    if not s or s.get("mode") != "human":
        return gr.update(), get_mode_banner(session_id)

    msgs = get_session_messages(session_id)
    if not msgs:
        return gr.update(), get_mode_banner(session_id)

    rendered = []
    for m in msgs:
        role = m["role"]
        content = m["content"]
        if role == "agent":
            rendered.append({"role": "assistant",
                             "content": f"🧑‍💼 **人工客服**：{content}"})
        else:
            rendered.append({"role": "user" if role == "user" else "assistant",
                             "content": content})
    return rendered, get_mode_banner(session_id)
