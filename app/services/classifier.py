import time
import joblib
from pathlib import Path

from ..config import get_settings

_pipeline = None
_loaded_at = None
_total_classifications = 0
_total_latency_ms = 0.0


def load_model() -> None:
    global _pipeline, _loaded_at
    path = Path(get_settings().model_path)
    if not path.exists():
        raise FileNotFoundError(f"Model not found at {path}")
    _pipeline = joblib.load(path)
    from datetime import datetime, timezone
    _loaded_at = datetime.now(timezone.utc)


def is_model_loaded() -> bool:
    return _pipeline is not None


def predict(text: str) -> dict:
    global _total_classifications, _total_latency_ms

    if not is_model_loaded():
        raise RuntimeError("Model not loaded")

    t0 = time.perf_counter()
    result = _pipeline.predict_one(text)
    processing_ms = round((time.perf_counter() - t0) * 1000, 2)

    _total_classifications += 1
    _total_latency_ms += processing_ms

    return {**result, "processing_ms": processing_ms}


def get_model_stats() -> dict:
    avg_latency = _total_latency_ms / _total_classifications if _total_classifications else 0.0
    return {
        "total_classifications": _total_classifications,
        "avg_latency_ms": round(avg_latency, 2),
        "loaded_at": _loaded_at,
    }
