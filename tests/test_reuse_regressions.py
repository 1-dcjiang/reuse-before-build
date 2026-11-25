#!/usr/bin/env python3
"""reuse-before-build 的回归测试：锁住与 neko 插件同源的缺陷。"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, "scripts")
VERIFY = os.path.join(SCRIPTS, "verify_localized.py")
SCAN = os.path.join(SCRIPTS, "repo_scan.py")
CONTRACT = os.path.join(ROOT, "localization.contract.json")
sys.path.insert(0, SCRIPTS)

import repo_scan  # noqa: E402


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestContractBaseline(unittest.TestCase):
    def setUp(self):
        self.verify = _load(VERIFY, "rbb_verify_regression")

    def _contract(self):
        with open(CONTRACT, encoding="utf-8") as fh:
            return json.load(fh)

    def test_code_baseline_matches_the_shipped_contract(self):
        contract = self._contract()
        self.assertEqual(
            contract["block"]["canonical_sha256"].lower(),
            self.verify.CANONICAL_SHA256,
        )
        self.assertEqual(self.verify.check_contract_baseline(contract), [])

    def test_relaxed_contract_is_rejected(self):
        contract = self._contract()
        contract["rules_min"] = 1
        contract["must_have"] = [item for item in contract["must_have"] if item["id"] != "gate"]
        contract["declaration"]["keys"] = ["host"]
        contract["declaration"]["within_last"] = 999
        missing = self.verify.check_contract_baseline(contract)
        self.assertIn("rules_min:1!=6", missing)
        self.assertIn("must_have_ids", missing)
        self.assertIn("declaration_keys", missing)
        self.assertIn("declaration_within_last:999!=8", missing)
        contract = self._contract()
        contract["must_have"][0]["any"] = [""]
        self.assertIn(
            "must_have:gate(any_empty_or_non_string)",
            self.verify.check_contract_baseline(contract),
        )
        contract = self._contract()
        contract["rule_anchors"][0]["any"] = [None]
        self.assertIn(
            "rule_anchors:rule_1(any_empty_or_non_string)",
            self.verify.check_contract_baseline(contract),
        )

    def test_bad_anchor_types_do_not_crash_direct_checks(self):
        self.assertEqual(
            self.verify.check_anchors("anything", [{"id": "bad", "any": [None]}], "anchor"),
            ["anchor:bad"],
        )

    def test_bad_contract_root_shapes_do_not_crash(self):
        self.assertEqual(self.verify.contract_root_errors([]), ["contract(not_object)"])
        contract = self._contract()
        self.assertEqual(self.verify.contract_root_errors(contract), [])
        contract["block"] = []
        self.assertEqual(self.verify.contract_root_errors(contract), ["block(not_object)"])
        contract = self._contract()
        contract["block"]["begin"] = 1
        self.assertEqual(self.verify.contract_root_errors(contract), ["block.begin(not_string)"])
        contract = self._contract()
        contract["block"]["lang_marker_prefix"] = 1
        self.assertEqual(
            self.verify.contract_root_errors(contract),
            ["block.lang_marker_prefix(not_string)"],
        )
        contract = self._contract()
        contract["block"]["canonical_files"] = ["SKILL.md", 1]
        self.assertEqual(
            self.verify.contract_root_errors(contract),
            ["block.canonical_files(not_string_list)"],
        )
        contract = self._contract()
        contract["declaration"] = ["x"]
        self.assertEqual(
            self.verify.contract_root_errors(contract),
            ["declaration(not_object)"],
        )
        contract = self._contract()
        contract["declaration"]["keys"] = 1
        self.assertEqual(
            self.verify.contract_root_errors(contract),
            ["declaration.keys(not_string_list)"],
        )
        contract = self._contract()
        contract["declaration"]["prefix"] = 1
        self.assertEqual(
            self.verify.contract_root_errors(contract),
            ["declaration.prefix(not_string)"],
        )
        contract = self._contract()
        contract["declaration"]["within_last"] = "abc"
        self.assertEqual(
            self.verify.contract_root_errors(contract),
            ["declaration.within_last(not_int)"],
        )

    def test_contract_flag_still_cannot_point_outside_the_package(self):
        tmp = tempfile.mkdtemp(prefix="rbb_contract_")
        self.addCleanup(shutil.rmtree, tmp, True)
        path = os.path.join(tmp, "empty-contract.json")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("{}")
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", VERIFY, os.path.join(ROOT, "SKILL.md"),
             "--contract", path],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("REFUSED", proc.stderr)


class TestRepoScanDedupe(unittest.TestCase):
    def test_repeated_keyword_is_not_duplicated_in_the_table(self):
        row = {
            "full_name": "o/r",
            "stargazersCount": 9,
            "pushedAt": "2026-11-01T00:00:00Z",
            "license": {"key": "mit"},
            "language": "Rust",
            "openIssuesCount": 2,
            "url": "https://github.com/o/r",
            "matched_keyword": "kw",
        }
        old_argv = sys.argv
        old_auth, old_scan, old_which = repo_scan.auth_ok, repo_scan.scan, repo_scan.which_path_only
        try:
            repo_scan.auth_ok = lambda *args, **kwargs: (True, "")
            repo_scan.scan = lambda *args, **kwargs: ([dict(row)], True)
            repo_scan.which_path_only = lambda name: "gh"
            sys.argv = [SCAN, "kw", "kw"]
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = repo_scan.main()
        finally:
            sys.argv = old_argv
            repo_scan.auth_ok, repo_scan.scan, repo_scan.which_path_only = old_auth, old_scan, old_which
        self.assertEqual(code, 0, err.getvalue())
        self.assertNotIn("kw, kw", out.getvalue())

    def test_case_insensitive_duplicate_keyword_is_not_scanned_twice(self):
        row = {
            "full_name": "o/r",
            "stargazersCount": 9,
            "pushedAt": "2026-11-01T00:00:00Z",
            "license": {"key": "mit"},
            "language": "Rust",
            "openIssuesCount": 2,
            "url": "https://github.com/o/r",
            "matched_keyword": "Kw",
        }
        calls = []
        old_argv = sys.argv
        old_auth, old_scan, old_which = repo_scan.auth_ok, repo_scan.scan, repo_scan.which_path_only
        try:
            repo_scan.auth_ok = lambda *args, **kwargs: (True, "")
            repo_scan.scan = lambda kw, *args, **kwargs: (calls.append(kw) or [dict(row)], True)
            repo_scan.which_path_only = lambda name: "gh"
            sys.argv = [SCAN, "Kw", "kw", "KW"]
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = repo_scan.main()
        finally:
            sys.argv = old_argv
            repo_scan.auth_ok, repo_scan.scan, repo_scan.which_path_only = old_auth, old_scan, old_which
        self.assertEqual(code, 0, err.getvalue())
        self.assertEqual(calls, ["Kw"])
        self.assertIn("Kw", out.getvalue())


if __name__ == "__main__":
    unittest.main()



class TestCriticalSections(unittest.TestCase):
    """1.2.13：关键章节正文只有"关键词"不算过，正文哈希与代码基线双锁。"""

    def setUp(self):
        self.verify = _load(VERIFY, "rbb_verify_sections")

    def _contract(self):
        with open(CONTRACT, encoding="utf-8") as fh:
            return json.load(fh)

    def _skill(self):
        with open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8") as fh:
            return fh.read()

    def test_shipped_contract_pins_every_section(self):
        contract = self._contract()
        self.assertEqual(contract["version"], 5)
        self.assertEqual(
            {item["id"] for item in contract["critical_sections"]},
            set(self.verify.CANONICAL_SECTION_SHA256),
        )
        self.assertEqual(self.verify.check_contract_baseline(contract), [])

    def test_shipped_skill_matches_pinned_sections(self):
        contract = self._contract()
        self.assertEqual(
            self.verify.check_critical_sections(
                self._skill(), contract["critical_sections"], True
            ),
            [],
        )

    def test_one_extra_sentence_in_a_section_is_rejected(self):
        contract = self._contract()
        text = self._skill()
        tampered = text.replace(
            "**Modifiability gate, before any Join verdict.**",
            "**Modifiability gate, before any Join verdict.** 这一句原文没有。",
            1,
        )
        self.assertNotEqual(tampered, text)
        self.assertIn(
            "section_hash:step2",
            self.verify.check_critical_sections(tampered, contract["critical_sections"], True),
        )

    def test_body_and_contract_hash_rewritten_together_are_rejected(self):
        contract = self._contract()
        contract["critical_sections"][0]["sha256"] = "0" * 64
        self.assertIn(
            "critical_sections_hash:step2",
            self.verify.check_contract_baseline(contract),
        )

    def test_dropped_section_or_relaxed_floor_is_rejected(self):
        contract = self._contract()
        del contract["critical_sections"][0]
        self.assertIn("critical_sections:step2", self.verify.check_contract_baseline(contract))
        contract = self._contract()
        contract["critical_sections"][2]["min_chars"] = 1
        self.assertIn(
            "critical_sections_floor:hard_constraints(1<350)",
            self.verify.check_contract_baseline(contract),
        )

    def test_section_hash_is_crlf_safe(self):
        contract = self._contract()
        crlf = self._skill().replace("\n", "\r\n")
        self.assertEqual(
            self.verify.check_critical_sections(crlf, contract["critical_sections"], True),
            [],
        )
