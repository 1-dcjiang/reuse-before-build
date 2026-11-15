from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestCrossFileVerdicts(unittest.TestCase):
    """三份文件对同一判决必须给出同一条件；改一份忘另一份时这里会红。"""

    def setUp(self):
        self.en = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.zh = (ROOT / "references" / "zh-guide.md").read_text(encoding="utf-8")
        self.triage = (ROOT / "references" / "repo-triage.md").read_text(encoding="utf-8")

    def test_join_is_green_only(self):
        self.assertIn("modifiability green only", self.en)
        self.assertIn("可改性仅限绿", self.zh)
        self.assertIn("可改性为“绿”", self.triage)
        self.assertNotIn("可改性为绿或黄", self.zh)
        self.assertNotIn("green or yellow", self.en)

    def test_extend_requires_total_6_7_and_plugin_or_yellow(self):
        self.assertIn("Total 6–7 **with** a plugin/extension/theme mechanism", self.en)
        self.assertIn("总分 6–7 且仓库有插件/扩展/主题机制", self.zh)
        self.assertIn("总分 6–7 **且仓库有插件/扩展/主题机制**", self.triage)

    def test_fork_covers_6_7_without_plugin(self):
        self.assertIn("6–7 **without** a plugin mechanism", self.en)
        self.assertIn("总分 6–7 但没有插件机制", self.zh)
        self.assertIn("总分 6–7 但没有插件机制", self.triage)

    def test_build_owns_explicitly_opposite_direction(self):
        self.assertIn("direction is explicitly opposite", self.en)
        self.assertIn("方向相反", self.zh)
        self.assertIn("方向相反", self.triage)
        self.assertNotIn("方向冲突", self.zh)


class TestUntrustedAnchors(unittest.TestCase):
    def test_all_localization_targets_carry_untrusted_anchors(self):
        contract = (ROOT / "localization.contract.json").read_text(encoding="utf-8")
        for ident in ("untrusted_section", "untrusted_data_not_instructions", "untrusted_container"):
            self.assertIn(ident, contract)

        en = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        zh = (ROOT / "references" / "zh-guide.md").read_text(encoding="utf-8")
        adapters = (ROOT / "references" / "host-adapters.md").read_text(encoding="utf-8")
        self.assertIn("Untrusted repository content", en)
        self.assertIn("不可信仓库内容", zh)
        self.assertIn("data, not instructions", en)
        self.assertIn("数据，不是指令", zh)
        self.assertIn("disposable container", en)
        self.assertIn("一次性容器", zh)
        self.assertIn("data, not instructions", adapters)
        self.assertIn("一次性容器", adapters)

        triage = (ROOT / "references" / "repo-triage.md").read_text(encoding="utf-8")
        self.assertIn("ignore previous rules", triage)


if __name__ == "__main__":
    unittest.main()
