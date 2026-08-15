# Current root diagnosis

## Pre-fix

/dashboard imported DashboardPage directly from frontend/src/Dashboard.tsx. The component had been collapsed from the historical V1/V2 split into one shared shell. The V2 route had already been redirected, but the source identity was still ambiguous and the visual presentation read as V1 with governance controls added.

Classification: SHARED_HYBRID_ROOT / PARTIAL_V2_REHOME.

## Final

/dashboard imports CurrentDashboard from the same evolved source module. It owns the root-level V2 presentation landmarks:

CurrentDashboard → DashboardGovernanceOverview → DashboardLibraryNavigation → CanonicalFormsLibrary → FormDetails/FormHistory/FormEditor → Reports/Engineering Works/Definitions

The root has no mode prop, no V1 route, and no V1 component import. Canonical APIs remain the data/service layer.

Final classification: TRUE_V2_ROOT.
