from __future__ import annotations


class AIError(Exception):
    """Typed internal AI failure; HTTP mapping happens at the API boundary."""

    def __init__(self, code: str, *, status_code: int = 502):
        super().__init__(code)
        self.code = code
        self.status_code = status_code
