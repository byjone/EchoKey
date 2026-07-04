# Echo Key — Educational Keyboard Monitor (with GUI)

Echo Key is a Python desktop application that shows, in real time, which keys are being pressed on the computer. It started as an exercise to understand how a keylogger works under the hood: how you capture operating-system events, how you coordinate a background thread with a graphical interface, and how you present that data without freezing the window.

It's not meant to spy on anyone. Every capture session asks for explicit consent before it starts, and while it's running, the window shows at all times exactly what's being recorded.

## Table of contents

- [Project goal](#project-goal)
- [Legal and ethical notice](#legal-and-ethical-notice)
- [Features](#features)
- [Operating system compatibility](#operating-system-compatibility)
- [Installation](#installation)
- [How to use the app](#how-to-use-the-app)
- [Building an executable](#building-an-executable)
- [Code structure](#code-structure)
- [Privacy and security of exported data](#privacy-and-security-of-exported-data)
- [Bugs fixed in this version](#bugs-fixed-in-this-version)
- [Possible future improvements](#possible-future-improvements)
- [License](#license)

## Project goal

The starting question was specific: what does it actually take to capture keystrokes in real time and display them in a GUI without the app freezing or breaking? Echo Key is the answer to that question, and along the way it works as a learning project on three fronts:

- Concurrent programming in Python (threads and queues).
- Capturing operating-system events with `pynput`.
- Building interfaces with Tkinter.

The app itself:

- Asks for permission before recording anything.
- Shows typing statistics (keys per minute, breakdown by key type).
- Keeps a recent history, with a search box and category filter.
- Lets you export that history to JSON or TXT for later analysis.

## Legal and ethical notice

Read this before using the program:

- Echo Key captures keystrokes **system-wide**, not just inside its own window. If you leave it recording and switch to another application, those keystrokes get logged too, including anything typed into password fields in other apps (the visual masking of those fields does nothing against a keystroke capture tool).
- Use it **only on your own machine**, with your own consent, and for educational or self-analysis purposes (for example, measuring your typing speed).
- Capturing another person's keystrokes without their knowledge and explicit consent is illegal in most countries and a serious violation of their privacy. This project isn't intended for that, and anyone using it that way does so at their own responsibility.
- The exported history is saved **unencrypted**. If you typed a password while the app was recording, that password ends up in plain text in the exported file. The app shows a security reminder both before exporting and right after saving, spelling out what to do with that file.

## Features

- Real-time display of the last key pressed, including combinations with CTRL, SHIFT, ALT, and WIN.
- Distinguishes between normal keys, special keys (arrows, Enter, F1-F20, etc.), modifiers, and combinations.
- Session timer and keys-per-minute (KPM) calculation.
- History of the last 300 keystrokes, with a text search box and category filter.
- Session summary: top 10 most-used keys, KPM, and percentage breakdown by key type.
- Bar chart of the top 10 most-used keys.
- Export to JSON or TXT, with a confirmation prompt and a security reminder after saving.
- Optional sound on each keypress (Windows only; the checkbox is disabled elsewhere).
- Button to clear all stored memory and reset counters.
- Automatic session pause after 30 seconds of inactivity.
- ESC key to stop recording instantly, at any time.
- Warning if the keyboard listener fails to start (for example, due to missing permissions), instead of leaving the app in an inconsistent state.

## Operating system compatibility

Echo Key runs on Windows, Linux, and macOS, but not every piece behaves the same on all three:

| Component | Windows | Linux | macOS |
|---|---|---|---|
| GUI (Tkinter) | Yes | Yes (may need the `python3-tk` package installed separately) | Yes |
| System-wide keyboard capture (`pynput`) | Yes, no extra steps | Yes, but may require extra permissions depending on the distro and display server (X11/Wayland) | Yes, requires granting Accessibility permissions to the app (or to the Terminal/IDE running it) in System Settings |
| Keypress sound (`winsound`) | Yes | Not available; the checkbox is automatically disabled | Not available; the checkbox is automatically disabled |
| Export to JSON / TXT | Yes | Yes | Yes |
| Building an executable with PyInstaller | Yes (produces a `.exe`) | Yes (produces a native Linux binary) | Yes (produces a native macOS binary) |

A few things worth knowing:

- The `winsound` module is Windows-only. The code imports it inside a `try/except`, so on Linux and macOS it's simply unavailable and the sound checkbox stays disabled; the rest of the app works normally.
- PyInstaller does **not** cross-compile: the executable it produces only works on the operating system you run it from. To get a Windows `.exe` you need to run PyInstaller on Windows; for a Linux or macOS binary, run it from those systems respectively.
- On Linux, Tkinter sometimes isn't bundled with the system's Python interpreter and needs to be installed separately (see the installation section).

## Installation

You need Python 3.9 or newer. Check your installed version with:

```bash
python --version
```

### 1. Clone or download the repository

```bash
git clone https://github.com/byjone/EchoKey.git
cd EchoKey
```

### 2. Install dependencies

Echo Key depends on a single external library, `pynput` (Tkinter ships with Python on Windows and macOS).

**Windows (CMD or PowerShell):**
```powershell
pip install pynput
```

**Linux / macOS:**
```bash
pip3 install pynput
```

If your system has multiple Python versions installed and `pip` doesn't point to the right one:

```bash
python -m pip install pynput
```

**Linux only:** if running the app throws an error related to `tkinter`, install the matching system package. For example, on Debian/Ubuntu-based distributions:

```bash
sudo apt install python3-tk
```

### 3. Run the application

```bash
python echo_key.py
```

or, on Linux/macOS if your Python command is `python3`:

```bash
python3 echo_key.py
```

## How to use the app

1. Open the program. The main window appears, empty.
2. Click **"▶ Iniciar sesión"** ("Start session"). A consent prompt appears asking permission to capture keystrokes system-wide; accept it to continue.
3. Start typing anywhere: the last key, the history, and the statistics update in real time.
4. Click **"⏹ Detener sesión"** ("Stop session") — or press ESC — to stop recording whenever you want.
5. Use **"📋 Resumen"** ("Summary") for a quick breakdown of the session, or **"📊 Gráfico top"** ("Top chart") to see the most-used keys as a bar chart.
6. Use **"💾 Exportar JSON"** or **"📄 Exportar TXT"** to save the data to a file. The app shows a security reminder before saving and another right after, spelling out what to do with that file before moving or sharing it.
7. Use **"🗑 Limpiar"** ("Clear") to erase everything captured so far without closing the program.

> Note: the interface labels are in Spanish (the language the app was originally built in). This README describes what each button does in English so you can follow along either way.

## Building an executable

To distribute Echo Key as a standalone program, so people don't need Python installed to run it, you can package it with **PyInstaller**.

### 1. Install PyInstaller

**Windows (CMD or PowerShell):**
```powershell
pip install pyinstaller
```

**Linux / macOS:**
```bash
pip3 install pyinstaller
```

### 2. Generate the executable

**Windows (CMD or PowerShell), from the project folder:**
```powershell
pyinstaller --onefile --windowed --name EchoKey echo_key.py
```

**Linux / macOS, from the project folder:**
```bash
pyinstaller --onefile --windowed --name EchoKey echo_key.py
```

The command is the same on all three systems; what changes is the type of file it produces, depending on where you run it from.

What each flag does:

- `--onefile`: bundles everything into a single executable file, instead of a folder with multiple files.
- `--windowed`: prevents a console window from opening behind the GUI.
- `--name EchoKey`: sets the name of the resulting executable (`EchoKey.exe` on Windows, `EchoKey` on Linux/macOS).

The result lands in the `dist/` folder:

- Windows: `dist\EchoKey.exe`
- Linux/macOS: `dist/EchoKey`

**Important:** PyInstaller only produces a valid executable for the operating system you run it from. There's no cross-compilation: to get a Windows `.exe` you have to run PyInstaller on Windows; for a Linux or macOS binary, you have to do it from those systems.

## Code structure

The whole project lives in a single file, `echo_key.py`:

- **Header with a glossary**: at the top of the file there's a comment block explaining basic terms (thread, queue, callback, widget, lock) for anyone who hasn't worked with threads before.
- **Imports and startup checks**: loads the required libraries and detects whether the system supports sound (`winsound`).
- **`timestamp()` function**: generates the timestamp for each event.
- **`EchoKey` class**: holds all the application logic.
  - `_build_ui`: builds the window and all its visual elements.
  - `_on_press` / `_on_release`: run on a background thread every time a key is pressed or released. They only register the key and drop the information into a queue; they never touch the UI or the statistics directly.
  - `_periodic_process` / `_handle_event` / `_handle_control`: run on the main thread, read the queue, and are the only ones responsible for safely updating the UI, the statistics, and the history.
  - `_start_listener` / `_stop_listener` / `_toggle_listener` / `_reset_ui_stopped`: control starting and stopping keyboard capture, including warning the user if the listener fails to start.
  - `_export_json` / `_export_txt` / `_security_reminder`: handle data export along with the matching security reminders.
  - `_check_inactivity`: automatically pauses the session after 30 seconds without activity.

The code is commented with someone new to threading in Python in mind (comments are in Spanish, matching the original code); if you want to understand how each part works, the `.py` file itself is the best reference.

## Privacy and security of exported data

- The generated JSON/TXT files are saved **in plain text**, with no encryption at all.
- The app shows a reminder right after exporting, pointing out that before moving that file to a USB drive, uploading it to the cloud, or sending it by email, you should:
  - Compress it into a password-protected `.zip`, or encrypt it with a tool like 7-Zip (AES-256) or VeraCrypt.
  - Avoid leaving it in folders that sync automatically to the cloud without encrypting it first.
  - Delete it securely once you no longer need it.
- The app captures keystrokes system-wide while recording, so the history and any exported files can end up including passwords or other sensitive information if something like that was typed during the session.

## Bugs fixed in this version

Compared to an earlier version of the code, the following issues were fixed:

- **Race conditions between threads**: the statistics (`self.stats`) and the set of currently-pressed keys (`self.pressed`) were being modified from both the keyboard thread and the main thread with no protection at all. Now the statistics are only touched from the main thread, and `self.pressed` is protected with a lock (`threading.Lock`).
- **ESC was updating the UI from the wrong thread**: pressing ESC used to call a function directly from the keyboard thread that touched Tkinter widgets. Now ESC just asks, through the queue, for the main thread to stop the session.
- **No error handling when the listener failed to start**: if `pynput` couldn't start (for example, due to missing permissions), the error was silently swallowed and the UI was left in an inconsistent state (the button saying "Stop" while nothing was actually being recorded). Now the failure is reported to the UI, along with an OS-specific hint.
- **Blocking beep**: the optional sound was played inside the keyboard callback itself, which could introduce small delays while typing. It now runs on its own short-lived thread.
- **Vague consent prompt**: the text was expanded to make it explicit that the capture is system-wide, not just within the app's window, and that it can include passwords typed in other applications.
- **No security reminder after exporting**: now, every time a JSON or TXT file is saved, a reminder appears with concrete steps on how to handle it (encrypt before moving to a USB drive or the cloud, avoid unencrypted cloud-synced folders, delete it once it's no longer needed).

## Possible future improvements

- Automatic encryption of exported files, for example by prompting for a password on export.
- Option to limit capture to only when the Echo Key window has focus, instead of system-wide.
- Typing speed graphs over time.
- Automated multi-platform packaging (for example, using GitHub Actions to build executables for Windows, Linux, and macOS on each release).

## License

You're free to use, modify, and distribute this project for educational purposes. If you publish it in your own repository, it's a good idea to add an explicit license (e.g. MIT) and keep this ethical notice visible.
