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
- validated real Qwen synthesis on the PT71 ROCm environment
- Linux/PipeWire startup hang fixed by deferred runtime initialization
- first Linux hotkey portal backend committed
- runtime hotkey backend selection committed

Primary planning document:
- `IMPLEMENTATION_PLAN.md`

Repository guidance:
- `AGENTS.md`

## Immediate Next Step

Turn the current shells into a polished first vertical slice:
- finish and validate the GNOME Shell hotkey fallback as a clean "not available" path
- document that neither the portal backend nor GNOME `GrabAccelerator` currently yields a working global hotkey on this desktop
- choose the next viable Linux hotkey strategy for this environment
- then continue with Wave 4: Linux selection path, settings UI, and richer history/playback behavior

## Resume Point

Resume from the GNOME/Zorin hotkey fallback slice.

Committed hotkey work already in history:
- `a808527` `Add first Linux global hotkey backend slice`
- `89429ff` `Add hotkey backend selection bootstrap`

Current uncommitted worktree at last sync:
- modified: `src/text_reader_app/hotkeys/__init__.py`
- new: `src/text_reader_app/hotkeys/gnome_shell_hotkey.py`
- user-created and unresolved: `icon.svg`

Known desktop facts:
- `XDG_SESSION_TYPE=wayland`
- `XDG_CURRENT_DESKTOP=zorin:GNOME`
- the XDG portal backend currently reports that `org.freedesktop.portal.GlobalShortcuts` is unavailable on this desktop
- `org.gnome.Shell` exposes `GrabAccelerator` / `AcceleratorActivated` over D-Bus and is the current fallback target
- the GNOME fallback was smoke-tested and currently returns `not_available` with `GNOME Shell does not allow external GrabAccelerator registration on this desktop.`

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
- [x] Validate real Qwen synthesis in the active PT71-based development environment
- [x] Fix Linux/PipeWire startup hang by deferring runtime initialization
- [x] Add first Linux portal hotkey backend slice
- [x] Add runtime hotkey backend selection
- [ ] Finish GNOME Shell hotkey fallback backend
- [ ] Choose a Linux hotkey strategy that can actually work on the current Zorin/GNOME Wayland desktop
- [ ] Add Linux selection capture path
- [ ] Add settings UI
- [ ] Add richer persistent history and playback behavior

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
- Status: clipboard path and real synthesis path are implemented and validated on PT71; portal hotkey slice and bootstrap selection are implemented; GNOME fallback is being hardened, but no working global hotkey path exists yet on this desktop

### Wave 4

- Add Linux selection path
- Add configurable settings UI
- Add persistent history playback behavior
- Status: not started

### Wave 5

- Add Windows-specific backends

## Known Risks To Revisit During Implementation

- Wayland selection access may be unreliable across desktops/apps.
- Wayland global hotkey support depends on portal availability.
- Windows ROCm runtime must be benchmarked separately.
- Audio seek behavior must be verified early with the chosen playback stack.
- Offscreen bootstrap test works, but system tray behavior still needs a real desktop session.
- Full offscreen GUI+audio smoke tests are not reliable in headless mode because Qt tray/multimedia lifecycle can stay alive even when partial checks pass.
- The current desktop does not appear to expose `org.freedesktop.portal.GlobalShortcuts`, so a desktop-specific fallback is likely required for Wayland hotkeys here.
- `icon.svg` exists in the worktree but is not yet integrated or documented; treat it as user work unless explicitly adopted.

## Environment Notes

- On this machine, the active local `.venv` now points to `tests/venv_pt71`.
- That environment has:
  - `torch 2.10.0+rocm7.1`
  - `qwen_tts`
  - `PySide6`
  - editable install of `text_reader_app`
- Real synthesis was validated there and produced a WAV file under `/tmp/textreader-qwen-real-venv/`.
- The app entry point is `.venv/bin/text-reader-app`.

## Definition Of Done For The First Vertical Slice

The first useful slice is complete when:
- the tray app starts
- the player window opens
- one source mode works end to end
- one text item can be stored in history
- Qwen can generate audio
- audio playback can start and be paused
- one global hotkey path works on the target desktop

## Update Rule

When work resumes:
- mark completed checklist items
- add new blockers here
- keep this file focused on the operational next step, not full architecture
