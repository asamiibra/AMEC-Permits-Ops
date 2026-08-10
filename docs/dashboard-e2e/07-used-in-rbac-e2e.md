# Used In + RBAC

The combined gate is verified in both layers: UI controls disappear or redirect for non-Owner personas, while direct API writes return `403 CAPABILITY_DENIED`. Binding state is filtered independently from capability state, so a role is not authorization and authorization is not applicability.

Results: `USED_IN_PLUS_RBAC_COMBINED_GATE_PASS`, `BINDING_IS_NOT_AUTHORIZATION_PASS`, `ROLE_IS_NOT_APPLICABILITY_PASS`, `MASTER_CONTENT_RBAC_NEGATIVE_E2E_PASS`, `CLIENT_VISIBLE_SOR_CREDENTIAL_ZERO`, `RAW_SOR_PATH_NORMAL_UI_ZERO`, `ARBITRARY_SOR_FOLDER_SELECTION_ZERO`.
