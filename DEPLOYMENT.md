# LSDQ Deployment Guide

This document covers building, packaging, and releasing LSDQ as a distributable Windows installer.

## Overview

```
Python source
   → PyInstaller (onefile)  → LSDQ.exe
   → Inno Setup              → LSDQ-Setup.exe  (bundles LSDQ.exe + OllamaSetup.exe)
   → Upload to Google Drive / OneDrive (large file distribution)
```

## Prerequisites

- Windows 10/11, **x64** (not ARM64) Python environment
- [Inno Setup](https://jrsoftware.org/isinfo.php) installed
- `OllamaSetup.exe` (latest) placed alongside the installer sources for silent bundling
- All Python dependencies installed in a clean virtual environment

## 1. Build the Executable (PyInstaller)

```bash
cd D:\lsdq
venv\Scripts\activate
pyinstaller lsdq.spec
```

### `lsdq.spec` notes
- Uses **onefile** mode
- `hiddenimports` is kept minimal — no `chromadb` or `onnxruntime` entries, since the custom numpy vector store has no such dependencies. Adding them back in unnecessarily bloats the build and can reintroduce packaging issues.
- Bundled static assets (HTML/CSS/JS, icons) must be referenced via `resource_path()` in code, not hardcoded relative paths, or they won't resolve correctly once packaged.

Output: `dist/LSDQ.exe`

### Common build issues

| Symptom | Cause | Fix |
|---|---|---|
| Silent ingestion failure on fresh install | Ingestion attempted before Ollama/models ready | Ensure the readiness check in `setup.html` flow gates ingestion |
| Corrupted/broken UI styling | `<button>` / `<script>` tags accidentally nested inside `<style>` | Check template files for malformed HTML before building |
| Build succeeds but wrong app is compiled | Inno Setup opened the wrong `.iss`/project | Explicitly open `installer.iss` before compiling, don't rely on "last opened project" |

## 2. Build the Installer (Inno Setup)

1. Open **`installer.iss`** explicitly (do not rely on Inno Setup's "recent project" — this has caused the wrong project being compiled in the past)
2. Verify the script references:
   - `dist/LSDQ.exe` as the main application executable
   - `OllamaSetup.exe` bundled for silent installation if Ollama isn't already present
   - Correct Start Menu / Desktop shortcut entries
3. Compile: **Build → Compile** (or `ISCC.exe installer.iss` from the command line)

Output: `LSDQ-Setup.exe` (~1.5 GB, dominated by the bundled `OllamaSetup.exe` and PyInstaller runtime)

## 3. Verify the Build

Before distributing, test on a clean machine (or a VM) that doesn't already have Ollama or the models installed:

- [ ] Installer runs and completes without errors
- [ ] Start Menu / Desktop shortcuts launch the app correctly
- [ ] First-run `setup.html` correctly detects missing Ollama and installs/prompts
- [ ] Model download progress streams correctly via SSE
- [ ] Document ingestion succeeds after setup completes (this is the step that previously failed silently — test it explicitly)
- [ ] Chat sessions persist correctly across app restarts
- [ ] Writable data is being written to `%LOCALAPPDATA%\LSDQ`, not next to the installed `.exe`

## 4. Windows SmartScreen

The installer and executable are currently **unsigned**, so Windows SmartScreen will show a warning on first run.

**Current approach (Option B):** Document for end users that they should click **More info → Run anyway**. Include this note in the release page and any distribution instructions.

**Future improvement:** Code signing would eliminate this friction entirely. This requires purchasing a code signing certificate (standard or EV) from a recognized CA.

> Note: `Smart App Control` may need to be disabled on development machines during testing/iteration — this is a dev-machine setting only and not something end users need to touch.

## 5. Distribution

Given the installer's size (~1.5 GB), GitHub Releases may not be ideal for hosting directly (check current GitHub file size limits). Recommended approach:

1. Upload `LSDQ-Setup.exe` to Google Drive or OneDrive
2. Set sharing permissions to "anyone with the link"
3. Link to it from the GitHub Releases page description, along with:
   - Version number / changelog
   - SHA-256 checksum of the installer (for integrity verification)
   - SmartScreen warning note

```bash
# Generate a checksum to publish alongside the download link
certutil -hashfile LSDQ-Setup.exe SHA256
```

## Release Checklist

- [ ] Version bumped (in app metadata / about screen)
- [ ] Built on a clean x64 Python venv
- [ ] Verified on a clean test machine per Section 3
- [ ] Checksum generated
- [ ] Uploaded to Drive/OneDrive with correct sharing permissions
- [ ] GitHub Release notes published with download link, checksum, and SmartScreen note
