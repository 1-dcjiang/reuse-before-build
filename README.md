# reuse-before-build · 先复用，再新建

> 一个面向 AI 编程助手的 Skill：**在写新程序之前，先去找已经存在的公开实现，并优先加入那个仓库、成为公共贡献者，而不是从零再造一个。**

A skill for AI coding assistants: **search for existing open-source implementations first, and contribute upstream instead of building a new one from scratch.**

**编码代理**：Claude Code · Codex CLI · Cursor · GitHub Copilot · Gemini CLI · Windsurf · Cline · Roo Code · Kilo Code · Continue · Aider · OpenHands · Amp · Zed · JetBrains Junie · Amazon Q / Kiro · Trae · Qoder · 通义灵码 · CodeGeeX · 文心 Comate · 腾讯 CodeBuddy（走 `AGENTS.md` / `CLAUDE.md` / `.cursor/rules` 等仓库规则文件）

**对话式 AI**：ChatGPT · Claude.ai · Gemini · Grok · Microsoft Copilot · Perplexity · Mistral Le Chat · DeepSeek · 豆包 · Kimi · 通义千问 · 文心一言 · 腾讯元宝 · 智谱清言 · 讯飞星火 · MiniMax · 阶跃（走自定义指令 / 系统提示）

**自建 Agent**：LangChain · LlamaIndex · CrewAI · AutoGen · Dify · Coze · n8n 及任何能吃 system prompt 的 Agent。

---

## 它解决什么问题

AI 现在最常见的失败模式不是"写不出代码"，而是**在别人已经做过的地方，从零写了一个更差的版本**：

- 一个能用 `ffmpeg` + 现成库解决的剪辑需求，被写成 1400 行自制框架；
- 一个 Obsidian 插件，市场上已经有 3 个同类，作者还活着，最后变成第 4 个没人维护的；
- 上游 issue 里已经有人提过同一需求、维护者回了 "PRs welcome"，却没人去接。

这个 Skill 把"先检索、再评估、再贡献、最后才新建"固化成可执行流程，并**用门禁挡住"直接开写"这个默认行为**。

## 核心规则（五条）

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
Join 提 PR 进上游 → Extend 做官方插件 → Fork 改完回提 → Build 新建（须写明理由）
```

## 目录

```
SKILL.md                               主流程、两条档位（快速档 / 完整档）、硬约束
references/discovery-playbook.md       三轮检索：GitHub 限定符、gh 命令、插件市场、issue 考古
references/repo-triage.md              六维打分细则 + 许可证兼容速查 + 红旗清单
references/contribution-protocol.md    issue → PR 全流程、PR 模板、降级路径、反模式
references/worked-examples.md          Join / Extend / Fork / Build 四种结论的交付形态
references/host-adapters.md            各平台落位 + 中英文可粘贴精简提示
scripts/repo_scan.py                   一键粗筛：gh search 批量跑、去重、标出无许可与停滞仓库
```

## 安装

四种落位，按宿主自选。完整的平台清单、规则文件名对照、字数预算见 [references/host-adapters.md](references/host-adapters.md)。

**① Skill 目录**（Claude / 支持 Agent Skills 规范的宿主）
把整个目录放进 Skills 目录即可，`SKILL.md` 的 frontmatter 会被自动读取，`references/` 按需加载。

**② 仓库规则文件**（编码代理：Codex CLI / Cursor / Copilot / Gemini CLI / Windsurf / Cline / Aider / Trae / Qoder / Junie …）
把 `references/host-adapters.md` 的「严格版」写进仓库根 `AGENTS.md`（跨工具事实标准）；Claude Code 用 `CLAUDE.md`，Copilot 用 `.github/copilot-instructions.md`，Cursor 用 `.cursor/rules/*.mdc`，Windsurf 用 `.windsurf/rules/`。

**③ 自定义指令**（ChatGPT / Claude.ai / Gemini / Grok / DeepSeek / 豆包 / Kimi / 通义 / 文心 / 元宝 / 智谱 / 星火 / MiniMax …）
复制「精简版（中文）」或「Condensed prompt (English)」进设置里的自定义指令；有知识文件/项目说明的（ChatGPT Projects、Claude Projects、Gemini Gems）把完整版一起传上去。

**④ 自建 Agent**（LangChain / LlamaIndex / CrewAI / AutoGen / Dify / Coze / n8n）
放 system prompt 第一段，并在工具说明里给出 `web_search` / `fetch` / `gh` 能力；无工具时走 skill 里的「能力受限」降级。

## 快速开始

有 GitHub CLI 时，先出一张候选表再动脑：

```bash
gh auth status
python scripts/repo_scan.py "video highlight clip" "auto cut shorts" --stars 100
```

输出形如：

```
| 仓库 | ★ | 最近推送 | 语言 | 许可 | open issues | 命中关键词 | URL |
| haierkeys/obsidian-fast-note-sync | 3152 | 2026-08-14 | JavaScript | apache-2.0 | 111 | ... |
```

然后按 `references/repo-triage.md` 打开每个仓库读 `CONTRIBUTING` 与最近合并的 PR，做六维打分。

没有 `gh` / 没有联网时：`references/discovery-playbook.md` 里有可直接粘贴到 GitHub 搜索框的检索串，以及"无能力时如何降级"的写法（禁止凭记忆编造 star 数与许可证）。

## 三条底线

- 代码仓库**没有 LICENSE 文件 = 不可复制、不可提交**（默认保留所有权利）。
- 没读 `CONTRIBUTING` 就提 PR，在主流仓库几乎必被拒。
- 刷低质量 PR（错别字、格式化、无测试重复实现）不会让你"成为作者"，只会让账号被拉黑。

## 许可

MIT，见 [LICENSE](LICENSE)。
