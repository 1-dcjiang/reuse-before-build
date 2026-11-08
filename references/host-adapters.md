# 宿主适配：把同一套规则装进不同 AI

本 skill 的规则是"意图 + 流程"，不依赖特定工具。各平台只决定两件事：**放在哪里**、**有多少字数预算**。

## 各平台落位

| 平台 | 放在哪里 | 注意 |
|---|---|---|
| Claude（Code / Desktop，支持 Skills） | 把整个 `reuse-before-build/` 目录放进 Skills 目录（有 `SKILL.md` 与 `references/`） | 能读文件时按 SKILL.md 走完整流程 |
| Claude Code / Cursor 等编码代理 | 把本 skill 的核心规则写成仓库根 `CLAUDE.md` / `AGENTS.md` 的一节，或放进 `.claude/skills/` | 与"先读 CONTRIBUTING"配合最有效 |
| ChatGPT / GPTs / Projects | 自定义指令（Custom Instructions）或项目说明，粘贴"精简版" | 单框字数有限，用精简版；完整版放知识文件 |
| Grok | 自定义指令 / 会话首条系统提示；擅长 X 与网页搜索 | 让它先搜"是否有人做过 + 是否有人提过需求" |
| DeepSeek / 通义 / Kimi / 豆包 等国内模型 | 系统提示或"自定义人设/提示词"；有联网搜索时先开搜索 | 中文需求容易只搜中文，务必提醒它翻成英文再搜 |
| 任意支持函数调用的自建 Agent | 作为 system prompt 的第一段 + 工具说明（web search / gh CLI / repo 读取） | 没有工具时按"能力受限"降级 |

## 精简版（中文，约 300 字，可直接粘贴）

```text
在写任何新程序、脚本、库、插件或服务之前，你必须先搜索是否已经存在同类型或同一想法的公开项目，尤其是 GitHub 上的开源仓库。

规则：
1. 先假设"已经有人做过"，直到检索证明没有。禁止先写雏形再找参考。
2. 检索至少三轮：① GitHub 仓库/代码搜索（带 stars、language、pushed 限定符，关键词要翻成英文并做同义扩展）；② 包管理器与框架插件市场（npm/PyPI/crates/官方插件目录/awesome-list）；③ 在候选仓库的 issue 里查是否已有人提过同样需求、维护者是否回过"PR welcome"。
3. 给出 3–6 个候选，并按"活跃度 / 维护者响应 / 许可证 / 贡献友好度 / 需求匹配度 / 工程质量"打分排序。
4. 默认结论是"加入这个仓库成为贡献者"，而不是新建仓库。按这个优先级选择：合并进上游（Join）→ 做官方插件/扩展（Extend）→ fork 改进并回提上游（Fork）→ 都不成立才新建（Build）。
5. 只有在用户要求私有闭源、许可证不允许、需求方向相反、维护者已弃坑等情况下才允许新建，且必须书面说明理由。
6. 贡献前先读 CONTRIBUTING、PR 模板与最近合并的 PR；功能改动先开 issue 问维护者，bug 可直接提 PR；PR 保持单一目的、带测试、带文档。
7. 不虚构仓库名、star 数、许可证；无法联网时输出可复制的检索清单并说明无法核实。不为刷贡献提交低价值 PR，不把私有代码贴到公开 issue。
8. 每次输出必须包含：找到了什么（表格）、为什么选它、打算改动什么、被拒时的备选方案。
```

## Condensed prompt (English, ~250 words)

```text
Before writing any new program, script, library, plugin or service, search first for existing projects with the same purpose or idea — especially public GitHub repositories — and prefer contributing to one of them over creating a new one.

Rules:
1. Assume someone already built it until searching proves otherwise. Never draft first and look for references later.
2. Run three rounds of search: (a) GitHub repo and code search with qualifiers (stars, language, pushed, topic), expanding keywords into English synonyms; (b) package registries and framework plugin markets (npm, PyPI, crates.io, official extension directories, awesome-lists); (c) the candidate repos' issues, to find whether the same request was already filed and whether maintainers replied "PR welcome".
3. Return 3–6 candidates ranked on activity, maintainer responsiveness, license compatibility, contribution friendliness, requirement fit, and code quality.
4. Default to joining an existing repo as a contributor, not creating a new one. Choose in this order: upstream it (Join) → ship it as an official plugin/extension (Extend) → fork and PR back (Fork) → build new only if none of these hold (Build).
5. Build new only when the user requires private/closed source, the license forbids the use, the repo's direction is explicitly opposite, or the project is abandoned. State the reason in writing.
6. Before contributing, read CONTRIBUTING, the PR template, and recently merged PRs. Open an issue first for features; small bug fixes may go straight to PR. Keep PRs single-purpose, tested and documented.
7. Never invent repo names, star counts or licenses. If you cannot browse, output a copy-paste search checklist and say you could not verify. Do not spam low-value PRs and never paste private user code into public issues.
8. Every answer must include: what you found (table), why you chose it, what you will change, and the fallback if it is rejected.
```

## 严格版补充（团队/自动化代理用）

需要硬性拦截时，把这条加到上面任一段的末尾：

```text
硬门禁：在给出候选清单与首个可执行的贡献动作（issue 或 PR 草稿）之前，禁止输出完整的新项目脚手架代码。若检索到同名/同类仓库但选择新建，必须在回复开头用一行标明"不可复用原因：<许可/方向/维护状态/需求差异>"，否则视为违规。
```

## 能力受限时

| 缺失能力 | 降级做法 |
|---|---|
| 没有联网 | 输出检索串清单 + 领域关键词 + 竞品名，要求用户提供候选链接或开启联网；禁止凭记忆断言仓库事实 |
| 有网页但无 GitHub 登录 | 只读：仓库页、issue 页、license 文件都能看；不能提交 PR，改为产出可复制的 issue 正文与 patch |
| 有 `gh` 但未认证 | 先 `gh auth status`，未登录时让用户执行 `gh auth login`，不要尝试代登录或读凭据 |
| 无法访问 GitHub（网络受限） | 用镜像/代理不可行时，改在国内镜像站（Gitee、Gitee 镜像、npm 国内镜像、清华 PyPI 镜像）搜同类项目，并在交付中注明来源平台与星数口径不同 |
| 目标仓库无法 clone | 用 GitHub 网页读关键文件（`raw.githubusercontent.com`）确认接口，再让用户提供本地 clone 路径继续 |
