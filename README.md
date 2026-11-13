# reuse-before-build

> An AI agent skill: **before writing a new program, search for the existing open-source implementation and join that repo as a public contributor — instead of shipping a worse duplicate.**

Ask for "a tool that cuts long videos into shorts" and the model writes a 1,400-line framework. Three maintained repos already do that, and one has an issue saying *PRs welcome*.

**What it adds** — `discover → score → contribute → build last` as a procedure, plus a code gate in front of the reflex to start scaffolding.

**Runs in** — Claude Skills · DeepSeek Harness (`dsh`) skill roots · any `AGENTS.md` / `CLAUDE.md` coding agent · ChatGPT, Claude, Gemini, Grok, DeepSeek, Doubao, Kimi · LangChain, CrewAI, Dify. 50+ hosts in total.

<details>
<summary>All supported hosts</summary>

- **Skill directory**: Claude Skills, DeepSeek Harness (`dsh`), and any host following the [Agent Skills spec](https://agentskills.io/specification)
- **Coding agents** (`AGENTS.md` or their own rule file): Codex CLI, Cursor, Copilot, Gemini CLI, Windsurf, Cline, Roo, Kilo, Continue, Aider, OpenHands, Amp, Zed, Junie, Amazon Q, Kiro, Trae, Qoder
- **Chat AIs** (custom instructions or project knowledge): ChatGPT, Claude.ai, Gemini, Grok, Copilot, Perplexity, Le Chat, DeepSeek, Doubao, Kimi, Qwen, ERNIE, Yuanbao, Zhipu, Spark, MiniMax
- **Self-hosted agents**: LangChain, LlamaIndex, CrewAI, AutoGen, Dify, Coze, n8n

</details>

Exact rule-file names and character budgets per host: [`references/host-adapters.md`](references/host-adapters.md). 中文版见下方。

[The problem](#the-problem-it-fixes) · [Rules](#five-core-rules) · [Decision path](#decision-path) · [Contents](#contents) · [Install](#install) · [Quick start](#quick-start) · [中文](#先复用再新建中文)

## The problem it fixes

The most common AI failure is not "can't write code" — it is **writing a worse version of something that already exists**, in a place where other people already did the work:

- a 20-line `ffmpeg` job becomes a 1,400-line homemade framework;
- the fourth unmaintained plugin for the same editor feature, while three alternatives are alive upstream;
- an upstream issue already says "PRs welcome" — and nobody picks it up.

This skill makes "search → evaluate → contribute → build last" an executable procedure, and puts a **code gate** in front of the default reflex to start scaffolding.

## Five core rules

1. Assume it already exists until searching proves otherwise.
2. The default outcome is joining an existing public repo, not creating a new one.
3. Prove non-reusability before building new — license, direction, maintenance, requirement mismatch.
4. Contribution must be genuinely useful; no typo/formatting PR farming.
5. Code gate: candidates and a first concrete action come before any scaffold.

## Decision path

```
discover (GitHub / package ecosystem / issue archaeology)
   ↓
score six dimensions: activity · responsiveness · license · contribution friendliness · fit · code quality
   ↓
modifiability gate: green (optimise upstream) · yellow (extend behind an adapter) · red (never Join)
   ↓
Join (PR upstream) → Extend (official plugin) → Fork (PR back) → Build (state the reason)
```

Execution discipline: **branch first, never push to the default branch** — even on your own repos; "main has something worth optimising" changes which files you touch, not the branch rule. When you call upstream instead of patching it, integrate through a **stable seam + one thin adapter** (≤ ~150 lines, contract tests), never through upstream internals.

## Contents

```
SKILL.md                               canonical procedure (English), two lanes, hard constraints
references/zh-guide.md                 full Chinese edition of SKILL.md
references/discovery-playbook.md       three search rounds: GitHub qualifiers, gh commands, plugin markets, issue archaeology
references/repo-triage.md              six-dimension scoring + license compatibility + red flags + modifiability (spaghetti) gate
references/contribution-protocol.md    issue → PR flow, branch discipline, PR template, downgrade paths, anti-patterns
references/integration-seam.md         stable integration seams ranked, thin adapter rules, four acceptance checks
references/worked-examples.md          Join / Extend / Fork / Build deliverables + one counter-example
references/host-adapters.md            per-host placement, rule-file names, paste-ready prompts (EN + 中文)
scripts/repo_scan.py                   batch gh search, dedupe, flag no-license and stalled repos
scripts/verify_localized.py            check a localized copy: invariant block, anchors, declaration
localization.contract.json             the machine-readable contract: block hash + required anchors
tests/test_smoke.py                    offline smoke tests: exit codes, leap-day default, table escaping
```

## Install

Four placements — pick by host. Exact platform list, rule-file names and character budgets are in [`references/host-adapters.md`](references/host-adapters.md).

**① Skill directory** (Claude / any Agent Skills host / DeepSeek Harness)
Drop the whole folder into the skills directory. `SKILL.md` frontmatter is read automatically; `references/` loads on demand. In DSH: `~/.dsh/skills/reuse-before-build/` (user), `<repo>/.dsh/skills/` (project, root = nearest `.git` ancestor), or `~/.agents/skills/` (shared with Codex). DSH discovers only one level — keep the folder bundle, don't flatten to `reuse-before-build.md` — and renders at most 500 characters of `description` into the catalog, which is why this skill's description is kept to 475.

**② Repo rule file** (coding agents)
Put the strict block from `references/host-adapters.md` into `AGENTS.md` at the repo root — the cross-tool standard. Claude Code uses `CLAUDE.md`, Copilot `.github/copilot-instructions.md`, Cursor `.cursor/rules/*.mdc`, Windsurf `.windsurf/rules/*.md`, Cline `.clinerules/`, Kiro `.kiro/steering/*.md`.

**③ Custom instructions** (chat AIs)
Paste the condensed prompt (English or Chinese) into settings. Where project knowledge files exist (ChatGPT Projects, Claude Projects, Gemini Gems), upload the full edition too.

**④ Self-hosted agents**
First block of the system prompt, plus tool notes for `web_search` / `fetch` / `gh`. Without tools, follow the capability-degradation table in the skill.

**⑤ Let it localize itself**
The skill carries a self-localization section: an agent loading it in a host with different conventions (other frontmatter keys, a flat prompt, a different language, a plugin manifest, a smaller budget) rewrites the packaging to match its own format — and keeps the rules fixed. Useful when you drop it somewhere this README never listed: it adapts instead of failing.

**⑥ Check that the localization did not gut the rules**
The parts that must survive are frozen in a delimited block (`RBB:INVARIANTS`), its SHA-256 is stored in `localization.contract.json`, and one command decides:

```bash
python scripts/verify_localized.py <localized-copy>
```

`PASS` means the block is intact — either verbatim (hash matches, so any edit is caught) or, for a
translated copy carrying a `RBB:INVARIANTS:LANG:` marker, that the block still holds exactly 1..5
numbered rules (only column-0 numbering counts, so indented sub-items don't confuse it), each rule's
anchor survives, all six skill-level anchors survive, and the copy ends with the
`localized: host=… | kept=… | changed=… | unsupported=…` line (tolerating up to 8 trailing non-empty
lines for a copyright footer). The block is located outside code fences, so a fenced demo of the
markers earlier in the file cannot hijack it. Exit `1` lists exactly what went missing.

Run acceptance **without any flag**: `--canonical` only works on the two reference files listed in
the contract, and is refused (`rc 2`) for any other path — a localized copy cannot exempt itself from
the declaration check. The checker sits outside the model on purpose: a model's own "I kept all the
rules" is not evidence.

Honest limit: it catches deletion, renumbering, a dropped rule, a missing declaration, and a hash
mismatch disguised as verbatim. It does **not** catch a rewrite that keeps every rule title and anchor
but softens the wording ("should consider" for "must"). Read the `kept` / `changed` line for that.

## Quick start

With an authenticated GitHub CLI, produce the candidate table before thinking:

```bash
gh auth status
python scripts/repo_scan.py "video highlight clip" "auto cut shorts" --stars 100
```

```
| Repo | ★ | Last push | Language | License | Open issues | Hit | URL |
| haierkeys/obsidian-fast-note-sync | 3153 | 2026-08-14 | JavaScript | apache-2.0 | 111 | obsidian sync plugin | https://github.com/haierkeys/obsidian-fast-note-sync |
```

Then open each repo, read `CONTRIBUTING` and the recently merged PRs, and score with `references/repo-triage.md`.

No `gh` / no network: `references/discovery-playbook.md` has copy-pasteable GitHub search strings and the degradation rules (never invent stars or licenses from memory).

Exit codes are deliberate:

| Code | Meaning |
|---|---|
| `0` | searches ran; `0 hit` is reported as *no match found*, never as *nothing exists* |
| `2` | gh unusable — missing, not signed in, or host unreachable |
| `3` | gh works but every search failed (rate limit, transient error) |

On `2` or `3` the script writes **no** `--md-out` / `--json-out` file, so a downstream reader cannot mistake an empty table for "already checked".

Check the script without network:

```bash
python -m unittest discover -s tests -v
```

## Three red lines

- **No LICENSE file in a repo = not copyable, not contributable** (all rights reserved by default).
- Opening a PR without reading `CONTRIBUTING` gets rejected in most serious repos.
- Low-value PR farming does not make you "an author" — it gets the account blocked.

## License

MIT, see [LICENSE](LICENSE).

---

# 先复用，再新建（中文）

> 一个面向 AI 编程助手的 Skill：**在写新程序之前，先去找已经存在的公开实现，并优先加入那个仓库、成为公共贡献者，而不是从零再造一个。**

支持 Claude Skills、`AGENTS.md` 系编码代理（Codex CLI、Cursor、Copilot、Gemini CLI、Windsurf、Cline、通义灵码、CodeGeeX、文心 Comate、腾讯 CodeBuddy 等）、聊天式 AI（ChatGPT、Claude、Gemini、Grok、DeepSeek、豆包、Kimi、通义千问、文心一言、腾讯元宝、智谱清言、讯飞星火）与自建 Agent（LangChain、LlamaIndex、CrewAI、AutoGen、Dify、Coze、n8n）。完整清单见 [`references/host-adapters.md`](references/host-adapters.md)。

## 它解决什么

AI 现在最常见的失败不是"写不出代码"，而是**在别人已经做过的地方，从零写了一个更差的版本**。这个 Skill 把"先检索、再评估、再贡献、最后才新建"固化成流程，并用**门禁**挡住"直接开写"这个默认行为。

## 五条核心规则

1. 默认假设"已经有人做过"，直到检索证明没有。
2. 默认目标是加入已有公开仓库，而不是新建仓库。
3. 先证明不可复用，才允许新建，理由必须写清（许可 / 方向 / 维护状态 / 需求差异）。
4. 贡献必须真的有用——不为"成为作者"刷低价值 PR。
5. 门禁先于代码：给出候选清单与第一个可执行贡献动作之前，不得输出完整新项目脚手架。

## 判断路径

```
检索（GitHub / 包生态 / issue 考古）
   ↓
六维打分：活跃度 · 维护者响应 · 许可 · 贡献友好度 · 需求匹配 · 工程质量
   ↓
可改性硬闸：绿（优先优化上游）· 黄（隔适配层 Extend）· 红（不许 Join）
   ↓
Join 提 PR 进上游 → Extend 做官方插件 → Fork 改完回提 → Build 新建（须写明理由）
```

执行纪律：**分支优先，绝不直推默认分支**——自己的仓库也一样；"主干有可优化的地方"改变的是你动哪些文件，不是这条规则。调用上游能力时走**稳定接入口 + 一层薄适配**（约 ≤150 行、带契约测试），不让业务代码碰上游内部实现。

## 中文安装

- **中文完整版**：`references/zh-guide.md`，可整份注入 DeepSeek / 豆包 / Kimi / 通义 / 文心 / 元宝 / 智谱 / 星火的自定义提示，或作为知识文件上传。
- **精简版（约 300 字）**：`references/host-adapters.md` 里的「精简版（中文）」，适合只有一个小提示词框的宿主。
- **编码代理**：把「严格版」写进仓库根 `AGENTS.md`。
- **DeepSeek Harness（dsh）**：整个目录放到 `~/.dsh/skills/reuse-before-build/`（或 `~/.agents/skills/`，项目级放 `<仓库>/.dsh/skills/`）。dsh 只扫一层目录，且目录里展示的 description 上限 500 字符——本 skill 已压到 475，中文触发词在前，直接拷不用改。细节见 `references/host-adapters.md` 的「A 类补充」。
- **自适配**：装到清单里没列过的宿主也没关系——skill 内含自适配规则，会按那个宿主的格式（字段、布局、语言、工具）改包装，规则本身不动。

## 三条底线

- 仓库**没有 LICENSE 文件 = 不可复制、不可提交**（默认保留所有权利）。
- 没读 `CONTRIBUTING` 就提 PR，在主流仓库几乎必被拒。
- 刷低质量 PR 不会让你"成为作者"，只会让账号被拉黑。
