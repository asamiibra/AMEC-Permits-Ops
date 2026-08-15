"""Internal test-only hard-stop seam used by the local closure harness.

It is environment-driven, has no HTTP/API surface, and is inert unless a
closure subprocess explicitly opts into one named boundary.
"""

from __future__ import annotations

import os
import signal


def hard_kill_if_requested(boundary: str) -> None:
    if os.getenv("PROPOSALOPS_CLOSURE_CRASH_POINT") == boundary:
        os.kill(os.getpid(), signal.SIGKILL)
