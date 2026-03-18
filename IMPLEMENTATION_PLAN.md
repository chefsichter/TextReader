# TextReader Implementation Plan

## Status

Stand: 2026-03-18

Dieses Dokument sammelt die aktuell geklärten Anforderungen, die recherchierten technischen Entscheidungen und den geplanten Umsetzungsweg fuer die Desktop-App.

Ziel: Der Stand soll spaeter ohne erneute Grundsatzdiskussion wieder aufgenommen und in Code umgesetzt werden koennen.

## Implemented So Far

This section reflects the actual codebase state as of the latest sync, not just the original plan.

Implemented and committed:
- Python package scaffold
- Qt bootstrap
- tray-first GUI shell
- player window shell with playback state updates
- SQLite settings repository
- SQLite history repository
- clipboard capture path
- Qwen runtime config
- real Qwen WAV synthesis path
- audio playback controller
- runtime audio cache path
- PT71 ROCm-based editable development environment
- Linux/PipeWire startup fix via deferred runtime initialization
- first Linux global hotkey portal backend
- runtime hotkey backend selection bootstrap
- GNOME Shell Wayland hotkey fallback backend

Not yet implemented:
- Linux selection capture path
- settings UI
- richer persistent history navigation
- Windows-specific backends

## Produktziel

Die App soll selektierten Text oder Clipboard-Text auf Hotkey vorlesen.

Zielplattformen:
- Linux zuerst
- Windows danach

Rahmenbedingungen:
- Tray-App
- globaler Hotkey
- Qwen-TTS lokal
- moeglichst fluessig
- Linux und Windows sollen GPU-Beschleunigung mit ROCm/PyTorch nutzen, soweit technisch verfuegbar

## Fixierte Anforderungen

### Bedienung

- Die App ist eine Tray-App.
- Es gibt genau einen globalen Hotkey.
- Standard-Hotkey ist `Alt+L`.
- Der Hotkey ist spaeter in den Einstellungen aenderbar.
- Im Tray ist einstellbar, ob der Hotkey:
  - selektierten Text liest
  - oder Clipboard-Text liest
- Wenn das Lesen der gewaehlten Quelle fehlschlaegt, zeigt die App eine Fehlermeldung an.

### Verlauf und Wiedergabe

- Jeder erfasste Text wird im Verlauf gespeichert.
- Der Verlauf bleibt ueber App-Neustarts erhalten.
- Auch bei fehlgeschlagener Audio-Erzeugung wird der Text gespeichert.
- Audio-Wiedergabe braucht:
  - Slider zum Springen an eine beliebige Position
  - Buttons fuer Spruenge vor/zurueck
- Die Sprungweite ist in den Einstellungen konfigurierbar.

### Einstellungen

- Einstellungen werden global persistent gespeichert.
- Konfigurierbar sind mindestens:
  - Hotkey
  - Quelle des Hotkeys (`selection` oder `clipboard`)
  - Stimme
  - Sprache
  - Sprungweite

### Entwicklung / Start

- Linux soll zunaechst ueber ein `editable`-venv-Setup entwickelt werden.
- Ein GUI-Startlink soll auf die venv-Installation zeigen, damit immer der aktuelle Code gestartet wird.
- Windows moeglichst aehnlich, sofern praktikabel.

## Recherche-Ergebnisse

## TTS / Runtime

Lokale Benchmark-Artefakte im Projekt:
- `tests/BENCHMARK_RESULTS.md`
- `tests/benchmark_results.json`
- `tests/benchmark_full_results.json`

Empfohlene Linux-Qwen-Konfiguration laut lokalem Benchmark:
- Modell: `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice`
- `dtype=torch.bfloat16`
- `attn_implementation="sdpa"`
- kein `torch.compile`
- kein `PYTORCH_TUNABLEOP_ENABLED`
- `HSA_ENABLE_SDMA=0` optional, aber kein Muss

Wichtige lokale Ergebnisse:
- `0.6B + sdpa` war die beste getestete Konfiguration
- mittlere gemessene RTF laut Dokument: `0.712`
- `eager` ist deutlich langsamer und fuer das Produktziel nicht sinnvoll
- `torch.compile` war in den Tests praktisch nicht nutzbar

Schlussfolgerung:
- Python ist der pragmatisch beste Hauptstack, weil die produktrelevante Qwen-Integration und Benchmarkbasis bereits dort liegt.

## GUI / Framework

Empfehlung:
- Python + PySide6 (Qt)

Begruendung:
- Cross-Platform-Desktop-GUI fuer Linux und Windows
- Tray-Unterstuetzung
- Clipboard-Zugriff
- Audio-/Multimedia-Unterstuetzung
- geringere Komplexitaet als Tauri + separater Python-Service
- direkter Zugriff auf die Python-TTS-Runtime

Nicht bevorzugt:
- Tauri: nur sinnvoll, wenn bewusst Web-UI + separater Backend-Service gewuenscht ist
- GTK: fuer Linux gut, fuer Linux+Windows als gemeinsamer Hauptstack weniger attraktiv
- Electron: fuer diesen Use-Case zu schwergewichtig

## Linux / Wayland

Globaler Hotkey:
- primaer ueber das XDG Global Shortcuts Portal
- auf dem aktuellen Zorin/GNOME-Wayland-Desktop existiert ein GNOME-Shell-Fallback ueber `org.gnome.Shell.GrabAccelerator`
- beide bisher untersuchten Linux-Hotkey-Pfade sind auf dem aktuellen Desktop bereits getestet:
  - das Portal meldet `org.freedesktop.portal.GlobalShortcuts` als nicht verfuegbar
  - GNOME Shell lehnt externe `GrabAccelerator`-Registrierungen ab

Auswahl lesen:
- technisch schwieriger als Clipboard
- Wayland erlaubt keinen generischen globalen Zugriff wie traditionelle X11-Setups
- daher best-effort-Implementierung mit klarer Fehlermeldung, wenn direkte Ermittlung nicht funktioniert

Wichtige Produktentscheidung:
- kein stiller Fallback von `selection` auf `clipboard`
- die Quelle bleibt explizit einstellbar
- wenn die gewaehlte Quelle nicht lesbar ist, gibt es einen Fehler

## Windows

Auswahl lesen:
- geplant ueber Windows UI Automation des fokussierten Controls
- Workflow "Hotkey Auswahl holen und lesen" ist ausreichend

ROCm / PyTorch:
- offizielle AMD-Doku nennt PyTorch-via-PIP auf Windows fuer ROCm 7.2
- damit ist Windows-GPU-Support realistisch
- Linux-Benchmarkwerte sind trotzdem nicht automatisch auf Windows uebertragbar

Schlussfolgerung:
- gleiche Architektur moeglich
- Windows-GPU-Runtime spaeter separat validieren

## Architekturentscheidung

Die App wird als modulare Python-Desktop-App umgesetzt.

Architekturprinzipien:
- kleine, klar getrennte Module
- Single Responsibility
- kein unnötiger Overhead
- keine unnötigen Fallback-Konstruktionen
- Dateinamen sollen bereits ihren Zweck erklaeren

## Geplante Modulstruktur

```text
src/text_reader_app/
  app_bootstrap.py
  domain/
    models.py
  gui/
    tray_controller.py
    player_window.py
    settings_window.py
  hotkeys/
    global_shortcut_portal.py
    global_shortcut_windows.py
  capture/
    text_capture_service.py
    clipboard_reader.py
    linux_selection_reader.py
    windows_selection_reader.py
  tts/
    qwen_runtime_config.py
    qwen_speech_synthesizer.py
  audio/
    audio_playback_controller.py
  history/
    history_repository.py
    audio_cache_store.py
  settings/
    settings_repository.py
```

## Komponentenbeschreibung

### `app_bootstrap.py`

Verantwortlich fuer:
- App-Start
- Initialisierung von Logging
- Laden der Einstellungen
- Initialisierung Datenbank
- Verdrahtung von GUI, Hotkeys, Capture, TTS und Audio

### GUI

`tray_controller.py`
- baut das Tray-Menue auf
- zeigt Status
- startet direkte Aktionen
- oeffnet Player- und Settings-Fenster

`player_window.py`
- zeigt aktuellen Verlaufseintrag
- Audio-Slider
- Play/Pause/Stop
- Sprung vor/zurueck
- Vorheriger/nachster Verlaufseintrag
- Textvorschau
- Fehlermeldungen

`settings_window.py`
- Hotkey
- Quellmodus
- Stimme
- Sprache
- Sprungweite
- ggf. Dev-/Runtime-Infos

### Hotkeys

`global_shortcut_portal.py`
- Linux/Wayland-Hotkey ueber XDG Global Shortcuts Portal

`gnome_shell_hotkey.py`
- GNOME/Zorin-Wayland-Fallback ueber `org.gnome.Shell.GrabAccelerator`

`global_shortcut_windows.py`
- nativer Windows-Hotkey

### Capture

`text_capture_service.py`
- zentrale Orchestrierung
- entscheidet anhand der Einstellung, ob `selection` oder `clipboard` gelesen wird

`clipboard_reader.py`
- liest Clipboard ueber Qt

`linux_selection_reader.py`
- liest selektierten Text auf Linux soweit in der Session verfuergbar
- liefert klaren Fehler, falls nicht moeglich

`windows_selection_reader.py`
- liest Textselektion aus dem fokussierten Control ueber UI Automation

### TTS

`qwen_runtime_config.py`
- kapselt Modell-ID und Laufzeitparameter

`qwen_speech_synthesizer.py`
- laedt Modell
- erzeugt Audio fuer einen Text
- liefert Audio-Pfad und Metadaten

### Audio

`audio_playback_controller.py`
- Wiedergabe
- Pause/Fortsetzen
- Stop
- Seek ueber Slider
- feste Spruenge vor/zurueck

### Persistenz

`history_repository.py`
- SQLite fuer Verlauf

`audio_cache_store.py`
- lokaler Audio-Cache
- Dateinamen, Pfade, spaeter optional Cleanup

`settings_repository.py`
- persistente globale Einstellungen

## Laufzeitfluss

1. Globaler Hotkey wird ausgeloest.
2. App liest die Einstellung fuer den Quellmodus.
3. `text_capture_service` liest Text aus `selection` oder `clipboard`.
4. Der Text wird sofort im Verlauf gespeichert.
5. Der Verlaufseintrag startet im Status `captured` oder `synthesizing`.
6. Qwen-TTS erzeugt Audio und speichert es im Cache.
7. Verlaufseintrag wird mit Audio-Pfad, Dauer und Metadaten aktualisiert.
8. Wiedergabe startet.
9. GUI aktualisiert Status und Position.

Wenn ein Schritt fehlschlaegt:
- Verlaufseintrag bleibt erhalten
- Status wird als Fehler markiert
- die App zeigt eine Fehlermeldung an

## Datenmodell

Geplante SQLite-Tabellen:

### `app_settings`

- `key`
- `value`
- `updated_at`

### `history_entries`

- `id`
- `created_at`
- `source_type`
- `source_app`
- `text`
- `status`
- `error_message`
- `voice`
- `language`
- `model_id`
- `audio_path`
- `audio_duration_ms`
- `last_position_ms`

Moegliche Statuswerte:
- `captured`
- `synthesizing`
- `ready`
- `playing`
- `failed`

## GUI-Konzept

### Tray-Menue

- Status anzeigen
- Modus `Auswahl lesen`
- Modus `Clipboard lesen`
- Aktion `Jetzt ausloesen`
- `Player oeffnen`
- `Einstellungen`
- `Beenden`

### Player-Fenster

- Statuszeile
- aktueller Verlaufseintrag
- Slider mit aktueller Position und Gesamtdauer
- Buttons:
  - Zurueckspringen
  - Play/Pause
  - Vorspringen
  - Stop
- Verlauf:
  - vorheriger Eintrag
  - naechster Eintrag
- Textvorschau
- Stimme / Sprache
- sichtbare Fehlerflaeche

## Risiken

### Wayland-Auswahl

Der groesste technische Risikobereich ist das Lesen selektierten Texts unter Wayland.

Risiko:
- je nach Desktop/Compositor/Anwendung ist die globale Ermittlung von Selection unzuverlaessig oder nicht moeglich

Strategie:
- Hotkey sauber ueber Portal
- Selection-Reader als best-effort
- klare Fehleranzeige statt stiller Fehlfunktion

### Windows-ROCm

Risiko:
- offiziell moeglich, aber Benchmark- und Kompatibilitaetslage fuer genau diese App noch offen

Strategie:
- gleiche Architektur
- separate spaetere Windows-Validierung

### Audio-Seek

Risiko:
- konkrete Seek-Qualitaet haengt vom gewaehlten Wiedergabepfad ab

Strategie:
- zuerst robusten Qt-basierten Pfad evaluieren
- Seek und Positionsupdates frueh pruefbar machen

## Empfohlene Umsetzungsreihenfolge

### Phase 1

Projektgeruest:
- `pyproject.toml`
- Paketstruktur
- Logging
- Settings
- SQLite-Basis

### Phase 2

GUI:
- Tray-App
- Player-Fenster
- Settings-Fenster

### Phase 3

Audio:
- lokales Abspielen
- Slider
- Seek
- Sprungbuttons
- Verlauf mit bereits vorhandenen Audio-Dateien

### Phase 4

TTS:
- Qwen-Runtime
- Synthese-Workflow
- persistente Historieneintraege

### Phase 5

Quellen:
- Clipboard-Reader
- Hotkey an Clipboard-Workflow binden

### Phase 6

Wayland/Linux:
- globaler Hotkey ueber Portal
- Auswahl lesen implementieren

### Phase 7

Konfiguration:
- Hotkey aenderbar
- Stimme/Sprache aenderbar
- Sprungweite aenderbar

### Phase 8

Windows:
- Hotkey-Backend
- UI-Automation-Auswahl
- Windows-GPU-Benchmark und Runtime-Test

## Entwicklungssetup

Linux-Dev-Ziel:
- lokales `.venv`
- `pip install -e .`
- Start ueber `python -m text_reader_app`
- `.desktop`-Eintrag zeigt auf das venv und das Python-Modul

Vorteil:
- GUI-Start verwendet immer den aktuellen Workspace-Code

Aktueller Ist-Zustand:
- `.venv` zeigt auf `tests/venv_pt71`
- diese Umgebung wurde fuer echte Qwen-Synthese validiert
- Startpfad fuer die App: `.venv/bin/text-reader-app`

Windows-Ziel:
- ebenfalls `.venv`
- `pip install -e .`
- Start via `pythonw -m text_reader_app` oder Shortcut

## Quellen

Offizielle oder lokale Quellen, die dieser Planung zugrunde liegen:

- Lokaler Benchmark: `tests/BENCHMARK_RESULTS.md`
- Lokale Messdaten: `tests/benchmark_results.json`
- Qt Clipboard: <https://doc.qt.io/qt-6/qclipboard.html>
- PySide6 QClipboard: <https://doc.qt.io/qtforpython-6.5/PySide6/QtGui/QClipboard.html>
- PySide6 System Tray: <https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QSystemTrayIcon.html>
- Qt Multimedia: <https://doc.qt.io/qt-6/qmediaplayer.html>
- XDG Global Shortcuts Portal: <https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.GlobalShortcuts.html>
- Windows UI Automation Text Selection: <https://learn.microsoft.com/en-us/windows/win32/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextpattern-getselection>
- AT-SPI Text Interface: <https://gnome.pages.gitlab.gnome.org/at-spi2-core/libatspi/iface.Text.html>
- Wayland Primary Selection Protocol: <https://wayland.app/protocols/primary-selection-unstable-v1>
- AMD ROCm Windows PyTorch Install Guide: <https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/install/installrad/windows/install-pytorch.html>

## Offene Punkte fuer spaetere Umsetzung

Diese Punkte sind fuer die erste Planung ausreichend geklaert, muessen aber bei der Implementierung technisch konkretisiert werden:

- genauer Linux-Wayland-Auswahlmechanismus pro Desktop-Umgebung
- konkreter Qt-Audio-Backend-Pfad fuer robustes Seeking
- Dateipfade fuer Cache, DB und Logs
- Windows-GPU-Validierung fuer die gewaehlte Qwen-Integration

## Naechster sinnvoller Schritt

Den Hotkey auf dem aktuellen Zorin/GNOME-Wayland-Desktop produktiv machen:
- den naechsten praktikablen Linux-Hotkey-Ansatz recherchieren oder einen Desktop-spezifischen Integrationsweg waehlen
- danach Wave 4 beginnen:
  - Linux selection capture path
  - settings UI
  - persistent history/playback UX
