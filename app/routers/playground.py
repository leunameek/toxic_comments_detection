from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services import classifier

router = APIRouter(prefix="/playground", tags=["Playground"])


class PlaygroundRequest(BaseModel):
    text: str = Field(..., max_length=500)


class PlaygroundResult(BaseModel):
    label: int
    label_text: str
    score: float
    action: str
    top_features: list[str]
    cleaned_text: str
    language: str
    processing_ms: float


@router.post("/classify", response_model=PlaygroundResult)
def playground_classify(req: PlaygroundRequest):
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="Text cannot be empty")

    if not classifier.is_model_loaded():
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        from langdetect import detect
        language = detect(req.text)
    except Exception:
        language = "es"

    try:
        from pipeline import clean_text
        cleaned = clean_text(req.text)
    except Exception:
        cleaned = req.text

    result = classifier.predict(req.text)

    return PlaygroundResult(
        label=result["label"],
        label_text="TOXIC" if result["label"] == 1 else "CLEAN",
        score=result["score"],
        action=result["action"],
        top_features=result["top_features"],
        cleaned_text=cleaned,
        language=language,
        processing_ms=result["processing_ms"],
    )
