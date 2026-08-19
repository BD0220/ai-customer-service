"""
Gradio 前端界面（升级版）
展示 Agent 工具调用过程，支持多轮对话。
"""

import gradio as gr
from customer_service_agent import chat
from db import get_all_tickets, update_ticket_status, get_ticket_stats


def respond(message: str, history: list, session_id: str):
    """
    处理用户消息，支持多轮对话和工具调用展示。
    """
    if not message or not message.strip():
        yield history, session_id, ""
        return

    # 添加用户消息
    history = history + [[message, ""]]
    yield history, session_id, ""

    # 调用 Agent
    result = chat(message.strip(), session_id=session_id or None)
    session_id = result["session_id"]

    # 构建回复，包含工具调用过程
    reply = result["reply"]

    # 如果有工具调用，追加显示调用链路
    if result.get("tool_trace"):
        trace_text = "\n\n---\n🔧 **Agent 工具调用过程：**\n"
        for t in result["tool_trace"]:
            args_str = ", ".join(f"{k}={v}" for k, v in t["arguments"].items())
            trace_text += f"- 第{t['round']}轮：`{t['tool']}({args_str})`\n"
        reply += trace_text

    # 如果转人工了，追加工单信息
    if result["need_human"] and result.get("ticket_id"):
        priority_label = "🔴 紧急" if result["priority"] == "urgent" else "🟡 普通"
        reply += f"\n\n🎫 **工单号：** #{result['ticket_id']} | **级别：** {priority_label}"

    history[-1][1] = reply
    yield history, session_id, ""


def refresh_tickets():
    """刷新工单列表和统计"""
    tickets = get_all_tickets()
    stats = get_ticket_stats()

    rows = []
    for t in tickets:
        status_map = {
            "pending": "⏳ 待处理",
            "processing": "🔄 处理中",
            "done": "✅ 已完成",
        }
        priority_map = {
            "normal": "🟡 普通",
            "urgent": "🔴 紧急",
        }
        rows.append([
            t["id"],
            t["summary"][:80] + ("..." if len(t["summary"]) > 80 else ""),
            priority_map.get(t["priority"], t["priority"]),
            status_map.get(t["status"], t["status"]),
            t.get("session_id", "-")[:16] if t.get("session_id") else "-",
            t["created_at"],
        ])

    stats_text = (
        f"📊 **工单统计：** 总计 {stats['total']} | "
        f"⏳ 待处理 {stats['pending']} | "
        f"🔄 处理中 {stats['processing']} | "
        f"✅ 已完成 {stats['done']} | "
        f"🔴 紧急 {stats['urgent']}"
    )

    return rows, stats_text


def mark_processing(ticket_id_str: str):
    if not ticket_id_str:
        rows, stats = refresh_tickets()
        return rows, stats, "请先输入工单号"
    try:
        tid = int(ticket_id_str)
    except ValueError:
        rows, stats = refresh_tickets()
        return rows, stats, "工单号必须是数字"
    ok = update_ticket_status(tid, "processing")
    msg = f"工单 #{tid} 已标记为处理中 🔄" if ok else f"工单 #{tid} 不存在"
    rows, stats = refresh_tickets()
    return rows, stats, msg


def mark_done(ticket_id_str: str):
    if not ticket_id_str:
        rows, stats = refresh_tickets()
        return rows, stats, "请先输入工单号"
    try:
        tid = int(ticket_id_str)
    except ValueError:
        rows, stats = refresh_tickets()
        return rows, stats, "工单号必须是数字"
    ok = update_ticket_status(tid, "done")
    msg = f"工单 #{tid} 已标记为已完成 ✅" if ok else f"工单 #{tid} 不存在"
    rows, stats = refresh_tickets()
    return rows, stats, msg


# ========== 构建 Gradio 界面 ==========

with gr.Blocks(
    title="AI 智能客服工单系统 v2.0",
    theme=gr.themes.Soft(),
    css="footer {display: none !important;}",
) as demo:

    gr.Markdown("# 🤖 AI 智能客服工单系统")
    gr.Markdown("LLM Agent · Function Calling · RAG · 多轮对话 | 自动解决率目标 70%+")

    # 隐藏的 session 状态
    session_state = gr.State("")

    with gr.Tabs():
        # ---------- 客服对话页 ----------
        with gr.Tab("💬 客服对话"):
            chatbot = gr.Chatbot(
                label="小助手",
                height=500,
                bubble_full_width=False,
                avatar_images=(None, "🤖"),
                render_markdown=True,
            )
            with gr.Row():
                msg_input = gr.Textbox(
                    placeholder="试试问：我的订单到哪了？退货政策是什么？耳机有什么颜色？",
                    show_label=False,
                    scale=8,
                )
                send_btn = gr.Button("发送 🚀", variant="primary", scale=1)

            with gr.Row():
                reset_btn = gr.Button("🔄 新对话", size="sm")

            gr.Examples(
                examples=[
                    "你好，我想查一下我的订单",
                    "订单 ORD20260815001 现在什么状态？",
                    "帮我查下这个订单的物流",
                    "退货需要什么条件？退款多久到账？",
                    "你们有什么耳机？",
                    "我要投诉！商品有质量问题！",
                ],
                inputs=msg_input,
                label="💡 试试这些问题（多轮对话也可以）",
            )

            # 事件绑定
            send_btn.click(
                respond,
                inputs=[msg_input, chatbot, session_state],
                outputs=[chatbot, session_state, msg_input],
            )
            msg_input.submit(
                respond,
                inputs=[msg_input, chatbot, session_state],
                outputs=[chatbot, session_state, msg_input],
            )

            def reset_chat():
                return [], "", ""

            reset_btn.click(reset_chat, outputs=[chatbot, session_state, msg_input])

        # ---------- 工单管理页 ----------
        with gr.Tab("📋 工单管理"):
            stats_md = gr.Markdown("")
            ticket_table = gr.Dataframe(
                headers=["工单号", "问题摘要", "紧急程度", "状态", "会话ID", "创建时间"],
                datatype=["number", "str", "str", "str", "str", "str"],
                value=lambda: refresh_tickets()[0],
                interactive=False,
                wrap=True,
            )

            with gr.Row():
                ticket_id_input = gr.Textbox(
                    label="输入工单号",
                    placeholder="例如：1",
                    scale=2,
                )
                processing_btn = gr.Button("标记为处理中 🔄", variant="secondary", scale=1)
                done_btn = gr.Button("标记为已完成 ✅", variant="primary", scale=1)
                refresh_btn = gr.Button("刷新列表 🔄", scale=1)

            status_msg = gr.Markdown("")

            # 初始化统计
            demo.load(
                lambda: refresh_tickets(),
                outputs=[ticket_table, stats_md],
            )

            refresh_btn.click(
                lambda: refresh_tickets(),
                outputs=[ticket_table, stats_md],
            )
            processing_btn.click(
                mark_processing,
                inputs=ticket_id_input,
                outputs=[ticket_table, stats_md, status_msg],
            )
            done_btn.click(
                mark_done,
                inputs=ticket_id_input,
                outputs=[ticket_table, stats_md, status_msg],
            )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
