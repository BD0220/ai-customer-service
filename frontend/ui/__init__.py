"""Gradio 界面包：样式、各页面回调、布局组装。

结构（职责单一，避免单文件过载）：
- style.py           CSS 与主题常量（挂载方 api_server.py 使用）
- handlers_chat.py   对话页：应答、接管提示、用户侧轮询
- handlers_agent.py  人工坐席工作台：会话列表、坐席回复、接管/交还/关闭
- handlers_tickets.py 工单管理：列表、状态流转
- build.py           知识库加载、页面切换、统计视图、Blocks 组装与事件绑定

对外只暴露三个名字：demo（组装好的 Blocks）、CSS、GRADIO_THEME。
"""

from .style import CSS, GRADIO_THEME
from .build import build_demo

demo = build_demo()

__all__ = ["demo", "CSS", "GRADIO_THEME"]
