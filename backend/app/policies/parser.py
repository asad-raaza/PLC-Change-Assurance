"""YAML policy validation. Policies must be valid before activation."""

from __future__ import annotations

import hashlib
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError


class PolicyIfThen(BaseModel):
    if_: dict[str, str] = Field(alias="if", default_factory=dict)
    then: dict[str, str] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class ChangeRequirements(BaseModel):
    approval_required: bool = False


class PolicyApplies(BaseModel):
    plc: str | list[str] | None = None


class PolicyWhen(BaseModel):
    process_state: str | None = None


class PolicyBody(BaseModel):
    name: str
    version: str = "1.0.0"
    applies_to: PolicyApplies = Field(default_factory=PolicyApplies)
    when: PolicyWhen = Field(default_factory=PolicyWhen)
    rules: list[Any] = Field(default_factory=list)
    change_requirements: ChangeRequirements = Field(default_factory=ChangeRequirements)


class PolicyDocument(BaseModel):
    policy: PolicyBody


class PolicyValidationError(ValueError):
    pass


def parse_policy_yaml(text: str) -> tuple[PolicyDocument, str]:
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise PolicyValidationError(f"Invalid YAML: {exc}") from exc
    if not isinstance(raw, dict) or "policy" not in raw:
        raise PolicyValidationError("Document must contain a top-level 'policy' key")
    try:
        doc = PolicyDocument.model_validate(raw)
    except ValidationError as exc:
        raise PolicyValidationError(str(exc)) from exc
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return doc, digest


DEMO_POLICY_YAML = """\
policy:
  name: heating-safety
  version: "1.0.0"
  applies_to:
    plc: tank-plc-01
  when:
    process_state: HEATING
  rules:
    - Temperature_SP <= 85
    - Pressure <= 70
    - if:
        PumpSpeed: "> 60"
      then:
        InletValve: "> 40"
  change_requirements:
    approval_required: true
"""
