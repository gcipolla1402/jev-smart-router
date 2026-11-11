import asyncio
import os
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from dotenv import load_dotenv
from typesafe_sdk import AsyncTypeSafeClient, Choice, RetryPolicy

from .schemas import (
    CATEGORIES,
    PRIORITIES,
    AnalyzeResponse,
    TechnicalDetails,
)

load_dotenv()

CATEGORY_QUESTION = "Classify this customer message into the most appropriate routing category."
PRIORITY_QUESTION = "Determine the appropriate handling priority for this customer message."

QUEUE_BY_CATEGORY = {
    "FRAUDE": "FILA_FRAUDE",
    "SUPORTE_TECNICO": "FILA_SUPORTE",
    "COMERCIAL": "FILA_COMERCIAL",
    "CANCELAMENTO": "FILA_CANCELAMENTO",
}


class JEVServiceError(RuntimeError):
    """Base error safe to translate into an API response."""


class MissingAPIKeyError(JEVServiceError):
    pass


class CallLimitExceededError(JEVServiceError):
    pass


class InvalidJEVResponseError(JEVServiceError):
    pass


@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str
    timeout_seconds: float
    max_real_calls: int

    @classmethod
    def from_env(cls) -> "Settings":
        try:
            timeout = float(os.getenv("JEV_TIMEOUT_SECONDS", "20"))
            max_calls = int(os.getenv("MAX_REAL_JEV_CALLS", "20"))
        except ValueError as exc:
            raise JEVServiceError("Configuração numérica do JEV inválida.") from exc

        if timeout <= 0 or max_calls < 0:
            raise JEVServiceError("Configuração numérica do JEV inválida.")

        return cls(
            api_key=os.getenv("TYPESAFE_API_KEY", "").strip(),
            model=os.getenv("JEV_MODEL", "jev-latest").strip() or "jev-latest",
            timeout_seconds=timeout,
            max_real_calls=max_calls,
        )


def build_state(message: str) -> dict[str, str]:
    return {"customer_message": message}


def build_questions() -> dict[str, Choice]:
    return {
        "category": Choice(
            instructions=CATEGORY_QUESTION,
            criteria={category: None for category in CATEGORIES},
        ),
        "priority": Choice(
            instructions=PRIORITY_QUESTION,
            criteria={priority: None for priority in PRIORITIES},
        ),
    }


def route_category(category: str) -> str:
    try:
        return QUEUE_BY_CATEGORY[category]
    except KeyError as exc:
        raise InvalidJEVResponseError("O JEV retornou uma categoria inválida.") from exc


def _validate_answer(answer: Any, allowed: tuple[str, ...], label: str) -> None:
    if answer is None or answer.choice not in allowed:
        raise InvalidJEVResponseError(f"O JEV retornou {label} inválida.")
    if set(answer.probabilities) != set(allowed):
        raise InvalidJEVResponseError(f"O JEV retornou probabilidades de {label} inválidas.")
    values = answer.probabilities.values()
    if any(not isinstance(value, (int, float)) or value < 0 or value > 1 for value in values):
        raise InvalidJEVResponseError(f"O JEV retornou probabilidades de {label} inválidas.")


class JEVService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings
        self._real_call_count = 0
        self._counter_lock = asyncio.Lock()

    @property
    def real_call_count(self) -> int:
        return self._real_call_count

    async def _reserve_call(self, settings: Settings) -> None:
        async with self._counter_lock:
            if self._real_call_count >= settings.max_real_calls:
                raise CallLimitExceededError(
                    f"Limite de {settings.max_real_calls} chamadas reais atingido."
                )
            self._real_call_count += 1

    async def analyze(self, message: str) -> AnalyzeResponse:
        settings = self._settings or Settings.from_env()
        if not settings.api_key:
            raise MissingAPIKeyError("TYPESAFE_API_KEY não configurada.")

        await self._reserve_call(settings)
        started_at = perf_counter()

        async with AsyncTypeSafeClient(
            api_key=settings.api_key,
            model=settings.model,
            timeout=settings.timeout_seconds,
            retry=RetryPolicy(max_retries=0),
        ) as client:
            result = await client.system_one(
                state=build_state(message),
                questions=build_questions(),
            )

        latency_ms = round((perf_counter() - started_at) * 1000)
        category_answer = result.choices.get("category")
        priority_answer = result.choices.get("priority")
        _validate_answer(category_answer, CATEGORIES, "categoria")
        _validate_answer(priority_answer, PRIORITIES, "prioridade")

        category = category_answer.choice
        priority = priority_answer.choice

        return AnalyzeResponse(
            category=category,
            priority=priority,
            probabilities=category_answer.probabilities,
            queue=route_category(category),
            technical_details=TechnicalDetails(
                model=result.model,
                latency_ms=latency_ms,
                input_tokens=result.usage.input_tokens,
                output_tokens=result.usage.output_tokens,
                category_native_confidence=category_answer.confidence,
                priority_native_confidence=priority_answer.confidence,
            ),
        )

