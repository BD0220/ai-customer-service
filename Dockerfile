# AI 智能客服工单系统 - Docker 镜像
# 使用官方 Python 3.11 精简镜像作为基础
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量，防止 Python 生成 .pyc 文件，并确保日志实时输出
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 先复制依赖文件，利用 Docker 缓存层加速构建
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目所有文件到容器中
COPY . .

# 暴露端口：
#   8000 - FastAPI 后端服务
#   7860 - Gradio 前端界面
EXPOSE 8000 7860

# 容器启动时同时运行 FastAPI 和 Gradio
# 使用 sh -c 让两个进程并行运行
CMD ["sh", "-c", "uvicorn api_server:app --host 0.0.0.0 --port 8000 & python ui.py"]
