"""AI-D0/D1 architecture and provider-safe context contracts.

This package deliberately contains no provider SDK, network client, worker,
outbox, or persistence integration.  ProposalOps remains the control plane.
"""

from .contracts import (
    AIArchitectureContract,
    AIContextManifest,
    AIExecutionMode,
    AIPurpose,
    AITargetEntityType,
)
from .gateway import ModelGateway
from .skill_registry import SkillDefinition, SkillRegistry


def __getattr__(name: str):
    """Load the runtime lazily so settings can validate AI bindings at startup.

    ``skill_runtime`` imports the API principal type.  Eagerly importing it
    here makes ``settings -> ai.runtime_binding -> ai -> skill_runtime`` a
    cycle when external inference is enabled in a hosted process.
    """
    if name in {"SkillExecutionRequest", "SkillRuntime", "execute_skill"}:
        from . import skill_runtime

        value = getattr(skill_runtime, name)
        globals()[name] = value
        return value
    raise AttributeError(name)

__all__ = [
    "AIArchitectureContract",
    "AIContextManifest",
    "AIExecutionMode",
    "AIPurpose",
    "AITargetEntityType",
    "ModelGateway",
    "SkillDefinition",
    "SkillRegistry",
    "SkillExecutionRequest",
    "SkillRuntime",
    "execute_skill",
]
