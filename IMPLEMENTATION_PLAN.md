# TextReader Implementation Plan

## Status

Stand: 2026-03-18

Dieses Dokument beschreibt den aktuellen Architekturstand, die getroffenen Produktentscheidungen und den jetzt implementierten Umsetzungsweg fuer die Desktop-App.

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
- Audio-Playback mit Slider, Jump und Stop
- History-Navigation vor/zurueck
- Linux Portal-Hotkey-Backend
- GNOME-Shell-Hotkey-Fallback
- lokale Command-Bridge fuer desktopseitige Shortcuts und Single-Instance-Kommandos
- Windows-Hotkey-Backend
- Launcher-Skripte fuer den aktuellen Workspace-Code

Noch nicht validiert:
- echtes Tray-/Shortcut-UAT in einer realen GNOME-Desktop-Session
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
    synthesis_worker.py
  hotkeys/
    global_shortcut_portal.py
    gnome_shell_hotkey.py
    global_shortcut_windows.py
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
- Hotkey-Backend waehlen
- lokale Command-Bridge starten
- CLI-Kommandos wie `--trigger-active-source` verarbeiten

`application_controller.py`
- Persistenz und Runtime-Services orchestrieren
- Settings lesen/schreiben
- History-Eintraege erzeugen und aktualisieren
- Playback-/TTS-Interaktion koordinieren

`gui/`
- Player-Fenster
- Settings-Fenster
- Tray-Menue
- Hintergrund-Worker fuer blockierende Synthese

`hotkeys/`
- Linux Portal
- GNOME Shell Fallback
- Windows RegisterHotKey
- lokale Trigger-Schnittstelle fuer desktopverwaltete Shortcuts

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

Interne Hotkey-Backends:
- XDG Global Shortcuts Portal, wenn verfuegbar
- GNOME `GrabAccelerator` als Fallback

Aktueller Desktop-Befund auf Zorin/GNOME Wayland:
- `org.freedesktop.portal.GlobalShortcuts` fehlt
- `org.gnome.Shell.GrabAccelerator` lehnt externe Registrierungen ab

Praktischer Hotkey-Weg fuer diesen Desktop:
- laufende App startet eine lokale Command-Bridge
- globaler Shortcut wird desktopseitig verwaltet
- Aufruf z. B. ueber `text-reader-app --trigger-active-source`
- GNOME Custom Shortcut kann daher den Trigger uebernehmen

Selection auf Linux:
- best effort
- zuerst ueber vorhandene Desktop-Tools wie `wl-paste --primary` bzw. `xclip`
- danach Qt-Selection, wenn die Session sie bereitstellt
- bei Fehlschlag klare Fehlermeldung

### Windows

Hotkey:
- nativer RegisterHotKey-Backend

Selection:
- best effort ueber PowerShell + UI Automation des fokussierten Controls

ROCm:
- Codepfad ist vorbereitet, aber die reale Windows-Runtime muss separat validiert werden

## Laufzeitfluss

1. Hotkey oder Tray-Aktion loest den aktiven Quellmodus aus.
2. Die App liest `selection` oder `clipboard`.
3. Der Text wird sofort als History-Eintrag gespeichert.
4. Ein Hintergrund-Worker startet die TTS-Synthese.
5. Nach Abschluss wird der History-Eintrag mit Fehler oder Audio aktualisiert.
6. Erfolgreiches Audio wird in den Player geladen und kann abgespielt werden.
7. Player-UI, History-Position und Playback-Metadaten werden aktualisiert.

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
- Linux-Selection-Smoke-Test
- lokale Command-Bridge
- Clipboard-Capture + Settings-Persistenz im laufenden Qt-Eventloop
- Offscreen-GUI-Shell-Erzeugung

Noch offen:
- echtes GNOME-Custom-Shortcut-UAT
- echtes Tray-/Audio-UAT in einer sichtbaren Desktop-Session
- Windows-Runtime-Validierung

## Naechster sinnvoller Schritt

Real-Desktop-UAT und Packaging:
- GNOME-Custom-Shortcut gegen `scripts/trigger_text_reader.sh` pruefen
- Tray-/Player-Verhalten in einer echten Desktop-Session pruefen
- Windows-Backends auf einem realen Windows-System validieren
