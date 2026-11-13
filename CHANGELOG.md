# Changelog

## 1.2.6 — 2026-11-13

收尾 v1.2.5 复查剩余小点：

- `auth_ok` 不再硬编码 `"gh"`，改为接受 `gh_binary`；`main()` 用 `shutil.which("gh")` 解析一次，登录检查与检索共用同一个可执行文件。
- 补 `--json-out` 越界、符号链接逃逸、`--gh-host` 透传与 `gh_binary` 回归；离线测试增至 63 条。
- CHANGELOG 日期对齐 GitHub Release 页的 UTC 日期：1.2.2–1.2.5 统一为 2026-11-13。

## 1.2.5 — 2026-11-13

按 v1.2.4 复查（8.3 / 10）修发布前问题：

- `--md-out` / `--json-out` 限定在 `--out-dir`（默认当前目录）内，绝对路径逃逸、`..` 逃逸和符号链接逃逸都会被拒绝；已存在的文件拒绝覆盖，写入使用独占模式 `x`。
- 版本号不再只存在于 tag / CHANGELOG：`SKILL.md` frontmatter 加 `version: 1.2.5`，三个脚本加 `__version__ = "1.2.5"`，README 顶部标注版本。
- 脱敏正则补 URL userinfo（`https://user:pass@host/...`）与 `Cookie:` 头；单测覆盖 gh token、Bearer、api_key、access_token、Authorization、URL 凭据与 Cookie。
- `auth_ok` 支持 `--gh-host` 显式指定目标 host，不再只能查 `GH_HOST` / github.com 一个固定值；检索子进程同步使用该 host。
- 补齐 1.1.0–1.2.1 的占位日期。
- 新增输出路径、防覆盖、脱敏正则、`--gh-host` 与版本号回归；58 tests OK，ruff check 全绿。

## 1.2.4 — 2026-11-13

按第三轮复查（8.3 / 10）同步主仓扫描器：

- 脱敏正则新增 `Bearer`、`api_key`、`access_token`、`Authorization`；坏 JSON 的 stdout 片段也过 `redact_text()`。
- `activity_points` 先判 `isinstance(str)`，数字/列表不再让 `.replace` 抛 `AttributeError`。
- CLI 参数校验：`--stars` 限制 0..1,000,000，`--limit` 限制 1..10，`--updated-since` 必须是 `YYYY-MM-DD`。
- 新增非字符串 `pushedAt`、坏 JSON stdout 脱敏、CLI 参数校验回归；51 tests OK，ruff check 全绿。
- 规则本体、契约哈希、四段提示词 sha256 均未变。

## 1.2.3 — 2026-11-13

按第二轮第三方复查同步 `scripts/repo_scan.py` 的同类加固：

- `gh_json` / `auth_ok` 统一捕获 `OSError`（含 `PermissionError`），子进程启动失败转成可读 `RuntimeError`。
- stderr 回显前经 `redact_text()` 去掉 token/口令与本机绝对路径。
- `parse_search_output` 只保留 dict 行，非 dict 的 `--json` 输出不再让后续 `row.get` 崩。
- `activity_points` 把 `now - pushed` 纳入 `try`，无时区时间抛 `TypeError` 时返回 0。
- 去重键 `url` / `full_name` 都空时直接跳过，不再合并成一条无来源候选。
- 新增非 dict JSON、无时区时间、PermissionError、stderr 脱敏回归；48 tests OK，ruff check 全绿。
- 规则本体、契约哈希、四段提示词 sha256 均未变。

## 1.2.2 — 2026-11-13

- **`gh` 参数注入**：`scripts/repo_scan.py` 的 `gh search repos` 改为所有选项前置、检索串放在 `--` 之后；`-foo` 这类关键词不再被当成选项。
- **契约测试**：新增 `tests/fixtures/gh_search_repos.json`（录好的真实 `--json` 输出），既直接测 JSON 形状，也用假 `gh` 真正跑一遍 `subprocess` 并校验 `--` 前后的 argv 顺序。
- 规则本体、契约哈希 `fa0f991f…bc93`、四段提示词 sha256 均未变。

## 1.2.1 — 2026-11-13

- `prompt_digest.py` 登记表结构校验：缺 `id` / `versions` 非数组 / id 重复 / `prompts` 非数组 → `FAIL` + `rc=2`。
- `verify_localized.py` 换 NEKO 版；清理 7 个 E741。

## 1.2.0 — 2026-11-13

- 四段粘贴型提示词 sha256 登记（`prompt-digests.json` + `scripts/prompt_digest.py`）。
- `references/host-adapters.md` 增加 `RBB:PROMPT` 锚点与版本核对说明。

## 1.1.0 — 2026-11-13

- 可改性硬闸（`references/repo-triage.md`，红档禁止 Join）。
- 稳定接入口 + ≤150 行薄适配层（`references/integration-seam.md`）。
- 贡献协议加入分支纪律：不直推默认分支。
