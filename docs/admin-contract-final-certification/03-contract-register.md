# Contract Register

The register is backed by one API projection and exposes All, Need Action, Authority Review, and Ready / Close lanes. Its primary columns are Contract, Contract Ref, Stage, Amount, Close Date, and Open, with Client and Project/Opportunity context where available. Lane counts are server-derived; the browser regression verifies count/row reconciliation and valid opens.

The controlled failure path is distinct from an empty register. Direct register navigation, refresh, owner authorization, and non-owner redirect were covered in PostgreSQL browser evidence.

