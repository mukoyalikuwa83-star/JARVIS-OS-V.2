"""Voice Mood Detection — analyzes speech patterns to infer user mood and energy."""
import time
import json
from collections import deque
from pathlib import Path
from typing import Optional

_MOOD_STATE_PATH = Path(__file__).resolve().parent.parent / ".jarvis" / "mood_state.json"
_MOOD_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

class VoiceMoodAnalyzer:
    """
    Analyzes voice metrics to detect mood in real time.
    
    Tracked signals:
    - Speech rate (words/minute) — fast = excited/anxious, slow = tired/bored
    - Volume (RMS energy) — loud = energetic/angry, soft = tired/sad
    - Pause frequency — long pauses = thinking/tired, no pauses = rushed
    - Turn duration — short turns = focused, long turns = rambling/relaxed
    - Time between turns — fast = eager, slow = distracted/tired
    """

    def __init__(self, window_size: int = 20):
        self._window_size = window_size
        self._speech_rates: deque = deque(maxlen=window_size)
        self._volumes: deque = deque(maxlen=window_size)
        self._turn_durations: deque = deque(maxlen=window_size)
        self._inter_turn_gaps: deque = deque(maxlen=window_size)
        self._word_counts: deque = deque(maxlen=window_size)
        self._timestamps: deque = deque(maxlen=window_size)
        
        self._current_mood = "neutral"
        self._mood_confidence = 0.5
        self._energy_level = 0.5
        self._stress_level = 0.0
        self._fatigue_level = 0.0
        
        self._turn_start_time = 0.0
        self._last_turn_end_time = 0.0
        self._current_volume = 0.0
        
        self._mood_history: deque = deque(maxlen=100)
        
        self._load_state()

    def start_turn(self):
        self._turn_start_time = time.monotonic()

    def end_turn(self, word_count: int, avg_volume: float):
        now = time.monotonic()
        duration = now - self._turn_start_time if self._turn_start_time else 0
        
        if self._last_turn_end_time > 0:
            gap = now - self._last_turn_end_time
            self._inter_turn_gaps.append(gap)
        
        if duration > 0 and word_count > 0:
            wpm = (word_count / duration) * 60
            self._speech_rates.append(wpm)
        
        self._turn_durations.append(duration)
        self._word_counts.append(word_count)
        self._volumes.append(avg_volume)
        self._timestamps.append(now)
        self._last_turn_end_time = now
        
        self._analyze_mood()

    def update_realtime_volume(self, rms: float):
        self._current_volume = rms

    def _analyze_mood(self):
        if len(self._speech_rates) < 3:
            return
        
        rates = list(self._speech_rates)
        volumes = list(self._volumes)
        durations = list(self._turn_durations)
        gaps = list(self._inter_turn_gaps)
        
        avg_rate = sum(rates) / len(rates)
        avg_vol = sum(volumes) / len(volumes)
        avg_dur = sum(durations) / len(durations)
        avg_gap = sum(gaps) / len(gaps) if gaps else 2.0
        
        recent_rates = rates[-5:]
        recent_vols = volumes[-5:]
        rate_trend = (recent_rates[-1] - recent_rates[0]) / max(recent_rates[0], 1)
        vol_trend = (recent_vols[-1] - recent_vols[0]) / max(recent_vols[0], 0.001)
        
        energy_score = min(1.0, (avg_rate / 180.0) * 0.5 + (avg_vol / 0.05) * 0.5)
        stress_score = min(1.0, max(0.0, rate_trend * 2 + vol_trend * 1.5))
        fatigue_score = min(1.0, max(0.0, 1.0 - (avg_rate / 120.0)) * 0.5 + (avg_gap / 5.0) * 0.5)
        
        if avg_rate > 160 and avg_vol > 0.03:
            mood = "excited"
            conf = min(1.0, (avg_rate - 140) / 60 + (avg_vol - 0.02) / 0.03)
        elif avg_rate > 140 and avg_vol > 0.025:
            mood = "energetic"
            conf = min(1.0, (avg_rate - 120) / 60)
        elif avg_rate < 80 and avg_vol < 0.015:
            mood = "tired"
            conf = min(1.0, (80 - avg_rate) / 40 + (0.015 - avg_vol) / 0.01)
        elif avg_rate < 90 and avg_vol < 0.012:
            mood = "sad"
            conf = min(1.0, (90 - avg_rate) / 30)
        elif stress_score > 0.6:
            mood = "frustrated"
            conf = stress_score
        elif avg_rate > 130 and avg_dur < 1.5:
            mood = "rushed"
            conf = min(1.0, (avg_rate - 110) / 50)
        elif avg_rate < 100 and avg_gap < 1.0:
            mood = "thinking"
            conf = min(1.0, (110 - avg_rate) / 30)
        else:
            mood = "neutral"
            conf = 0.7
        
        self._current_mood = mood
        self._mood_confidence = conf
        self._energy_level = energy_score
        self._stress_level = stress_score
        self._fatigue_level = fatigue_score
        
        self._mood_history.append({
            "time": time.time(),
            "mood": mood,
            "confidence": round(conf, 2),
            "energy": round(energy_score, 2),
            "stress": round(stress_score, 2),
            "fatigue": round(fatigue_score, 2),
            "wpm": round(avg_rate, 1),
            "volume": round(avg_vol, 4),
        })
        
        self._save_state()

    def get_mood(self) -> str:
        return self._current_mood

    def get_confidence(self) -> float:
        return self._mood_confidence

    def get_energy(self) -> float:
        return self._energy_level

    def get_stress(self) -> float:
        return self._stress_level

    def get_fatigue(self) -> float:
        return self._fatigue_level

    def get_adaptation_hint(self) -> str:
        if self._fatigue_level > 0.7:
            return "user_seems_tired_be_gentle"
        elif self._stress_level > 0.7:
            return "user_seems_stressed_be_concise"
        elif self._energy_level > 0.8:
            return "user_is_energetic_match_energy"
        elif self._current_mood == "excited":
            return "user_is_excited_be_enthusiastic"
        elif self._current_mood == "sad":
            return "user_seems_down_be_supportive"
        elif self._current_mood == "thinking":
            return "user_is_thinking_give_space"
        elif self._current_mood == "rushed":
            return "user_is_rushed_be_quick"
        else:
            return "neutral"

    def get_summary(self) -> dict:
        return {
            "mood": self._current_mood,
            "confidence": round(self._mood_confidence, 2),
            "energy": round(self._energy_level, 2),
            "stress": round(self._stress_level, 2),
            "fatigue": round(self._fatigue_level, 2),
            "adaptation": self.get_adaptation_hint(),
            "sample_size": len(self._speech_rates),
        }

    def _save_state(self):
        try:
            data = {
                "current_mood": self._current_mood,
                "mood_confidence": self._mood_confidence,
                "energy_level": self._energy_level,
                "stress_level": self._stress_level,
                "fatigue_level": self._fatigue_level,
                "mood_history": list(self._mood_history)[-20:],
            }
            _MOOD_STATE_PATH.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

    def _load_state(self):
        try:
            if _MOOD_STATE_PATH.exists():
                data = json.loads(_MOOD_STATE_PATH.read_text())
                self._current_mood = data.get("current_mood", "neutral")
                self._mood_confidence = data.get("mood_confidence", 0.5)
                self._energy_level = data.get("energy_level", 0.5)
                self._stress_level = data.get("stress_level", 0.0)
                self._fatigue_level = data.get("fatigue_level", 0.0)
                for entry in data.get("mood_history", [])[-20:]:
                    self._mood_history.append(entry)
        except Exception:
            pass
