# AI 智能客服工单系统 v2.0 - Docker 镜像
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 先复制依赖文件，利用 Docker 缓存层
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目所有文件
COPY . .

# 暴露端口：8000=FastAPI, 7860=Gradio
EXPOSE 8000 7860

# 同时启动 FastAPI 和 Gradio
CMD ["sh", "-c", "uvicorn api_server:app --host 0.0.0.0 --port 8000 & python ui.py"]
