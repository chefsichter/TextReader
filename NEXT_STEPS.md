# NEXT_STEPS.md

## Current State

Stand: 2026-03-18

Research, product clarification, and first architecture planning are complete.

The initial application scaffold now exists:
- Python package skeleton
- editable-installable `pyproject.toml`
- local `.venv` with editable install
- Qt application bootstrap
- minimal tray shell
- minimal player window
- SQLite-backed settings repository
- SQLite-backed history repository
- placeholder Qwen runtime config
- audio playback shell
- clipboard capture path
- Qwen synthesizer with real WAV output path when dependencies are available
- first tray callback flow for clipboard capture into history
- controller-managed audio cache path and playback handoff

Primary planning document:
- `IMPLEMENTATION_PLAN.md`

Repository guidance:
- `AGENTS.md`

## Immediate Next Step

Turn the current shells into a polished first vertical slice:
- validate real Qwen generation in the editable `.venv`
- wire player controls more fully to playback state and seek updates
- add the first hotkey backend

## Execution Checklist

- [x] Create `pyproject.toml`
- [x] Create `src/text_reader_app/` package skeleton
- [x] Add application bootstrap entry point
- [x] Add minimal PySide6 tray app
- [x] Add minimal player window
- [x] Add settings repository stub
- [x] Add SQLite history repository stub
- [x] Add placeholder runtime config for Qwen
- [x] Ensure local dev startup works from editable venv
- [x] Add audio playback controller shell
- [x] Add clipboard capture path
- [x] Add Qwen synthesizer shell
- [x] Connect tray clipboard action to capture + history + synth shell status
- [x] Add real WAV output path for Qwen synthesis when runtime dependencies exist
- [x] Route synthesized audio into the playback controller

## Implementation Order

### Wave 1

- Create package structure
- Create bootstrap
- Create tray shell
- Create player shell
- Status: complete

### Wave 2

- Add persistent settings
- Add history database
- Add audio playback controller shell
- Status: complete for the current shell level

### Wave 3

- Add Qwen runtime integration
- Add clipboard read path
- Add hotkey integration
- Status: clipboard path and real synthesis path are implemented; runtime validation + hotkey pending

### Wave 4

- Add Linux selection path
- Add configurable settings UI
- Add persistent history playback behavior

### Wave 5

- Add Windows-specific backends

## Known Risks To Revisit During Implementation

- Wayland selection access may be unreliable across desktops/apps.
- Wayland global hotkey support depends on portal availability.
- Windows ROCm runtime must be benchmarked separately.
- Audio seek behavior must be verified early with the chosen playback stack.
- Offscreen bootstrap test works, but system tray behavior still needs a real desktop session.
- Full offscreen GUI+audio smoke tests are not reliable in headless mode because Qt tray/multimedia lifecycle can stay alive even when partial checks pass.
- The editable `.venv` still lacks `qwen_tts`/`torch`, so the real synthesis path is implemented but not yet executable there.

## Definition Of Done For The First Vertical Slice

The first useful slice is complete when:
- the tray app starts
- the player window opens
- one source mode works end to end
- one text item can be stored in history
- Qwen can generate audio
- audio playback can start and be paused

## Update Rule

When work resumes:
- mark completed checklist items
- add new blockers here
- keep this file focused on the operational next step, not full architecture
