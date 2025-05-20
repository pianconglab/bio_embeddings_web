import os
import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from bio_embeddings.embed import SeqVecEmbedder
from typing import List
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

# 请求/响应模型
class SeqRequest(BaseModel):
    sequence: str

class SeqResponse(BaseModel):
    result: List[float]

class HealthResponse(BaseModel):
    status: str

# Lifespan 事件管理：启动前加载资源，关闭时清理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 读取环境变量 WORKERS（默认 2）
    workers = int(os.getenv("WORKERS", "2"))
    # 初始化 SeqVecEmbedder 池
    pool = Queue()
    for _ in range(workers):
        pool.put(SeqVecEmbedder())
    # 初始化线程池
    executor = ThreadPoolExecutor(max_workers=workers)

    # 挂载到 app.state，供后续请求使用
    app.state.embedder_pool = pool
    app.state.executor = executor

    yield  # 应用开始接收请求

    # 清理：关闭线程池
    executor.shutdown(wait=True)

# 创建 FastAPI 应用，绑定 lifespan
app = FastAPI(title="Protein Embedding API", lifespan=lifespan)

# 同步阻塞操作，在线程池内运行
def sync_embed(seq: str) -> List[float]:
    embedder = app.state.embedder_pool.get()
    try:
        embedding = embedder.embed(seq)
        reduced = embedder.reduce_per_protein(embedding)
        return reduced.tolist()
    finally:
        app.state.embedder_pool.put(embedder)

# Embed 接口
@app.post("/embed", response_model=SeqResponse)
async def embed_sequence(req: SeqRequest):
    seq = req.sequence.strip().upper()
    if not seq:
        raise HTTPException(status_code=400, detail="sequence 字段不能为空")
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            app.state.executor, sync_embed, seq
        )
        return SeqResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding 失败: {e}")

# 健康检查
@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok")
