# NEXT_STEPS.md

## Current State

Stand: 2026-03-18

The app is now beyond the initial scaffold. The current codebase contains:
- tray app with player and settings windows
- persistent SQLite settings and history
- clipboard capture path
- Linux selection capture path
- real Qwen WAV synthesis
- background synthesis worker to keep the UI responsive
- playback slider, jump controls, and previous/next history navigation
- Linux portal hotkey backend
- GNOME Shell hotkey fallback backend
- local command bridge for desktop-managed shortcuts and single-instance commands
- Windows hotkey backend
- Windows selection backend
- launcher scripts under `scripts/`

Primary planning document:
- `IMPLEMENTATION_PLAN.md`

Repository guidance:
- `AGENTS.md`

## Immediate Next Step

Run real desktop UAT and packaging polish:
- bind a GNOME custom shortcut to `/home/chefsichter/Dokumente/TextReader/scripts/trigger_text_reader.sh`
- verify tray and player behavior in a real desktop session
- validate the Windows-specific backends on a Windows machine

## Resume Point

Resume from post-Wave-5 validation and packaging polish.

Committed hotkey work already in history:
- `a808527` `Add first Linux global hotkey backend slice`
- `89429ff` `Add hotkey backend selection bootstrap`
- `ae1f88a` `Add GNOME Shell hotkey fallback backend`

Current uncommitted worktree at last sync:
- user-created and unresolved: `icon.svg`

Known desktop facts:
- `XDG_SESSION_TYPE=wayland`
- `XDG_CURRENT_DESKTOP=zorin:GNOME`
- the XDG portal backend currently reports that `org.freedesktop.portal.GlobalShortcuts` is unavailable on this desktop
- `org.gnome.Shell.GrabAccelerator` currently rejects external registrations on this desktop
- the practical replacement strategy is the local command bridge plus a desktop-managed GNOME shortcut

## Execution Checklist

- [x] Create `pyproject.toml`
- [x] Create `src/text_reader_app/` package skeleton
- [x] Add application bootstrap entry point
- [x] Add tray app and player window
- [x] Add settings repository
- [x] Add SQLite history repository
- [x] Add Qwen runtime config
- [x] Ensure local dev startup works from editable venv
- [x] Add audio playback controller
- [x] Add clipboard capture path
- [x] Add Qwen synthesizer with real WAV output
- [x] Route synthesized audio into the playback controller
- [x] Validate real Qwen synthesis in the active PT71-based development environment
- [x] Fix Linux/PipeWire startup hang by deferring runtime initialization
- [x] Add first Linux portal hotkey backend slice
- [x] Add runtime hotkey backend selection
- [x] Finish GNOME Shell hotkey fallback backend
- [x] Choose a Linux hotkey strategy that can actually work on the current Zorin/GNOME Wayland desktop
- [x] Add Linux selection capture path
- [x] Add settings UI
- [x] Add richer persistent history and playback behavior
- [x] Add Windows-specific backends
- [x] Add launcher scripts for the current workspace code
- [ ] Run GNOME desktop shortcut UAT against the local trigger script
- [ ] Validate Windows-specific backends on a Windows machine

## Wave Status

### Wave 1

- package structure
- bootstrap
- tray shell
- player shell
- Status: complete

### Wave 2

- persistent settings
- history database
- audio playback controller
- Status: complete

### Wave 3

- Qwen runtime integration
- clipboard path
- hotkey integration
- Status: complete, with desktop-specific fallback strategy on current GNOME/Wayland

### Wave 4

- Linux selection path
- configurable settings UI
- persistent history playback behavior
- Status: implemented

### Wave 5

- Windows-specific backends
- Status: implemented in code, not yet runtime-validated on Windows

## Validation Notes

Validated in this Linux environment:
- `python3 -m compileall src/text_reader_app`
- `timeout 8s .venv/bin/text-reader-app --help`
- `timeout 8s scripts/run_text_reader.sh --help`
- offscreen Linux selection capture smoke test
- local command bridge smoke test
- settings persistence + clipboard capture smoke test inside the Qt event loop
- offscreen GUI shell creation smoke test

Known limits:
- full tray/audio UAT still needs a real desktop session
- Windows hotkey and selection code cannot be runtime-validated from this Linux machine
- `icon.svg` exists in the worktree but is not yet integrated; treat it as user work unless explicitly adopted

## Update Rule

When work resumes:
- keep this file operational, not architectural
- mark completed validation items
- record any desktop-specific blocker here before changing implementation direction
