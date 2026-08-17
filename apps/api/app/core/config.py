"""全局配置：从 apps/api/.env 读取，全部支持环境变量覆盖。"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # apps/api/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # LLM
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"

    # Web 搜索
    tavily_api_key: str = ""

    # 本地模型（向量/精排）
    hf_home: str = "../../models"
    hf_endpoint: str = "https://hf-mirror.com"
    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"

    # 数据库
    database_url: str = "sqlite+aiosqlite:///./kra.db"

    # 向量库（Qdrant）
    qdrant_url: str = "http://localhost:6333"

    # 知识库检索相关度阈值：低于此值的片段视为无关（输出"未找到相关信息"）
    kb_min_score: float = 0.45

    # PDF 智能解析（P1：类型分流 + 版面还原 + 图片 OCR + 页标记）
    pdf_ocr_enabled: bool = True       # false 回退 pypdf 纯文本提取
    pdf_ocr_min_chars: int = 50        # 页文本充足阈值（低于则整页 OCR）
    pdf_margin_top: float = 0.05       # 页眉剔除区（页高 5% 内）
    pdf_margin_bottom: float = 0.95    # 页脚剔除区（页高 95% 以下）

    # 上传限制
    max_upload_mb: int = 100           # 单文件上传上限（MB）

    # VLM 图表多模态理解（OpenAI 兼容，mimo-v2.5；Key 留空自动关闭）
    vlm_api_key: str = ""
    vlm_base_url: str = "https://api.xiaomimimo.com/v1"
    vlm_model: str = "mimo-v2.5"

    @property
    def vlm_enabled(self) -> bool:
        return bool(self.vlm_api_key.strip())
    # 混合检索：稀疏词法权重显著性阈值（宽松兜底档，HYBRID_SEARCH=true 时生效）
    kb_sparse_min_weight: float = 0.5
    # 宽松兜底档 dense 下限（sparse 独有命中补算）
    kb_relax_min_score: float = 0.35
    # 混合检索开关（bge-m3 dense+sparse 双路 RRF）；false 回退纯 dense
    hybrid_search: bool = True
    # 查询增强：提问前 LLM 改写+关键词扩展（false 回退原问题直接检索）
    query_processing: bool = True
    # 重排：RRF 融合后 bge-reranker-v2-m3 模型精排（false 仅 RRF 排名）
    rerank_enabled: bool = True

    # 服务
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173"

    @property
    def models_dir(self) -> Path:
        return (BASE_DIR / self.hf_home).resolve()

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_enabled(self) -> bool:
        return bool(self.deepseek_api_key.strip())

    @property
    def tavily_enabled(self) -> bool:
        return bool(self.tavily_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
