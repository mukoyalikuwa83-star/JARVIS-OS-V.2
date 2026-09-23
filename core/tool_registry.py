# Auto-extracted TOOL_DECLARATIONS from main.py
# Do not modify manually — edit source in main.py or regenerate.

TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": (
            "Opens any application on the computer. "
            "Use this whenever the user asks to open, launch, or start any app, "
            "website, or program. Always call this tool — never just say you opened it."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "web_search",
        "description": "Searches the web for any information.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query":  {"type": "STRING", "description": "Search query"},
                "mode":   {"type": "STRING", "description": "search (default) or compare"},
                "items":  {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Items to compare"},
                "aspect": {"type": "STRING", "description": "price | specs | reviews"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "weather_report",
        "description": "Gives the weather report to user",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "City name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "check_messages",
        "description": (
            "Reads the current Instagram or Apple Messages conversation and optionally searches Contacts. "
            "Use this before drafting a reply or when the user asks about recent messages."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "platform": {"type": "STRING", "description": "all | Instagram | iMessage | Contacts. Default: all."},
                "include_contacts": {"type": "BOOLEAN", "description": "Also search the user's Contacts."},
                "contact_query": {"type": "STRING", "description": "Optional spoken contact name to match."},
                "max_messages": {"type": "INTEGER", "description": "Maximum current-chat lines to inspect. Default: 30."}
            },
            "required": []
        }
    },
    {
        "name": "prepare_message_reply",
        "description": (
            "Creates an approval-gated message draft, approves the current pending draft, or cancels it. "
            "Never approve unless the user explicitly confirms the exact pending draft."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "enum": ["prepare", "approve", "cancel"], "description": "Draft lifecycle action."},
                "platform": {"type": "STRING", "description": "Instagram, iMessage, WhatsApp, Telegram, or another supported platform."},
                "receiver": {"type": "STRING", "description": "Recipient name. Optional for the currently open chat."},
                "message_text": {"type": "STRING", "description": "Exact draft text, required for prepare."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "send_message",
        "description": (
            "Sends a user-authored message through iMessage, WhatsApp, Telegram, Instagram, Discord, or the current chat. "
            "For Instagram, the first call prepares a visible draft; use action=approve only after explicit user confirmation."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":       {"type": "STRING", "enum": ["send", "approve", "cancel"], "description": "Default: send. Approve/cancel operates on the pending draft."},
                "receiver":     {"type": "STRING", "description": "Recipient contact name. Optional for current/focused chats and approval actions."},
                "message_text": {"type": "STRING", "description": "Exact message content. Required for send."},
                "platform":     {"type": "STRING", "description": "iMessage, WhatsApp, Telegram, Instagram, Discord, or current/focused."}
            },
            "required": ["platform"]
        }
    },
    {
        "name": "email_control",
        "description": (
            "Connects Gmail through Google OAuth, checks connection status, reads/searches Gmail, and prepares email. "
            "Gmail is the default provider; Apple Mail remains an optional macOS fallback. "
            "For Gmail, prepare opens a visible compose window and types To, Cc/Bcc, Subject, and Body in sequence. "
            "Every outgoing email is approval-gated: first call action=prepare, then call action=approve "
            "only after the user explicitly confirms the exact pending recipient, subject, and body."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["connect", "status", "disconnect", "inbox", "unread", "search", "read", "prepare", "approve", "cancel"],
                    "description": "Email operation."
                },
                "provider": {
                    "type": "STRING",
                    "enum": ["gmail", "apple_mail", "default"],
                    "description": "Email provider. Default: gmail."
                },
                "browser": {
                    "type": "STRING",
                    "description": "Browser for the visible Gmail compose window. Default: chrome."
                },
                "credentials_path": {
                    "type": "STRING",
                    "description": "Path to a Google Desktop OAuth client JSON file, used only for connect."
                },
                "limit": {"type": "INTEGER", "description": "Maximum inbox/search results, 1-30."},
                "query": {"type": "STRING", "description": "Sender or subject text for search."},
                "message_id": {"type": "STRING", "description": "Message ID returned by inbox/search, required for read."},
                "to": {"type": "STRING", "description": "Recipient email address or comma-separated addresses."},
                "cc": {"type": "STRING", "description": "Optional Cc addresses."},
                "bcc": {"type": "STRING", "description": "Optional Bcc addresses."},
                "subject": {"type": "STRING", "description": "Exact email subject for prepare."},
                "body": {"type": "STRING", "description": "Exact email body for prepare."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "reminder",
        "description": "Sets a timed reminder using Task Scheduler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date":    {"type": "STRING", "description": "Date in YYYY-MM-DD format"},
                "time":    {"type": "STRING", "description": "Time in HH:MM format (24h)"},
                "message": {"type": "STRING", "description": "Reminder message text"}
            },
            "required": ["date", "time", "message"]
        }
    },
    {
        "name": "youtube_video",
        "description": (
            "Controls YouTube. Use for: playing videos, summarizing a video's content, "
            "getting video info, or showing trending videos."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play | summarize | get_info | trending (default: play)"},
                "query":  {"type": "STRING", "description": "Search query for play action"},
                "save":   {"type": "BOOLEAN", "description": "Save summary to Notepad (summarize only)"},
                "region": {"type": "STRING", "description": "Country code for trending e.g. TR, US"},
                "url":    {"type": "STRING", "description": "Video URL for get_info action"},
            },
            "required": []
        }
    },
    {
        "name": "media_control",
        "description": (
            "Controls music playback, primarily Spotify. Use when the user asks to play, resume, pause, "
            "stop, toggle, skip, or go back in Spotify, Apple Music, YouTube Music, or the active media player. "
            "Spotify is the default platform. Pass a song, artist, album, playlist, or Spotify link in query."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["play", "pause", "stop", "toggle", "next", "previous", "play_query"],
                    "description": "Playback command. Use play_query to find a specific song or other item."
                },
                "platform": {
                    "type": "STRING",
                    "enum": ["spotify", "apple_music", "youtube_music", "system"],
                    "description": "Music platform. Default: spotify."
                },
                "query": {
                    "type": "STRING",
                    "description": "Song, artist, album, playlist, or Spotify link for play/play_query."
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "screen_process",
        "description": (
            "Captures and analyzes the screen or webcam image. "
            "MUST be called when user asks what is on screen, what you see, "
            "analyze my screen, look at camera, etc. "
            "You have NO visual ability without this tool. "
            "After calling this tool, stay SILENT — the vision module speaks directly."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"},
                "text":  {"type": "STRING", "description": "The question or instruction about the captured image"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "computer_settings",
        "description": (
            "Controls the computer: volume, brightness, window management, keyboard shortcuts, "
            "typing text on screen, closing apps, fullscreen, dark mode, WiFi, restart, shutdown, "
            "scrolling, tab management, zoom, screenshots, lock screen, refresh/reload page. "
            "Use for ANY single computer control command. NEVER route to agent_task."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "The action to perform"},
                "description": {"type": "STRING", "description": "Natural language description of what to do"},
                "value":       {"type": "STRING", "description": "Optional value: volume level, text to type, etc."}
            },
            "required": []
        }
    },
    {
        "name": "browser_control",
        "description": (
            "Controls any web browser. Use for: opening websites, searching the web, "
            "clicking elements, filling forms, scrolling, screenshots, navigation, any web-based task. "
            "Always pass the 'browser' parameter when the user specifies a browser (e.g. 'open in Edge', "
            "'use Firefox', 'open Chrome'). Multiple browsers can run simultaneously."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "go_to | search | click | type | scroll | fill_form | smart_click | smart_type | get_text | get_url | press | new_tab | close_tab | screenshot | back | forward | reload | switch | list_browsers | close | close_all | search_jobs | submit_proposal | open_dashboard | open_messages | open_job | automation_log"},
                "browser":     {"type": "STRING", "description": "Target browser: chrome | edge | firefox | opera | operagx | brave | vivaldi | safari. Omit to use the currently active browser."},
                "url":         {"type": "STRING", "description": "URL for go_to / new_tab action"},
                "query":       {"type": "STRING", "description": "Search query for search action"},
                "engine":      {"type": "STRING", "description": "Search engine: google | bing | duckduckgo | yandex (default: google)"},
                "selector":    {"type": "STRING", "description": "CSS selector for click/type"},
                "text":        {"type": "STRING", "description": "Text to click or type"},
                "description": {"type": "STRING", "description": "Element description for smart_click/smart_type"},
                "direction":   {"type": "STRING", "description": "up | down for scroll"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount in pixels (default: 500)"},
                "key":         {"type": "STRING", "description": "Key name for press action (e.g. Enter, Escape, F5)"},
                "path":        {"type": "STRING", "description": "Save path for screenshot"},
                "incognito":   {"type": "BOOLEAN", "description": "Open in private/incognito mode"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_controller",
        "description": "Manages and opens local files and folders: open, list, create, delete, move, copy, rename, read, write, find, disk usage. Use action=open for a file path; do not use open_app for files.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "open | list | create_file | create_folder | delete | move | copy | rename | read | write | find | largest | disk_usage | organize_desktop | info"},
                "path":        {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home"},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name":    {"type": "STRING", "description": "New name for rename"},
                "content":     {"type": "STRING", "description": "Content for create_file/write"},
                "name":        {"type": "STRING", "description": "File name to search for"},
                "extension":   {"type": "STRING", "description": "File extension to search (e.g. .pdf)"},
                "count":       {"type": "INTEGER", "description": "Number of results for largest"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "desktop_control",
        "description": "Controls the desktop: wallpaper, organize, clean, list, stats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "wallpaper | wallpaper_url | organize | clean | list | stats | task"},
                "path":   {"type": "STRING", "description": "Image path for wallpaper"},
                "url":    {"type": "STRING", "description": "Image URL for wallpaper_url"},
                "mode":   {"type": "STRING", "description": "by_type or by_date for organize"},
                "task":   {"type": "STRING", "description": "Natural language desktop task"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_helper",
        "description": "Writes, edits, explains, runs, or builds code files.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "write | edit | explain | run | build | auto (default: auto)"},
                "description": {"type": "STRING", "description": "What the code should do or what change to make"},
                "language":    {"type": "STRING", "description": "Programming language (default: python)"},
                "output_path": {"type": "STRING", "description": "Where to save the file"},
                "file_path":   {"type": "STRING", "description": "Path to existing file for edit/explain/run/build"},
                "code":        {"type": "STRING", "description": "Raw code string for explain"},
                "args":        {"type": "STRING", "description": "CLI arguments for run/build"},
                "timeout":     {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "dev_agent",
        "description": "Builds complete multi-file projects from scratch: plans, writes files, installs deps, opens VSCode, runs and fixes errors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description":  {"type": "STRING", "description": "What the project should do"},
                "language":     {"type": "STRING", "description": "Programming language (default: python)"},
                "project_name": {"type": "STRING", "description": "Optional project folder name"},
                "timeout":      {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"},
            },
            "required": ["description"]
        }
    },
    {
        "name": "agent_task",
        "description": (
            "Executes complex multi-step tasks requiring multiple different tools. "
            "Examples: 'research X and save to file', 'find and organize files'. "
            "DO NOT use for single commands. NEVER use for Steam/Epic — use game_updater."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal":     {"type": "STRING", "description": "Complete description of what to accomplish"},
                "priority": {"type": "STRING", "description": "low | normal | high (default: normal)"}
            },
            "required": ["goal"]
        }
    },
    {
        "name": "computer_control",
        "description": "Direct computer control: type, click, hotkeys, scroll, move mouse, screenshots, find elements on screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "type | smart_type | click | double_click | right_click | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | screen_find | screen_click | random_data | user_data"},
                "text":        {"type": "STRING", "description": "Text to type or paste"},
                "x":           {"type": "INTEGER", "description": "X coordinate"},
                "y":           {"type": "INTEGER", "description": "Y coordinate"},
                "keys":        {"type": "STRING", "description": "Key combination e.g. 'ctrl+c'"},
                "key":         {"type": "STRING", "description": "Single key e.g. 'enter'"},
                "direction":   {"type": "STRING", "description": "up | down | left | right"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount (default: 3)"},
                "seconds":     {"type": "NUMBER",  "description": "Seconds to wait"},
                "title":       {"type": "STRING",  "description": "Window title for focus_window"},
                "description": {"type": "STRING",  "description": "Element description for screen_find/screen_click"},
                "type":        {"type": "STRING",  "description": "Data type for random_data"},
                "field":       {"type": "STRING",  "description": "Field for user_data: name|email|city"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
                "path":        {"type": "STRING",  "description": "Save path for screenshot"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "game_updater",
        "description": (
            "THE ONLY tool for ANY Steam or Epic Games request. "
            "Use for: installing, downloading, updating games, listing installed games, "
            "checking download status, scheduling updates. "
            "ALWAYS call directly for any Steam/Epic/game request. "
            "NEVER use agent_task, browser_control, or web_search for Steam/Epic."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING",  "description": "update | install | list | download_status | schedule | cancel_schedule | schedule_status (default: update)"},
                "platform":  {"type": "STRING",  "description": "steam | epic | both (default: both)"},
                "game_name": {"type": "STRING",  "description": "Game name (partial match supported)"},
                "app_id":    {"type": "STRING",  "description": "Steam AppID for install (optional)"},
                "hour":      {"type": "INTEGER", "description": "Hour for scheduled update 0-23 (default: 3)"},
                "minute":    {"type": "INTEGER", "description": "Minute for scheduled update 0-59 (default: 0)"},
                "shutdown_when_done": {"type": "BOOLEAN", "description": "Shut down PC when download finishes"},
            },
            "required": []
        }
    },
    {
        "name": "flight_finder",
        "description": "Searches Google Flights and speaks the best options.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "origin":      {"type": "STRING",  "description": "Departure city or airport code"},
                "destination": {"type": "STRING",  "description": "Arrival city or airport code"},
                "date":        {"type": "STRING",  "description": "Departure date (any format)"},
                "return_date": {"type": "STRING",  "description": "Return date for round trips"},
                "passengers":  {"type": "INTEGER", "description": "Number of passengers (default: 1)"},
                "cabin":       {"type": "STRING",  "description": "economy | premium | business | first"},
                "save":        {"type": "BOOLEAN", "description": "Save results to Notepad"},
            },
            "required": ["origin", "destination", "date"]
        }
    },
    {
        "name": "jarvis_ui_control",
        "description": (
            "Changes the assistant's own interface. Use when the user asks to open or close the Command Center, "
            "change the theme or graphics quality, open settings, enter compact mode, toggle fullscreen, or show shortcuts."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["open_command_center", "close_command_center", "change_theme", "change_graphics_quality", "open_settings", "compact_mode", "fullscreen", "show_shortcuts"],
                    "description": "The interface action to perform."
                },
                "theme": {
                    "type": "STRING",
                    "enum": ["arc_reactor", "stealth_red", "vibranium_purple", "nanotech_gold", "platinum"],
                    "description": "Required for change_theme."
                },
                "graphics_quality": {
                    "type": "STRING",
                    "enum": ["low", "medium", "high"],
                    "description": "Required for change_graphics_quality. Low favors performance, medium is balanced, and high enables full visual detail."
                },
            },
            "required": ["action"]
        }
    },
    {
        "name": "deep_research",
        "description": (
            "Runs rigorous, multi-query web research and keeps the report in volatile memory unless the user asks to save it. "
            "Use when the user explicitly asks for deep, thorough, comprehensive, or source-backed research. "
            "On the first call, ask whether the user wants a background status bar or visible browser research. "
            "After completion, use this tool again to save the latest report or read it aloud."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "question": {
                    "type": "STRING",
                    "description": "The research question. Required on the initial ask call; optional when confirming a pending request."
                },
                "execution_mode": {
                    "type": "STRING",
                    "enum": ["ask", "background", "visible"],
                    "description": "Always use ask initially. Background shows a labeled status bar; visible opens a controlled browser and visits sources."
                },
                "result_action": {
                    "type": "STRING",
                    "enum": ["none", "save_files", "save_desktop", "read_report"],
                    "description": "Action for the latest completed in-memory report. Use only after the user chooses one of these options."
                },
                "depth": {
                    "type": "STRING",
                    "enum": ["quick", "standard", "deep"],
                    "description": "Research breadth. Default: standard."
                },
                "focus_areas": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "Optional angles, constraints, or subtopics to prioritize."
                },
                "max_sources": {
                    "type": "INTEGER",
                    "description": "Maximum verified source links to retain, from 5 to 50."
                },
                "output_path": {
                    "type": "STRING",
                    "description": "Optional explicit path used only with save_files or save_desktop. Research never saves automatically."
                },
            },
            "required": []
        }
    },
    {
        "name": "create_presentation",
        "description": (
            "Creates, edits, redesigns, or extends an editable Microsoft PowerPoint (.pptx) presentation. "
            "Use this directly whenever the user asks to make a PowerPoint, presentation, "
            "slide deck, pitch deck, briefing deck, or slideshow. Do not use code_helper, "
            "file_processor, computer_control, or agent_task. First ask whether the user wants "
            "a native 3D model, then ask whether they want to see the task or keep it in the background."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "topic": {
                    "type": "STRING",
                    "description": "Subject, goal, and important content instructions. Required on the initial ask; optional when confirming the pending run mode."
                },
                "execution_mode": {
                    "type": "STRING",
                    "enum": ["ask", "background", "visible"],
                    "description": "Always use ask initially. Visible shows real build phases; background keeps a compact status indicator."
                },
                "mode": {
                    "type": "STRING",
                    "description": "auto | create | edit | redesign | extend. Default: auto."
                },
                "title": {
                    "type": "STRING",
                    "description": "Optional presentation title."
                },
                "audience": {
                    "type": "STRING",
                    "description": "Who will view the presentation, such as executives, investors, clients, or students."
                },
                "slide_count": {
                    "type": "INTEGER",
                    "description": "Final slide count from 3 to 50. Default: inferred or 8."
                },
                "tone": {
                    "type": "STRING",
                    "description": "Desired writing and visual tone, such as executive, persuasive, technical, or educational."
                },
                "theme": {
                    "type": "STRING",
                    "description": "Visual theme: minimal | editorial | executive | platinum. Default: minimal."
                },
                "appearance": {
                    "type": "STRING",
                    "enum": ["auto", "light", "dark"],
                    "description": "Overall slide appearance. Honor light or dark when requested; auto uses the restrained dark style."
                },
                "transition": {
                    "type": "STRING",
                    "enum": ["morph", "fade", "none"],
                    "description": "Native PowerPoint slide transition. Default: morph, with a fade fallback for older PowerPoint versions."
                },
                "source_file": {
                    "type": "STRING",
                    "description": "Backward-compatible single source path. Leave empty to use the uploaded file."
                },
                "source_files": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "Source paths: PDF, Office files, data, text, images, audio, video, or PowerPoint."
                },
                "source_urls": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "Specific source URLs supplied by the user."
                },
                "template_file": {
                    "type": "STRING",
                    "description": "Existing PPTX template or deck to preserve for edit/extend operations."
                },
                "model_source_file": {
                    "type": "STRING",
                    "description": "A PPTX used only as a native 3D model library. Its slides and text are not copied into the new presentation."
                },
                "use_native_3d": {
                    "type": "BOOLEAN",
                    "description": "The user's answer to the 3D-model question. Omit on the initial call unless the user already explicitly answered."
                },
                "three_d_mode": {
                    "type": "STRING",
                    "enum": ["ask", "yes", "no"],
                    "description": "Use ask on the initial call unless the user already explicitly requested or rejected 3D."
                },
                "quality": {
                    "type": "STRING",
                    "description": "fast | quality | premium. Default: quality."
                },
                "language": {
                    "type": "STRING",
                    "description": "Optional output language; otherwise infer from the request."
                },
                "allow_web_research": {
                    "type": "BOOLEAN",
                    "description": "Use broader web research. Set true only after the user explicitly permits web search."
                },
                "export_pdf": {
                    "type": "BOOLEAN",
                    "description": "Also export a PDF when Microsoft PowerPoint is available. Default: true."
                },
                "include_speaker_notes": {
                    "type": "BOOLEAN",
                    "description": "Generate editable speaker notes. Default: false."
                },
                "output_path": {
                    "type": "STRING",
                    "description": "Optional .pptx output path or destination folder."
                },
                "open_after_create": {
                    "type": "BOOLEAN",
                    "description": "Open the finished PowerPoint after creation. Default: false."
                },
            },
            "required": []
        }
    },
    {
        "name": "task_status",
        "description": "Checks or cancels background jobs, including presentation and deep-research jobs.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "get | all | cancel. Default: get."
                },
                "task_id": {
                    "type": "STRING",
                    "description": "Background task ID for get or cancel."
                },
            },
            "required": []
        }
    },
    {
    "name": "file_processor",
    "description": (
        "Processes any file that the user has uploaded or dropped onto the interface. "
        "Use this when the user refers to an uploaded file and wants an action on it. "
        "Supports: images (describe/ocr/resize/compress/convert), "
        "PDFs (summarize/extract_text/to_word), "
        "Word docs & text files (summarize/fix/reformat/translate), "
        "CSV/Excel (analyze/stats/filter/sort/convert), "
        "JSON/XML (validate/format/analyze), "
        "code files (explain/review/fix/optimize/run/document/test), "
        "audio (transcribe/trim/convert/info), "
        "video (trim/extract_audio/extract_frame/compress/transcribe/info), "
        "archives (list/extract), "
        "presentations (summarize/extract_text). "
        "ALWAYS call this tool when a file has been uploaded and the user gives a command about it. "
        "If the user's command is ambiguous, pick the most logical action for that file type."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {
                "type": "STRING",
                "description": "Full path to the uploaded file. Leave empty to use the currently uploaded file."
            },
            "action": {
                "type": "STRING",
                "description": (
                    "What to do with the file. Examples by type:\n"
                    "image: describe | ocr | resize | compress | convert | info\n"
                    "pdf: summarize | extract_text | to_word | info\n"
                    "docx/txt: summarize | fix | reformat | translate_hint | word_count | to_bullet\n"
                    "csv/excel: analyze | stats | filter | sort | convert | info\n"
                    "json: validate | format | analyze | to_csv\n"
                    "code: explain | review | fix | optimize | run | document | test\n"
                    "audio: transcribe | trim | convert | info\n"
                    "video: trim | extract_audio | extract_frame | compress | transcribe | info | convert\n"
                    "archive: list | extract\n"
                    "pptx: summarize | extract_text | analyze"
                )
            },
            "instruction": {
                "type": "STRING",
                "description": "Free-form instruction if action doesn't cover it. E.g. 'translate this to Turkish', 'find all email addresses'"
            },
            "format": {
                "type": "STRING",
                "description": "Target format for conversion. E.g. 'mp3', 'pdf', 'csv', 'png'"
            },
            "width":     {"type": "INTEGER", "description": "Target width for image resize"},
            "height":    {"type": "INTEGER", "description": "Target height for image resize"},
            "scale":     {"type": "NUMBER",  "description": "Scale factor for image resize (e.g. 0.5)"},
            "quality":   {"type": "INTEGER", "description": "Quality 1-100 for image/video compress"},
            "start":     {"type": "STRING",  "description": "Start time for trim: seconds or HH:MM:SS"},
            "end":       {"type": "STRING",  "description": "End time for trim: seconds or HH:MM:SS"},
            "timestamp": {"type": "STRING",  "description": "Timestamp for video frame extraction HH:MM:SS"},
            "column":    {"type": "STRING",  "description": "Column name for CSV filter/sort"},
            "value":     {"type": "STRING",  "description": "Filter value for CSV filter"},
            "condition": {"type": "STRING",  "description": "Filter condition: equals|contains|gt|lt"},
            "ascending": {"type": "BOOLEAN", "description": "Sort order for CSV sort (default: true)"},
            "save":      {"type": "BOOLEAN", "description": "Save result to file (default: true)"},
            "destination": {"type": "STRING", "description": "Output folder for archive extract"},
        },
        "required": []
    }
},
    {
        "name": "save_memory",
        "description": (
            "Save an important personal fact about the user to long-term memory. "
            "Call this silently whenever the user reveals something worth remembering: "
            "name, age, city, job, preferences, hobbies, relationships, projects, or future plans. "
            "Do NOT call for: weather, reminders, searches, or one-time commands. "
            "Do NOT announce that you are saving — just call it silently. "
            "Values must be in English regardless of the conversation language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": (
                        "identity — name, age, birthday, city, job, language, nationality | "
                        "preferences — favorite food/color/music/film/game/sport, hobbies | "
                        "projects — active projects, goals, things being built | "
                        "relationships — friends, family, partner, colleagues | "
                        "wishes — future plans, things to buy, travel dreams | "
                        "notes — habits, schedule, anything else worth remembering"
                    )
                },
                "key":   {"type": "STRING", "description": "Short snake_case key (e.g. name, favorite_food, sister_name)"},
                "value": {"type": "STRING", "description": "Concise value in English (e.g. Fatih, pizza, older sister)"},
            },
            "required": ["category", "key", "value"]
        }
    },
    {
        "name": "system_info",
        "description": (
            "Gets real-time system information: time, date, battery, CPU, RAM, disk usage, network status, "
            "IP address, and WiFi details. Use this whenever the user asks about the time, date, system status, "
            "battery level, storage space, internet connection, or any system-level information."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["all", "time", "battery", "cpu", "ram", "disk", "network", "wifi"],
                    "description": "What info to return. Default: all."
                }
            },
            "required": []
        }
    },
    {
        "name": "bluetooth_control",
        "description": (
            "Controls Bluetooth: scan for devices, pair, connect, disconnect, toggle on/off, check status. "
            "Use this when the user asks about Bluetooth, wants to connect a device, or check Bluetooth status."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["status", "scan", "connect", "disconnect", "toggle", "pair"],
                    "description": "Bluetooth action. Default: status."
                },
                "address": {"type": "STRING", "description": "MAC address of the Bluetooth device (for connect/disconnect/pair)"},
                "name": {"type": "STRING", "description": "Device name (for connect/disconnect)"},
                "enable": {"type": "BOOLEAN", "description": "For toggle: true=enable, false=disable"},
                "duration": {"type": "INTEGER", "description": "Scan duration in seconds (for scan). Default: 8."}
            },
            "required": []
        }
    },
    {
        "name": "wifi_control",
        "description": (
            "Controls WiFi: scan available networks, connect/disconnect, show saved profiles, toggle WiFi on/off, "
            "show current connection status, IP address, signal strength. Use this whenever the user asks about "
            "WiFi, wants to connect to a network, or check internet connection details."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["status", "scan", "connect", "disconnect", "profiles", "toggle"],
                    "description": "WiFi action. Default: status."
                },
                "ssid": {"type": "STRING", "description": "Network name (for connect)"},
                "password": {"type": "STRING", "description": "WiFi password (for connect)"},
                "enable": {"type": "BOOLEAN", "description": "For toggle: true=enable, false=disable"}
            },
            "required": []
        }
    },
    {
        "name": "calendar_control",
        "description": (
            "Manages Google Calendar via browser: create events, list upcoming events, delete events. "
            "Use this when the user asks about their schedule, wants to create a meeting, or manage calendar events."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["create", "list", "delete"],
                    "description": "Calendar action."
                },
                "title": {"type": "STRING", "description": "Event title (for create/delete)"},
                "date": {"type": "STRING", "description": "Event date: 'today', 'tomorrow', 'next monday', or YYYY-MM-DD"},
                "time": {"type": "STRING", "description": "Event time in HH:MM format (24h)"},
                "duration": {"type": "INTEGER", "description": "Duration in minutes (default: 60)"},
                "description": {"type": "STRING", "description": "Event description"},
                "location": {"type": "STRING", "description": "Event location"},
                "browser": {"type": "STRING", "description": "Browser to use. Default: chrome."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "autonomous_control",
        "description": (
            "Controls autonomous agent behavior: start/stop monitoring, add scheduled rules, check system health, "
            "view alerts, set auto-actions. Use this when the user wants the assistant to proactively monitor "
            "the system, schedule recurring checks, or set up automatic responses to conditions."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["start", "stop", "add_rule", "remove_rule", "list_rules", "check_now", "get_alerts", "set_auto_action", "status"],
                    "description": "Autonomous agent action."
                },
                "type": {"type": "STRING", "description": "Monitor type: all, disk, battery, network (for start)"},
                "interval": {"type": "INTEGER", "description": "Check interval in seconds (for start). Default: 300."},
                "time": {"type": "STRING", "description": "Time for daily rules (HH:MM)"},
                "message": {"type": "STRING", "description": "Rule description/message"},
                "action_name": {"type": "STRING", "description": "Action to perform when rule triggers"},
                "index": {"type": "INTEGER", "description": "Rule index to remove"},
                "trigger": {"type": "STRING", "description": "Trigger condition (for set_auto_action)"},
                "limit": {"type": "INTEGER", "description": "Number of alerts to return (for get_alerts). Default: 10."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "market_monitor",
        "description": (
            "Monitor stocks and cryptocurrency prices. Get current prices, manage a watchlist. "
            "Use when the user asks about stock prices, crypto values, market data, or wants to track investments."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "enum": ["get_prices", "add", "remove", "watchlist"],
                           "description": "Market action."},
                "symbol": {"type": "STRING", "description": "Stock ticker or crypto name (e.g. AAPL, bitcoin)"},
                "category": {"type": "STRING", "description": "stocks or crypto"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "daily_briefing",
        "description": (
            "Get morning briefings, weather summaries, and news headlines. "
            "Use when the user asks for a briefing, weather, news, or morning summary."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "enum": ["weather", "news", "morning_briefing"],
                           "description": "Briefing action."},
                "city": {"type": "STRING", "description": "City for weather (auto-detected if empty)"},
                "count": {"type": "INTEGER", "description": "Number of news headlines. Default: 5."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "contact_manager",
        "description": (
            "Manage contacts: add, search, delete, list. Stores name, phone, email, platform, relationship, notes. "
            "Use when the user wants to save, find, or manage contact information."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "enum": ["add", "search", "delete", "list"],
                           "description": "Contact action."},
                "name": {"type": "STRING", "description": "Contact name"},
                "phone": {"type": "STRING", "description": "Phone number"},
                "email": {"type": "STRING", "description": "Email address"},
                "platform": {"type": "STRING", "description": "Primary platform (whatsapp, imessage, instagram)"},
                "relationship": {"type": "STRING", "description": "Relationship (friend, family, work, etc)"},
                "notes": {"type": "STRING", "description": "Additional notes"},
                "query": {"type": "STRING", "description": "Search query for search action"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "taskbar_detect",
        "description": (
            "Detect running apps, pinned taskbar apps, focus existing windows. "
            "Use BEFORE trying to open any app to check if it's already running. "
            "Actions: is_running (check if app is open), focus (bring to foreground), running_list (all open apps), pinned_list (taskbar pinned apps)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "enum": ["is_running", "focus", "running_list", "pinned_list"],
                           "description": "Detection action."},
                "app_name": {"type": "STRING", "description": "App name to check or focus"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "full_control",
        "description": (
            "FULL SYSTEM CONTROL: volume, brightness, WiFi, Bluetooth, power, sleep, shutdown, restart, "
            "lock screen, screenshots, settings (display/sound/network/bluetooth/power/privacy/update), "
            "alarms, camera capture, audio devices, USB devices, processes, startup apps, environment variables, "
            "disk info, system info, scheduled tasks, restore points, user accounts, open/close any app, "
            "kill processes, open Control Panel/Task Manager/Device Manager, Calculator, Notepad, Paint, CMD, PowerShell. "
            "This is the MASTER control tool for everything on the computer."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING",
                           "enum": [
                               "volume_up", "volume_down", "volume_set", "volume_mute",
                               "brightness_up", "brightness_down", "brightness_set",
                               "wifi_on", "wifi_off", "bluetooth_on", "bluetooth_off",
                               "airplane_mode", "do_not_disturb",
                               "lock_screen", "sleep", "shutdown", "restart",
                               "screenshot", "set_wallpaper", "empty_trash",
                               "open_settings", "open_control_panel", "open_task_manager",
                               "open_device_manager", "open_network_settings", "open_sound_settings",
                               "open_display_settings", "open_power_settings", "open_bluetooth_settings",
                               "set_alarm", "list_alarms", "delete_alarm",
                               "capture_camera", "list_cameras",
                               "list_audio_devices", "set_default_audio",
                               "list_printers",
                               "lock_app", "kill_process", "list_processes",
                               "open_app", "close_app",
                               "list_startup_apps", "add_startup", "remove_startup",
                               "list_env_vars", "set_env_var",
                               "disk_info", "list_usb_devices", "list_drivers",
                               "check_updates", "system_info_full",
                               "list_scheduled_tasks", "create_system_restore",
                               "list_user_accounts", "list_shares",
                               "open_camera_app", "open_calculator", "open_notepad",
                               "open_paint", "open_cmd", "open_powershell",
                           ],
                           "description": "System control action."},
                "target": {"type": "STRING", "description": "Target app, device, name, or setting name"},
                "value": {"type": "STRING", "description": "Value to set (volume %, brightness %, env var value, etc.)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "cybersec",
        "description": (
            "CYBERSECURITY & ETHICAL HACKING: port scanning, network info, WiFi security analysis, "
            "system security audit, password strength checking, file hashing, firewall status, "
            "running services, installed software, secrets detection, DNS/WHOIS lookup, "
            "network connections, ARP table, traceroute, WiFi passwords, user accounts, "
            "file permissions, startup programs, scheduled tasks, vulnerability scanning. "
            "All tools are for DEFENSIVE SECURITY and EDUCATIONAL purposes."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING",
                           "enum": [
                               "port_scan", "open_ports", "network_info", "wifi_security",
                               "system_audit", "password_check", "hash_file", "firewall_status",
                               "running_services", "installed_software", "env_secrets_check",
                               "credential_check", "dns_lookup", "whois_lookup", "mac_lookup",
                               "network_connections", "arp_table", "traceroute", "wifi_passwords",
                               "user_accounts", "file_permissions", "startup_programs",
                               "scheduled_tasks", "browser_history_check", "encryption_info",
                               "vulnerability_check", "help",
                           ],
                           "description": "Cybersecurity action to perform."},
                "target": {"type": "STRING", "description": "Target IP, hostname, file path, or password to check"},
                "value": {"type": "STRING", "description": "Additional parameter"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "screen_auto",
        "description": (
            "SCREEN AUTOMATION: physically control the screen with mouse/keyboard. "
            "Click, type, scroll, drag, take screenshots, find elements, extract text via OCR, "
            "list/focus/maximize/minimize/close/resize/move windows, "
            "press hotkeys (ctrl+c, alt+tab, etc.), paste text, navigate UI elements. "
            "USE THIS when background commands don't work — go physical."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING",
                           "enum": [
                               "click", "double_click", "right_click",
                               "type_text", "hotkey", "scroll", "scroll_down",
                               "drag", "move_mouse", "screenshot",
                               "get_screen_size", "get_mouse_pos",
                               "find_on_screen", "extract_text", "read_screen",
                               "list_windows", "focus_window", "maximize_window",
                               "minimize_window", "close_window", "resize_window",
                               "move_window", "wait_and_click", "paste_text",
                               "press_enter", "press_escape", "press_tab",
                               "press_backspace", "select_all", "copy_selection", "undo",
                               "click_on_text", "click_text",
                           ],
                           "description": "Screen automation action."},
                "target": {"type": "STRING", "description": "Text to type, window title, description, or hotkey combo"},
                "value": {"type": "STRING", "description": "Additional value"},
                "x": {"type": "STRING", "description": "X coordinate or width"},
                "y": {"type": "STRING", "description": "Y coordinate or height"},
                "x1": {"type": "STRING", "description": "Start X for drag"},
                "y1": {"type": "STRING", "description": "Start Y for drag"},
                "x2": {"type": "STRING", "description": "End X for drag"},
                "y2": {"type": "STRING", "description": "End Y for drag"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "monitor",
        "description": (
            "PROACTIVE MONITORING: check battery, disk space, CPU, network usage, "
            "messages, calendar, reminders. Get alerts when something needs attention. "
            "Use this to stay on top of system health and incoming messages."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING",
                           "enum": [
                               "check_all", "check_battery", "check_disk",
                               "check_network", "check_cpu", "check_messages",
                               "check_calendar", "check_reminders",
                               "get_alerts", "clear_alerts", "get_status",
                               "set_threshold",
                           ],
                           "description": "Monitoring action."},
                "target": {"type": "STRING", "description": "Threshold name (disk, cpu, network)"},
                "value": {"type": "STRING", "description": "Threshold value"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "cleanup",
        "description": (
            "SYSTEM CLEANUP & OPTIMIZATION: clear temp files, empty recycle bin, "
            "clean browser cache, Windows Update cache, system logs, "
            "manage startup programs, kill processes, check memory, "
            "repair system files, check disk errors, optimize drives."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING",
                           "enum": [
                               "clean_temp", "clean_recycle", "clean_browser_cache",
                               "clean_windows_update", "clean_logs", "disk_cleanup",
                               "defrag_check", "startup_list", "startup_disable",
                               "startup_enable", "process_list", "process_kill",
                               "memory_status", "repair_system", "check_disk_errors",
                               "update_drivers", "optimize_drives",
                           ],
                           "description": "Cleanup action."},
                "target": {"type": "STRING", "description": "Target process name, startup item, etc."},
            },
            "required": ["action"]
        }
    },
    {
        "name": "sing",
        "description": (
            "SING A SONG: Look up lyrics and sing them rhythmically. "
            "Provide artist and title, or a query like 'Bohemian Rhapsody by Queen'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING", "description": "Song title."},
                "artist": {"type": "STRING", "description": "Artist name."},
                "song": {"type": "STRING", "description": "Song title (alias)."},
                "query": {"type": "STRING", "description": "Search query like 'Song Title by Artist'."},
            },
        }
    },
    {
        "name": "proactive_tasks",
        "description": (
            "PROACTIVE AUTO-TASKS: manage background jobs like content creation, "
            "social posting, data entry, email drafts, file organization, reports, "
            "research, monitoring. Add, list, pause, resume, delete jobs."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING",
                           "enum": ["add", "list", "pause", "resume", "delete"],
                           "description": "Job management action."},
                "type": {"type": "STRING",
                         "description": "Job type: content_creation, social_post, data_entry, email_draft, file_organize, report_generate, reminder, research, monitor, custom."},
                "description": {"type": "STRING", "description": "What the job should do."},
                "schedule": {"type": "STRING", "description": "once, hourly, daily."},
                "job_id": {"type": "STRING", "description": "Job ID for pause/resume/delete."},
                "params": {"type": "OBJECT", "description": "Additional job parameters."},
            },
        }
    },
    {
        "name": "phone_control",
        "description": (
            "PHONE CALLS & TEXTS: make phone calls, send text messages. "
            "Works with WhatsApp, Skype, Telegram, or any open messaging/call app."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING",
                           "enum": ["call", "text"],
                           "description": "Make a call or send a text."},
                "number": {"type": "STRING", "description": "Phone number to call/text."},
                "contact": {"type": "STRING", "description": "Contact name to search for."},
                "message": {"type": "STRING", "description": "Text message to send."},
                "method": {"type": "STRING", "description": "auto, use_open_app, skype, tel."},
            },
        }
    },
    {
        "name": "coding_assistant",
        "description": (
            "CODING ASSISTANT: write, run, test, and debug code. "
            "Supports Python, JavaScript, Java, C++, HTML, SQL, Rust. "
            "Auto-detects language. Run code, test against expected output, debug errors."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING",
                           "enum": ["write", "run", "test", "debug"],
                           "description": "Write code to file, run it, test output, or debug errors."},
                "code": {"type": "STRING", "description": "Source code to write/run/test/debug."},
                "filename": {"type": "STRING", "description": "Filename to save or run."},
                "language": {"type": "STRING", "description": "python, javascript, java, c_cpp, html, sql, rust."},
                "expected": {"type": "STRING", "description": "Expected output for test action."},
                "error": {"type": "STRING", "description": "Error message for debug action."},
                "timeout": {"type": "NUMBER", "description": "Run timeout in seconds (default 30)."},
            },
        }
    },
    {
        "name": "learning_memory",
        "description": (
            "LEARNING MEMORY: remember user preferences, track action patterns, "
            "store active context, save/run/list workflows. The system learns over time."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING",
                           "enum": ["remember", "get_pref", "list_prefs", "track", "insight",
                                    "set_context", "get_context", "clear_context",
                                    "save_workflow", "get_workflow", "list_workflows",
                                    "run_workflow", "delete_workflow"],
                           "description": "Memory action."},
                "key": {"type": "STRING", "description": "Preference/context key."},
                "value": {"type": "STRING", "description": "Preference/context value."},
                "action_name": {"type": "STRING", "description": "Action to track/inspect."},
                "context": {"type": "STRING", "description": "Context for pattern tracking."},
                "name": {"type": "STRING", "description": "Workflow name."},
                "steps": {"type": "ARRAY", "description": "Workflow steps.", "items": {"type": "OBJECT"}},
            },
        }
    },
    {
        "name": "notification_center",
        "description": (
            "NOTIFICATION CENTER: push alerts, get notification history, "
            "schedule future alerts (one-time or repeating), cancel alerts."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING",
                           "enum": ["push", "get", "read", "schedule", "scheduled", "cancel"],
                           "description": "Notification action."},
                "title": {"type": "STRING", "description": "Notification title."},
                "message": {"type": "STRING", "description": "Notification/alert message."},
                "level": {"type": "STRING", "description": "info, warning, error, success."},
                "source": {"type": "STRING", "description": "Source of notification."},
                "unread_only": {"type": "STRING", "description": "true to show only unread."},
                "limit": {"type": "NUMBER", "description": "Max notifications to return."},
                "notif_id": {"type": "STRING", "description": "Notification ID to mark read."},
                "delay_seconds": {"type": "NUMBER", "description": "Delay in seconds for schedule."},
                "delay_minutes": {"type": "NUMBER", "description": "Delay in minutes for schedule."},
                "repeat": {"type": "STRING", "description": "once, hourly, daily, weekly."},
                "alert_id": {"type": "STRING", "description": "Alert ID to cancel."},
            },
        }
    },
    {
        "name": "clipboard_manager",
        "description": (
            "CLIPBOARD: get/set clipboard, view history, save/retrieve snippets. "
            "Keeps last 100 items. Snippets persist across sessions."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING",
                           "enum": ["get", "set", "history", "copy_last", "save_snippet",
                                    "get_snippet", "list_snippets", "delete_snippet", "clear"],
                           "description": "Clipboard action."},
                "text": {"type": "STRING", "description": "Text to copy/set."},
                "index": {"type": "NUMBER", "description": "History index to restore."},
                "name": {"type": "STRING", "description": "Snippet name."},
                "limit": {"type": "NUMBER", "description": "Max history items to return."},
            },
        }
    },
    {
        "name": "alarm_timer",
        "description": (
            "ALARMS & TIMERS: set alarms at specific times, countdown timers, "
            "list/cancel alarms and timers. Supports recurring alarms."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING",
                           "enum": ["set_alarm", "set_timer", "stop_timer",
                                    "list_alarms", "list_timers", "cancel_alarm"],
                           "description": "Alarm/timer action."},
                "time": {"type": "STRING", "description": "Alarm time (e.g. '7:30 AM', '14:00')."},
                "seconds": {"type": "NUMBER", "description": "Timer seconds."},
                "minutes": {"type": "NUMBER", "description": "Timer minutes."},
                "label": {"type": "STRING", "description": "Alarm/timer label."},
                "repeat": {"type": "STRING", "description": "once, hourly, daily, weekly."},
                "alarm_id": {"type": "STRING", "description": "Alarm ID to cancel."},
                "timer_id": {"type": "STRING", "description": "Timer ID to stop."},
            },
        }
    },
    {
        "name": "smart_assistant",
        "description": (
            "SMART ASSISTANT: get workflow suggestions from learned patterns, "
            "search files on the system, generate daily activity reports, "
            "run quick predefined actions (screenshot, battery, wifi, disk, etc.)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING",
                           "enum": ["suggest", "search", "report", "quick"],
                           "description": "suggest=workflow tips, search=find files, report=daily summary, quick=quick action."},
                "query": {"type": "STRING", "description": "File search query."},
                "directory": {"type": "STRING", "description": "Directory to search in."},
                "file_type": {"type": "STRING", "description": "File extension filter (e.g. 'py', 'txt')."},
                "max_results": {"type": "NUMBER", "description": "Max search results."},
                "action_name": {"type": "STRING", "description": "Quick action name. Use 'list' to see all."},
            },
        }
    },
    {
        "name": "system_access",
        "description": (
            "FULL SYSTEM ACCESS: get device status, control hardware permissions, "
            "bluetooth (on/off/scan/pair/unpair/connected), wifi (on/off/scan/connect/disconnect/hotspot), "
            "night mode, clipboard, volume, brightness, airplane mode, DND, "
            "keyboard layout, running apps, foreground app, installed apps, services, "
            "network info, battery, screen info, audio/input/USB devices, printers, "
            "CPU/GPU/RAM/disk/monitor details, startup apps, scheduled tasks, "
            "env vars, system info, IP info, drivers, network connections, event logs, "
            "Windows Update, Defender, firewall, user accounts, shares, wallpaper, location."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": [
                        "get_location", "get_network_info", "get_battery_status",
                        "get_screen_info", "get_foreground_app", "get_running_apps",
                        "get_audio_devices", "get_input_devices", "get_usb_devices",
                        "get_printers", "get_startup_apps", "get_scheduled_tasks",
                        "get_env_vars", "get_system_info", "get_ip_info",
                        "get_cpu_info", "get_gpu_info", "get_ram_info",
                        "get_disk_info", "get_monitor_info",
                        "bluetooth_on", "bluetooth_off", "bluetooth_status",
                        "bluetooth_scan", "bluetooth_pair", "bluetooth_unpair",
                        "bluetooth_connected_devices",
                        "wifi_on", "wifi_off", "wifi_status", "wifi_scan",
                        "wifi_connect", "wifi_disconnect",
                        "wifi_hotspot_on", "wifi_hotspot_off", "wifi_hotspot_config",
                        "night_mode_on", "night_mode_off", "night_mode_status",
                        "set_wallpaper", "get_clipboard", "set_clipboard",
                        "get_volume", "set_volume", "get_brightness", "set_brightness",
                        "airplane_mode_on", "airplane_mode_off",
                        "dnd_on", "dnd_off",
                        "get_keyboard_layout", "set_keyboard_layout",
                        "get_installed_apps", "get_running_services",
                        "start_service", "stop_service",
                        "get_windows_update_status", "get_defender_status",
                        "get_firewall_status", "lock_workstation",
                        "get_user_accounts", "get_shares", "get_drivers",
                        "get_network_connections", "get_event_log",
                    ],
                    "description": "System access action."
                },
                "target": {"type": "STRING", "description": "Target device, SSID, service name, filter, or value depending on action."},
                "value": {"type": "STRING", "description": "Value to set (volume 0-100, brightness 0-100, password, etc.)."},
            },
        }
    },
    {
        "name": "self_control",
        "description": (
            "AUTONOMOUS SELF-CONTROL: health checks, auto-fix, system optimization, "
            "memory cleanup, disk repair, threat scanning, privacy checks, network health, "
            "startup optimization, scheduled task management, pattern learning, "
            "performance baseline/comparison, system reports, self-healing, "
            "auto-update checking, DNS/ARP flushing, temp cleaning, power profiles."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": [
                        "health_check", "full_diagnostic", "auto_fix",
                        "get_status", "get_uptime", "get_running_summary",
                        "optimize_system", "clean_temp", "clear_dns",
                        "flush_arp", "repair_system", "check_disk_errors",
                        "defrag_analysis", "power_profile", "scheduled_scan",
                        "threat_check", "privacy_check", "network_health",
                        "startup_optimize", "memory_cleanup", "process_audit",
                        "auto_schedule_add", "auto_schedule_list",
                        "auto_schedule_remove", "auto_schedule_run",
                        "learn_pattern", "get_patterns", "system_report",
                        "performance_baseline", "compare_baseline",
                        "get_alerts", "clear_alerts", "self_heal",
                        "auto_update_check",
                    ],
                    "description": "Self-control action."
                },
                "target": {"type": "STRING", "description": "Pattern category, task type, schedule type, power profile name, or task ID."},
                "value": {"type": "STRING", "description": "Observation text for learn_pattern, schedule interval, or filter string."},
            },
        }
    },
    {
        "name": "autonomous_brain",
        "description": (
            "AUTONOMOUS BRAIN: manages agent lifecycle, task scheduling, project planning, "
            "money tracking, research, brain health, self-healing, daily reports. "
            "Use this to start/stop agents, run autonomous cycles, track earnings, "
            "research opportunities, plan projects, and get status reports."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": [
                        "status", "start_day", "end_day", "run_cycle",
                        "spawn_agent", "kill_agent", "list_agents", "agent_status",
                        "add_idea", "list_ideas", "use_idea",
                        "log_task", "list_tasks",
                        "log_earning", "list_earnings",
                        "confirm_task", "research_opportunities",
                        "suggest_side_hustles", "plan_project",
                        "what_can_i_do", "while_user_sleeps",
                        "brain_health", "learn_from_mistake",
                        "auto_heal", "daily_report",
                    ],
                    "description": "Brain action."
                },
                "target": {"type": "STRING", "description": "Agent name, idea title, task description, project name, or mistake description."},
                "value": {"type": "STRING", "description": "Earning amount, source, project details, or additional info."},
            },
        }
    },
    {
        "name": "money_makers",
        "description": (
            "MONEY MAKERS: crypto monitoring (prices, alerts, portfolio), "
            "content creation (blog, twitter, youtube, newsletter), "
            "social media management, earnings tracking, passive income ideas, "
            "monetization research, project ideas, freelance opportunities."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": [
                        "crypto_status", "crypto_prices", "crypto_alert_check",
                        "crypto_set_alert", "portfolio_status", "portfolio_add",
                        "portfolio_rebalance", "content_create", "content_queue",
                        "content_publish", "social_post", "social_status",
                        "earnings_report", "track_earning",
                        "passive_income_ideas", "auto_content_pipeline",
                        "research_monetization", "project_ideas",
                        "freelance_opportunities",
                    ],
                    "description": "Money makers action."
                },
                "target": {"type": "STRING", "description": "Coin name, content topic, platform, earning source, or item ID."},
                "value": {"type": "STRING", "description": "Amount, content text, content type, or additional details."},
            },
        }
    },
    {
        "name": "self_evolution",
        "description": (
            "SELF EVOLUTION: self-improvement, learning, brain creation, "
            "skill acquisition, code optimization, self-audit, evolution tracking, "
            "ability discovery, auto-improve, brain backup/restore."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": [
                        "status", "learn_skill", "get_skills", "self_audit",
                        "upgrade_brain", "create_agent_brain", "connect_brains",
                        "discover_abilities", "test_ability", "fix_self",
                        "optimize_code", "evolve", "get_evolution_log",
                        "scan_for_improvements", "auto_improve",
                        "backup_brain", "restore_brain",
                    ],
                    "description": "Self evolution action."
                },
                "target": {"type": "STRING", "description": "Skill name, agent name, ability name, or backup ID."},
                "value": {"type": "STRING", "description": "Skill description, agent purpose, or additional info."},
            },
        }
    },
    {
        "name": "auto_start",
        "description": (
            "AUTO START: auto-start on boot, always-on daemon, wake scheduling. "
            "Enable/disable auto-start, manage Task Scheduler entries, "
            "start/stop daemon, schedule wake-ups."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": [
                        "status", "enable", "disable",
                        "add_startup", "remove_startup",
                        "add_task_scheduler", "remove_task_scheduler",
                        "wake_on_lan", "schedule_wake",
                        "is_running", "start_daemon", "stop_daemon",
                        "daemon_status",
                    ],
                    "description": "Auto start action."
                },
                "target": {"type": "STRING", "description": "Wake time (HH:MM) for schedule_wake."},
            },
        }
    },
    {
        "name": "mood_status",
        "description": (
            "MOOD STATUS: Get real-time analysis of the user's mood, energy, stress, "
            "and fatigue based on voice patterns. Returns current mood, confidence, "
            "and adaptation hints. Use this to adapt your behavior naturally."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["get", "history", "summary"],
                    "description": "get=current mood, history=recent mood timeline, summary=overall stats"
                }
            }
        }
    },
    {
        "name": "screen_awareness",
        "description": (
            "SCREEN AWARENESS: Smart screen context tracking. Knows when to read the screen, "
            "what the user is doing, and understands references like 'that', 'this', 'open that'. "
            "Use to proactively help with what's on screen."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["context", "should_read", "navigation_hint", "errors", "recent_apps"],
                    "description": "context=current screen context, should_read=check if screen should be read, navigation_hint=help with user references, errors=recent errors, recent_apps=app history"
                },
                "user_text": {
                    "type": "STRING",
                    "description": "User's text input (for navigation_hint to understand references like 'that', 'this')"
                }
            }
        }
    },
    {
        "name": "real_hustle",
        "description": (
            "REAL SIDE HUSTLE: Autonomous money-making engine. Creates products, tracks revenue, "
            "manages withdrawals, provides action plans. The user can withdraw money JARVIS earns. "
            "Use to start hustles, check earnings, create products, record sales, and withdraw funds."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": [
                        "status", "ideas", "create_product", "record_revenue",
                        "withdraw", "earnings_report", "action_plan",
                        "track_sale", "list_products", "balance",
                        "open_platform", "open_gig_search",
                    ],
                    "description": "status=hustle status, ideas=get ideas, create_product=make product, record_revenue=log income, withdraw=cash out, earnings_report=report, action_plan=what to do, track_sale=log sale, list_products=see products, balance=check balance, open_platform=OPEN real platform in browser (upwork/fiverr/gumroad/etc), open_gig_search=open Upwork+Fiverr and search for gigs matching a skill"
                },
                "name": {"type": "STRING", "description": "Product name (for create_product)"},
                "type": {"type": "STRING", "description": "Product type (freelance_coding, code_templates, content_writing, etc.)"},
                "description": {"type": "STRING", "description": "Product description (for create_product)"},
                "amount": {"type": "NUMBER", "description": "Dollar amount (for record_revenue, withdraw, track_sale). REQUIRED for withdraw - must be > 0"},
                "source": {"type": "STRING", "description": "Revenue source (for record_revenue)"},
                "method": {"type": "STRING", "description": "Withdrawal method (for withdraw): manual/bank_transfer/paypal"},
                "paypal_email": {"type": "STRING", "description": "PayPal email that receives the payout (required for method=paypal)"},
                "product_name": {"type": "STRING", "description": "Product name being sold (for track_sale)"}
            }
        }
    },
    {
        "name": "autonomous_worker",
        "description": (
            "AUTONOMOUS WORKER: Fully autonomous money-making engine. Creates platform accounts, "
            "builds profiles, finds jobs, applies, does the work, delivers, gets paid. "
            "Can fill signup forms via screen automation. Only asks user for CAPTCHA/verification."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": [
                        "status", "setup", "profile", "find_jobs", "quick_apply", "apply",
                        "work", "deliver", "wallet", "product", "products",
                        "pending", "approve", "reject", "earnings", "full_cycle",
                        "fill_form", "click_button", "type_in", "press_keys", "signup",
                        "clear_pending", "list_product", "activate", "catalog", "serve",
                        "catalog_json", "github", "more", "deploy", "paypal",
                        "redeploy", "heal",
                    ],
                    "description": "status=worker status, setup=open signup page, profile=create profile, find_jobs=search jobs, quick_apply=find top 3 jobs + draft proposals, apply=apply to job, work=build real project, deliver=mark delivered, wallet=setup payment, product=create product, products=list, pending=approvals, approve=approve+open browser, reject=reject, earnings=show money, full_cycle=complete workflow, fill_form=fill signup form, click_button=click UI element, type_in=type text, press_keys=press key combo, signup=attempt full signup, clear_pending=clean stale entries, list_product=create listing, activate=mark active + auto-list, catalog=index all zips, serve=start storefront server, catalog_json=JSON catalog, github=prepare repos for GitHub push, more=build N more products, deploy=push store to internet, paypal=set PayPal.me link, redeploy=update live store, heal=self-diagnose and fix issues"
                },
                "target": {"type": "STRING", "description": "Platform name (upwork/fiverr/gumroad/github/medium/substack/ko_fi), work type, job ID, or request ID"},
                "value": {"type": "STRING", "description": "Skill profile (python_developer/content_writer/bot_builder/web_scraper), job description, or additional info"},
            }
        }
    },
    {
        "name": "account_manager",
        "description": (
            "Save/load login credentials for side hustle platforms (Gumroad, Fiverr, Upwork, GitHub, Medium, etc). "
            "Use save to store credentials after signup, get to retrieve saved credentials for auto-login, "
            "list to see all saved accounts."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "save, get, list, delete"},
                "platform": {"type": "STRING", "description": "Platform name: gumroad, fiverr, upwork, github, medium, substack"},
                "email": {"type": "STRING", "description": "Email for the account"},
                "password": {"type": "STRING", "description": "Password for the account"},
                "username": {"type": "STRING", "description": "Username if different from email"},
                "notes": {"type": "STRING", "description": "Any notes about the account"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "noise_filter",
        "description": (
            "Filter speech noise from audio input. Apply noise reduction to improve voice recognition quality. "
            "Use 'process' to filter a file, 'status' to check filter state."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "process, status, help"},
                "input_file": {"type": "STRING", "description": "Path to audio file to filter"},
                "output_file": {"type": "STRING", "description": "Path for filtered output"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "instagram_browser",
        "description": (
            "Automate Instagram tasks: open chat, prepare drafts, send messages. "
            "Use 'open_chat' to open a DM, 'prepare_draft' to queue a message, 'send' to send a draft."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "open_chat, prepare_draft, send, clear_draft"},
                "username": {"type": "STRING", "description": "Instagram username to message"},
                "message": {"type": "STRING", "description": "Message text to send or draft"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "safe_text_entry",
        "description": (
            "Safely type text into any application with mouse-click blocking and speed control. "
            "Use 'type_text' to type slowly, 'type_enter' to type and press Enter, 'validate' to check target window."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "type_text, type_enter, validate"},
                "text": {"type": "STRING", "description": "Text to type"},
                "delay": {"type": "NUMBER", "description": "Delay between keystrokes in seconds (default 0.02)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "jarvis_file_stamp",
        "description": (
            "Stamp generated files with JARVIS metadata. Embeds creator info and timestamp into files. "
            "Use 'stamp' to mark a file, 'check' to verify a stamp, 'help' for usage."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "stamp, check, help"},
                "file_path": {"type": "STRING", "description": "Path to the file to stamp"},
                "content": {"type": "STRING", "description": "Text content to stamp (for text files)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "gumroad_api",
        "description": (
            "Gumroad API integration for real payment processing. "
            "Publish products, check sales, manage listings. "
            "Requires Gumroad access token (set with 'token' action)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["token", "products", "publish", "sales", "status"],
                    "description": "Gumroad API action."
                },
                "target": {"type": "STRING", "description": "Product ID, access token, or product name."},
                "value": {"type": "STRING", "description": "Price in cents, description, or additional info."},
            },
            "required": ["action"],
        }
    },
    {
        "name": "social_media",
        "description": (
            "Social media posting — real Twitter and Reddit posts. "
            "Share products, store links, and content. Requires API credentials in config.json."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["status", "twitter", "reddit", "share", "log"],
                    "description": "Social media action."
                },
                "target": {"type": "STRING", "description": "Post content or subreddit name."},
                "value": {"type": "STRING", "description": "Additional post content or options."},
            },
            "required": ["action"],
        }
    },
    {
        "name": "content_engine",
        "description": (
            "Content engine — generates real blog posts, tutorials, and marketing content. "
            "SEO-optimized articles, product descriptions, and social media content."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["status", "blog", "tutorial", "comparison", "description", "seo"],
                    "description": "Content engine action."
                },
                "target": {"type": "STRING", "description": "Article topic or product title."},
                "value": {"type": "STRING", "description": "Features, style, or SEO keywords."},
            },
            "required": ["action"],
        }
    },
    {
        "name": "camera_control",
        "description": (
            "Camera and vision control — capture photos, take screenshots, OCR, face detection, list cameras."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["capture", "screenshot", "ocr", "detect_faces", "list_cameras", "status"],
                    "description": "Camera action."
                },
                "path": {"type": "STRING", "description": "Image path for OCR."},
                "camera_index": {"type": "INTEGER", "description": "Camera index (default 0)."},
            },
            "required": ["action"],
        }
    },
    {
        "name": "phone_tracking",
        "description": (
            "Phone call tracking — log calls, manage contacts, get call history and stats."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["log_call", "get_calls", "add_contact", "get_contacts", "search_contact", "call_stats", "delete_contact"],
                    "description": "Phone tracking action."
                },
                "number": {"type": "STRING", "description": "Phone number."},
                "contact": {"type": "STRING", "description": "Contact name."},
                "direction": {"type": "STRING", "enum": ["incoming", "outgoing"], "description": "Call direction."},
                "duration": {"type": "INTEGER", "description": "Call duration in seconds."},
                "notes": {"type": "STRING", "description": "Call notes."},
                "name": {"type": "STRING", "description": "Contact name for search/add."},
                "email": {"type": "STRING", "description": "Contact email."},
                "limit": {"type": "INTEGER", "description": "Number of calls to retrieve."},
            },
            "required": ["action"],
        }
    },
    {
        "name": "smart_home",
        "description": (
            "Smart home control — add/remove/control devices, activate scenes, Hue, Home Assistant, MQTT."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["add_device", "remove_device", "list_devices", "control", "status", "scene", "discover"],
                    "description": "Smart home action."
                },
                "name": {"type": "STRING", "description": "Device name."},
                "type": {"type": "STRING", "description": "Device type (light, thermostat, plug)."},
                "command": {"type": "STRING", "description": "Command (on, off, brightness N)."},
                "scene": {"type": "STRING", "description": "Scene name (movie, morning, away, night)."},
                "protocol": {"type": "STRING", "description": "Protocol (hue, home_assistant, mqtt, http)."},
                "ip": {"type": "STRING", "description": "Device IP or bridge URL."},
                "api_key": {"type": "STRING", "description": "API key or token."},
                "room": {"type": "STRING", "description": "Room name."},
            },
            "required": ["action"],
        }
    },
    {
        "name": "vehicle_control",
        "description": (
            "Vehicle integration — Tesla API (status, lock, unlock, climate, location, charge), OBD-II, GPS tracking."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["tesla_status", "tesla_unlock", "tesla_lock", "tesla_climate", "tesla_location", "tesla_charge", "obd_read", "obd_codes", "gps_track", "setup", "status"],
                    "description": "Vehicle action."
                },
                "tesla_token": {"type": "STRING", "description": "Tesla API token."},
                "tesla_email": {"type": "STRING", "description": "Tesla account email."},
                "temperature": {"type": "NUMBER", "description": "Climate temperature in Celsius."},
                "port": {"type": "STRING", "description": "OBD or GPS serial port."},
            },
            "required": ["action"],
        }
    },
    {
        "name": "cybersecurity",
        "description": (
            "Cybersecurity monitoring — port scanning, network scan, firewall check, malware scan, security report."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["scan_ports", "scan_network", "check_firewall", "check_updates", "malware_scan", "check_connections", "security_report", "check_ssl", "status"],
                    "description": "Security action."
                },
                "host": {"type": "STRING", "description": "Target host for port scan."},
                "ports": {"type": "STRING", "description": "Comma-separated ports to scan."},
                "domain": {"type": "STRING", "description": "Domain for SSL check."},
            },
            "required": ["action"],
        }
    },
    {
        "name": "data_analysis",
        "description": (
            "Data analysis — analyze CSV/JSON, statistics, trends, comparison, filtering, charts."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["analyze_csv", "analyze_json", "compare", "trend", "summarize", "filter", "sort", "convert", "statistics", "visualize"],
                    "description": "Analysis action."
                },
                "path": {"type": "STRING", "description": "File path."},
                "path2": {"type": "STRING", "description": "Second file path for comparison."},
                "column": {"type": "STRING", "description": "Column name."},
                "value": {"type": "STRING", "description": "Filter value."},
                "values": {"type": "STRING", "description": "Comma-separated numeric values."},
                "labels": {"type": "STRING", "description": "Comma-separated chart labels."},
                "title": {"type": "STRING", "description": "Chart title."},
                "to": {"type": "STRING", "description": "Target format (json, csv)."},
            },
            "required": ["action"],
        }
    },
    {
        "name": "automation_engine",
        "description": (
            "Automation engine — create/run automations, schedule tasks, set timers, reminders, workflows."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["create", "list", "delete", "run", "stop", "schedule", "timer", "reminder", "workflow", "status"],
                    "description": "Automation action."
                },
                "name": {"type": "STRING", "description": "Automation name."},
                "id": {"type": "STRING", "description": "Automation ID."},
                "trigger": {"type": "STRING", "description": "Trigger type (manual, schedule, event)."},
                "actions": {"type": "ARRAY", "description": "List of actions to execute.", "items": {"type": "STRING"}},
                "interval": {"type": "INTEGER", "description": "Interval in seconds."},
                "cron": {"type": "STRING", "description": "Cron expression."},
                "time": {"type": "STRING", "description": "Scheduled time."},
                "message": {"type": "STRING", "description": "Reminder message."},
                "seconds": {"type": "INTEGER", "description": "Timer duration in seconds."},
                "steps": {"type": "ARRAY", "description": "Workflow steps.", "items": {"type": "STRING"}},
            },
            "required": ["action"],
        }
    },
    {
        "name": "stripe_payments",
        "description": (
            "Stripe payment processing — create products, prices, payment links, checkout sessions, "
            "manage customers, subscriptions, refunds, and view balance/transactions."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["create_payment_link", "create_product", "list_products", "create_price", "create_checkout", "get_balance", "list_transactions", "create_refund", "create_customer", "create_subscription", "status"],
                    "description": "Stripe action."
                },
                "name": {"type": "STRING", "description": "Product or customer name."},
                "product_name": {"type": "STRING", "description": "Product name for payment link."},
                "description": {"type": "STRING", "description": "Product description."},
                "amount": {"type": "NUMBER", "description": "Amount in dollars (e.g. 9.99)."},
                "currency": {"type": "STRING", "description": "Currency code (usd, zar, eur)."},
                "price_id": {"type": "STRING", "description": "Stripe price ID."},
                "product_id": {"type": "STRING", "description": "Stripe product ID."},
                "charge_id": {"type": "STRING", "description": "Charge ID for refund."},
                "customer_id": {"type": "STRING", "description": "Customer ID."},
                "email": {"type": "STRING", "description": "Customer email."},
                "recurring": {"type": "BOOLEAN", "description": "Create recurring price."},
                "interval": {"type": "STRING", "description": "Recurring interval (month, year, week, day)."},
                "limit": {"type": "INTEGER", "description": "Number of items to list."},
                "mode": {"type": "STRING", "description": "Checkout mode (payment, subscription, setup)."},
                "success_url": {"type": "STRING", "description": "Checkout success URL."},
                "cancel_url": {"type": "STRING", "description": "Checkout cancel URL."},
                "payload": {"type": "STRING", "description": "Webhook payload."},
                "sig_header": {"type": "STRING", "description": "Webhook signature header."},
            },
            "required": ["action"],
        }
    },
]
