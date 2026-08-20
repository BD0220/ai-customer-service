"""
Gradio 前端界面 v2.1 — 侧边栏布局
与 GitHub Pages 在线 Demo (index.html) 风格一致：
左侧深色侧边栏导航 + 右侧内容区，4 个模块：对话/工单/知识库/统计。
"""

import os
import gradio as gr
from customer_service_agent import chat
from db import get_all_tickets, update_ticket_status, get_ticket_stats

# ========== 知识库 ==========
KB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base")


def load_kb_docs():
    docs = []
    if os.path.isdir(KB_DIR):
        for fname in sorted(os.listdir(KB_DIR)):
            if fname.endswith(".md"):
                fpath = os.path.join(KB_DIR, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                docs.append((fname.replace(".md", ""), content))
    return docs


KB_DOCS = load_kb_docs()


def get_kb_titles():
    return [d[0] for d in KB_DOCS]


def get_kb_content(title):
    for t, content in KB_DOCS:
        if t == title:
            return content
    return ""


# ========== 对话处理 ==========
def respond(message, history, session_id):
    if not message or not message.strip():
        yield history, session_id, ""
        return

    history = history + [[message, ""]]
    yield history, session_id, ""

    result = chat(message.strip(), session_id=session_id or None)
    session_id = result["session_id"]
    reply = result["reply"]

    if result.get("tool_trace"):
        trace_text = "\n\n---\n🔧 **Agent 工具调用过程：**\n"
        for t in result["tool_trace"]:
            args_str = ", ".join(f"{k}={v}" for k, v in t["arguments"].items())
            trace_text += f"- 第{t['round']}轮：`{t['tool']}({args_str})`\n"
        reply += trace_text

    if result["need_human"] and result.get("ticket_id"):
        p = "🔴 紧急" if result["priority"] == "urgent" else "🟡 普通"
        reply += f"\n\n🎫 **工单号：** #{result['ticket_id']} | **级别：** {p}"

    history[-1][1] = reply
    yield history, session_id, ""


# ========== 工单 ==========
def refresh_tickets():
    tickets = get_all_tickets()
    stats = get_ticket_stats()

    rows = []
    for t in tickets:
        sm = {"pending": "⏳ 待处理", "processing": "🔄 处理中", "done": "✅ 已完成"}
        pm = {"normal": "🟡 普通", "urgent": "🔴 紧急"}
        rows.append([
            t["id"],
            t["summary"][:80] + ("..." if len(t["summary"]) > 80 else ""),
            pm.get(t["priority"], t["priority"]),
            sm.get(t["status"], t["status"]),
            (t.get("session_id") or "-")[:16],
            t["created_at"],
        ])

    stats_text = (
        f"📊 **工单统计：** 总计 {stats['total']} | "
        f"⏳ 待处理 {stats['pending']} | "
        f"🔄 处理中 {stats['processing']} | "
        f"✅ 已完成 {stats['done']} | "
        f"🔴 紧急 {stats['urgent']}"
    )
    return rows, stats_text, stats


def mark_processing(tid_str):
    if not tid_str:
        r, s, _ = refresh_tickets()
        return r, s, "⚠️ 请先输入工单号"
    try:
        tid = int(tid_str)
    except ValueError:
        r, s, _ = refresh_tickets()
        return r, s, "⚠️ 工单号必须是数字"
    ok = update_ticket_status(tid, "processing")
    msg = f"✅ 工单 #{tid} → 处理中" if ok else f"❌ 工单 #{tid} 不存在"
    r, s, _ = refresh_tickets()
    return r, s, msg


def mark_done(tid_str):
    if not tid_str:
        r, s, _ = refresh_tickets()
        return r, s, "⚠️ 请先输入工单号"
    try:
        tid = int(tid_str)
    except ValueError:
        r, s, _ = refresh_tickets()
        return r, s, "⚠️ 工单号必须是数字"
    ok = update_ticket_status(tid, "done")
    msg = f"✅ 工单 #{tid} → 已完成" if ok else f"❌ 工单 #{tid} 不存在"
    r, s, _ = refresh_tickets()
    return r, s, msg


# ========== 页面切换 ==========
def show_page(page_name):
    return (
        gr.update(visible=(page_name == "chat")),
        gr.update(visible=(page_name == "tickets")),
        gr.update(visible=(page_name == "knowledge")),
        gr.update(visible=(page_name == "stats")),
        gr.update(variant="primary" if page_name == "chat" else "secondary"),
        gr.update(variant="primary" if page_name == "tickets" else "secondary"),
        gr.update(variant="primary" if page_name == "knowledge" else "secondary"),
        gr.update(variant="primary" if page_name == "stats" else "secondary"),
    )


# ========== 自定义 CSS ==========
CSS = """
/* 全局 */
.gradio-container { max-width: 100% !important; padding: 0 !important; }
footer {display: none !important;}
#main-row { gap: 0 !important; }

/* 侧边栏 */
#sidebar {
  background: #0f172a !important;
  min-height: 100vh !important;
  padding: 0 !important;
  border-radius: 0 !important;
  max-width: 240px !important;
  min-width: 240px !important;
}
#sidebar .gr-column { padding: 0 !important; gap: 0 !important; }

.sidebar-logo {
  padding: 20px;
  border-bottom: 1px solid #1e293b;
  display: flex;
  align-items: center;
  gap: 10px;
}
.sidebar-logo .logo-icon {
  width: 36px; height: 36px;
  background: linear-gradient(135deg, #f97316, #fb923c);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
}
.sidebar-logo .logo-text {
  font-size: 15px; font-weight: 700; color: #f8fafc;
}
.sidebar-logo .logo-sub {
  font-size: 11px; color: #64748b; font-weight: 400;
}

.nav-label {
  font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.05em;
  color: #475569; padding: 16px 20px 6px;
}

#sidebar button {
  justify-content: flex-start !important;
  text-align: left !important;
  padding: 10px 20px !important;
  margin: 0 10px !important;
  border-radius: 8px !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  border: none !important;
  background: transparent !important;
  color: #94a3b8 !important;
  width: calc(100% - 20px) !important;
}
#sidebar button:hover {
  background: #1e293b !important;
  color: #e2e8f0 !important;
}

.sidebar-footer {
  padding: 14px 20px;
  border-top: 1px solid #1e293b;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: auto;
}
.sidebar-avatar {
  width: 32px; height: 32px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 600; color: #fff;
}
.sidebar-user { font-size: 13px; font-weight: 600; color: #e2e8f0; }
.sidebar-role { font-size: 11px; color: #64748b; }

/* 右侧内容区 */
#content-area {
  background: #f1f5f9 !important;
  padding: 0 !important;
}

/* 顶部栏 */
.top-bar {
  height: 60px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
}
.top-bar h2 { font-size: 18px; font-weight: 700; margin: 0; color: #0f172a; }
.status-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 12px; background: #ecfdf5; color: #065f46;
  border-radius: 20px; font-size: 12px; font-weight: 600;
}

.page-body { padding: 24px 28px 40px; }

/* 聊天卡片 */
.chat-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  overflow: hidden;
}
.chat-header {
  padding: 14px 20px;
  border-bottom: 1px solid #e2e8f0;
  font-size: 15px; font-weight: 600;
  display: flex; align-items: center; gap: 10px;
}
[data-testid="chatbot"] {
  border: none !important;
  border-radius: 0 !important;
  background: #f8fafc !important;
}
[data-testid="chatbot"] .message.bot {
  background: #fff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 12px !important;
  border-top-left-radius: 4px !important;
}
[data-testid="chatbot"] .message.user {
  background: #f97316 !important;
  color: #fff !important;
  border-radius: 12px !important;
  border-top-right-radius: 4px !important;
}

/* 输入区 */
.input-area { padding: 16px 20px; background: #fff; border-top: 1px solid #e2e8f0; }
.input-area textarea {
  border-radius: 10px !important;
  border: 1.5px solid #e2e8f0 !important;
}
.input-area textarea:focus {
  border-color: #f97316 !important;
  box-shadow: 0 0 0 3px rgba(249,115,22,0.1) !important;
}

/* 按钮统一样式 */
.gr-button-primary {
  background: #f97316 !important;
  border: none !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
}
.gr-button-primary:hover { background: #ea580c !important; }
.gr-button-secondary {
  border-radius: 10px !important;
  border: 1px solid #e2e8f0 !important;
  background: #f8fafc !important;
}

/* 统计卡片 */
.stat-card {
  background: #fff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 10px !important;
  padding: 18px 20px !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
}
.stat-card .label { font-size: 13px; color: #64748b; }
.stat-card .value { font-size: 28px; font-weight: 800; color: #0f172a; }

/* 表格 */
.gr-dataframe {
  border-radius: 10px !important;
  border: 1px solid #e2e8f0 !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
}
.gr-dataframe th {
  background: #f8fafc !important;
  font-weight: 600 !important;
  color: #475569 !important;
}

/* 知识库 */
.kb-textbox textarea {
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif !important;
  font-size: 14px !important;
  line-height: 1.8 !important;
}

/* 移动端隐藏侧边栏 */
@media (max-width: 768px) {
  #sidebar { display: none !important; }
  #content-area { max-width: 100% !important; }
  .page-body { padding: 16px !important; }
}
"""


def build_stats_view(stats=None):
    """构建统计页内容"""
    if stats is None:
        _, _, stats = refresh_tickets()

    total = stats.get("total", 0)
    pending = stats.get("pending", 0)
    processing = stats.get("processing", 0)
    done = stats.get("done", 0)
    urgent = stats.get("urgent", 0)

    md = f"""
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:20px;">
  <div class="stat-card">
    <div class="label">总工单</div>
    <div class="value" style="color:#f97316;">{total}</div>
  </div>
  <div class="stat-card">
    <div class="label">待处理</div>
    <div class="value">{pending}</div>
  </div>
  <div class="stat-card">
    <div class="label">处理中</div>
    <div class="value" style="color:#3b82f6;">{processing}</div>
  </div>
  <div class="stat-card">
    <div class="label">紧急工单</div>
    <div class="value" style="color:#ef4444;">{urgent}</div>
  </div>
</div>

<div class="stat-card" style="margin-bottom:16px;">
  <div style="font-size:15px;font-weight:700;margin-bottom:12px;">📊 工单状态分布</div>
  <div style="display:flex;gap:24px;align-items:center;">
    <div style="text-align:center;">
      <div style="font-size:32px;font-weight:800;color:#f59e0b;">{pending}</div>
      <div style="font-size:12px;color:#64748b;">⏳ 待处理</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:32px;font-weight:800;color:#3b82f6;">{processing}</div>
      <div style="font-size:12px;color:#64748b;">🔄 处理中</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:32px;font-weight:800;color:#10b981;">{done}</div>
      <div style="font-size:12px;color:#64748b;">✅ 已完成</div>
    </div>
  </div>
</div>

<div class="stat-card">
  <div style="font-size:15px;font-weight:700;margin-bottom:12px;">🔧 Agent 工具集</div>
  <div style="font-size:13px;color:#475569;line-height:2;">
    <code style="background:#f0fdfa;color:#0f766e;padding:2px 8px;border-radius:4px;font-weight:600;">query_order</code> &nbsp;查询订单（按单号或列出全部）<br>
    <code style="background:#f0fdfa;color:#0f766e;padding:2px 8px;border-radius:4px;font-weight:600;">query_logistics</code> &nbsp;查询物流轨迹<br>
    <code style="background:#f0fdfa;color:#0f766e;padding:2px 8px;border-radius:4px;font-weight:600;">query_product</code> &nbsp;搜索/查询商品<br>
    <code style="background:#f0fdfa;color:#0f766e;padding:2px 8px;border-radius:4px;font-weight:600;">calculate_return</code> &nbsp;估算退货退款<br>
    <code style="background:#f0fdfa;color:#0f766e;padding:2px 8px;border-radius:4px;font-weight:600;">escalate_to_human</code> &nbsp;转人工客服
  </div>
</div>
"""
    return md


# ========== 构建界面 ==========

with gr.Blocks(
    title="AI 智能客服 Agent 系统 v2.0",
    theme=gr.themes.Soft(
        primary_hue="orange",
        neutral_hue="slate",
    ),
    css=CSS,
) as demo:

    with gr.Row(elem_id="main-row", equal_height=False):

        # ===== 左侧边栏 =====
        with gr.Column(scale=0, min_width=240, elem_id="sidebar"):
            gr.HTML("""
                <div class="sidebar-logo">
                    <div class="logo-icon">🤖</div>
                    <div>
                        <div class="logo-text">AI 客服 Agent</div>
                        <div class="logo-sub">v2.0 · ReAct + RAG</div>
                    </div>
                </div>
                <div class="nav-label">工作台</div>
            """)

            btn_chat = gr.Button("💬  客服对话", variant="primary", size="lg")
            btn_tickets = gr.Button("🎫  工单管理", variant="secondary", size="lg")

            gr.HTML('<div class="nav-label">资源</div>')

            btn_kb = gr.Button("📚  知识库", variant="secondary", size="lg")
            btn_stats = gr.Button("📊  数据统计", variant="secondary", size="lg")

            gr.HTML("""
                <div class="sidebar-footer">
                    <div class="sidebar-avatar">客</div>
                    <div>
                        <div class="sidebar-user">客服工作台</div>
                        <div class="sidebar-role">在线 · Agent 模式</div>
                    </div>
                </div>
            """)

        # ===== 右侧内容区 =====
        with gr.Column(scale=1, elem_id="content-area"):
            gr.HTML("""
                <div class="top-bar">
                    <h2 id="page-title">💬 客服对话</h2>
                    <div class="status-pill">● Agent 在线</div>
                </div>
            """)

            session_state = gr.State("")

            # --- 对话页 ---
            with gr.Column(visible=True, elem_classes=["page-body"]) as page_chat:
                with gr.Column(elem_classes=["chat-card"]):
                    gr.HTML("""
                        <div class="chat-header">
                            <span style="font-size:20px;">🤖</span>
                            <div>
                                <div>智能客服助手</div>
                                <div style="font-size:12px;color:#64748b;font-weight:400;">DeepSeek · ReAct Agent · Function Calling + RAG</div>
                            </div>
                        </div>
                    """)
                    chatbot = gr.Chatbot(
                        height=500,
                        bubble_full_width=False,
                        avatar_images=(None, "🤖"),
                        render_markdown=True,
                        placeholder="你好！我是智能客服小助手，可以帮你查订单、查物流、咨询退货政策、了解商品信息。",
                        show_label=False,
                    )
                    with gr.Column(elem_classes=["input-area"]):
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
                            label="💡 试试这些问题",
                        )

            # --- 工单页 ---
            with gr.Column(visible=False, elem_classes=["page-body"]) as page_tickets:
                stats_md = gr.Markdown("")
                ticket_table = gr.Dataframe(
                    headers=["#", "问题摘要", "紧急程度", "状态", "会话 ID", "创建时间"],
                    datatype=["number", "str", "str", "str", "str", "str"],
                    value=lambda: refresh_tickets()[0],
                    interactive=False,
                    wrap=True,
                    row_count=10,
                    show_label=False,
                )
                with gr.Row():
                    tid_input = gr.Textbox(
                        label="输入工单号",
                        placeholder="例如：1",
                        scale=2,
                    )
                    btn_processing = gr.Button("标记处理中 🔄", variant="secondary", scale=1)
                    btn_done = gr.Button("标记已完成 ✅", variant="primary", scale=1)
                    btn_refresh = gr.Button("刷新列表 🔄", scale=1)
                status_msg = gr.Markdown("")

            # --- 知识库页 ---
            with gr.Column(visible=False, elem_classes=["page-body"]) as page_kb:
                gr.Markdown(
                    "📖 **RAG 知识库** — Agent 通过 TF-IDF 检索以下文档，"
                    "自动将相关段落注入 System Prompt。"
                )
                kb_selector = gr.Dropdown(
                    choices=get_kb_titles(),
                    value=get_kb_titles()[0] if KB_DOCS else None,
                    label="选择文档",
                    allow_custom_value=False,
                )
                kb_text = gr.Textbox(
                    value=lambda: get_kb_content(get_kb_titles()[0]) if KB_DOCS else "",
                    label="文档内容",
                    lines=25,
                    max_lines=30,
                    interactive=False,
                    show_label=False,
                    elem_classes=["kb-textbox"],
                )

            # --- 统计页 ---
            with gr.Column(visible=False, elem_classes=["page-body"]) as page_stats:
                stats_html = gr.HTML(build_stats_view())
                btn_stats_refresh = gr.Button("🔄 刷新统计", size="sm")

    # ========== 事件绑定 ==========

    # 页面切换
    btn_chat.click(
        lambda: show_page("chat"),
        outputs=[page_chat, page_tickets, page_kb, page_stats,
                 btn_chat, btn_tickets, btn_kb, btn_stats],
    )
    btn_tickets.click(
        lambda: show_page("tickets"),
        outputs=[page_chat, page_tickets, page_kb, page_stats,
                 btn_chat, btn_tickets, btn_kb, btn_stats],
    ).then(
        lambda: refresh_tickets()[:2],
        outputs=[ticket_table, stats_md],
    )
    btn_kb.click(
        lambda: show_page("knowledge"),
        outputs=[page_chat, page_tickets, page_kb, page_stats,
                 btn_chat, btn_tickets, btn_kb, btn_stats],
    )
    btn_stats.click(
        lambda: show_page("stats"),
        outputs=[page_chat, page_tickets, page_kb, page_stats,
                 btn_chat, btn_tickets, btn_kb, btn_stats],
    ).then(
        lambda: build_stats_view(),
        outputs=[stats_html],
    )

    # 聊天
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

    # 工单
    demo.load(
        lambda: refresh_tickets()[:2],
        outputs=[ticket_table, stats_md],
    )
    btn_refresh.click(
        lambda: refresh_tickets()[:2],
        outputs=[ticket_table, stats_md],
    )
    btn_processing.click(
        mark_processing,
        inputs=tid_input,
        outputs=[ticket_table, stats_md, status_msg],
    )
    btn_done.click(
        mark_done,
        inputs=tid_input,
        outputs=[ticket_table, stats_md, status_msg],
    )

    # 知识库
    kb_selector.change(
        get_kb_content,
        inputs=kb_selector,
        outputs=kb_text,
    )

    # 统计刷新
    btn_stats_refresh.click(
        lambda: build_stats_view(),
        outputs=[stats_html],
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
