# Changelog

## 1.2.2 — 2026-11-14

- **`gh` 参数注入**：`scripts/repo_scan.py` 的 `gh search repos` 改为所有选项前置、检索串放在 `--` 之后；`-foo` 这类关键词不再被当成选项。
- **契约测试**：新增 `tests/fixtures/gh_search_repos.json`（录好的真实 `--json` 输出），既直接测 JSON 形状，也用假 `gh` 真正跑一遍 `subprocess` 并校验 `--` 前后的 argv 顺序。
- 规则本体、契约哈希 `fa0f991f…bc93`、四段提示词 sha256 均未变。

## 1.2.1 — 2026-11-XX

- `prompt_digest.py` 登记表结构校验：缺 `id` / `versions` 非数组 / id 重复 / `prompts` 非数组 → `FAIL` + `rc=2`。
- `verify_localized.py` 换 NEKO 版；清理 7 个 E741。

## 1.2.0 — 2026-11-XX

- 四段粘贴型提示词 sha256 登记（`prompt-digests.json` + `scripts/prompt_digest.py`）。
- `references/host-adapters.md` 增加 `RBB:PROMPT` 锚点与版本核对说明。

## 1.1.0 — 2026-11-XX

- 可改性硬闸（`references/repo-triage.md`，红档禁止 Join）。
- 稳定接入口 + ≤150 行薄适配层（`references/integration-seam.md`）。
- 贡献协议加入分支纪律：不直推默认分支。
