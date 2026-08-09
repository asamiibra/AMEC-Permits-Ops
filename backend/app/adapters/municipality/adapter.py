from typing import Protocol


class MunicipalityAdapter(Protocol):
    def read_application(self, application_id: str) -> dict: ...
    def read_current_state(self, application_id: str) -> dict: ...
    def read_status(self, application_id: str) -> dict: ...
    def read_comments(self, application_id: str) -> list[dict]: ...
    def health_check(self) -> dict: ...


class MockMunicipalityAdapter:
    """Read-only local authority simulator. Deliberately has no submit operation."""
    def __init__(self, applications: dict[str, dict]): self.applications = applications
    def read_application(self, application_id: str) -> dict: return self.applications[application_id]
    def read_current_state(self, application_id: str) -> dict: return self.applications[application_id]
    def read_status(self, application_id: str) -> dict: return {"status": self.applications[application_id]["status"], "repetition_count": self.applications[application_id]["repetition_count"]}
    def read_comments(self, application_id: str) -> list[dict]: return self.applications[application_id].get("comments", [])
    def health_check(self) -> dict: return {"adapter": "MUNICIPALITY", "status": "OK", "name": "Permit Authority Simulator", "synthetic": True}
