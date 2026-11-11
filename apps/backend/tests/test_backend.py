import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from typesafe_sdk import ChoiceAnswer, SystemOneResponse, Usage

from app.jev_service import (
    CallLimitExceededError,
    InvalidJEVResponseError,
    JEVService,
    MissingAPIKeyError,
    Settings,
    build_questions,
    build_state,
    route_category,
)
from app.main import app
from app.schemas import AnalyzeRequest, CATEGORIES, PRIORITIES


def run(coro):
    return asyncio.run(coro)


class FakeClient:
    response: SystemOneResponse
    captured: dict = {}

    def __init__(self, **kwargs):
        self.captured["client_kwargs"] = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def system_one(self, **kwargs):
        self.captured["request_kwargs"] = kwargs
        return self.response


def response(category="FRAUDE", priority="ALTA") -> SystemOneResponse:
    category_probabilities = {name: 0.02 for name in CATEGORIES}
    category_probabilities[category] = 0.94
    priority_probabilities = {name: 0.05 for name in PRIORITIES}
    priority_probabilities[priority] = 0.90
    return SystemOneResponse(
        model="jev-test",
        usage=Usage(input_tokens=21, output_tokens=7),
        answers={
            "category": ChoiceAnswer(
                choice=category, confidence=0.94, probabilities=category_probabilities
            ),
            "priority": ChoiceAnswer(
                choice=priority, confidence=0.90, probabilities=priority_probabilities
            ),
        },
    )


def settings(max_calls=20) -> Settings:
    return Settings("test-key", "jev-test", 20, max_calls)


def test_empty_message_is_rejected():
    with pytest.raises(ValidationError):
        AnalyzeRequest(message="   ")


def test_empty_message_returns_422():
    with TestClient(app) as client:
        assert client.post("/api/analyze", json={"message": ""}).status_code == 422


def test_state_contains_only_customer_message():
    assert build_state("Olá") == {"customer_message": "Olá"}


def test_questions_have_only_allowed_categories_and_priorities():
    questions = build_questions()
    assert tuple(questions["category"].criteria) == CATEGORIES
    assert tuple(questions["priority"].criteria) == PRIORITIES


@pytest.mark.parametrize(
    ("category", "queue"),
    [
        ("FRAUDE", "FILA_FRAUDE"),
        ("SUPORTE_TECNICO", "FILA_SUPORTE"),
        ("COMERCIAL", "FILA_COMERCIAL"),
        ("CANCELAMENTO", "FILA_CANCELAMENTO"),
    ],
)
def test_routing(category, queue):
    assert route_category(category) == queue


def test_invalid_category_is_rejected():
    with pytest.raises(InvalidJEVResponseError):
        route_category("OUTRA")


def test_missing_api_key_is_rejected_before_call():
    service = JEVService(Settings("", "jev-test", 20, 20))
    with pytest.raises(MissingAPIKeyError):
        run(service.analyze("Mensagem"))
    assert service.real_call_count == 0


def test_call_limit(monkeypatch):
    FakeClient.response = response()
    monkeypatch.setattr("app.jev_service.AsyncTypeSafeClient", FakeClient)
    service = JEVService(settings(max_calls=1))
    run(service.analyze("Primeira"))
    with pytest.raises(CallLimitExceededError):
        run(service.analyze("Segunda"))


def test_invalid_jev_response(monkeypatch):
    invalid = response()
    invalid = SimpleNamespace(
        model=invalid.model,
        usage=invalid.usage,
        choices={"priority": invalid.choices["priority"]},
    )
    FakeClient.response = invalid
    monkeypatch.setattr("app.jev_service.AsyncTypeSafeClient", FakeClient)
    with pytest.raises(InvalidJEVResponseError):
        run(JEVService(settings()).analyze("Mensagem"))


def test_analysis_uses_sdk_contract_and_returns_route(monkeypatch):
    FakeClient.response = response("COMERCIAL", "MEDIA")
    FakeClient.captured = {}
    monkeypatch.setattr("app.jev_service.AsyncTypeSafeClient", FakeClient)

    result = run(JEVService(settings()).analyze("Quero conhecer os planos"))

    assert result.category == "COMERCIAL"
    assert result.priority == "MEDIA"
    assert result.queue == "FILA_COMERCIAL"
    assert FakeClient.captured["request_kwargs"]["state"] == {
        "customer_message": "Quero conhecer os planos"
    }
    assert FakeClient.captured["client_kwargs"]["retry"].max_retries == 0


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

