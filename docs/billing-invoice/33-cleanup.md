# Cleanup

Billing test records are isolated to the pytest database and removed by the test fixture. No generated invoice exports are stored in source or master-content directories; issued artifacts remain synthetic database records.

Status: IMPLEMENTED_AND_VERIFIED
