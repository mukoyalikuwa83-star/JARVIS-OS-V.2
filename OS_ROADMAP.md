# JARVIS OS — Requirement-to-Code Roadmap

Companion tracker for **JARVIS OS Requirements Specification v1.0 (13 Sep 2026)**.
Status per item: `[x] done` / `[~] partial` / `[ ] open` / `[H] needs hardware` / `[B] Boss decision`.

Legend — where each status points:
- **IN-REPO**: satisfied by existing code in this project (verified in the source tree).
- **MILE-1**: buildable on this Windows dev machine now (Milestone 1 has a no-hardware path).
- **HARD**: requires Linux/AOSP hardware, flashing, or a base distro.

---

## Part 2 — Functional Requirements

### 2.1 Boot & System Identity
| # | Requirement | Status | Where |
|---|---|---|---|
| 1 | Boot directly into JARVIS (no separate desktop/login to get past) | `[ ]` MILE-1 → Linux shell (M1) | — |
| 2 | Boot identity by voice (ElevenLabs voice profile) + PIN fallback | `[~]` IN-REPO (voice pipeline) | `core/identity.py`, `actions/tts_engine.py`, `core/prompt.txt` |
| 3 | Boot sequence shows real hardware status | `[~]` IN-REPO (system_info) | `actions/system_info.py`, `actions/system_access.py` |
| 4 | Usable state before all background services start | `[ ]` MILE-1 | — |

### 2.2 Kernel & Hardware Layer (ALL inherited — not reinvented)
| # | Requirement | Status | Where |
|---|---|---|---|
| 1 | LTS Linux kernel (desktop) / current AOSP branch (mobile) | `[H]` HARD | — |
| 2 | Use platform HALs (graphics/storage/wifi/bt/audio/radio) | `[H]` HARD | — |
| 3 | All Jarvis-specific additions stay in user space | `[x]` ARCHITECTURE RULE | `DESIGN.md`, build spec v1.0 |

### 2.3 The Jarvis Shell
| # | Requirement | Status | Where |
|---|---|---|---|
| 1 | Desktop: JARVIS is compositor + shell, draws whole screen | `[ ]` MILE-1 (Wayland compositor proof, then shell) | — |
| 2 | Mobile: JARVIS replaces launcher/home screen | `[H]` HARD (AOSP) | — |
| 3 | Voice is first-class input throughout the shell | `[~]` IN-REPO (app-level today) | `core/prompt.txt`, TTS/ASR pipeline |
| 4 | Shell shows live autonomy status from the same audit log | `[~]` IN-REPO (dashboard) | `api/dashboard.py`, `core/audit_log.py` |

### 2.4 Process, App & Resource Management
| # | Requirement | Status | Where |
|---|---|---|---|
| 1 | Flatpak + AppImage support (desktop) | `[H]` HARD | — |
| 2 | Standard APK support (mobile) | `[H]` HARD | — |
| 3 | Domain agents run as background services w/ resource limits | `[~]` IN-REPO (worker + sandbox) | `actions/autonomous_worker.py`, `actions/sandbox_trading.py`, `full_pipeline` |

### 2.5 Storage & File System
| # | Requirement | Status | Where |
|---|---|---|---|
| 1 | Full-disk/device encryption tied to boot identity | `[H]` HARD | — |
| 2 | Unified file view across desktop + mobile | `[ ]` MILE-3 | — |
| 3 | Independent backup schedule (separate from sync) | `[ ]` MILE-1 | — |

### 2.6 Networking & Connectivity
| # | Requirement | Status | Where |
|---|---|---|---|
| 1 | Wi-Fi/Bluetooth/cellular inherited | `[H]` HARD | — |
| 2 | Single internal API for agent network access (no raw sockets) | `[~]` IN-REPO (curl-based shared API) | `actions/_api.py` |
| 3 | OS-level mic/camera/location-in-use indicator | `[ ]` MILE-1 | — |

### 2.7 Security & Permissions Model
| # | Requirement | Status | Where |
|---|---|---|---|
| 1 | Secure boot | `[H]` HARD | — |
| 2 | Sandbox every app behind explicit, revocable permissions | `[~]` IN-REPO (approval gate + sandbox) | `core/approval_gate.py`, `actions/sandbox_trading.py` |
| 3 | Credential vault as OS-level service | `[~]` IN-REPO | `core/credential_vault.py`, `core/secret_store.py` |
| 4 | Single permission broker, no side channel, agents included | `[x]` IN-REPO (Phase 8 verified) | `core/permission_broker.py`, `core/safety_guardian.py`, `core/approval_gate.py`, `core/audit_log.py` |

### 2.8 The Jarvis Core Services
| v1.0 domain | OS manifestation | Status | Where in code |
|---|---|---|---|
| Computer Control | Native to shell | `[~]` | `core/service_api.py` (register) + `actions/computer_control.py`, `desktop.py`, `full_control.py`, `screen_automation.py` |
| Phone & Messaging | Native telephony/SMS/SIM service | `[~]` | `core/service_api.py` (register) + `actions/phone_comms.py`, `phone_control.py`, `phone_tracking.py`, `send_message.py` |
| Smart-Home / IoT / locks | Device-management service | `[~]` | `core/service_api.py` (register) + `actions/smart_home.py`, `vehicle_control.py` |
| Money engine (trading + discovery) | Background service w/ own resource + permission entry | `[x]` | `core/service_api.py` (money/money_record) + `actions/sandbox_trading.py`, `trading_orchestration.py`, `opportunity_discovery.py`, `real_hustle.py`, `autonomous_worker.py` |
| Information & News | OS system log | `[~]` | `core/service_api.py` (audit/audit_integrity) + `actions/market_monitor.py`, `web_search.py`, `deep_research.py` |
| Tracking & Monitoring | Shell default view | `[x]` | `actions/phone_tracking.py`, `proactive_monitor.py`, `proactive_tasks.py` |
| Safety & Guardian / autonomy ladder | Permission broker + kill switch | `[x]` | `core/permission_broker.py`, `core/safety_guardian.py`, `core/autonomy.py`, `core/approval_gate.py` |
| Memory & Learning / audit log | OS-level service, stable API | `[x]` | `core/service_api.py` (memory/memory_write) + `core/audit_log.py`, `actions/learning_memory.py`, `conversation_memory`, `lazy_loader` |
| Multi-agent orchestrator | System service, stable internal API | `[x]` | `core/service_api.py` (orchestrator) + `actions/autonomous_agent.py`, `autonomous_brain.py`, `dev_agent.py` |
| Run identically in substance on desktop/mobile | One core decision-maker | `[~]` M3 software layers (invoke_service is platform-agnostic); hardware-side MILE-3 | — |

### 2.9 Cross-Device Sync
| # | Requirement | Status | Where |
|---|---|---|---|
| 1 | One shared memory + audit log across devices | `[~]` single-file local today; `core/service_api.py` memory/audit services are the client contract (2.9.1 `core/syncstore.py` next) | `.jarvis/audit*.json`, `.jarvis/memory/` |
| 2 | Cross-device handoff (approval on one, answer on other) | `[ ]` MILE-3 | — |
| 3 | Sync conflicts flagged, never silently dropped | `[ ]` MILE-3 | — |

### 2.10 Updates & Recovery
| # | Requirement | Status | Where |
|---|---|---|---|
| 1 | OTA for platform + JARVIS components, versioned separately | `[H]` HARD | — |
| 2 | Atomic updates with rollback | `[H]` HARD | — |
| 3 | Recovery mode independent of Core | `[H]` HARD | — |

### 2.11 Accessibility & Multi-User
| # | Requirement | Status | Where |
|---|---|---|---|
| 1 | Inherit Linux/Android a11y tooling | `[H]` HARD | — |
| 2 | Multi-profile support | `[ ]` MILE-1 | — |

---

## Part 3 — Non-Functional Requirements

| Need | Status | Note |
|---|---|---|
| Dev hardware: mainstream Linux-compatible desktop/laptop | `[H]` | Boss decision (Part 3.1) |
| Dev hardware: Android test device w/ unlockable bootloader + custom-ROM community | `[H]` | Boss decision (Part 3.1) |
| External storage for builds (tens of GB) | `[H]` | Part 3.1 |
| Separate machine/spare drive for backups | `[H]` | Part 3.1 |
| Base distro (Debian or Arch) | `[H]` | Part 3.2, App E step 2 |
| Wayland compositor framework | `[ ]` MILE-1 | Part 3.2, App E step 3 (proven on Linux) |
| AOSP source + build toolchain | `[H]` | Part 3.2, App E step 4 |
| Version control / CI sized for OS builds | `[~]` | repo has git + optional CI |
| Device-flashing/imaging toolchain | `[H]` | Part 3.2 |
| Licensing review (GPLv2 kernel, Apache AOSP, per-file firmware) | `[B]` | Part 3.4, App E step 6 |
| Update server for OTA | `[ ]` MILE-3 | Part 3.5.1 |
| Crash reporting that survives failed boot | `[H]` | Part 3.5.2 |
| Staging environment before shipping updates | `[ ]` MILE-3 | Part 3.5.3 |

---

## Part 4 — Safety at OS Stakes

| # | Requirement | Status | Where |
|---|---|---|---|
| 4.1 | Recovery mode in separate protected partition | `[H]` | — |
| 4.1 | Hardware-level reset path (physical button combo) | `[H]` | — |
| 4.1 | Atomic rollback-capable updates ("restore" = known-good) | `[H]` | — |
| 4.2 | 5-layer kill switch carried forward unchanged | `[x]` IN-REPO | `core/safety_guardian.py` + kill-switch memory |
| 4.2 | Credential vault → OS service, no-stored-passwords rule identical | `[~]` IN-REPO | `core/credential_vault.py`, `core/secret_store.py` |
| 4.2 | Approval-gate list enforced at Core layer, no more-permissive answer | `[x]` IN-REPO | `core/approval_gate.py` (Phase 3 verified) |
| 4.2 | Truthful reporting extended to system-level logs (kernel panic ≠ smoothed-over) | `[~]` IN-REPO (audit integrity) | `core/audit_log.py`, `actions/reconciliation.py` |
| 4.2 | Sandboxing extended to every app, not only Jarvis agents | `[ ]` MILE-1 | — |
| 4.3 | Drills: mid-update power cut, Core boot crash, hw reset trigger, mid-session permission revoke | `[H]`/`[~]` | Guardian drills exist app-level; hardware drills need test device |

---

## Part 6 — Milestone Path (Definition of Done)

### Milestone 1 — Jarvis as a Desktop Shell
Not done until: Boss uses it as everyday desktop · Figure 4.1 power-loss test passes · existing Linux app ecosystem works without special-casing.
> **Start per Part 5.2 / Appendix E:** integrate as a shell extension on an existing mature desktop env FIRST (de-risk), own the compositor only after that's proven. First 30 days = dev hw → base distro → hello-world compositor → stock AOSP build+flash → VCS/backup routine → licensing read.

**Status: `[ ]` — blocked on dev hardware (Part 3.1) and Boss decisions (Part 5.3).**

### Milestone 2 — Jarvis as a Mobile Build
Not done until: everyday phone · standard APKs run · phone/comms domain native to OS.
**Status: `[ ]` — blocked on test device + AOSP env.**

### Milestone 3 — One Core, Synced
Not done until: approval on one device answered from other · exactly one audit log + one memory, never two that silently disagree.
**Status: `[ ]` — M3 software layer is DESIGNABLE NOW on this machine (see below).**

### Milestone 4 — "...And More"
New form factor = small shell project on existing Core. Deliberately open.
**Status: `[ ]` — deferred until M3.**

---

## What I Can Build on THIS Machine Right Now (no hardware)

Software layers that are targets on any platform and are testable here:

1. **OS-service API surface for Jarvis Core (2.8)** — `[x]` DONE (Phase 9 verified) — `core/service_api.py`: memory, audit, audit_integrity, money, money_record, orchestrator behind `invoke_service(caller, service, method, params, autonomy_level, granted)`; every sensitive service routes through the permission broker (no more-permissive answer than an agent). Tests: `test_phase9.py`.
2. **Permission broker abstraction (2.7.4)** — `[x]` DONE (Phase 8 verified) — `core/permission_broker.py`: single `request_permission(capability, caller, domain, action, reasoning, autonomy_level, granted)` gate over guardian → approval gate → standing grants → audit, with no side channel. Tests: `test_phase8.py`.
3. **Unified memory/audit client (2.9.1 client side)** — a `SyncStore` in-process API that reads/writes the single local memory+audit store with conflict-shaped write checks, ready to point at a remote endpoint in M3. (Next layer: `core/syncstore.py`.)
4. **Resource-limit supervisor stub (2.4.3)** — per-agent resource budgets (memory/CPU/scope counters) enforced at the worker level, the OS-version groundwork.
5. **First 30-day checklist runner** — this roadmap already is items 1–6 of App E; next concrete step is hardware.

---

## Appendix E — First 30 Days (tracker)
| Step | Requirement | Status |
|---|---|---|
| 1 | Dedicated dev hardware (does not touch main machine) | `[ ]` Boss |
| 2 | Mainstream Linux distro installed on dev box | `[ ]` |
| 3 | Minimal "hello world" Wayland compositor builds + runs | `[ ]` |
| 4 | Stock (unmodified) AOSP image builds + flashes to test device | `[ ]` |
| 5 | Version control + backup/imaging routine for both efforts | `[~]` git repo exists |
| 6 | Read Part 3.4 licensing terms in full | `[ ]` Boss |

---

## Boss Decisions Open (Part 5.3)
- [ ] Which Android version for the first mobile fork, and upgrade cadence.
- [ ] How many hardware models officially supported per milestone.
- [ ] Solo forever vs trusted collaborators (changes Part 3.5 infra budget).
- [ ] Desktop shell: resemble Windows/FRIDAY vs fully voice-first from the start.