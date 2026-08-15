# Real process crash harness

`backend/scripts/integrated_local_closure.py --mode crash` starts separate OS Python children and uses an internal SIGKILL failpoint at five storage boundaries, source promotion boundaries, and after the business commit before dispatch. The seam is environment-driven and has no HTTP surface.
