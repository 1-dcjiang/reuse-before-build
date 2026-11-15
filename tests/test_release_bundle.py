from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import make_release_bundle as bundle  # noqa: E402


class TestReleaseBundlePolicy(unittest.TestCase):
    def test_version_comes_from_skill_frontmatter(self):
        self.assertRegex(bundle.read_version(), r"^[0-9]")

    def test_version_mismatch_is_refused_before_writing(self):
        tmp = tempfile.mkdtemp(prefix="rbb_rel_")
        self.addCleanup(shutil.rmtree, tmp, True)
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "make_release_bundle.py"),
             "--version", "0.0.0", "--out-dir", tmp],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("SKILL.md", proc.stderr)

    def test_tag_must_point_to_head(self):
        tmp = tempfile.mkdtemp(prefix="rbb_rel_")
        self.addCleanup(shutil.rmtree, tmp, True)
        with mock.patch.object(bundle, "read_version", return_value="1.2.9"), \
             mock.patch.object(bundle, "_git",
                               return_value=subprocess.CompletedProcess([], 0, "", "")), \
             mock.patch.object(bundle, "_git_required", side_effect=["tagsha", "headsha"]):
            with self.assertRaisesRegex(ValueError, "不指向当前 HEAD"):
                bundle.build("1.2.9", Path(tmp))

    def test_existing_asset_is_not_overwritten(self):
        tmp = tempfile.mkdtemp(prefix="rbb_rel_")
        self.addCleanup(shutil.rmtree, tmp, True)
        Path(tmp, "SHA256SUMS").write_text("sentinel\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "拒绝覆盖"):
            bundle.build("1.2.9", Path(tmp))
        self.assertEqual(Path(tmp, "SHA256SUMS").read_text(encoding="utf-8"), "sentinel\n")


class TestReleaseBundleSnapshot(unittest.TestCase):
    """只在 v<SKILL version> 指向当前 HEAD 时跑；普通 PR 没有这个 tag。"""

    def test_zip_is_tag_snapshot_and_sums_match(self):
        version = bundle.read_version()
        tag_ref = f"refs/tags/v{version}^{{commit}}"
        tag = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--verify", tag_ref],
            capture_output=True, text=True,
        )
        head = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True,
        )
        if tag.returncode != 0 or tag.stdout.strip() != head.stdout.strip():
            self.skipTest(f"v{version} 不存在或不指向当前 HEAD；发布包测试只在打 tag 的提交上跑")

        tmp = Path(tempfile.mkdtemp(prefix="rbb_rel_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        archive, doc, sums = bundle.build(version, tmp)

        self.assertTrue(archive.is_file())
        self.assertTrue(doc.is_file())
        self.assertEqual(doc.read_bytes(), (ROOT / "references" / "integration-seam.md").read_bytes())

        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
            self.assertTrue(names)
            self.assertTrue(all(n.startswith(f"reuse-before-build-{version}/") for n in names))
            skill = zf.read(f"reuse-before-build-{version}/SKILL.md").decode("utf-8")
            self.assertIn(f"version: {version}", skill)

        lines = sums.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        for line in lines:
            digest, name = line.split("  ", 1)
            path = tmp / name
            self.assertEqual(
                digest,
                hashlib.sha256(path.read_bytes()).hexdigest(),
                f"{name} 的 SHA256SUMS 与实际文件不一致",
            )

    def test_main_refuses_existing_output(self):
        tmp = Path(tempfile.mkdtemp(prefix="rbb_rel_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "integration-seam.md").write_text("sentinel\n", encoding="utf-8")
        rc = bundle.main(["--version", bundle.read_version(), "--out-dir", str(tmp)])
        self.assertEqual(rc, 2)
        self.assertEqual((tmp / "integration-seam.md").read_text(encoding="utf-8"), "sentinel\n")


if __name__ == "__main__":
    unittest.main()
