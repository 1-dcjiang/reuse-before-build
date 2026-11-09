#!/usr/bin/env python3
"""离线 smoke test：不联网也能跑，只依赖标准库。

跑法：
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import contextlib
import datetime as dt
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPT = os.path.join(ROOT, "scripts", "repo_scan.py")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import repo_scan  # noqa: E402


def run(args, env=None, timeout=90):
    return subprocess.run(
        [sys.executable, "-X", "utf8", SCRIPT, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
    )


class TestHelpers(unittest.TestCase):
    def test_md_cell_escapes_pipe(self):
        self.assertEqual(repo_scan.md_cell("a|b"), "a\\|b")

    def test_md_cell_flattens_newlines(self):
        self.assertEqual(repo_scan.md_cell("a\nb\rc"), "a b c")

    def test_md_cell_empty(self):
        self.assertEqual(repo_scan.md_cell(None), "-")
        self.assertEqual(repo_scan.md_cell(""), "-")

    def test_default_since_survives_leap_day(self):
        # 2028 是闰年；旧实现 replace(year-1) 会 ValueError。减 365 天落到 2027-03-01。
        self.assertEqual(repo_scan.default_since(dt.date(2028, 2, 29)), "2027-03-01")

    def test_default_since_normal_date(self):
        self.assertEqual(repo_scan.default_since(dt.date(2026, 11, 9)), "2025-11-09")

    def test_render_table_escapes_every_cell(self):
        row = {
            "full_name": "a/b|c", "stargazersCount": 3, "license": {"key": "mit"},
            "pushedAt": "2026-01-01T00:00:00Z", "language": "Py\nthon",
            "openIssuesCount": 1, "url": "https://x|y", "matched_keyword": ["k|w"],
            "_activity": 2, "_lic_label": "MIT",
        }
        lines = repo_scan.render_table([row]).splitlines()
        self.assertEqual(len(lines), 3, "表头 + 分隔行 + 1 行数据")
        for line in lines:
            # 未被反斜杠转义的竖线才是列分隔符，必须正好 9 个（8 列）
            self.assertEqual(len(re.findall(r"(?<!\\)\|", line)), 9, f"列数被破坏：{line}")
        self.assertIn("a/b\\|c", lines[2])

    def test_render_table_stalled_marker(self):
        row = {
            "full_name": "a/b", "stargazersCount": 1, "pushedAt": "2024-01-01T00:00:00Z",
            "language": "Go", "openIssuesCount": 0, "url": "https://x",
            "matched_keyword": ["k"], "_activity": 0, "_lic_label": "MIT",
        }
        self.assertIn("⚠停滞", repo_scan.render_table([row]))


class TestOutputs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rbb_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run_stubbed(self, keywords, extra_args, scan_result):
        old_argv, old_auth, old_scan = sys.argv, repo_scan.auth_ok, repo_scan.scan
        try:
            repo_scan.auth_ok = lambda: (True, "")
            repo_scan.scan = lambda kw, s, u, l: scan_result
            sys.argv = [SCRIPT, *keywords, *extra_args]
            err, out = io.StringIO(), io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                code = repo_scan.main()
        finally:
            sys.argv, repo_scan.auth_ok, repo_scan.scan = old_argv, old_auth, old_scan
        return code, out.getvalue(), err.getvalue()

    def test_md_and_json_out_are_written(self):
        row = {"full_name": "o/r", "stargazersCount": 9, "pushedAt": "2026-11-01T00:00:00Z",
               "license": {"key": "mit"}, "language": "Rust", "openIssuesCount": 2,
               "url": "https://github.com/o/r", "matched_keyword": "kw"}
        md = os.path.join(self.tmp, "c.md")
        js = os.path.join(self.tmp, "c.json")
        code, out, _ = self._run_stubbed(["kw"], ["--md-out", md, "--json-out", js], ([row], True))
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(md))
        with open(md, encoding="utf-8") as fh:
            self.assertIn("o/r", fh.read())
        with open(js, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data[0]["full_name"], "o/r")
        self.assertIn("_lic_score", data[0])

    def test_no_files_written_on_rc3(self):
        md = os.path.join(self.tmp, "c.md")
        js = os.path.join(self.tmp, "c.json")
        code, _, err = self._run_stubbed(["kw"], ["--md-out", md, "--json-out", js], ([], False))
        self.assertEqual(code, 3)
        self.assertFalse(os.path.exists(md))
        self.assertFalse(os.path.exists(js))
        self.assertIn("未写出", err)


class TestCli(unittest.TestCase):
    def test_help(self):
        proc = run(["--help"])
        self.assertEqual(proc.returncode, 0)
        for flag in ("--stars", "--updated-since", "--limit", "--md-out", "--json-out"):
            self.assertIn(flag, proc.stdout)

    def test_missing_keywords(self):
        proc = run([])
        self.assertEqual(proc.returncode, 2)

    def test_gh_absent_returns_2(self):
        gh = shutil.which("gh")
        if not gh:
            self.skipTest("本机没有 gh，跳过（该场景已由 test_gh_absent_* 的 PATH 剥离覆盖）")
        env = dict(os.environ)
        keep = [p for p in env.get("PATH", "").split(os.pathsep)
                if p and not os.path.exists(os.path.join(p, "gh.exe")) and not os.path.exists(os.path.join(p, "gh"))]
        env["PATH"] = os.pathsep.join(keep)
        proc = run(["x"], env=env)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("未找到 gh CLI", proc.stderr)

    def test_all_keywords_fail_returns_3(self):
        """gh 可用但检索全失败（限流/瞬时故障）时必须是 rc=3，不能是 0。

        用打桩代替真联网：auth 通过、每个关键词都返回 ok=False。
        """
        import contextlib
        import io

        old_argv = sys.argv
        old_auth, old_scan = repo_scan.auth_ok, repo_scan.scan
        try:
            repo_scan.auth_ok = lambda: (True, "")
            repo_scan.scan = lambda kw, s, u, l: ([], False)
            sys.argv = [SCRIPT, "obsidian sync plugin"]
            err, out = io.StringIO(), io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                code = repo_scan.main()
        finally:
            sys.argv = old_argv
            repo_scan.auth_ok, repo_scan.scan = old_auth, old_scan
        self.assertEqual(code, 3)
        self.assertIn("检索失败 ≠ 没有同类项目", err.getvalue())

    def test_gh_host_unreachable_returns_2(self):
        """gh 在但连不上主机：属于 gh 不可用，rc=2，且提示里要点明不是'没搜到'。"""
        if not shutil.which("gh"):
            self.skipTest("本机没有 gh")
        env = dict(os.environ)
        env["GH_HOST"] = "nohost.invalid"
        proc = run(["obsidian sync plugin"], env=env)
        self.assertEqual(proc.returncode, 2, msg=proc.stderr[-400:])
        self.assertIn("gh 无法确认可用", proc.stderr)


if __name__ == "__main__":
    unittest.main()
