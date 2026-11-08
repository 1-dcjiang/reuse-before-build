#!/usr/bin/env python3
"""reuse-before-build · 候选仓库粗筛

用 gh CLI 对多个关键词跑 GitHub 仓库检索，去重后输出一张候选表，
供人工/模型进入六维评估（references/repo-triage.md）。

依赖：GitHub CLI（gh）已安装且 `gh auth status` 通过。不依赖任何第三方 Python 包。

用法：
    python repo_scan.py "video highlight clip" "auto cut shorts" --stars 100
    python repo_scan.py "obsidian sync" --updated-since 2025-01-01 --limit 8 --md-out candidates.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys

try:  # Windows 控制台默认 cp936，中文会炸；能改就改
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


PERMISSIVE = {"mit", "apache-2.0", "bsd-3-clause", "bsd-2-clause", "isc", "mpl-2.0", "0bsd", "unlicense"}


def gh_json(args: list[str], timeout: int = 60) -> list[dict]:
    proc = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        shell=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"gh 失败（exit {proc.returncode}）：{proc.stderr.strip()[:300]}")
    out = proc.stdout.strip()
    return json.loads(out) if out else []


def scan(keyword: str, stars: int, updated_since: str, limit: int) -> list[dict]:
    query = f"{keyword} stars:>{stars} pushed:>{updated_since}"
    fields = "url,nameWithOwner,stargazersCount,pushedAt,license,isArchived,language,openIssuesCount,description"
    # nameWithOwner 不在 JSON FIELDS 列表里，用 owner/name 组合
    fields = "url,name,owner,stargazersCount,pushedAt,license,isArchived,language,openIssuesCount,description"
    try:
        rows = gh_json(
            ["search", "repos", query, "--archived=false", "--limit", str(limit), "--json", fields]
        )
    except RuntimeError as exc:
        print(f"[warn] 关键词 {keyword!r} 检索失败：{exc}", file=sys.stderr)
        return []
    for row in rows:
        owner = (row.get("owner") or {}).get("login", "")
        row["full_name"] = f"{owner}/{row.get('name', '')}" if owner else row.get("name", "")
        row["matched_keyword"] = keyword
    return rows


def activity_points(pushed_at: str) -> int:
    if not pushed_at:
        return 0
    try:
        pushed = dt.datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
    except ValueError:
        return 0
    days = (dt.datetime.now(dt.timezone.utc) - pushed).days
    if days <= 90:
        return 2
    if days <= 365:
        return 1
    return 0


def license_flags(license_obj: dict | None) -> tuple[int, str]:
    key = ((license_obj or {}).get("key") or "").lower()
    if not key:
        return 0, "无 LICENSE ⚠"
    if key in PERMISSIVE:
        return 2, (license_obj or {}).get("spdxId") or key
    return 1, (license_obj or {}).get("spdxId") or key


def main() -> int:
    parser = argparse.ArgumentParser(description="GitHub 候选仓库粗筛（reuse-before-build）")
    parser.add_argument("keywords", nargs="+", help="一个或多个检索串（英文效果最好）")
    parser.add_argument("--stars", type=int, default=100, help="星数下限，默认 100")
    parser.add_argument(
        "--updated-since",
        default=(dt.date.today().replace(year=dt.date.today().year - 1)).isoformat(),
        help="最近推送日期下限，默认一年前（YYYY-MM-DD）",
    )
    parser.add_argument("--limit", type=int, default=8, help="每个关键词返回条数，默认 8")
    parser.add_argument("--md-out", default="", help="把 Markdown 表格写入该文件")
    parser.add_argument("--json-out", default="", help="把原始结果写入该 JSON 文件")
    args = parser.parse_args()

    if not shutil.which("gh"):
        print("未找到 gh CLI。安装 GitHub CLI 并 `gh auth login` 后重试；"
              "没有 gh 时改用 references/discovery-playbook.md 的网页检索串。", file=sys.stderr)
        return 2

    merged: dict[str, dict] = {}
    for kw in args.keywords:
        for row in scan(kw, args.stars, args.updated_since, args.limit):
            key = (row.get("url") or row.get("full_name") or "").rstrip("/").lower()
            if key in merged:
                merged[key].setdefault("matched_keyword", [])
                if isinstance(merged[key]["matched_keyword"], list):
                    merged[key]["matched_keyword"].append(kw)
                continue
            row["matched_keyword"] = [kw]
            merged[key] = row

    rows = list(merged.values())
    for row in rows:
        row["_activity"] = activity_points(row.get("pushedAt", ""))
        row["_lic_score"], row["_lic_label"] = license_flags(row.get("license"))

    rows.sort(key=lambda r: (-r["_lic_score"], -r["_activity"], -(r.get("stargazersCount") or 0)))

    header = "| 仓库 | ★ | 最近推送 | 语言 | 许可 | open issues | 命中关键词 | URL |\n|---|---|---|---|---|---|---|---|"
    lines = [header]
    for row in rows:
        pushed = (row.get("pushedAt") or "")[:10] or "-"
        lic = row["_lic_label"]
        if row["_activity"] == 0:
            pushed = f"{pushed} ⚠停滞"
        lines.append(
            "| {name} | {stars} | {pushed} | {lang} | {lic} | {issues} | {kw} | {url} |".format(
                name=row.get("full_name") or "-",
                stars=row.get("stargazersCount") or 0,
                pushed=pushed,
                lang=row.get("language") or "-",
                lic=lic,
                issues=row.get("openIssuesCount") if row.get("openIssuesCount") is not None else "-",
                kw=", ".join(row.get("matched_keyword") or []),
                url=row.get("url") or "-",
            )
        )

    table = "\n".join(lines)
    print(table)
    print(f"\n共 {len(rows)} 个去重候选（{len(args.keywords)} 个关键词）。"
          "下一步：按 references/repo-triage.md 打开每个仓库读 CONTRIBUTING 与最近合并的 PR，做六维打分。",
          file=sys.stderr)

    if args.md_out:
        with open(args.md_out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(table + "\n")
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
