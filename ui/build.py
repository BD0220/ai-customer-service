"""界面组装：知识库加载、页面切换、统计视图、Blocks 布局与事件绑定。"""

import os

import gradio as gr

from .handlers_chat import respond, poll_user_chat
from .handlers_tickets import refresh_tickets, mark_processing, mark_done
from .handlers_agent import (
    refresh_agent_sessions,
    select_session,
    poll_agent_workbench,
    send_agent_reply,
    switch_session_mode,
)

# ========== 知识库 ==========
KB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge_base")


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


# ========== 页面切换 ==========
def show_page(page_name):
    return (
        gr.update(visible=(page_name == "chat")),
        gr.update(visible=(page_name == "tickets")),
        gr.update(visible=(page_name == "agent")),
        gr.update(visible=(page_name == "knowledge")),
        gr.update(visible=(page_name == "stats")),
        gr.update(variant="primary" if page_name == "chat" else "secondary"),
        gr.update(variant="primary" if page_name == "tickets" else "secondary"),
        gr.update(variant="primary" if page_name == "agent" else "secondary"),
        gr.update(variant="primary" if page_name == "knowledge" else "secondary"),
        gr.update(variant="primary" if page_name == "stats" else "secondary"),
    )


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


def build_demo():
    """构建完整的 Gradio Blocks（布局 + 事件绑定）。"""
    with gr.Blocks(title="AI 智能客服 Agent 系统 v3.0") as demo:

        with gr.Row(elem_id="main-row", equal_height=False):

            # ===== 左侧边栏 =====
            with gr.Column(scale=0, min_width=240, elem_id="sidebar"):
                gr.HTML("""
                    <div class="sidebar-logo">
                        <div class="logo-icon">🤖</div>
                        <div>
                            <div class="logo-text">AI 客服 Agent</div>
                            <div class="logo-sub">v3.0 · ReAct + RAG + 接管</div>
                        </div>
                    </div>
                    <div class="nav-label">工作台</div>
                """)

                btn_chat = gr.Button("💬  客服对话", variant="primary", size="lg")
                btn_tickets = gr.Button("🎫  工单管理", variant="secondary", size="lg")
                btn_agent = gr.Button("🧑‍💼  人工工作台", variant="secondary", size="lg")

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
                    mode_md = gr.Markdown("", show_label=False)  # 人工接管提示条
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

                # --- 人工坐席工作台页 ---
                with gr.Column(visible=False, elem_classes=["page-body"]) as page_agent:
                    workbench_sid = gr.State("")      # 当前点选的会话
                    sessions_cache = gr.State([])     # 会话列表缓存（点选时按行号取 sid）
                    gr.Markdown(
                        "🧑‍💼 **人工坐席工作台** — 点选左侧会话查看对话，直接回复用户；"
                        "处理完点「交还 AI」或「关闭会话」。被接管的会话中 AI 自动暂停应答。"
                    )
                    with gr.Row():
                        with gr.Column(scale=1):
                            agent_sessions = gr.Dataframe(
                                headers=["会话 ID", "模式", "未结工单", "最后消息", "更新时间"],
                                datatype=["str", "str", "number", "str", "str"],
                                interactive=False,
                                wrap=True,
                                row_count=12,
                                show_label=False,
                            )
                            btn_ag_refresh = gr.Button("🔄 刷新列表", size="sm")
                        with gr.Column(scale=2):
                            agent_mode_md = gr.Markdown("（左侧点选一个会话开始处理）")
                            agent_chat = gr.HTML(
                                '<div style="color:#94a3b8;padding:30px;text-align:center;">'
                                '（尚未选择会话）</div>'
                            )
                            agent_reply_box = gr.Textbox(
                                placeholder="以人工客服身份回复用户……",
                                label="坐席回复",
                                lines=2,
                                max_lines=4,
                            )
                            with gr.Row():
                                btn_ag_send = gr.Button("发送回复 🚀", variant="primary", scale=2)
                                btn_ag_handback = gr.Button("交还 AI 🤖", variant="secondary", scale=1)
                                btn_ag_resolve = gr.Button("关闭会话 ✅", variant="secondary", scale=1)
                            agent_status = gr.Markdown("")

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
            outputs=[page_chat, page_tickets, page_agent, page_kb, page_stats,
                     btn_chat, btn_tickets, btn_agent, btn_kb, btn_stats],
        )
        btn_tickets.click(
            lambda: show_page("tickets"),
            outputs=[page_chat, page_tickets, page_agent, page_kb, page_stats,
                     btn_chat, btn_tickets, btn_agent, btn_kb, btn_stats],
        ).then(
            lambda: refresh_tickets()[:2],
            outputs=[ticket_table, stats_md],
        )
        btn_agent.click(
            lambda: show_page("agent"),
            outputs=[page_chat, page_tickets, page_agent, page_kb, page_stats,
                     btn_chat, btn_tickets, btn_agent, btn_kb, btn_stats],
        ).then(
            lambda: refresh_agent_sessions(),
            outputs=[agent_sessions, sessions_cache],
        )
        btn_kb.click(
            lambda: show_page("knowledge"),
            outputs=[page_chat, page_tickets, page_agent, page_kb, page_stats,
                     btn_chat, btn_tickets, btn_agent, btn_kb, btn_stats],
        )
        btn_stats.click(
            lambda: show_page("stats"),
            outputs=[page_chat, page_tickets, page_agent, page_kb, page_stats,
                     btn_chat, btn_tickets, btn_agent, btn_kb, btn_stats],
        ).then(
            lambda: build_stats_view(),
            outputs=[stats_html],
        )

        # 聊天（输出多了 mode_md：接管提示条）
        send_btn.click(
            respond,
            inputs=[msg_input, chatbot, session_state],
            outputs=[chatbot, session_state, msg_input, mode_md],
        )
        msg_input.submit(
            respond,
            inputs=[msg_input, chatbot, session_state],
            outputs=[chatbot, session_state, msg_input, mode_md],
        )
        reset_btn.click(
            lambda: ([], "", "", ""),
            outputs=[chatbot, session_state, msg_input, mode_md],
        )

        # 用户侧轮询：人工接管期间刷出坐席回复（AI 模式下不覆写气泡）
        user_timer = gr.Timer(2.5)
        user_timer.tick(
            poll_user_chat,
            inputs=[chatbot, session_state],
            outputs=[chatbot, mode_md],
        )

        # 人工工作台
        agent_sessions.select(
            select_session,
            inputs=[sessions_cache],
            outputs=[workbench_sid, agent_mode_md, agent_chat],
        )
        btn_ag_refresh.click(
            lambda: refresh_agent_sessions(),
            outputs=[agent_sessions, sessions_cache],
        )
        btn_ag_send.click(
            send_agent_reply,
            inputs=[agent_reply_box, workbench_sid, sessions_cache],
            outputs=[agent_sessions, sessions_cache, agent_status, agent_chat, agent_reply_box],
        )
        btn_ag_handback.click(
            lambda sid, cache: switch_session_mode("ai", sid, cache),
            inputs=[workbench_sid, sessions_cache],
            outputs=[agent_sessions, sessions_cache, agent_status, agent_mode_md],
        )
        btn_ag_resolve.click(
            lambda sid, cache: switch_session_mode("closed", sid, cache),
            inputs=[workbench_sid, sessions_cache],
            outputs=[agent_sessions, sessions_cache, agent_status, agent_mode_md],
        )
        # 工作台轮询：列表和当前对话区自动刷新（坐席不用手点刷新）
        agent_timer = gr.Timer(3)
        agent_timer.tick(
            poll_agent_workbench,
            inputs=[workbench_sid, sessions_cache],
            outputs=[agent_sessions, sessions_cache, agent_mode_md, agent_chat],
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

    return demo
