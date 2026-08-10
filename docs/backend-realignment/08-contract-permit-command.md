# InitiatePermitFromContract

`POST /api/contracts/{contract_id}/permit` links into the existing
PermitApplication domain. It requires a canonical Proposal/Project chain,
checks the contract and permit Project invariants, supports multiple linked
applications, and sets `controlling_contract_id` without changing permit
package, findings, authority, or human-final-submit behavior.
