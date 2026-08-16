# Accessibility visual regression

Focus-visible styling was normalized to a 2px high-contrast outline with 2px offset. Low-contrast metadata/actions were darkened. Non-interactive Admin preview lane containers now use `role="group"` instead of an incorrect tablist role; interactive Admin lane tabs are unchanged.

Axe WCAG 2A/2AA checks at 1440px found no serious or critical violations on Dashboard, AMEC Work, Engineering, Permit, Authority Cases, Issues, Notifications, or Admin.
