from fastapi import APIRouter, HTTPException, status

from .jev_service import (
    CallLimitExceededError,
    InvalidJEVResponseError,
    JEVService,
    JEVServiceError,
    MissingAPIKeyError,
)
from .schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse

router = APIRouter()
jev_service = JEVService()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    try:
        return await jev_service.analyze(payload.message)
    except MissingAPIKeyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except CallLimitExceededError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except InvalidJEVResponseError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except JEVServiceError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível concluir a análise com o JEV.",
        ) from exc

