# Assistant — Usage Guide

This guide is focused on **daily usage** once you've installed and started the app.

## Start the assistant

```bash
jarvis
```

If `GEMINI_API_KEY` is set correctly, the assistant will:
- open the UI
- start microphone audio
- connect to Gemini Live
- listen and respond by voice

## What you can say (practical examples)

### 1) Basic actions
- "Open Chrome"
- "What's the weather in Paris?"
- "Search the web for …"

### 2) Screen / camera questions
- "What is on my screen?"
- "Look at my camera and tell me what you see"
- "Analyze this screenshot"

### 3) Reminders
- "Set a reminder for tomorrow at 8:30 AM to call Mom"

### 4) Files
When you have a file available via the UI/upload flow, you can ask for:
- "Summarize this PDF"
- "Extract text from this image"
- "Fix and optimize this code"
- "Analyze this CSV"

### 5) Desktop controls
Examples (depending on what your toolset supports):
- "Organize my desktop by type"
- "Clean my downloads folder"
- "Take a screenshot"

### 6) Gmail

Gmail uses Google OAuth rather than an API key or Gmail password. One-time setup:

1. Create or select a project in Google Cloud.
2. Enable the Gmail API.
3. Configure Google Auth Platform Branding, Audience, and Data Access. If the app
   is External and still in testing, add your Gmail account as a test user.
4. Add the scopes `gmail.readonly` and `gmail.send`.
5. Create an OAuth Client ID with application type **Desktop app** and download
   its JSON file.
6. Drag that JSON into the assistant and say: "Connect Gmail using this file."
7. Complete Google's consent page in the browser that opens.

The assistant stores the refresh credential in the operating-system keychain, not in
`token.json` or the project configuration. Example commands:

- "Is Gmail connected?"
- "Show my unread Gmail messages."
- "Search Gmail for `from:alex@example.com newer_than:7d`."
- "Read Gmail message ID 18f..."
- "Prepare an email to alex@example.com with subject Project Update saying the deck is ready."
- "Approve that email."
- "Cancel that email."
- "Disconnect Gmail."

Preparing a Gmail email never sends it. The assistant opens a visible Gmail compose window,
types the recipient, optional Cc/Bcc, subject, and body in sequence, then leaves the
draft open for review. A separate explicit approval verifies that the visible draft
still matches and clicks Gmail's Send button. On first use, sign in to Gmail inside
the controlled Chrome profile when prompted, then ask to prepare the
email again. If the Gmail API connection already identifies the account, the assistant
prefills that address and waits while you complete Google's password or 2FA screen;
credentials are never read or stored. The browser session remains signed
in for later drafts.

### 7) Deep Research
The assistant can investigate a complex question across multiple searches, compare evidence,
surface disagreements and uncertainty, and save a cited report.
Examples:

- "Do deep research on whether heat pumps make financial sense for my home."
- "Thoroughly research the leading local AI frameworks, focusing on privacy and Mac performance."
- "Do quick deep research on this company before my interview."
- "What is the status of my research?"
- "Cancel research task 4f2a8c10."

Before research begins, the assistant asks whether you want it to run quietly in the
background or let you watch the research. Background mode shows a compact bar
labeled `RUNNING IN THE BACKGROUND` and keeps browser windows closed. Visible
mode opens the controlled browser, performs each search, and visits sources
in separate tabs so you can follow the investigation. No research starts while
waiting for that choice.

Research depth can be `quick`, `standard` (default), or `deep`. Reports are saved as
Markdown only when you explicitly ask to save them. Until then, the report,
search plan, evidence, and sources remain in volatile memory and are not written to
task history or `outputs/research`. When research finishes, a detailed
summary is provided and you can save the report to Files, save it to Desktop, or read the
entire report aloud. Deep Research requires a valid Gemini API key. Source gathering uses direct web search so one research
run does not exhaust the Gemini request quota. Gemini is used for final synthesis
when quota is available; otherwise a source-first fallback report is kept in memory.

### 8) PowerPoint presentations
The assistant can create, edit, redesign, and extend editable widescreen `.pptx` decks.
Presentation jobs run in the background, report progress through `task_status`,
and export a PDF when Microsoft PowerPoint is available. Examples:

- "Create an eight-slide PowerPoint about renewable energy for high-school students."
- "Make a quality-mode executive presentation using these PDFs and spreadsheets."
- "Redesign the uploaded deck, preserve its branding, and add speaker notes."
- "Extend this investor deck to 20 slides and export both PowerPoint and PDF."
- "Create a premium presentation from this product-demo video."
- "What is the status of my presentation?"
- "Cancel presentation task 4f2a8c10."

Available themes are `arc_reactor`, `executive`, and `platinum`. By default,
presentations are saved in `Desktop/JARVIS Presentations`. Quality modes are
`fast`, `quality` (default), and `premium`, with a maximum of 50 slides.

Sources may include PDF, Word, PowerPoint, Excel, CSV, JSON, Markdown, text,
images, audio, video, or specific URLs. Supplied sources are used first and
will only perform broader web research after you explicitly allow it. Supplied
decks are never overwritten during edit, redesign, or extension jobs.

## Troubleshooting during usage

### API key issues
If you see:
- `GEMINI_API_KEY environment variable not set`

Fix:
- ensure `.env` exists in the repo root
- set `GEMINI_API_KEY`
- restart the assistant

### Voice not available
If the assistant can't use your selected voice, it will fall back to the default voice (`puck`).

Fix:
- set `GEMINI_VOICE_NAME` to a supported voice name from `main.py`

### If tools fail
Errors are usually logged to the UI log.

Fix:
- check environment permissions (mic, display, etc.)
- ensure any optional dependencies (like Playwright) are installed
- if needed, open an issue with the traceback
