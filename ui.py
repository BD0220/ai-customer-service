"""
Gradio 前端界面
包含两个标签页：
  - 客服对话：用户与 AI 客服聊天
  - 工单管理：人工客服查看和处理工单
"""

import gradio as gr
from customer_service_agent import chat
from db import get_all_tickets, update_ticket_status


def respond(message: str, history: list):
    """
    处理用户在聊天窗口发送的消息。

    Args:
        message: 用户当前输入的消息
        history: Gradio 自动维护的对话历史 [[user, assistant], ...]

    Yields:
        (history, "") 用于流式更新聊天界面
    """
    if not message or not message.strip():
        yield history, ""
        return

    # 先把用户消息加到历史中，AI 回复先留空
    history = history + [[message, ""]]
    yield history, ""

    # 调用核心客服逻辑
    result = chat(message.strip())
    reply = result["reply"]

    # 如果触发了转人工，在回复后面追加工单信息提示
    if result["need_human"] and result.get("ticket_id"):
        priority_label = "🔴 紧急" if result["priority"] == "urgent" else "🟡 普通"
        reply += f"\n\n（工单号：#{result['ticket_id']}，级别：{priority_label}）"

    # 更新最后一条 AI 回复
    history[-1][1] = reply
    yield history, ""


def refresh_tickets():
    """
    从数据库读取所有工单，格式化为表格展示。

    Returns:
        list[list]：表格数据，每行对应一条工单
    """
    tickets = get_all_tickets()
    rows = []
    for t in tickets:
        # 状态映射为中文标签
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
            t["created_at"],
        ])
    return rows


def mark_processing(ticket_id_str: str):
    """将工单标记为处理中"""
    if not ticket_id_str:
        return refresh_tickets(), "请先输入工单号"
    try:
        tid = int(ticket_id_str)
    except ValueError:
        return refresh_tickets(), "工单号必须是数字"
    ok = update_ticket_status(tid, "processing")
    msg = f"工单 #{tid} 已标记为处理中 🔄" if ok else f"工单 #{tid} 不存在"
    return refresh_tickets(), msg


def mark_done(ticket_id_str: str):
    """将工单标记为已完成"""
    if not ticket_id_str:
        return refresh_tickets(), "请先输入工单号"
    try:
        tid = int(ticket_id_str)
    except ValueError:
        return refresh_tickets(), "工单号必须是数字"
    ok = update_ticket_status(tid, "done")
    msg = f"工单 #{tid} 已标记为已完成 ✅" if ok else f"工单 #{tid} 不存在"
    return refresh_tickets(), msg


# ========== 构建 Gradio 界面 ==========

with gr.Blocks(
    title="AI 智能客服工单系统",
    theme=gr.themes.Soft(),
    css="footer {display: none !important;}",
) as demo:

    gr.Markdown("# 🤖 AI 智能客服工单系统")
    gr.Markdown("AI 自动处理常见问题，复杂问题智能转人工")

    with gr.Tabs():
        # ---------- 标签页 1：客服对话 ----------
        with gr.Tab("💬 客服对话"):
            chatbot = gr.Chatbot(
                label="小助手",
                height=450,
                bubble_full_width=False,
                avatar_images=(None, "🤖"),
            )
            with gr.Row():
                msg_input = gr.Textbox(
                    placeholder="请输入您的问题，例如：我的订单怎么查？",
                    show_label=False,
                    scale=8,
                )
                send_btn = gr.Button("发送 🚀", variant="primary", scale=1)
            gr.Examples(
                examples=[
                    "我的订单什么时候发货？",
                    "帮我查一下物流",
                    "退货政策是什么？",
                    "这件衣服有什么尺码？",
                    "我要退款！商品质量太差了！",
                    "转人工",
                ],
                inputs=msg_input,
                label="试试这些问题 👇",
            )

            # 绑定发送事件（按钮点击 + 回车）
            send_btn.click(
                respond,
                inputs=[msg_input, chatbot],
                outputs=[chatbot, msg_input],
            )
            msg_input.submit(
                respond,
                inputs=[msg_input, chatbot],
                outputs=[chatbot, msg_input],
            )

        # ---------- 标签页 2：工单管理 ----------
        with gr.Tab("📋 工单管理"):
            gr.Markdown("### 待处理工单列表（点击刷新查看最新工单）")

            ticket_table = gr.Dataframe(
                headers=["工单号", "问题摘要", "紧急程度", "状态", "创建时间"],
                datatype=["number", "str", "str", "str", "str"],
                value=refresh_tickets,
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

            # 绑定按钮事件
            refresh_btn.click(
                refresh_tickets,
                outputs=ticket_table,
            )
            processing_btn.click(
                mark_processing,
                inputs=ticket_id_input,
                outputs=[ticket_table, status_msg],
            )
            done_btn.click(
                mark_done,
                inputs=ticket_id_input,
                outputs=[ticket_table, status_msg],
            )

            # 每 5 秒自动刷新一次工单列表
            gr.Markdown("⏱️ 列表每 5 秒自动刷新")


# 启动界面：python ui.py
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
