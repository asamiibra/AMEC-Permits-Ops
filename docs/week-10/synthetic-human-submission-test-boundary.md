# Synthetic human submission boundary

`POST /api/submission-cycles/synthetic-capture` is a capture/evidence API, not a submit operation. It requires an explicit synthetic external-human action marker and records `SYNTHETIC_EXTERNAL_HUMAN_SUBMIT_HARNESS`. No product route performs final submit, payment, declaration, signature, stamp, or certification.
