# TextReader Implementation Plan

## Status

Stand: 2026-03-18

Dieses Dokument beschreibt den aktuellen Architekturstand, die getroffenen Produktentscheidungen und den implementierten Umsetzungsweg der App.

## Produktziel

Die App liest selektierten Text oder Clipboard-Text auf Hotkey vor.

Zielplattformen:
- Linux zuerst
- Windows danach

Rahmenbedingungen:
- Tray-App
- genau ein globaler Hotkey
- Qwen-TTS lokal
- moeglichst fluessige Wiedergabe
- persistente History und globale Einstellungen

## Fixierte Entscheidungen

### Produkt

- Die App ist tray-first.
- Standard-Hotkey ist `Alt+L`.
- Der Hotkey kann `selection` oder `clipboard` ausloesen.
- Fehler beim Lesen der Quelle werden sichtbar angezeigt.
- Erfasster Text bleibt im Verlauf, auch wenn TTS fehlschlaegt.
- Verlauf bleibt ueber Neustarts erhalten.
- Wiedergabe braucht Slider, Sprung vor/zurueck und History-Navigation.
- Stimme, Sprache, Sprungweite, Quellmodus und Hotkey werden global gespeichert.

### Runtime

Bevorzugte Qwen-Konfiguration auf Linux laut lokalen Benchmarks:
- Modell: `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice`
- `dtype=torch.bfloat16`
- `attn_implementation="sdpa"`
- kein `torch.compile`
- kein `PYTORCH_TUNABLEOP_ENABLED`

Relevante lokale Quellen:
- `tests/BENCHMARK_RESULTS.md`
- `tests/benchmark_results.json`
- `tests/benchmark_full_results.json`

## Implementierter Stand

Bereits implementiert:
- Python/PySide6-App-Grundgeruest
- Qt-Bootstrap mit deferred runtime init fuer Linux/PipeWire
- Tray-App mit Player- und Settings-Fenster
- SQLite fuer Settings und History
- Clipboard-Capture
- Linux-Selection-Capture als best effort
- Windows-Selection-Capture als best effort ueber PowerShell/UI Automation
- echte Qwen-WAV-Synthese
- Hintergrund-Worker fuer Synthese, damit der UI-Thread responsiv bleibt
- Fortschrittsanzeige waehrend Synthese mit ETA-Heuristik und gesperrten Transport-Controls
- Abschlussanzeige mit real gemessener Synthesezeit versus erzeugter Audio-Laenge
- Audio-Playback mit Slider, Jump und Stop
- History-Navigation vor/zurueck
- keyboard hook hotkey backend fuer Linux und Windows, modelliert nach `hotkey-transcriber`
- lokale Command-Bridge fuer externe Trigger und Single-Instance-Kommandos
- Launcher-Skripte fuer den aktuellen Workspace-Code

Noch nicht validiert:
- echtes Tray-/Hotkey-/Audio-UAT in einer sichtbaren Linux-Desktop-Session
- Windows-Backends auf einem realen Windows-System
- Packaging jenseits der aktuellen Dev-Launcher

## Architektur

Die App bleibt modular und SRP-orientiert.

Wichtige Module:

```text
src/text_reader_app/
  app_bootstrap.py
  application_controller.py
  domain/models.py
  gui/
    tray_controller.py
    player_window.py
    settings_window.py
    hotkey_change_dialog.py
    synthesis_worker.py
  hotkeys/
    keyboard_hook_service.py
    trigger_parser.py
    local_command_bridge.py
  capture/
    text_capture_service.py
    clipboard_reader.py
    linux_selection_reader.py
    windows_selection_reader.py
    selection_capture_common.py
  tts/
    qwen_runtime_config.py
    qwen_speech_synthesizer.py
  audio/
    audio_playback_controller.py
  history/
    history_repository.py
    history_navigation.py
  settings/
    settings_repository.py
```

### Zentrale Verantwortungen

`app_bootstrap.py`
- Qt-App starten
- Runtime-Kontext aufbauen
- Hotkey-Backend starten
- lokale Command-Bridge starten
- CLI-Kommandos wie `--trigger-active-source` verarbeiten

`application_controller.py`
- Persistenz und Runtime-Services orchestrieren
- Settings lesen/schreiben
- Hotkey nach Einstellungen neu starten
- History-Eintraege erzeugen und aktualisieren
- Playback-/TTS-Interaktion koordinieren

`gui/`
- Player-Fenster
- Settings-Fenster
- Hotkey-Capture-Dialog
- Tray-Menue
- Hintergrund-Worker fuer blockierende Synthese

`hotkeys/`
- Trigger-Parsing
- Linux evdev keyboard hook
- Windows low-level keyboard hook
- lokale Command-Bridge

`capture/`
- Clipboard lesen
- Selection lesen
- klare Fehlergrenzen zwischen Plattform und App-Layer

`history/`
- History persistieren
- Navigation durch vorhandene Eintraege
- Playback-Metadaten speichern

## Plattformstrategie

### Linux / Wayland

Interner Hotkey-Backend:
- evdev-basierter Keyboard-Hook ueber `/dev/input/event*`, wie im funktionierenden `hotkey-transcriber`

Konsequenz:
- der Hotkey ist nicht von XDG-Portal oder GNOME-DBus-Unterstuetzung abhaengig
- Zugriff auf geeignete `/dev/input/event*`-Devices muss vorhanden sein

Selection auf Linux:
- best effort
- zuerst ueber vorhandene Desktop-Tools wie `wl-paste --primary` bzw. `xclip`
- danach Qt-Selection, wenn die Session sie bereitstellt
- bei Fehlschlag klare Fehlermeldung

### Windows

Hotkey:
- low-level keyboard hook, analog zu `hotkey-transcriber`

Selection:
- best effort ueber PowerShell + UI Automation des fokussierten Controls

ROCm:
- Codepfad ist vorbereitet, aber die reale Windows-Runtime muss separat validiert werden

## Laufzeitfluss

1. Hotkey oder Tray-Aktion loest den aktiven Quellmodus aus.
2. Die App liest `selection` oder `clipboard`.
3. Der Text wird sofort als History-Eintrag gespeichert.
4. Ein Hintergrund-Worker startet die TTS-Synthese.
5. Waehrenddessen zeigt die UI einen Arbeitsstatus mit ETA-Heuristik und deaktivierten Playback-Controls.
6. Nach Abschluss wird der History-Eintrag mit Fehler oder Audio aktualisiert.
7. Die UI zeigt die reale Synthesezeit im Verhaeltnis zur erzeugten Audio-Laenge an.
8. Erfolgreiches Audio wird in den Player geladen und kann abgespielt werden.
9. Player-UI, History-Position und Playback-Metadaten werden aktualisiert.

## Entwicklungssetup

Aktueller Linux-Dev-Stand:
- `.venv` zeigt auf `tests/venv_pt71`
- echte Qwen-Synthese ist dort validiert
- App-Entry-Point: `.venv/bin/text-reader-app`
- Launcher-Skript: `scripts/run_text_reader.sh`
- Trigger-Skript: `scripts/trigger_text_reader.sh`
- Desktop-Entry: `desktop/text-reader-app.desktop`

Windows-Ziel:
- ebenfalls editable venv
- Start ueber `pythonw -m text_reader_app` oder Shortcut

## Validierungsstand

In dieser Linux-Umgebung bereits validiert:
- `python3 -m compileall src/text_reader_app`
- `timeout 8s .venv/bin/text-reader-app --help`
- `timeout 8s scripts/run_text_reader.sh --help`
- Linux keyboard hook service started successfully
- hotkey trigger parsing and hotkey restart after settings changes
- Linux-Selection-Smoke-Test
- lokale Command-Bridge
- Clipboard-Capture + Settings-Persistenz im laufenden Qt-Eventloop
- Offscreen-GUI-Shell-Erzeugung

Noch offen:
- echtes Linux-Hotkey-UAT in einer sichtbaren Desktop-Session
- echtes Tray-/Audio-UAT in einer sichtbaren Desktop-Session
- Windows-Runtime-Validierung

## Naechster sinnvoller Schritt

Real-Desktop-UAT und Packaging:
- direkten In-App-Hotkey in einer echten Linux-Desktop-Session pruefen
- Tray-/Player-Verhalten in einer echten Desktop-Session pruefen
- Windows-Backends auf einem realen Windows-System validieren
