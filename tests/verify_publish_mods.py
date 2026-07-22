#!/usr/bin/env python3
from pathlib import Path
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from io import StringIO
import os
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pack_mods
import publish_mods


class FakePortalClient:
    def __init__(self, details_by_name):
        self.details_by_name = details_by_name
        self.uploads = []
        self.creates = []

    def get_mod_details(self, mod_name):
        return self.details_by_name.get(mod_name)

    def upload_existing_release(self, token, project, zip_path):
        self.uploads.append((token, project.name, zip_path.name))
        return {"success": True, "url": f"/mod/{project.name}"}

    def publish_new_mod(self, token, project, zip_path, fields):
        self.creates.append((token, project.name, zip_path.name, dict(fields)))
        return {"success": True, "url": f"/mod/{project.name}"}


def make_project(root: Path, name: str, version: str) -> pack_mods.ModProject:
    src = root / name / "src"
    src.mkdir(parents=True)
    info_path = src / "info.json"
    info_path.write_text(
        (
            "{"
            f'"name":"{name}",'
            f'"version":"{version}",'
            '"factorio_version":"2.1",'
            '"title":"Demo",'
            '"author":"MLJ",'
            '"description":"Demo"'
            "}"
        ),
        encoding="utf-8",
    )
    (src / "control.lua").write_text("-- demo", encoding="utf-8")
    return pack_mods.ModProject(root / name, src, info_path, name, version)


def make_zip(output_dir: Path, project: pack_mods.ModProject, name=None, version=None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{project.package_name}.zip"
    package_root = project.package_name
    info_name = name if name is not None else project.name
    info_version = version if version is not None else project.version
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            f"{package_root}/info.json",
            (
                "{"
                f'"name":"{info_name}",'
                f'"version":"{info_version}",'
                '"factorio_version":"2.1",'
                '"title":"Demo",'
                '"author":"MLJ",'
                '"description":"Demo"'
                "}"
            ),
        )
        archive.writestr(f"{package_root}/control.lua", "-- demo")
    return zip_path


def assert_equal(actual, expected, message: str) -> bool:
    if actual != expected:
        print(f"FAIL: {message}: expected {expected!r}, got {actual!r}")
        return False
    return True


def test_decision_and_zip_checks(temp: Path) -> bool:
    output_dir = temp / "ModZips"
    newer = make_project(temp, "newer-mod", "1.2.0")
    same = make_project(temp, "same-mod", "1.0.0")
    older = make_project(temp, "older-mod", "1.0.0")
    missing = make_project(temp, "missing-mod", "0.1.0")
    for project in [newer, same, older, missing]:
        make_zip(output_dir, project)

    client = FakePortalClient(
        {
            "newer-mod": {"releases": [{"version": "1.0.0"}, {"version": "1.1.9"}]},
            "same-mod": {"releases": [{"version": "1.0.0"}]},
            "older-mod": {"releases": [{"version": "1.0.1"}]},
        }
    )
    decisions = publish_mods.collect_publish_decisions(
        [newer, same, older, missing],
        client,
        output_dir,
        allow_create=False,
    )
    actions = {decision.project.name: decision.action for decision in decisions}
    expected = {
        "newer-mod": publish_mods.ACTION_UPLOAD,
        "same-mod": publish_mods.ACTION_SKIP,
        "older-mod": publish_mods.ACTION_SKIP,
        "missing-mod": publish_mods.ACTION_ERROR,
    }
    if not assert_equal(actions, expected, "publish decisions"):
        return False

    create_decision = publish_mods.build_publish_decision(missing, None, output_dir, allow_create=True)
    if not assert_equal(create_decision.action, publish_mods.ACTION_CREATE, "missing mod create decision"):
        return False

    bad_zip_project = make_project(temp, "bad-zip-mod", "2.0.0")
    bad_zip = make_zip(output_dir, bad_zip_project, version="9.9.9")
    try:
        publish_mods.verify_zip_package(bad_zip_project, bad_zip)
    except ValueError:
        return True

    print("FAIL: verify_zip_package accepted mismatched packaged info.json")
    return False


def test_execute_boundary(temp: Path) -> bool:
    project = make_project(temp, "execute-mod", "1.0.0")
    output_dir = temp / "ModZips"
    zip_path = make_zip(output_dir, project)
    decision = publish_mods.PublishDecision(
        project=project,
        action=publish_mods.ACTION_UPLOAD,
        local_version=project.version,
        remote_version="0.9.0",
        reason="local version is newer",
        zip_path=zip_path,
    )
    client = FakePortalClient({})
    stdout = StringIO()
    with redirect_stdout(stdout):
        status = publish_mods.execute_publish_actions([decision], client, "token-value", {})
    if not assert_equal(status, 0, "execute upload status"):
        return False
    if not assert_equal(client.uploads, [("token-value", "execute-mod", "execute-mod_1.0.0.zip")], "execute upload call"):
        return False

    old_token = os.environ.pop(publish_mods.TOKEN_ENV, None)
    try:
        stderr = StringIO()
        with redirect_stderr(stderr):
            status = publish_mods.main(["--execute", "--root", str(temp), "--output-dir", str(output_dir)])
        if not assert_equal(status, 1, "main rejects --execute without token"):
            return False
        if publish_mods.TOKEN_ENV not in stderr.getvalue():
            print("FAIL: missing-token error should name the required environment variable")
            return False
    finally:
        if old_token is not None:
            os.environ[publish_mods.TOKEN_ENV] = old_token

    return True


def test_multipart_contains_fields() -> bool:
    content_type, body = publish_mods.build_multipart_form(
        {"description": "hello"},
        [("file", "demo.zip", "application/zip", b"zip-bytes")],
    )
    if not content_type.startswith("multipart/form-data; boundary="):
        print(f"FAIL: unexpected multipart content type {content_type}")
        return False
    if b'name="description"' not in body or b"hello" not in body:
        print("FAIL: multipart body missing text field")
        return False
    if b'name="file"; filename="demo.zip"' not in body or b"zip-bytes" not in body:
        print("FAIL: multipart body missing file field")
        return False
    return True


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="publish_mods_verify_") as temp_dir:
        temp = Path(temp_dir)
        checks = [
            test_decision_and_zip_checks(temp),
            test_execute_boundary(temp),
            test_multipart_contains_fields(),
        ]
    if not all(checks):
        return 1

    print("PASS: publish_mods compares versions, validates zips, and keeps upload behind --execute plus token.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
