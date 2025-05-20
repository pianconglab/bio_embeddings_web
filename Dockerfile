FROM python:3.8-slim

WORKDIR /app

# 复制依赖文件列表
COPY requirements.txt .

# 安装依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

# 复制核心文件
COPY *.py .

# 暴露应用端口
EXPOSE 8080

# 运行应用程序
ENTRYPOINT ["python3", "run.py"]

# 设置健康检查
HEALTHCHECK --interval=30s \
            --timeout=5s \
            --start-period=120s \
            --retries=3 \
            CMD curl --silent --fail http://localhost:8080/health || exit 1
