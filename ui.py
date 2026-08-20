"""
Gradio 前端界面 v2.0
展示 Agent 工具调用过程，支持多轮对话、工单管理、知识库浏览。
风格与 GitHub Pages 在线 Demo 统一。
"""

import os
import gradio as gr
from customer_service_agent import chat
from db import get_all_tickets, update_ticket_status, get_ticket_stats

# ========== 知识库内容（从 knowledge_base/ 目录读取） ==========
KB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base")


def load_kb_docs():
    """加载知识库文档列表"""
    docs = []
    if os.path.isdir(KB_DIR):
        for fname in sorted(os.listdir(KB_DIR)):
            if fname.endswith(".md"):
                fpath = os.path.join(KB_DIR, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                title = fname.replace(".md", "")
                # 提取第一段作为摘要
                lines = content.strip().split("\n")
                desc = next((l for l in lines if l.strip() and not l.startswith("#")), "")[:60]
                docs.append((title, desc, content))
    return docs


KB_DOCS = load_kb_docs()


def get_kb_titles():
    """获取知识库文档标题列表"""
    return [d[0] for d in KB_DOCS]


def get_kb_content(title):
    """根据标题获取文档内容"""
    for t, desc, content in KB_DOCS:
        if t == title:
            return content
    return "请从左侧选择文档"


# ========== 对话处理 ==========
def respond(message: str, history: list, session_id: str):
    """处理用户消息，支持多轮对话和工具调用展示。"""
    if not message or not message.strip():
        yield history, session_id, ""
        return

    history = history + [[message, ""]]
    yield history, session_id, ""

    result = chat(message.strip(), session_id=session_id or None)
    session_id = result["session_id"]
    reply = result["reply"]

    # 追加工具调用链路
    if result.get("tool_trace"):
        trace_text = "\n\n---\n🔧 **Agent 工具调用过程：**\n"
        for t in result["tool_trace"]:
            args_str = ", ".join(f"{k}={v}" for k, v in t["arguments"].items())
            trace_text += f"- 第{t['round']}轮：`{t['tool']}({args_str})`\n"
        reply += trace_text

    # 追加工单信息
    if result["need_human"] and result.get("ticket_id"):
        priority_label = "🔴 紧急" if result["priority"] == "urgent" else "🟡 普通"
        reply += f"\n\n🎫 **工单号：** #{result['ticket_id']} | **级别：** {priority_label}"

    history[-1][1] = reply
    yield history, session_id, ""


# ========== 工单管理 ==========
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
        return rows, stats, "⚠️ 请先输入工单号"
    try:
        tid = int(ticket_id_str)
    except ValueError:
        rows, stats = refresh_tickets()
        return rows, stats, "⚠️ 工单号必须是数字"
    ok = update_ticket_status(tid, "processing")
    msg = f"✅ 工单 #{tid} 已标记为处理中" if ok else f"❌ 工单 #{tid} 不存在"
    rows, stats = refresh_tickets()
    return rows, stats, msg


def mark_done(ticket_id_str: str):
    if not ticket_id_str:
        rows, stats = refresh_tickets()
        return rows, stats, "⚠️ 请先输入工单号"
    try:
        tid = int(ticket_id_str)
    except ValueError:
        rows, stats = refresh_tickets()
        return rows, stats, "⚠️ 工单号必须是数字"
    ok = update_ticket_status(tid, "done")
    msg = f"✅ 工单 #{tid} 已标记为已完成" if ok else f"❌ 工单 #{tid} 不存在"
    rows, stats = refresh_tickets()
    return rows, stats, msg


# ========== 自定义 CSS ==========
CUSTOM_CSS = """
/* 全局 */
.gradio-container {
  max-width: 1100px !important;
  margin: 0 auto !important;
  padding-top: 20px !important;
}
footer {display: none !important;}

/* 标题区域 */
.gr-header {
  text-align: center;
  margin-bottom: 8px;
}
.gr-header h1 {
  font-size: 28px !important;
  font-weight: 800 !important;
  color: #0f172a !important;
  margin-bottom: 4px !important;
}
.gr-header p {
  color: #64748b !important;
  font-size: 14px !important;
}

/* 标签页 */
.tabs {
  border: none !important;
}
.tab-nav {
  border-bottom: 2px solid #e2e8f0 !important;
  gap: 4px !important;
}
button.tab-btn {
  font-size: 15px !important;
  font-weight: 600 !important;
  padding: 10px 20px !important;
  border-bottom: 3px solid transparent !important;
  border-radius: 0 !important;
  color: #64748b !important;
}
button.tab-btn.selected {
  color: #f97316 !important;
  border-bottom-color: #f97316 !important;
}

/* 聊天区 */
.gr-chatbot {
  border-radius: 10px !important;
  border: 1px solid #e2e8f0 !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
  background: #f8fafc !important;
}
[data-testid="chatbot"] .message.bot {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 12px !important;
  border-top-left-radius: 4px !important;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
}
[data-testid="chatbot"] .message.user {
  background: #f97316 !important;
  color: #ffffff !important;
  border-radius: 12px !important;
  border-top-right-radius: 4px !important;
}

/* 输入框 */
.gr-textbox textarea, .gr-textbox input {
  border-radius: 10px !important;
  border: 1.5px solid #e2e8f0 !important;
  font-size: 14px !important;
}
.gr-textbox textarea:focus, .gr-textbox input:focus {
  border-color: #f97316 !important;
  box-shadow: 0 0 0 3px rgba(249,115,22,0.1) !important;
}

/* 按钮 */
.gr-button-primary {
  background: #f97316 !important;
  border: none !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  padding: 10px 20px !important;
}
.gr-button-primary:hover {
  background: #ea580c !important;
}
.gr-button-secondary {
  border-radius: 10px !important;
  border: 1px solid #e2e8f0 !important;
  font-weight: 500 !important;
}

/* 表格 */
.gr-dataframe {
  border-radius: 10px !important;
  border: 1px solid #e2e8f0 !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
  overflow: hidden;
}
.gr-dataframe th {
  background: #f8fafc !important;
  font-weight: 600 !important;
  color: #475569 !important;
  font-size: 13px !important;
}

/* 统计卡片 */
.stats-row {
  display: flex !important;
  gap: 16px !important;
  margin-bottom: 16px !important;
}
.stat-card {
  flex: 1 !important;
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 10px !important;
  padding: 18px 20px !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
}
.stat-card .label {
  font-size: 13px !important;
  color: #64748b !important;
}
.stat-card .value {
  font-size: 28px !important;
  font-weight: 800 !important;
  color: #0f172a !important;
}

/* 知识库 */
.kb-viewer textarea {
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif !important;
  font-size: 14px !important;
  line-height: 1.8 !important;
}

/* Examples */
.gr-examples {
  border-radius: 10px !important;
}
.gr-examples button {
  border-radius: 20px !important;
  font-size: 13px !important;
}
"""

# ========== 构建 Gradio 界面 ==========

with gr.Blocks(
    title="AI 智能客服 Agent 系统 v2.0",
    theme=gr.themes.Soft(
        primary_hue="orange",
        neutral_hue="slate",
        font=[gr.themes.GoogleFont("Noto Sans SC"), "sans-serif"],
    ),
    css=CUSTOM_CSS,
) as demo:

    gr.Markdown(
        "# 🤖 AI 智能客服 Agent 系统\n"
        "LLM Agent · Function Calling · RAG · 多轮对话 | 自动解决率目标 70%+",
        elem_classes=["gr-header"],
    )

    session_state = gr.State("")

    with gr.Tabs():
        # ---------- 客服对话 ----------
        with gr.Tab("💬 客服对话"):
            chatbot = gr.Chatbot(
                label="智能客服助手",
                height=550,
                bubble_full_width=False,
                avatar_images=(None, "🤖"),
                render_markdown=True,
                placeholder="你好！我是智能客服小助手，可以帮你查订单、查物流、咨询退货政策、了解商品信息。",
            )
            with gr.Row():
                msg_input = gr.Textbox(
                    placeholder="试试问：我的订单到哪了？退货政策是什么？耳机有什么颜色？",
                    show_label=False,
                    scale=8,
                    max_lines=3,
                )
                send_btn = gr.Button("发送 🚀", variant="primary", scale=1, min_width=100)

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
            reset_btn.click(
                lambda: ([], "", ""),
                outputs=[chatbot, session_state, msg_input],
            )

        # ---------- 工单管理 ----------
        with gr.Tab("🎫 工单管理"):
            stats_md = gr.Markdown("")
            ticket_table = gr.Dataframe(
                headers=["工单号", "问题摘要", "紧急程度", "状态", "会话ID", "创建时间"],
                datatype=["number", "str", "str", "str", "str", "str"],
                value=lambda: refresh_tickets()[0],
                interactive=False,
                wrap=True,
                row_count=10,
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

        # ---------- 知识库 ----------
        with gr.Tab("📚 知识库"):
            gr.Markdown(
                "📖 RAG 知识库文档 — Agent 通过 TF-IDF 检索以下文档内容，"
                "自动将相关段落注入 System Prompt。"
            )
            with gr.Row():
                kb_selector = gr.Dropdown(
                    choices=get_kb_titles(),
                    value=get_kb_titles()[0] if KB_DOCS else None,
                    label="选择文档",
                    scale=1,
                )
            kb_content = gr.Textbox(
                value=lambda: get_kb_content(get_kb_titles()[0]) if KB_DOCS else "",
                label="文档内容",
                lines=25,
                max_lines=30,
                interactive=False,
                elem_classes=["kb-viewer"],
            )
            kb_selector.change(
                get_kb_content,
                inputs=kb_selector,
                outputs=kb_content,
            )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
