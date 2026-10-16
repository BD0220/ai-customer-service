"""Gradio 界面样式与主题（由 api_server.py 的 mount_gradio_app 使用）。

Gradio 6 起 theme/css 不再从 Blocks() 构造器传入，必须由挂载方传入，
所以这两个常量保持模块级导出，作为样式的单一来源。
"""
import gradio as gr

GRADIO_THEME = gr.themes.Soft(primary_hue="orange", neutral_hue="slate")

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
