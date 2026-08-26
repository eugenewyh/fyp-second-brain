"""In-app daily review scheduler — gated catch-up, then run at DAILY_REVIEW_HOUR."""

from __future__ import annotations

import logging
import threading
import time
from datetime import date, datetime, timedelta
from typing import Any, Callable

from second_brain.config import (
    DAILY_REVIEW_CATCH_UP,
    DAILY_REVIEW_ENABLED,
    DAILY_REVIEW_HOUR,
)
from second_brain.agent.daily_review import (
    is_review_running,
    load_review_state,
    review_status_payload,
    run_daily_review,
    save_review_state,
)

logger = logging.getLogger(__name__)

# How often to re-check when the research graph is busy
_BUSY_RETRY_SECONDS = 15 * 60
# Minimum sleep between loop iterations (avoid tight spin)
_MIN_SLEEP_SECONDS = 30


def seconds_until_hour(hour: int, *, now: datetime | None = None) -> float:
    """Seconds until the next occurrence of `hour`:00 local time."""
    now = now or datetime.now().astimezone()
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if now >= target:
        target = target + timedelta(days=1)
    return max(0.0, (target - now).total_seconds())


def past_scheduled_hour(hour: int | None = None, *, now: datetime | None = None) -> bool:
    """True if local time is at or after today's scheduled review hour."""
    now = now or datetime.now().astimezone()
    h = DAILY_REVIEW_HOUR if hour is None else hour
    return now.hour >= h


def needs_catch_up(state: dict | None = None) -> bool:
    """True if we have not completed/skipped a review for today yet."""
    if not DAILY_REVIEW_ENABLED:
        return False
    state = state if state is not None else load_review_state()
    today = date.today().isoformat()
    if state.get("last_run_date") != today:
        return True
    # Crashed mid-run — allow recovery
    if state.get("last_run_status") == "running":
        return True
    # Busy skip should retry later the same day
    if (
        state.get("last_run_status") == "skipped"
        and state.get("skipped_reason") == "busy"
    ):
        return True
    return False


def should_auto_catch_up(
    state: dict | None = None,
    *,
    now: datetime | None = None,
    hour: int | None = None,
) -> bool:
    """
    Whether the scheduler may auto-start a missed review.

    Requires catch-up enabled, a pending review, and local time at/after the
    scheduled hour — so launching the app at 7am does not burn LLM quota.
    """
    if not DAILY_REVIEW_CATCH_UP:
        return False
    if not needs_catch_up(state):
        return False
    return past_scheduled_hour(hour, now=now)


class DailyReviewScheduler:
    def __init__(
        self,
        *,
        acquire_lock: Callable[[], str | None],
        release_lock: Callable[[], None],
        hour: int | None = None,
        enabled: bool | None = None,
    ) -> None:
        """
        acquire_lock: returns None on success, or an active_run_id string if busy.
        release_lock: clears the research single-flight lock.
        """
        self._acquire = acquire_lock
        self._release = release_lock
        self._hour = DAILY_REVIEW_HOUR if hour is None else hour
        self._enabled = DAILY_REVIEW_ENABLED if enabled is None else enabled
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._wake = threading.Event()  # interrupt sleep for run-now / tests
        self._async_lock = threading.Lock()

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if not self._enabled:
            logger.info("Daily review scheduler disabled")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="daily-review-scheduler",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "Daily review scheduler started (hour=%s, catch_up=%s, auto=%s)",
            self._hour,
            DAILY_REVIEW_CATCH_UP,
            should_auto_catch_up(hour=self._hour),
        )

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

    def wake(self) -> None:
        """Interrupt sleep (e.g. after a manual run-now)."""
        self._wake.set()

    def try_run(self, *, reason: str = "scheduled", force: bool = False) -> dict:
        """
        Attempt a daily review if the research graph is free (blocking).
        Returns the review status dict (may be skipped:busy).
        """
        if is_review_running():
            return {
                **load_review_state(),
                "last_run_status": "skipped",
                "skipped_reason": "already_running",
                "last_run_reason": reason,
            }

        busy = self._acquire()
        if busy:
            state = load_review_state()
            state.update(
                {
                    "last_run_status": "skipped",
                    "skipped_reason": "busy",
                    "last_run_reason": reason,
                    "error": f"active_run_id={busy}",
                }
            )
            save_review_state(state)
            logger.info("Daily review deferred — research busy (%s)", busy)
            return state

        try:
            return run_daily_review(reason=reason, force=force, retrieval_scope="local")
        finally:
            self._release()

    def start_async(
        self,
        *,
        reason: str = "manual",
        force: bool = False,
    ) -> tuple[dict[str, Any], int]:
        """
        Start a daily review in a background thread.

        Returns (status_payload, http_status).
        - 202: accepted and running (or already running)
        - 409: research graph busy
        - 200: finished immediately (disabled / already_ran / nothing_to_review skip
               without starting work — rare for force=True)
        """
        with self._async_lock:
            if is_review_running() or load_review_state().get("last_run_status") == "running":
                return review_status_payload(), 202

            busy = self._acquire()
            if busy:
                state = load_review_state()
                state.update(
                    {
                        "last_run_status": "skipped",
                        "skipped_reason": "busy",
                        "last_run_reason": reason,
                        "error": f"active_run_id={busy}",
                    }
                )
                save_review_state(state)
                return review_status_payload(state), 409

            # Mark running early so status polls see it before the worker acquires the lock
            state = load_review_state()
            state.update(
                {
                    "last_run_status": "running",
                    "last_run_started_at": datetime.now().astimezone().isoformat(),
                    "last_run_finished_at": None,
                    "last_run_reason": reason,
                    "skipped_reason": None,
                    "error": None,
                }
            )
            save_review_state(state)

            def worker() -> None:
                try:
                    run_daily_review(
                        reason=reason, force=force, retrieval_scope="local"
                    )
                except Exception:
                    logger.exception("Async daily review failed")
                    failed = load_review_state()
                    failed.update(
                        {
                            "last_run_status": "failed",
                            "error": "async_worker_exception",
                            "last_run_finished_at": datetime.now().astimezone().isoformat(),
                        }
                    )
                    save_review_state(failed)
                finally:
                    self._release()
                    self.wake()

            threading.Thread(
                target=worker,
                name="daily-review-async",
                daemon=True,
            ).start()
            return review_status_payload(), 202

    def _loop(self) -> None:
        # Brief boot delay, then optional catch-up only after the scheduled hour
        self._sleep(5.0)
        if self._stop.is_set():
            return
        if should_auto_catch_up(hour=self._hour):
            try:
                self.try_run(reason="catch_up")
            except Exception:
                logger.exception("Catch-up daily review failed")

        while not self._stop.is_set():
            try:
                if should_auto_catch_up(hour=self._hour):
                    # Missed today's run (e.g. was busy earlier) — retry
                    result = self.try_run(reason="retry")
                    if result.get("skipped_reason") == "busy":
                        self._sleep(_BUSY_RETRY_SECONDS)
                        continue

                wait = seconds_until_hour(self._hour)
                logger.debug("Daily review sleeping %.0fs until hour %s", wait, self._hour)
                self._sleep(wait)
                if self._stop.is_set():
                    break
                # Only fire at/after the scheduled hour for the "scheduled" reason
                now = datetime.now().astimezone()
                if now.hour >= self._hour and needs_catch_up():
                    self.try_run(reason="scheduled")
            except Exception:
                logger.exception("Daily review scheduler loop error")
                self._sleep(60.0)

    def _sleep(self, seconds: float) -> None:
        """Sleep that can be interrupted by stop/wake."""
        deadline = time.monotonic() + max(_MIN_SLEEP_SECONDS if seconds < 0 else seconds, 0)
        # Allow short sleeps under MIN for the initial 5s boot delay
        if seconds < _MIN_SLEEP_SECONDS:
            deadline = time.monotonic() + max(0.0, seconds)
        while not self._stop.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            self._wake.clear()
            self._wake.wait(timeout=min(remaining, 30.0))
            if self._wake.is_set() and not self._stop.is_set():
                # Woken for an external reason — exit sleep early
                break


# Process-wide instance, set by server startup
SCHEDULER: DailyReviewScheduler | None = None


def get_scheduler() -> DailyReviewScheduler | None:
    return SCHEDULER


def start_scheduler(
    *,
    acquire_lock: Callable[[], str | None],
    release_lock: Callable[[], None],
) -> DailyReviewScheduler:
    global SCHEDULER
    if SCHEDULER is None:
        SCHEDULER = DailyReviewScheduler(
            acquire_lock=acquire_lock,
            release_lock=release_lock,
        )
    SCHEDULER.start()
    return SCHEDULER
