from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
ROOT = Path(__file__).resolve().parents[3]
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / 'backend' / '.env', env_file_encoding='utf-8', extra='ignore')
    lm_studio_base_url: str = 'http://127.0.0.1:1234/v1'
    lm_studio_model: str = 'llama-3.2-1b-instruct'
    lm_studio_api_key: str = 'lm-studio'
    embedding_model: str = 'sentence-transformers/all-MiniLM-L6-v2'
    reranker_model: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'
    chroma_dir: Path = ROOT / 'storage/chroma'
    sqlite_path: Path = ROOT / 'storage/app.sqlite3'
    upload_dir: Path = ROOT / 'storage/pdfs'
    max_upload_mb: int = 50
    semantic_similarity_threshold: float = .55
    min_chunk_tokens: int = 80
    max_chunk_tokens: int = 420
    chunk_overlap_sentences: int = 1
    vector_top_k: int = 12
    bm25_top_k: int = 12
    # Maximum Chroma cosine distance accepted as semantically relevant evidence.
    retrieval_max_cosine_distance: float = 0.45
    rrf_k: int = 60
    rerank_top_k: int = 5
    recent_message_limit: int = 12
    summary_every_messages: int = 8
    max_context_tokens: int = 6000
    ocr_enabled: bool = False
@lru_cache
def get_settings():
    s=Settings()
    for name in ('chroma_dir','sqlite_path','upload_dir'):
        p=getattr(s,name)
        if not p.is_absolute(): p=ROOT/p; setattr(s,name,p)
        (p.parent if name=='sqlite_path' else p).mkdir(parents=True,exist_ok=True)
    return s


