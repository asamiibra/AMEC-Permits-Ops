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
from .skill_runtime import SkillExecutionRequest, SkillRuntime, execute_skill

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
