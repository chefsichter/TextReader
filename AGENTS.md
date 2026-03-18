# AGENTS.md

## Purpose

This file defines how work in this repository should be continued across future sessions.

The project goal and architecture live in `IMPLEMENTATION_PLAN.md`.
The immediate execution state lives in `NEXT_STEPS.md`.

When resuming work in this repository:
- read this file first
- then read `IMPLEMENTATION_PLAN.md`
- then read `NEXT_STEPS.md`

## Project Summary

This repository is for a tray-based desktop app that reads aloud either selected text or clipboard text on hotkey.

Primary target:
- Linux first

Secondary target:
- Windows

Core stack decision:
- Python
- PySide6 / Qt
- Qwen-TTS
- PyTorch
- SQLite

## Required Working Style

Follow the `fbra-creating-code` skill expectations for all new code:
- refresh repo context before editing
- keep modules small and cohesive
- prefer SRP
- avoid duplication
- avoid speculative abstractions
- keep functions short where practical
- keep Python files small enough to stay easy to navigate
- use descriptive file names

## Product Decisions Locked In

- The app is a tray app.
- There is exactly one global hotkey.
- Default hotkey is `Alt+L`.
- The hotkey is configurable.
- The hotkey action is configurable:
  - read selection
  - or read clipboard
- If the chosen source cannot be read, show an error.
- Captured text is stored in history even if TTS generation fails.
- History persists across restarts.
- Playback requires:
  - a seek slider
  - configurable jump forward/back controls
- Voice, language, hotkey, jump size, and source mode are stored globally.

## Runtime Decisions Locked In

Preferred Qwen runtime on Linux, based on local benchmark artifacts:
- model: `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice`
- dtype: `torch.bfloat16`
- attention: `sdpa`
- do not use `torch.compile`
- do not enable `PYTORCH_TUNABLEOP_ENABLED`

Relevant local files:
- `tests/BENCHMARK_RESULTS.md`
- `tests/benchmark_results.json`
- `tests/benchmark_full_results.json`

## Platform Notes

### Linux / Wayland

- Use the XDG Global Shortcuts Portal for the global hotkey where available.
- Reading selected text on Wayland is a best-effort feature.
- Do not silently fall back from `selection` mode to `clipboard` mode.
- If selection access fails, show a visible error.

### Windows

- Planned hotkey backend: native Windows global hotkey support
- Planned selection backend: Windows UI Automation
- ROCm / PyTorch on Windows should be validated separately from Linux

## Architecture Guidance

Keep responsibilities split into modules like:
- bootstrap
- gui
- hotkeys
- capture
- tts
- audio
- history
- settings
- domain

Prefer explicit orchestration services over hidden cross-module side effects.

## Session Resume Checklist

Before implementing anything substantial:
- read `AGENTS.md`
- read `IMPLEMENTATION_PLAN.md`
- read `NEXT_STEPS.md`
- inspect current repo tree
- check whether the worktree already contains user changes
- continue from the next unchecked execution item

## Documentation Rule

After each meaningful implementation step:
- update `NEXT_STEPS.md`
- if architecture or decisions changed, update `IMPLEMENTATION_PLAN.md`

