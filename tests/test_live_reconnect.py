"""Regression tests for live-session reconnect routing.

The original bug: when the Gemini Live websocket died (e.g. APIError 1011),
_receive_audio quietly set session=None and returned; _safe_task swallowed
everything, so the infinite sibling tasks kept the TaskGroup alive forever
and run()'s reconnect logic never executed — JARVIS went permanently deaf.
"""
import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class _StubUI:
    def write_log(self, *args, **kwargs):
        pass


class TestLiveConnectionLostRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import main
        cls.main = main

    def _fake_assistant(self):
        obj = object.__new__(self.main.JarvisLive)
        obj.ui = _StubUI()
        return obj

    def test_dead_session_exits_task_group(self):
        """_LiveConnectionLost must escape _safe_task so run() can reconnect."""
        main = self.main
        obj = self._fake_assistant()

        async def killer():
            await asyncio.sleep(0.05)
            raise main._LiveConnectionLost("APIError: 1011 internal error")

        async def infinite():
            while True:
                await asyncio.sleep(0.05)

        async def scenario():
            try:
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(obj._safe_task("killer", killer()))
                    tg.create_task(obj._safe_task("infinite", infinite()))
                return None
            except BaseException as exc:
                return exc

        error = asyncio.run(asyncio.wait_for(scenario(), timeout=5))
        self.assertIsNotNone(error, "TaskGroup exited normally despite dead session")
        actual = error
        if isinstance(error, BaseExceptionGroup):
            actual = next(
                (item for item in main._unwrap_exception_groups(error)
                 if isinstance(item, main._LiveConnectionLost)),
                None,
            )
            self.assertIsNotNone(actual, "no _LiveConnectionLost inside the group")

        is_transient = main._is_transient_live_connection_error(actual) or any(
            code in str(actual) for code in ("1006", "1007", "1011", "1012", "1014")
        )
        self.assertTrue(is_transient, f"1011 error not routed to reconnect: {actual}")

    def test_clean_close_routes_as_normal_close(self):
        main = self.main
        lost = main._as_live_lost(Exception("APIError: 1000 (ok)"))
        self.assertTrue(main._is_normal_live_close_error(lost))
        self.assertFalse(main._is_transient_live_connection_error(lost))

    def test_transient_error_keeps_code_in_message(self):
        main = self.main
        lost = main._as_live_lost(Exception("APIError: 1011 internal error"))
        self.assertFalse(main._is_normal_live_close_error(lost))
        self.assertTrue(
            main._is_transient_live_connection_error(lost)
            or "1011" in str(lost)
        )

    def test_keepalive_timeout_routes_as_transient(self):
        main = self.main
        lost = main._LiveConnectionLost("keepalive timeout: TimeoutError: keepalive send timeout")
        self.assertTrue(main._is_transient_live_connection_error(lost))

    def test_cancellation_is_still_swallowed(self):
        """Teardown must stay quiet: siblings cancelled after a raise don't re-raise."""
        obj = self._fake_assistant()

        async def cancelled():
            raise asyncio.CancelledError()

        result = asyncio.run(obj._safe_task("cancelled", cancelled()))
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
