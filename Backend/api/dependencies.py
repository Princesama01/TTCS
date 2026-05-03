import threading

from api.pipeline import LegalVectorPipeline
from config import settings

_pipeline = None
_pipeline_lock = threading.Lock()


def get_pipeline() -> LegalVectorPipeline:
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:
                _pipeline = LegalVectorPipeline(storage_path=settings.QDRANT_PATH)
    return _pipeline


async def shutdown_pipeline():
    global _pipeline
    with _pipeline_lock:
        if _pipeline and hasattr(_pipeline, "store") and hasattr(_pipeline.store, "client"):
            try:
                _pipeline.store.client.close()
            except Exception:
                pass
        _pipeline = None
