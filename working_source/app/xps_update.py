"""Safe startup updater for XPS Tracker Updater.

This module intentionally uses only Python's standard library so it can run
before the application's third-party dependencies are imported.  A failed
update check never prevents the installed application from opening.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


CURRENT_VERSION = "89"
UPDATE_SCHEDULED_EXIT_CODE = 20
CONFIG_FILENAME = "update_config.json"
USER_AGENT = f"XPS-Tracker-Updater/{CURRENT_VERSION}"


class UpdateError(Exception):
    """An update could not be validated or prepared safely."""


def _version_parts(value: object) -> tuple[int, ...]:
    text = str(value or "").strip().lower()
    if text.startswith("v"):
        text = text[1:]
    if not re.fullmatch(r"\d+(?:\.\d+)*", text):
        raise UpdateError(f"Invalid version number: {value!r}")
    return tuple(int(part) for part in text.split("."))


def is_newer_version(candidate: object, current: object = CURRENT_VERSION) -> bool:
    left = list(_version_parts(candidate))
    right = list(_version_parts(current))
    width = max(len(left), len(right))
    left.extend([0] * (width - len(left)))
    right.extend([0] * (width - len(right)))
    return tuple(left) > tuple(right)


def _require_https(url: object, label: str) -> str:
    value = str(url or "").strip()
    if not value.lower().startswith("https://"):
        raise UpdateError(f"{label} must use HTTPS.")
    return value


def validate_manifest(data: object) -> dict:
    if not isinstance(data, dict):
        raise UpdateError("The update manifest is not a JSON object.")
    version = str(data.get("version") or "").strip().lstrip("vV")
    _version_parts(version)
    download_url = _require_https(data.get("download_url"), "Update download URL")
    digest = str(data.get("sha256") or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise UpdateError("The update manifest has an invalid SHA-256 checksum.")
    notes = data.get("release_notes", [])
    if isinstance(notes, str):
        notes = [notes]
    if not isinstance(notes, list) or not all(isinstance(item, str) for item in notes):
        raise UpdateError("The update release notes are invalid.")
    return {
        "version": version,
        "download_url": download_url,
        "sha256": digest,
        "release_notes": [item.strip() for item in notes if item.strip()],
    }


def _app_dir() -> Path:
    return Path(__file__).resolve().parent


def _data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".xps_tracker_updater")
    path = Path(base) / "XPS Tracker Updater" / "Updater"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _log(message: str) -> None:
    try:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with (_data_dir() / "update.log").open("a", encoding="utf-8") as handle:
            handle.write(f"[{stamp}] {message}\n")
    except Exception:
        pass


def load_config(app_dir: Path | None = None) -> dict:
    path = (app_dir or _app_dir()) / CONFIG_FILENAME
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {"enabled": False}
    except Exception as exc:
        _log(f"Could not read {CONFIG_FILENAME}: {exc}")
        return {"enabled": False}
    return data if isinstance(data, dict) else {"enabled": False}


def _read_json_url(url: str, timeout: float) -> object:
    request = urllib.request.Request(
        _require_https(url, "Manifest URL"),
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if getattr(response, "status", 200) != 200:
            raise UpdateError(f"Update server returned HTTP {response.status}.")
        return json.loads(response.read().decode("utf-8"))


def fetch_manifest(config: dict) -> dict:
    timeout = min(15.0, max(2.0, float(config.get("request_timeout_seconds", 5))))
    return validate_manifest(_read_json_url(config.get("manifest_url", ""), timeout))


def _show_update_prompt(manifest: dict) -> bool:
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()
    root.title("XPS Tracker Updater")
    try:
        icon = _app_dir() / "xps_tracker_updater.ico"
        if icon.exists():
            root.iconbitmap(default=str(icon))
    except Exception:
        pass
    notes = manifest.get("release_notes") or ["A newer version is available."]
    note_text = "\n".join(f"• {item}" for item in notes[:8])
    answer = messagebox.askyesno(
        "XPS Tracker Updater Update",
        f"XPS Tracker Updater v{manifest['version']} is available.\n"
        f"Installed version: v{CURRENT_VERSION}\n\n{note_text}\n\n"
        "Install the update now?",
        parent=root,
    )
    root.destroy()
    return bool(answer)


def _show_update_error(message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Update Could Not Be Installed",
            "The update could not be installed, so the current version will open normally.\n\n"
            f"{message}",
            parent=root,
        )
        root.destroy()
    except Exception:
        pass


def _download_package(url: str, destination: Path, expected_sha256: str, timeout: float) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    digest = hashlib.sha256()
    with urllib.request.urlopen(request, timeout=timeout) as response, destination.open("wb") as output:
        if getattr(response, "status", 200) != 200:
            raise UpdateError(f"Update download returned HTTP {response.status}.")
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual.lower() != expected_sha256.lower():
        destination.unlink(missing_ok=True)
        raise UpdateError("The downloaded update did not pass its SHA-256 verification.")


def safe_extract_zip(archive: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(archive) as package:
        for info in package.infolist():
            # Reject symbolic links and paths that would escape the staging folder.
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise UpdateError("The update package contains a symbolic link.")
            target = (destination / info.filename).resolve()
            try:
                target.relative_to(destination)
            except ValueError as exc:
                raise UpdateError("The update package contains an unsafe path.") from exc
        package.extractall(destination)


def find_payload_root(extracted: Path, expected_version: str) -> Path:
    candidates = [extracted, extracted / "XPS_Tracker_Updater"]
    candidates.extend(path.parent for path in extracted.rglob("reno_scan_updater.py"))
    seen: set[Path] = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        source = candidate / "reno_scan_updater.py"
        launcher = candidate / "run_xps_tracker.bat"
        updater = candidate / "xps_update.py"
        if not (source.is_file() and launcher.is_file() and updater.is_file()):
            continue
        match = re.search(
            r"^APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]",
            source.read_text(encoding="utf-8", errors="replace"),
            flags=re.MULTILINE,
        )
        if not match or _version_parts(match.group(1)) != _version_parts(expected_version):
            raise UpdateError("The package version does not match the update manifest.")
        return candidate
    raise UpdateError("The update package is missing required program files.")


def _powershell_literal(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def schedule_install(payload: Path, version: str, app_dir: Path | None = None) -> None:
    app_dir = (app_dir or _app_dir()).resolve()
    updater_dir = _data_dir()
    backup_dir = updater_dir / "Program Backups" / (
        f"v{CURRENT_VERSION}_before_v{version}_{time.strftime('%Y%m%d_%H%M%S')}"
    )
    script_path = updater_dir / "install_pending_update.ps1"
    log_path = updater_dir / "update.log"
    launcher = app_dir / "run_xps_tracker.bat"
    parent_pid = os.getpid()
    script = f"""$ErrorActionPreference = 'Stop'
$installDir = {_powershell_literal(app_dir)}
$payloadDir = {_powershell_literal(payload)}
$backupDir = {_powershell_literal(backup_dir)}
$launcher = {_powershell_literal(launcher)}
$logPath = {_powershell_literal(log_path)}
$parentPid = {parent_pid}
try {{ Wait-Process -Id $parentPid -Timeout 30 -ErrorAction SilentlyContinue }} catch {{}}
try {{
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    Get-ChildItem -LiteralPath $installDir -Force | Where-Object {{ $_.Name -ne '.venv' }} | ForEach-Object {{
        Copy-Item -LiteralPath $_.FullName -Destination $backupDir -Recurse -Force
    }}
    Get-ChildItem -LiteralPath $payloadDir -Force | Where-Object {{ $_.Name -ne '.venv' }} | ForEach-Object {{
        Copy-Item -LiteralPath $_.FullName -Destination $installDir -Recurse -Force
    }}
    Add-Content -LiteralPath $logPath -Value ('[' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '] Installed v{version}.')
    Start-Process -FilePath $launcher -WorkingDirectory $installDir
}} catch {{
    Add-Content -LiteralPath $logPath -Value ('[' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '] Install failed: ' + $_.Exception.Message)
    try {{
        Get-ChildItem -LiteralPath $backupDir -Force | ForEach-Object {{
            Copy-Item -LiteralPath $_.FullName -Destination $installDir -Recurse -Force
        }}
        Start-Process -FilePath $launcher -WorkingDirectory $installDir
    }} catch {{}}
}}
try {{ Remove-Item -LiteralPath (Split-Path -Parent $payloadDir) -Recurse -Force }} catch {{}}
"""
    script_path.write_text(script, encoding="utf-8-sig")
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
        ],
        cwd=str(app_dir),
        close_fds=True,
        creationflags=creationflags,
    )


def prepare_update(manifest: dict, config: dict) -> None:
    pending_parent = _data_dir() / "pending"
    pending_parent.mkdir(parents=True, exist_ok=True)
    pending = Path(tempfile.mkdtemp(prefix=f"v{manifest['version']}_", dir=pending_parent))
    archive = pending / "update.zip"
    extracted = pending / "extracted"
    extracted.mkdir()
    try:
        timeout = min(300.0, max(15.0, float(config.get("download_timeout_seconds", 120))))
        _download_package(manifest["download_url"], archive, manifest["sha256"], timeout)
        safe_extract_zip(archive, extracted)
        payload = find_payload_root(extracted, manifest["version"])
        schedule_install(payload, manifest["version"])
    except Exception:
        shutil.rmtree(pending, ignore_errors=True)
        raise


def main() -> int:
    config = load_config()
    if not config.get("enabled"):
        return 0
    accepted = False
    try:
        manifest = fetch_manifest(config)
        if not is_newer_version(manifest["version"]):
            return 0
        if not _show_update_prompt(manifest):
            return 0
        accepted = True
        prepare_update(manifest, config)
        return UPDATE_SCHEDULED_EXIT_CODE
    except (UpdateError, urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        # Startup must remain usable when the update server or internet is down.
        _log(f"Update check failed; continuing with v{CURRENT_VERSION}: {exc}")
        if accepted:
            _show_update_error(str(exc))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
