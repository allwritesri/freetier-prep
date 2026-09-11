"""TTL hard-timer with an injectable clock.

Tests advance the clock instead of sleeping; the server runs a background
loop calling check_expired on the real clock.
"""

import time


class Clock:
    def now(self) -> float:
        return time.time()


class FakeClock(Clock):
    def __init__(self, start: float | None = None):
        self._now = start if start is not None else time.time()

    def now(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


class TTLScheduler:
    def __init__(self, db, gcp, provisioner, clock: Clock, max_retries: int = 3):
        self.db = db
        self.gcp = gcp
        self.provisioner = provisioner
        self.clock = clock
        self.max_retries = max_retries

    def check_expired(self) -> list[dict]:
        from .teardown import teardown_session

        results = []
        for session in self.db.expired_active_sessions(self.clock.now()):
            results.append({
                "session_id": session["id"],
                "result": teardown_session(
                    self.db, self.gcp, self.provisioner, session,
                    reason="TTL expired", max_retries=self.max_retries,
                ),
            })
        return results
