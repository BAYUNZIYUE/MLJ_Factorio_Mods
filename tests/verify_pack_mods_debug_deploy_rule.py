#!/usr/bin/env python3
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pack_mods


def make_project(root: Path, name: str = "demo-mod", version: str = "1.2.3") -> pack_mods.ModProject:
    src = root / name / "src"
    src.mkdir(parents=True)
    (src / "info.json").write_text(
        (
            "{"
            f'"name":"{name}",'
            f'"version":"{version}",'
            '"factorio_version":"2.0",'
            '"title":"Demo",'
            '"author":"MLJ",'
            '"description":"Demo"'
            "}"
        ),
        encoding="utf-8",
    )
    (src / "control.lua").write_text("-- demo", encoding="utf-8")
    return pack_mods.ModProject(root / name, src, src / "info.json", name, version)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pack_mods_deploy_") as temp_dir:
        temp = Path(temp_dir)
        project = make_project(temp)
        zip_path = temp / f"{project.package_name}.zip"
        zip_path.write_text("zip placeholder", encoding="utf-8")
        mods_dir = temp / "mods"
        mods_dir.mkdir()

        original = pack_mods.WINDOWS_FACTORIO_MODS_DIR
        try:
            pack_mods.WINDOWS_FACTORIO_MODS_DIR = mods_dir
            pack_mods.deploy_zip(project, zip_path)
            deployed_zip = mods_dir / zip_path.name
            if deployed_zip.read_text(encoding="utf-8") != "zip placeholder":
                print("FAIL: expected zip deployment into Factorio mods folder")
                return 1

            pack_mods.deploy_debug_folder(project)
            deployed = mods_dir / project.package_name
            if (deployed / "control.lua").is_file():
                print("FAIL: folder deployment should be skipped after zip deployment")
                return 1

            (mods_dir / f"{project.name}_9.9.9.zip").write_text("zip placeholder", encoding="utf-8")
            pack_mods.deploy_debug_folder(project)
            if (deployed / "control.lua").exists():
                print("FAIL: folder deployment should be skipped when a matching zip exists")
                return 1

            deployed_zip.unlink()
            (mods_dir / f"{project.name}_9.9.9.zip").unlink()
            pack_mods.deploy_debug_folder(project)
            if not (deployed / "control.lua").is_file():
                print("FAIL: expected unpacked folder deployment when no zip exists")
                return 1
        finally:
            pack_mods.WINDOWS_FACTORIO_MODS_DIR = original

    print("PASS: pack_mods deploys zips and only deploys folders when no matching Factorio zip exists.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
