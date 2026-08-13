# Regulatory contact

`ContactPoint` is case/project scoped and carries purpose, channel, value, verification, status, effective dates, maintainer, and optional project-pinned evidence. Read models mask the value and expose `value_present`. `REGULATORY` is purpose-specific; a general client mobile is not substituted. The route audit event explicitly records `general_mobile_is_regulatory_contact: false`, and the focused test keeps `GENERAL/MOBILE` and `REGULATORY/EMAIL` as separate contacts.
