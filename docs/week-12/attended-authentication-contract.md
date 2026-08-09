# Attended authentication contract

`AttendedAuthSession` records user/role, environment, adapter, lifecycle, auth/MFA mode, challenge timing, and hashed session reference. States include `WAITING_FOR_HUMAN_AUTH`, `WAITING_FOR_MFA`, `AUTHENTICATED`, `EXPIRED`, `CANCELLED`, and `HANDED_OFF`. Passwords, OTPs, cookies, tokens, and authenticator secrets are not accepted or stored.
