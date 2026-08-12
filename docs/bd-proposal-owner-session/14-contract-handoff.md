# Contract handoff

`POST /api/bd/proposals/{id}/handoff/contract` requires the exact accepted revision and produces a contract-eligible handoff reference. It does not create a legal contract automatically; `machine_legal_contract` is false.
