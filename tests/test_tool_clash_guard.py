"""Tests for tool-call clash resolution (duplicate / overlapping playback calls)."""
import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402


def _call(name, args=None, call_id="call-1"):
    return SimpleNamespace(name=name, args=args or {}, id=call_id)


def _resolve(calls):
    return main.JarvisLive._resolve_tool_call_clashes(calls)


class TestToolClashGuard(unittest.TestCase):
    def test_identical_duplicate_is_skipped(self):
        c1 = _call("web_search", {"query": "weather"}, "a")
        c2 = _call("web_search", {"query": "weather"}, "b")
        plans = _resolve([c1, c2])
        self.assertIsNone(plans[0][1])
        self.assertIsNotNone(plans[1][1])
        self.assertIn("Duplicate", plans[1][1])

    def test_same_name_different_args_both_run(self):
        c1 = _call("web_search", {"query": "weather"}, "a")
        c2 = _call("web_search", {"query": "news"}, "b")
        plans = _resolve([c1, c2])
        self.assertIsNone(plans[0][1])
        self.assertIsNone(plans[1][1])

    def test_song_query_media_wins(self):
        yt = _call("youtube_video", {"action": "play", "query": "any song"}, "a")
        media = _call("media_control", {"action": "play_query", "query": "any song"}, "b")
        plans = _resolve([yt, media])
        yt_plan = next(p for p in plans if p[0].name == "youtube_video")
        media_plan = next(p for p in plans if p[0].name == "media_control")
        self.assertIsNotNone(yt_plan[1])
        self.assertIn("media_control", yt_plan[1])
        self.assertIsNone(media_plan[1])

    def test_video_query_youtube_wins(self):
        yt = _call(
            "youtube_video",
            {"action": "play", "query": "lofi music video", "url": "https://youtube.com/watch?v=1"},
            "a",
        )
        media = _call("media_control", {"action": "play_query", "query": "lofi music"}, "b")
        plans = _resolve([yt, media])
        yt_plan = next(p for p in plans if p[0].name == "youtube_video")
        media_plan = next(p for p in plans if p[0].name == "media_control")
        self.assertIsNone(yt_plan[1])
        self.assertIsNotNone(media_plan[1])
        self.assertIn("youtube_video", media_plan[1])

    def test_youtube_summarize_does_not_clash(self):
        yt = _call("youtube_video", {"action": "summarize", "query": "some video"}, "a")
        media = _call("media_control", {"action": "play_query", "query": "any song"}, "b")
        plans = _resolve([yt, media])
        self.assertIsNone(plans[0][1])
        self.assertIsNone(plans[1][1])

    def test_no_clash_all_execute(self):
        calls = [
            _call("get_time", {}, "a"),
            _call("media_control", {"action": "pause"}, "b"),
        ]
        plans = _resolve(calls)
        self.assertTrue(all(reason is None for _, reason in plans))

    def test_empty_batch(self):
        self.assertEqual(_resolve([]), [])
        self.assertEqual(_resolve(None), [])

    def test_youtube_url_hint_prefers_youtube(self):
        yt = _call("youtube_video", {"action": "play", "url": "https://m.youtube.com/watch?v=abc"}, "a")
        media = _call("media_control", {"action": "play_query", "query": "random"}, "b")
        plans = _resolve([yt, media])
        media_plan = next(p for p in plans if p[0].name == "media_control")
        self.assertIsNotNone(media_plan[1])

    def test_security_same_domain_skips_duplicate(self):
        cs = _call("cybersec", {"action": "port_scan", "target": "192.168.1.1"}, "a")
        cy = _call("cybersecurity", {"action": "scan_ports", "host": "192.168.1.1"}, "b")
        plans = _resolve([cs, cy])
        cs_plan = next(p for p in plans if p[0].name == "cybersec")
        cy_plan = next(p for p in plans if p[0].name == "cybersecurity")
        self.assertIsNone(cs_plan[1])
        self.assertIsNotNone(cy_plan[1])
        self.assertIn("cybersec", cy_plan[1])

    def test_security_different_domain_both_run(self):
        cs = _call("cybersec", {"action": "port_scan", "target": "192.168.1.1"}, "a")
        cy = _call("cybersecurity", {"action": "malware_scan", "path": "C:\\Temp"}, "b")
        plans = _resolve([cs, cy])
        self.assertTrue(all(reason is None for _, reason in plans))

    def test_timer_duplicate_skips_automation(self):
        alarm = _call("alarm_timer", {"action": "set_timer", "minutes": 5}, "a")
        auto = _call("automation_engine", {"action": "timer", "name": "tea"}, "b")
        plans = _resolve([alarm, auto])
        alarm_plan = next(p for p in plans if p[0].name == "alarm_timer")
        auto_plan = next(p for p in plans if p[0].name == "automation_engine")
        self.assertIsNone(alarm_plan[1])
        self.assertIsNotNone(auto_plan[1])
        self.assertIn("alarm_timer", auto_plan[1])

    def test_reminder_duplicate_skips_automation(self):
        rem = _call("reminder", {"date": "2026-10-03", "time": "09:00", "message": "stretch"}, "a")
        auto = _call("automation_engine", {"action": "reminder", "name": "stretch"}, "b")
        plans = _resolve([rem, auto])
        rem_plan = next(p for p in plans if p[0].name == "reminder")
        auto_plan = next(p for p in plans if p[0].name == "automation_engine")
        self.assertIsNone(rem_plan[1])
        self.assertIsNotNone(auto_plan[1])
        self.assertIn("reminder", auto_plan[1])

    def test_automation_unique_action_runs(self):
        rem = _call("reminder", {"date": "2026-10-03", "time": "09:00", "message": "stretch"}, "a")
        auto = _call("automation_engine", {"action": "create", "name": "backup"}, "b")
        plans = _resolve([rem, auto])
        self.assertTrue(all(reason is None for _, reason in plans))

    def test_automation_reminder_without_dedicated_tool_runs(self):
        auto = _call("automation_engine", {"action": "reminder", "name": "stretch"}, "a")
        plans = _resolve([auto])
        self.assertIsNone(plans[0][1])


if __name__ == "__main__":
    unittest.main()
