"""Lazy action handler loader - imports modules only when first accessed."""
import sys
import importlib
from functools import lru_cache

_HANDLER_CACHE = {}
_MODULE_CACHE = {}

# Map action names to their module paths
ACTION_HANDLERS = {
    # Core handlers
    "mood_detector": ("actions.mood_detector", "VoiceMoodAnalyzer"),
    "conversation_memory": ("actions.conversation_memory", "ConversationMemory"),
    "tts_engine": ("actions.tts_engine", "TTSEngine"),
    "screen_awareness": ("actions.screen_awareness", "ScreenAwareness"),
    "real_hustle": ("actions.real_hustle", "SideHustleEngine"),
    "product_enricher": ("actions.product_enricher", "enrich_product"),
    "pres_sources": ("actions.presentations.sources", None),
    "pres_quality": ("actions.presentations.quality", None),
    "pres_models3d": ("actions.presentations.models3d", None),
    "pres_models": ("actions.presentations.models", None),
    "pres_assets": ("actions.presentations.assets", None),
    "daily_briefing": ("actions.daily_briefing", "get_weather_summary"),
    "calendar_control": ("actions.calendar_control", "list_events"),
    "open_app": ("actions.open_app", "open_app"),
    "weather_report": ("actions.weather_report", "weather_action"),
    "browser_control": ("actions.browser_control", "browser_control"),
    "file_controller": ("actions.file_controller", "file_controller"),
    "message_monitor": ("actions.message_monitor", "check_messages"),
    "send_message": ("actions.send_message", "send_message"),
    "prepare_message_reply": ("actions.send_message", "prepare_message_reply"),
    "screen_automation": ("actions.screen_automation", "handle"),
    "email_control": ("actions.email_control", "email_control"),
    "reminder": ("actions.reminder", "reminder"),
    "youtube_video": ("actions.youtube_video", "youtube_video"),
    "media_control": ("actions.media_control", "media_control"),
    "screen_processor": ("actions.screen_processor", "screen_process"),
    "computer_settings": ("actions.computer_settings", "computer_settings"),
    "desktop_control": ("actions.desktop", "desktop_control"),
    "code_helper": ("actions.code_helper", "code_helper"),
    "dev_agent": ("actions.dev_agent", "dev_agent"),
    "web_search": ("actions.web_search", "web_search"),
    "file_processor": ("actions.file_processor", "file_processor"),
    "computer_control": ("actions.computer_control", "computer_control"),
    "game_updater": ("actions.game_updater", "game_updater"),
    "flight_finder": ("actions.flight_finder", "flight_finder"),
    "deep_research": ("actions.deep_research", "request_deep_research"),
    "presentation_maker": ("actions.presentation_maker", "request_presentation"),
    "system_info": ("actions.system_info", "handle"),
    "bluetooth_control": ("actions.bluetooth_control", "handle"),
    "wifi_control": ("actions.wifi_control", "handle"),
    "calendar_handle": ("actions.calendar_control", "handle"),
    "autonomous_agent": ("actions.autonomous_agent", "handle"),
    "market_monitor": ("actions.market_monitor", "handle"),
    "briefing_handle": ("actions.daily_briefing", "handle"),
    "contact_handle": ("actions.contact_manager", "handle"),
    "taskbar_detect": ("actions.taskbar_detect", None),
    "full_control": ("actions.full_control", "handle"),
    "cybersec_tools": ("actions.cybersec_tools", "handle"),
    "proactive_monitor": ("actions.proactive_monitor", "handle"),
    "system_cleanup": ("actions.system_cleanup", "handle"),
    "sing": ("actions.sing", "handle"),
    "proactive_tasks": ("actions.proactive_tasks", "handle"),
    "phone_control": ("actions.phone_control", "handle"),
    "phone_comms": ("actions.phone_comms", "PhoneCommsAgent"),
    "coding_assistant": ("actions.coding_assistant", "handle"),
    "learning_memory": ("actions.learning_memory", "handle"),
    "notification_center": ("actions.notification_center", "handle"),
    "clipboard_manager": ("actions.clipboard_manager", "handle"),
    "alarm_timer": ("actions.alarm_timer", "handle"),
    "smart_assistant": ("actions.smart_assistant", "handle"),
    "system_access": ("actions.system_access", "handle"),
    "self_control": ("actions.self_control", "handle"),
    "autonomous_brain": ("actions.autonomous_brain", "handle"),
    "money_makers": ("actions.money_makers", "handle"),
    "marketing_engine": ("actions.marketing_engine", "handle"),
    "namibian_payments": ("actions.namibian_payments", "handle"),
    "gumroad_api": ("actions.gumroad_api", "handle"),
    "social_media": ("actions.social_media", "handle"),
    "content_engine": ("actions.content_engine", "ContentEngineAgent"),
    "self_evolution": ("actions.self_evolution", "handle"),
    "auto_start": ("actions.auto_start", "handle"),
    "autonomous_worker": ("actions.autonomous_worker", "AutonomousWorker"),
    "account_manager": ("actions.account_manager", "handle"),
    "noise_filter": ("actions.noise_filter", "SpeechNoiseFilter"),
    "instagram_browser": ("actions.instagram_browser", None),
    "safe_text_entry": ("actions.safe_text_entry", None),
    "camera_control": ("actions.camera_control", "handle"),
    "phone_tracking": ("actions.phone_tracking", "handle"),
    "smart_home": ("actions.smart_home", "SmartHomeAgent"),
    "vehicle_control": ("actions.vehicle_control", "handle"),
    "cybersecurity": ("actions.cybersecurity", "handle"),
    "data_analysis": ("actions.data_analysis", "handle"),
    "automation_engine": ("actions.automation_engine", "handle"),
    "stripe_payments": ("actions.stripe_payments", "handle"),
    "trading_orchestration": ("actions.trading_orchestration", "TradingOrchestrationAgent"),
    "opportunity_discovery": ("actions.opportunity_discovery", "OpportunityDiscoveryAgent"),
    "reconciliation": ("actions.reconciliation", "handle"),
    "jarvis_file_stamp": ("actions.jarvis_file_stamp", None),
    "learning_memory_func": ("actions.learning_memory", "track_pattern"),
    "screen_processor_capture": ("actions.screen_processor", "_capture_screen"),
    "notification_push": ("actions.notification_center", "push_notification"),
    "autonomous_agent_check": ("actions.autonomous_agent", "_check_disk_space"),
    "calendar_events": ("actions.calendar_control", "list_events"),
    "proactive_pending": ("actions.proactive_tasks", "get_pending_jobs"),
    "learning_context": ("actions.learning_memory", "set_context"),
    "proactive_mark": ("actions.proactive_tasks", "mark_job_run"),
    "autonomous_brain_handle": ("actions.autonomous_brain", "handle"),
}

# Special handlers that need module objects (not just a function/class)
MODULE_HANDLERS = {
    "taskbar_detect": "actions.taskbar_detect",
    "instagram_browser": "actions.instagram_browser",
    "safe_text_entry": "actions.safe_text_entry",
    "jarvis_file_stamp": "actions.jarvis_file_stamp",
}


def _import_module(module_name: str):
    """Import and cache a module."""
    if module_name not in _MODULE_CACHE:
        _MODULE_CACHE[module_name] = importlib.import_module(module_name)
    return _MODULE_CACHE[module_name]


def get_handler(name: str):
    """Get an action handler by name, loading it on first access."""
    if name in _HANDLER_CACHE:
        return _HANDLER_CACHE[name]
    
    if name in ACTION_HANDLERS:
        module_name, attr = ACTION_HANDLERS[name]
        try:
            module = _import_module(module_name)
            if attr:
                handler = getattr(module, attr)
            else:
                handler = module
        except Exception:
            handler = None
    elif name in MODULE_HANDLERS:
        try:
            handler = _import_module(MODULE_HANDLERS[name])
        except Exception:
            handler = None
    else:
        handler = None
    
    _HANDLER_CACHE[name] = handler
    return handler


def get_module(name: str):
    """Get a full module by name, loading it on first access."""
    if name in _MODULE_CACHE:
        return _MODULE_CACHE[name]
    try:
        _MODULE_CACHE[name] = importlib.import_module(name)
        return _MODULE_CACHE[name]
    except Exception:
        return None


def preload_handlers(*names):
    """Preload specific handlers (useful for critical paths)."""
    for name in names:
        get_handler(name)


# For backward compatibility - expose as module attributes
def __getattr__(name: str):
    return get_handler(name)


def __dir__():
    return sorted(set(list(ACTION_HANDLERS.keys()) + list(MODULE_HANDLERS.keys()) + list(_HANDLER_CACHE.keys())))
