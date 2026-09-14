"""P04C server projection coverage for Proposal action authority."""

from .test_proposal_commercial_controls import _create_ready_proposal
from .test_bd_proposal_owner_session import _headers


def test_proposal_detail_projects_exact_action_capabilities_by_role(client):
    proposal_id = _create_ready_proposal(client)

    engineering = client.get(f"/api/bd/proposals/{proposal_id}", headers=_headers("RESPONSIBLE_ENGINEER"))
    assert engineering.status_code == 200, engineering.text
    capabilities = engineering.json()["action_capabilities"]
    assert {"EDIT_INTAKE", "EDIT_TECHNICAL", "RECORD_TECHNICAL_ASSESSMENT", "RECONCILE_LPO", "RECORD_CONTRACT_HANDOFF"} <= set(capabilities)
    assert capabilities["EDIT_INTAKE"]["available"] is False
    assert capabilities["EDIT_TECHNICAL"]["available"] is False
    assert capabilities["EDIT_TECHNICAL"]["reason"] == "STAGE_READ_ONLY"
    assert capabilities["RECORD_CONTRACT_HANDOFF"]["available"] is False

    owner = client.get(f"/api/bd/proposals/{proposal_id}", headers=_headers("SYSTEM_ADMIN"))
    assert owner.status_code == 200, owner.text
    owner_capabilities = owner.json()["action_capabilities"]
    assert owner_capabilities["EDIT_INTAKE"]["available"] is False
    assert owner_capabilities["EDIT_COMMERCIAL"]["available"] is True
    assert owner_capabilities["RECORD_CONTRACT_HANDOFF"]["available"] is False
