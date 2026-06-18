from pydantic import BaseModel, Field
from typing import Any, Literal

GenerationMode = Literal["v1", "v2", "compare"]


class GenerateRequest(BaseModel):
    product: str = Field(..., min_length=1, max_length=120)
    persona: str = Field(..., min_length=1, max_length=1200)
    mode: GenerationMode = "v1"


class JourneyStage(BaseModel):
    phase: str
    behavior: str
    emotion_score: int = Field(..., ge=1, le=10)
    pain_point: str
    opportunity: str


class JourneyMapResult(BaseModel):
    version: Literal["v1", "v2"]
    product: str
    persona: str
    stages: list[JourneyStage]
    mermaid_code: str


class StepTrace(BaseModel):
    step: int
    name: str
    output: dict[str, Any]


class CompareReport(BaseModel):
    summary: str
    emotion_curve_analysis: str
    recommendation: str


class GenerateResponse(BaseModel):
    mode: GenerationMode
    v1: JourneyMapResult | None = None
    v2: JourneyMapResult | None = None
    traces: list[StepTrace] = Field(default_factory=list)
    report: CompareReport | None = None


class V1GenerateRequest(BaseModel):
    product: str = Field(..., min_length=1, max_length=120)
    persona: str = Field(..., min_length=1, max_length=1200)


class V1GenerateResponse(BaseModel):
    stages: list[JourneyStage]
    summary: str
    cached: bool = False
    saved_cost: float = 0.0


class V2GenerateRequest(BaseModel):
    product: str = Field(..., min_length=1, max_length=120)
    persona: str = Field(..., min_length=1, max_length=1200)


class V2GenerateResponse(BaseModel):
    stages: list[JourneyStage]
    summary: str
    mermaid_code: str
    traces: list[StepTrace]
    cached: bool = False
    saved_cost: float = 0.0


class RefineRequest(BaseModel):
    """人工纠偏请求：用户修改了某个阶段的情绪分/痛点，请求重新生成后续阶段。"""
    product: str = Field(..., min_length=1, max_length=120)
    persona: str = Field(..., min_length=1, max_length=1200)
    stages: list[JourneyStage]  # 当前完整阶段列表
    modified_index: int = Field(..., ge=0)  # 被修改的阶段索引
    modified_emotion_score: int = Field(..., ge=1, le=10)  # 新的情绪分
    modified_pain_point: str  # 新的痛点


class RefineResponse(BaseModel):
    """纠偏后的完整旅程地图。"""
    stages: list[JourneyStage]
    summary: str = ""
    mermaid_code: str = ""
