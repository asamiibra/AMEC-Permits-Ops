# Repeating-grid edge maturity

The Week 9 grid engine is reused with canonical row identity, business key, parent identity, persisted-state readback, and schema drift fallback. The edge matrix covers zero/one/multiple rows, reorder, duplicate/missing/extra rows, parent mismatch, optional visibility, and persistence mismatch. Position alone is never identity.
