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

# 暴露端口：8000 = FastAPI API + Gradio 界面（单端口）
EXPOSE 8000

# 单进程单端口：Gradio 已通过 mount_gradio_app 挂载到 FastAPI
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
