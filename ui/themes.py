"""Theme definitions, color constants, and graphics profiles for the UI."""

from __future__ import annotations

from PyQt6.QtGui import QColor


# ---------------------------------------------------------------------------
# Graphics quality profiles
# ---------------------------------------------------------------------------

GRAPHICS_PROFILES = {
    "low": {
        "frame_ms": 50,
        "render_stride": 3,
        "wave_stride": 3,
        "noise_count": 0,
        "scanline_step": 8,
        "antialias": False,
        "activity_nodes": 10,
        "metrics_ms": 3500,
    },
    "medium": {
        "frame_ms": 33,
        "render_stride": 2,
        "wave_stride": 2,
        "noise_count": 60,
        "scanline_step": 6,
        "antialias": True,
        "activity_nodes": 16,
        "metrics_ms": 2000,
    },
    "high": {
        "frame_ms": 16,
        "render_stride": 1,
        "wave_stride": 1,
        "noise_count": 200,
        "scanline_step": 4,
        "antialias": True,
        "activity_nodes": 24,
        "metrics_ms": 1200,
    },
}


def _normalize_graphics_quality(quality: str | None) -> str:
    value = str(quality or "medium").strip().lower()
    aliases = {
        "med": "medium", "mid": "medium", "normal": "medium",
        "balanced": "medium", "performance": "low", "battery": "low",
        "max": "high", "maximum": "high", "ultra": "high",
    }
    value = aliases.get(value, value)
    if value not in GRAPHICS_PROFILES:
        raise ValueError("Graphics quality must be low, medium, or high.")
    return value


# ---------------------------------------------------------------------------
# Color helper
# ---------------------------------------------------------------------------

def qcol(h: str, a: int = 255) -> QColor:
    c = QColor(h)
    c.setAlpha(a)
    return c


# ---------------------------------------------------------------------------
# C — consolidated color palette
# ---------------------------------------------------------------------------

class C:
    # ── Backgrounds ──────────────────────────────────────────────────────────
    BG        = "#000306"
    PANEL     = "#00080f"
    PANEL2    = "#000b14"
    DARK      = "#000408"
    DARK2     = "#000c18"
    BAR_BG    = "#010f1a"
    CARD      = "#00090f"
    CARD_B    = "#000e18"
    HOLOGRAM  = "#00d4ff06"
    # ── Borders ──────────────────────────────────────────────────────────────
    BORDER    = "#0a2535"
    BORDER_B  = "#1a5c7a"
    BORDER_A  = "#0d3a55"
    STEEL     = "#0f2a3a"
    # ── Arc reactor blue — primary energy ────────────────────────────────────
    PRI       = "#00c8ff"
    PRI_DIM   = "#006a88"
    PRI_GHO   = "#001520"
    PRI_GLOW  = "#00c8ff14"
    ENERGY    = "#00e5ff"
    ENERGY_D  = "#0088bb"
    # ── Accent colors ────────────────────────────────────────────────────────
    ACC       = "#ff8c00"
    ACC2      = "#ffb300"
    AMBER     = "#ffb300"
    AMBER_D   = "#cc8800"
    PURPLE    = "#7b61ff"
    PURPLE_D  = "#3d2fa0"
    GREEN     = "#00ff88"
    GREEN_D   = "#00aa55"
    GREEN_GLO = "#00ff8810"
    RED       = "#ff2244"
    RED_D     = "#aa1133"
    RED_BG    = "#200810"
    GREEN_BG  = "#001a0d"
    PURPLE_BG = "#0a0a14"
    MUTED_C   = "#ff3366"
    # ── Typography ───────────────────────────────────────────────────────────
    TEXT      = "#7ae8ff"
    TEXT_DIM  = "#1e5a6a"
    TEXT_MED  = "#3a9ab0"
    WHITE     = "#e8f8ff"
    WHITE_DIM = "#8ab8cc"


# ---------------------------------------------------------------------------
# ThemeManager — dynamic color theming with presets
# ---------------------------------------------------------------------------

class ThemeManager:
    """Manages color themes for the UI."""

    _COLOR_KEYS = (
        "BG", "PANEL", "PANEL2", "DARK", "DARK2", "BAR_BG", "CARD", "CARD_B",
        "BORDER", "BORDER_B", "BORDER_A", "STEEL", "PRI", "PRI_DIM", "PRI_GHO",
        "PRI_GLOW", "ENERGY", "ENERGY_D", "ACC", "ACC2", "PURPLE", "GREEN", "RED",
        "TEXT", "TEXT_DIM", "TEXT_MED", "WHITE", "WHITE_DIM", "RED_BG", "GREEN_BG",
        "PURPLE_BG", "MUTED_C", "HOLOGRAM", "AMBER", "AMBER_D", "PURPLE_D",
        "GREEN_D", "GREEN_GLO", "RED_D",
    )

    _THEMES = {
        "arc_reactor": {
            "name": "Arc Reactor Blue",
            "BG": "#000306",
            "PANEL": "#00080f",
            "PANEL2": "#000b14",
            "DARK": "#000408",
            "DARK2": "#000c18",
            "BAR_BG": "#010f1a",
            "CARD": "#00090f",
            "CARD_B": "#000e18",
            "BORDER": "#0a2535",
            "BORDER_B": "#1a5c7a",
            "BORDER_A": "#0d3a55",
            "STEEL": "#0f2a3a",
            "WHITE": "#e8f8ff",
            "WHITE_DIM": "#8ab8cc",
            "PRI": "#00c8ff", "PRI_DIM": "#006a88", "PRI_GHO": "#001520",
            "PRI_GLOW": "#00c8ff14", "ENERGY": "#00e5ff", "ENERGY_D": "#0088bb",
            "ACC": "#ff8c00", "ACC2": "#ffb300", "PURPLE": "#7b61ff",
            "GREEN": "#00ff88", "RED": "#ff2244", "TEXT": "#7ae8ff",
            "TEXT_DIM": "#1e5a6a", "TEXT_MED": "#3a9ab0",
            "RED_BG": "#200810", "GREEN_BG": "#001a0d", "PURPLE_BG": "#0a0a14",
            "MUTED_C": "#ff3366",
            "HOLOGRAM": "#00d4ff06", "AMBER": "#ffb300", "AMBER_D": "#cc8800",
            "PURPLE_D": "#3d2fa0", "GREEN_D": "#00aa55", "GREEN_GLO": "#00ff8810",
            "RED_D": "#aa1133",
        },
        "stealth_red": {
            "name": "Stealth Red",
            "BG": "#080203",
            "PANEL": "#0f0406",
            "PANEL2": "#140608",
            "DARK": "#040202",
            "DARK2": "#180810",
            "BAR_BG": "#1a0a10",
            "CARD": "#0f0406",
            "CARD_B": "#180810",
            "BORDER": "#350a15",
            "BORDER_B": "#7a1a2a",
            "BORDER_A": "#550d1a",
            "STEEL": "#3a0f1a",
            "WHITE": "#ffe8e8",
            "WHITE_DIM": "#cc8a8a",
            "PRI": "#ff2244", "PRI_DIM": "#881122", "PRI_GHO": "#200810",
            "PRI_GLOW": "#ff224414", "ENERGY": "#ff4466", "ENERGY_D": "#bb2244",
            "ACC": "#ff8c00", "ACC2": "#ffb300", "PURPLE": "#ff61a0",
            "GREEN": "#ff6644", "RED": "#ff2244", "TEXT": "#ffaaaa",
            "TEXT_DIM": "#6a2a2a", "TEXT_MED": "#b05a5a",
            "RED_BG": "#20060a", "GREEN_BG": "#1a0905", "PURPLE_BG": "#160710",
            "MUTED_C": "#ff6680",
            "HOLOGRAM": "#ff224406", "AMBER": "#ffb300", "AMBER_D": "#b87800",
            "PURPLE_D": "#7a2048", "GREEN_D": "#b93a28", "GREEN_GLO": "#ff664410",
            "RED_D": "#99152a",
        },
        "vibranium_purple": {
            "name": "Vibranium Purple",
            "BG": "#030108",
            "PANEL": "#06020f",
            "PANEL2": "#080314",
            "DARK": "#020104",
            "DARK2": "#0c0418",
            "BAR_BG": "#0f051a",
            "CARD": "#06020f",
            "CARD_B": "#0c0418",
            "BORDER": "#250a35",
            "BORDER_B": "#5a1a7a",
            "BORDER_A": "#3a0d55",
            "STEEL": "#2a0f3a",
            "WHITE": "#f0e8ff",
            "WHITE_DIM": "#a88acc",
            "PRI": "#a855f7", "PRI_DIM": "#6b21a8", "PRI_GHO": "#1a0530",
            "PRI_GLOW": "#a855f714", "ENERGY": "#c084fc", "ENERGY_D": "#7c3aed",
            "ACC": "#f472b6", "ACC2": "#fb923c", "PURPLE": "#a855f7",
            "GREEN": "#34d399", "RED": "#f43f5e", "TEXT": "#d8b4fe",
            "TEXT_DIM": "#4a2870", "TEXT_MED": "#8b5cf6",
            "RED_BG": "#210711", "GREEN_BG": "#041a13", "PURPLE_BG": "#160724",
            "MUTED_C": "#fb7185",
            "HOLOGRAM": "#a855f706", "AMBER": "#fb923c", "AMBER_D": "#c35d16",
            "PURPLE_D": "#6b21a8", "GREEN_D": "#168f68", "GREEN_GLO": "#34d39910",
            "RED_D": "#a81f3b",
        },
        "nanotech_gold": {
            "name": "Nanotech Gold",
            "BG": "#050400",
            "PANEL": "#0a0800",
            "PANEL2": "#0e0c00",
            "DARK": "#040300",
            "DARK2": "#141000",
            "BAR_BG": "#1a1500",
            "CARD": "#0a0800",
            "CARD_B": "#0e0c00",
            "BORDER": "#352a0a",
            "BORDER_B": "#7a5c1a",
            "BORDER_A": "#553a0d",
            "STEEL": "#3a2a0f",
            "WHITE": "#fffae8",
            "WHITE_DIM": "#ccb88a",
            "PRI": "#fbbf24", "PRI_DIM": "#a16207", "PRI_GHO": "#1a1000",
            "PRI_GLOW": "#fbbf2414", "ENERGY": "#fcd34d", "ENERGY_D": "#d97706",
            "ACC": "#f97316", "ACC2": "#fb923c", "PURPLE": "#c084fc",
            "GREEN": "#4ade80", "RED": "#ef4444", "TEXT": "#fef3c7",
            "TEXT_DIM": "#6a5a1e", "TEXT_MED": "#b09a3a",
            "RED_BG": "#210907", "GREEN_BG": "#061a0b", "PURPLE_BG": "#140c1c",
            "MUTED_C": "#fb7185",
            "HOLOGRAM": "#fbbf2406", "AMBER": "#fbbf24", "AMBER_D": "#a16207",
            "PURPLE_D": "#7e4aa0", "GREEN_D": "#228b4b", "GREEN_GLO": "#4ade8010",
            "RED_D": "#a72c2c",
        },
        "platinum": {
            "name": "Platinum White",
            "BG": "#e9edf2", "PANEL": "#f4f6f8", "PANEL2": "#eef1f5",
            "DARK": "#dfe4ea", "DARK2": "#d5dce4", "BAR_BG": "#d1d7df",
            "CARD": "#f8f9fb", "CARD_B": "#e6eaf0",
            "BORDER": "#b8c1cb", "BORDER_B": "#8795a4", "BORDER_A": "#a4afbb",
            "STEEL": "#c4ccd5", "WHITE": "#15202b", "WHITE_DIM": "#4d5d6c",
            "PRI": "#006f94", "PRI_DIM": "#3b8ca8", "PRI_GHO": "#dcebf1",
            "PRI_GLOW": "#006f9414", "ENERGY": "#0082a8", "ENERGY_D": "#005f7d",
            "ACC": "#a85c00", "ACC2": "#8b6500", "PURPLE": "#6652ad",
            "GREEN": "#18794e", "RED": "#c93443", "TEXT": "#263746",
            "TEXT_DIM": "#62717f", "TEXT_MED": "#405668",
            "RED_BG": "#f6e3e6", "GREEN_BG": "#dfeee6", "PURPLE_BG": "#e9e5f4",
            "MUTED_C": "#aa2735", "HOLOGRAM": "#006f9408",
            "AMBER": "#8b6500", "AMBER_D": "#6e5000", "PURPLE_D": "#493887",
            "GREEN_D": "#0f5f3b", "GREEN_GLO": "#18794e12", "RED_D": "#962432",
        },
    }

    _current = "arc_reactor"
    _listeners: list = []

    @classmethod
    def current_name(cls) -> str:
        return cls._current

    @classmethod
    def theme_names(cls) -> list[str]:
        return list(cls._THEMES.keys())

    @classmethod
    def theme_display_name(cls, key: str) -> str:
        return cls._THEMES.get(key, {}).get("name", key)

    @classmethod
    def set_theme(cls, key: str):
        if key not in cls._THEMES:
            return
        cls._current = key
        t = cls._THEMES[key]
        for attr in cls._COLOR_KEYS:
            if attr in t:
                setattr(C, attr, t[attr])
        for cb in cls._listeners:
            try:
                cb(key)
            except Exception:
                pass

    @classmethod
    def add_listener(cls, cb):
        cls._listeners.append(cb)
