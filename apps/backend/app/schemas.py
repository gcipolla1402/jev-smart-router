from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Category = Literal["FRAUDE", "SUPORTE_TECNICO", "COMERCIAL", "CANCELAMENTO"]
Priority = Literal["BAIXA", "MEDIA", "ALTA"]

CATEGORIES: tuple[str, ...] = (
    "FRAUDE",
    "SUPORTE_TECNICO",
    "COMERCIAL",
    "CANCELAMENTO",
)
PRIORITIES: tuple[str, ...] = ("BAIXA", "MEDIA", "ALTA")


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=10_000)

    @field_validator("message")
    @classmethod
    def reject_blank_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A mensagem não pode estar vazia.")
        return value


class TechnicalDetails(BaseModel):
    model: str
    latency_ms: int = Field(ge=0)
    input_tokens: int | None
    output_tokens: int | None
    category_native_confidence: float = Field(ge=0, le=1)
    priority_native_confidence: float = Field(ge=0, le=1)


class AnalyzeResponse(BaseModel):
    category: Category
    priority: Priority
    probabilities: dict[Category, float]
    queue: str
    technical_details: TechnicalDetails


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ErrorResponse(BaseModel):
    detail: str

