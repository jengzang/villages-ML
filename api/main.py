"""
广东省自然村分析系统 FastAPI 主应用
Guangdong Province Natural Village Analysis System - Main FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import API_TITLE, API_DESCRIPTION, API_VERSION
from .character import frequency as char_frequency
from .character import tendency as char_tendency
from .character import embeddings as char_embeddings
from .character import significance as char_significance
from .village import search as village_search
from .village import data as village_data
from .metadata import stats as metadata_stats
from .semantic import category as semantic_category
from .semantic import labels as semantic_labels
from .semantic import composition as semantic_composition
from .clustering import assignments as cluster_assignments
from .spatial import hotspots as spatial_hotspots
from .spatial import integration as spatial_integration
from .ngrams import frequency as ngram_frequency
from .patterns import router as patterns_router
from .regional import aggregates_realtime as regional_aggregates
from .compute import clustering, semantic, features, subset
from .admin import run_ids as admin_run_ids

# 创建FastAPI应用
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS（根据需要调整）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(char_frequency.router, prefix="/api")
app.include_router(char_tendency.router, prefix="/api")
app.include_router(char_embeddings.router, prefix="/api")
app.include_router(char_significance.router, prefix="/api")
app.include_router(village_search.router, prefix="/api")
app.include_router(village_data.router, prefix="/api")
app.include_router(metadata_stats.router, prefix="/api")
app.include_router(semantic_category.router, prefix="/api")
app.include_router(semantic_labels.router, prefix="/api")
app.include_router(semantic_composition.router, prefix="/api")
app.include_router(cluster_assignments.router, prefix="/api")
app.include_router(spatial_hotspots.router, prefix="/api")
app.include_router(spatial_integration.router, prefix="/api")
app.include_router(ngram_frequency.router, prefix="/api")
app.include_router(patterns_router, prefix="/api")
app.include_router(regional_aggregates.router, prefix="/api")

# 注册计算模块路由
app.include_router(clustering.router, prefix="/api")
app.include_router(semantic.router, prefix="/api")
app.include_router(features.router, prefix="/api")
app.include_router(subset.router, prefix="/api")

# 注册管理模块路由
app.include_router(admin_run_ids.router, prefix="/api/admin", tags=["Admin"])


@app.get("/")
def root():
    """
    API根端点
    Root endpoint
    """
    return {
        "message": "广东省自然村分析系统 API",
        "version": API_VERSION,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
def health_check():
    """
    健康检查端点
    Health check endpoint
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
