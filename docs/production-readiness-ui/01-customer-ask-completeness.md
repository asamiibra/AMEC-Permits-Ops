# AMEC setup-item completeness

AMEC setup items are centralized in `customerProductionRequirements`. Each item has a stable ID, friendly title, category, AMEC contact role, internal owner, setup status, go-live need, optional safe fallback, and screen crosswalk.

The drawer presents only setup items relevant to the current screen. The Go-Live Setup view presents the complete list, filters still-needed/go-live items, and exports friendly rows as CSV. `unmapped-customer-asks.json` is the machine-readable proof that no defined setup item is orphaned.

Statuses shown to users are: Needed, Requested, Provided, Configured, Tested, Ready, and Not Needed. Internal workflow codes remain stable for compatibility and are not shown as normal drawer labels.
