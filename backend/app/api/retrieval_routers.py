"""Read-only governed retrieval API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..api.dependencies import current_user_role
from ..db import get_db
from ..models import Role
from ..services.governed_retrieval import (
    GovernedAIAnswer,
    GovernedRetrievalResult,
    RetrievalQuery,
    access_context_for_role,
    answer_from_retrieval,
    governed_retrieve,
)

router = APIRouter(prefix="/api/retrieval", tags=["governed-retrieval"])


class AnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    query: RetrievalQuery


@router.get("/query", response_model=list[GovernedRetrievalResult])
def query_retrieval(query: RetrievalQuery = Depends(), role: Role = Depends(current_user_role), db=Depends(get_db)):
    access = access_context_for_role(role, caller_id=f"role:{role.value}")
    return list(governed_retrieve(db, query, access))


@router.post("/answer", response_model=GovernedAIAnswer)
def answer_retrieval(payload: AnswerRequest, role: Role = Depends(current_user_role), db=Depends(get_db)):
    access = access_context_for_role(role, caller_id=f"role:{role.value}", purpose="AI_CONTEXT")
    return answer_from_retrieval(payload.question, governed_retrieve(db, payload.query, access))
