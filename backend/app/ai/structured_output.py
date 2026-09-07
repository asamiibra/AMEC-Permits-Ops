"""Strict provider and local output contract for the D3 draft."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .errors import AIError


_CITATION_KEY = re.compile(r"^CIT-[0-9]{3}$")
MAX_VISIBLE_DRAFT_BYTES = 48 * 1024


class DraftSection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    heading: str = Field(min_length=1, max_length=240)
    body: str = Field(min_length=1, max_length=12000)
    citation_keys: list[str] = Field(min_length=1, max_length=16)


class DraftAssumption(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    statement: str = Field(min_length=1, max_length=1000)
    basis: Literal["SOURCE_GROUNDED", "INFERENCE"]
    citation_keys: list[str] = Field(default_factory=list, max_length=16)


class TechnicalMethodologyDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    draft_title: str = Field(min_length=1, max_length=240)
    sections: list[DraftSection] = Field(min_length=2, max_length=8)
    assumptions: list[DraftAssumption] = Field(default_factory=list, max_length=10)
    open_questions: list[str] = Field(default_factory=list, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=20)
    source_coverage_note: str = Field(min_length=1, max_length=1000)
    draft_only: Literal[True] = True

    @model_validator(mode="after")
    def validate_bounded_text(self) -> "TechnicalMethodologyDraft":
        if any(len(item) > 1000 for item in (*self.open_questions, *self.limitations)):
            raise ValueError("question or limitation exceeds bound")
        if any(not all(_CITATION_KEY.fullmatch(key) for key in section.citation_keys) for section in self.sections):
            raise ValueError("section contains malformed citation key")
        for assumption in self.assumptions:
            if not all(_CITATION_KEY.fullmatch(key) for key in assumption.citation_keys):
                raise ValueError("assumption contains malformed citation key")
            if assumption.basis == "SOURCE_GROUNDED" and not assumption.citation_keys:
                raise ValueError("source-grounded assumption needs a citation")
        encoded = json.dumps(self.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(encoded) > MAX_VISIBLE_DRAFT_BYTES:
            raise ValueError("draft exceeds visible output bound")
        return self


PROVIDER_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "draft_title": {"type": "string"},
        "sections": {"type": "array", "items": {"type": "object", "properties": {"heading": {"type": "string"}, "body": {"type": "string"}, "citation_keys": {"type": "array", "items": {"type": "string"}}}, "required": ["heading", "body", "citation_keys"], "additionalProperties": False}},
        "assumptions": {"type": "array", "items": {"type": "object", "properties": {"statement": {"type": "string"}, "basis": {"type": "string", "enum": ["SOURCE_GROUNDED", "INFERENCE"]}, "citation_keys": {"type": "array", "items": {"type": "string"}}}, "required": ["statement", "basis", "citation_keys"], "additionalProperties": False}},
        "open_questions": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "source_coverage_note": {"type": "string"},
        "draft_only": {"type": "boolean"},
    },
    "required": ["draft_title", "sections", "assumptions", "open_questions", "limitations", "source_coverage_note", "draft_only"],
    "additionalProperties": False,
}


def validate_draft(payload: object) -> TechnicalMethodologyDraft:
    try:
        return TechnicalMethodologyDraft.model_validate(payload)
    except Exception as exc:
        raise AIError("AI_STRUCTURED_OUTPUT_VALIDATION_FAILED", status_code=502) from exc


def output_fingerprint(draft: TechnicalMethodologyDraft) -> str:
    canonical = json.dumps(draft.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
