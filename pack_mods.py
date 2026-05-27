#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "ModZips"
WINDOWS_FACTORIO_MODS_DIR = Path("/mnt/c/Users/MLJ/AppData/Roaming/Factorio/mods")
IGNORED_DIRS = {".git", ".idea", ".vscode", ".vs", "__pycache__", "bin", "obj", "tests"}
IGNORED_SUFFIXES = {".zip", ".psd"}
IGNORED_FILES = {".DS_Store", "Thumbs.db", "AGENTS.md", "README.md"}


@dataclass(frozen=True)
class ModProject:
    root_dir: Path
    src_dir: Path
    info_path: Path
    name: str
    version: str

    @property
    def package_name(self) -> str:
        return f"{self.name}_{self.version}"


def main() -> int:
    print("Scanning workspace:", ROOT)
    projects = discover_projects(ROOT)
    if not projects:
        print("ERROR: No mod projects found. Expected <mod>/src/info.json.", file=sys.stderr)
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    clear_output_directory(OUTPUT_DIR)
    print(f"Found {len(projects)} mod project(s).")

    success_count = 0
    failures = 0
    for index, project in enumerate(projects, start=1):
        progress = f"[{index}/{len(projects)}]"
        print(f"{progress} Packing {project.root_dir.name}...")
        try:
            zip_path = pack_project(project)
            success_count += 1
            print(f"{progress} OK {project.package_name} -> {zip_path}")
            deploy_debug_folder(project)
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"{progress} FAILED {project.root_dir}: {exc}", file=sys.stderr)

    print(f"Completed. Success: {success_count}, Failed: {failures}")
    if success_count > 0:
        open_output_directory(OUTPUT_DIR)

    return 0 if failures == 0 else 1


def clear_output_directory(output_dir: Path) -> None:
    for child in output_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def discover_projects(root: Path) -> list[ModProject]:
    projects: list[ModProject] = []
    for child in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if not child.is_dir() or child.name in IGNORED_DIRS or child.name == "ModZips":
            continue

        src_dir = child / "src"
        info_path = src_dir / "info.json"
        if not info_path.is_file():
            continue

        info = load_info(info_path)
        validate_project(child, src_dir, info)
        projects.append(
            ModProject(
                root_dir=child,
                src_dir=src_dir,
                info_path=info_path,
                name=str(info["name"]),
                version=str(info["version"]),
            )
        )

    return projects


def load_info(info_path: Path) -> dict[str, object]:
    with info_path.open("r", encoding="utf-8") as handle:
        info = json.load(handle)

    if not isinstance(info, dict):
        raise ValueError(f"info.json must contain an object: {info_path}")
    return info


def validate_project(root_dir: Path, src_dir: Path, info: dict[str, object]) -> None:
    for key in ("name", "version", "factorio_version", "title", "author", "description"):
        value = info.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{root_dir.name}: info.json must define non-empty '{key}'")

    version = str(info["version"])
    factorio_version = str(info["factorio_version"])
    if not is_semver(version):
        raise ValueError(f"{root_dir.name}: version must use major.minor.patch format")
    if not is_factorio_version(factorio_version):
        raise ValueError(f"{root_dir.name}: factorio_version must use major.minor format")

    has_entrypoint = any((src_dir / name).is_file() for name in (
        "control.lua",
        "data.lua",
        "data-updates.lua",
        "data-final-fixes.lua",
        "settings.lua",
        "settings-updates.lua",
        "settings-final-fixes.lua",
        "control.ts",
        "data.ts",
        "data-updates.ts",
        "data-final-fixes.ts",
        "settings.ts",
        "settings-updates.ts",
        "settings-final-fixes.ts",
    ))
    if not has_entrypoint:
        raise ValueError(f"{root_dir.name}: no recognized Factorio entrypoint file found in src")


def is_semver(value: str) -> bool:
    parts = value.split(".")
    return len(parts) == 3 and all(part.isdigit() for part in parts)


def is_factorio_version(value: str) -> bool:
    parts = value.split(".")
    return len(parts) == 2 and all(part.isdigit() for part in parts)


def pack_project(project: ModProject) -> Path:
    files = list(iter_pack_files(project))
    if not any(relative == Path("info.json") for _, relative in files):
        raise ValueError(f"{project.root_dir.name}: src/info.json must be included in package")

    zip_path = OUTPUT_DIR / f"{project.package_name}.zip"
    if zip_path.exists():
        zip_path.unlink()

    staging_root = Path(tempfile.mkdtemp(prefix="factorio_mod_pack_"))
    try:
        package_root = staging_root / project.package_name
        copy_package_files(project, package_root)

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file_path in sorted(package_root.rglob("*")):
                if file_path.is_file():
                    archive.write(file_path, file_path.relative_to(staging_root))
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)

    return zip_path


def copy_package_files(project: ModProject, package_root: Path) -> None:
    package_root.mkdir(parents=True, exist_ok=True)
    for source, relative in iter_pack_files(project):
        target = package_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def deploy_debug_folder(project: ModProject) -> None:
    if not WINDOWS_FACTORIO_MODS_DIR.is_dir():
        print(f"Skipped deploy for {project.package_name}: Factorio mods folder not found.")
        return

    zip_matches = sorted(WINDOWS_FACTORIO_MODS_DIR.glob(f"{project.name}_*.zip"))
    if zip_matches:
        names = ", ".join(path.name for path in zip_matches)
        print(f"Skipped deploy for {project.package_name}: zip exists in Factorio mods ({names}).")
        return

    target = WINDOWS_FACTORIO_MODS_DIR / project.package_name
    copy_package_files(project, target)
    print(f"Deployed folder for {project.package_name} -> {target}")


def iter_pack_files(project: ModProject) -> Iterable[tuple[Path, Path]]:
    for file_path in sorted(project.src_dir.rglob("*")):
        if not file_path.is_file():
            continue

        relative = file_path.relative_to(project.src_dir)
        if should_ignore(relative.parts, file_path.name):
            continue

        yield file_path, relative


def should_ignore(parts: tuple[str, ...], filename: str) -> bool:
    if any(part in IGNORED_DIRS for part in parts[:-1]):
        return True
    if filename in IGNORED_FILES:
        return True
    return Path(filename).suffix.lower() in IGNORED_SUFFIXES

def is_wsl() -> bool:
    release = platform.uname().release.lower()
    return "microsoft" in release or "wsl" in release


def convert_wsl_path_to_windows(path: Path) -> str:
    result = subprocess.run(
        ["wslpath", "-w", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_windows_explorer_command(path: Path) -> list[str]:
    explorer_path = Path("/mnt/c/Windows/explorer.exe")
    explorer = str(explorer_path) if explorer_path.is_file() else "explorer.exe"
    windows_path = convert_wsl_path_to_windows(path)
    return [explorer, windows_path]


def open_output_directory(output_dir: Path) -> None:
    try:
        if os.name == "nt":
            os.startfile(output_dir)  # type: ignore[attr-defined]
        elif is_wsl():
            subprocess.Popen(get_windows_explorer_command(output_dir))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(output_dir)])
        else:
            subprocess.Popen(["xdg-open", str(output_dir)])
        print(f"Opened output folder: {output_dir}")
    except Exception as exc:  # noqa: BLE001
        print(f"Could not open output folder automatically: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
