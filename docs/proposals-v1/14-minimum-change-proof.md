# Controlled minimum change

The supplied baseline was changed only from `Duration: 3 months` to `Duration: 4 months` for a QA probe. This is not a source-supported Al Watan draft and must not be issued as one.

Verified: 79 package members retained; 78 member payloads byte-identical; word/document.xml differs only at the duration digit; full DOCX reopens and renders as 12 pages. Pages 1–11 are pixel-identical. Page 12 difference bounding box is [373, 1010, 386, 1029] at 1414×2000 rendering resolution. Final page 12 visually inspected; unchanged pages share exact pixels with inspected baseline pages.

Reproduce package mutation with scripts/proposals_v1/package_probe.py using the authorized local baseline. This proves controlled package preservation only, not AI minimum-change generation.
