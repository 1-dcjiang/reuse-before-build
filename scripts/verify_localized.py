#!/usr/bin/env python3
"""校验一份本地化副本是否保住了不可变项。

三道闸：
  1. 不变块（<!-- RBB:INVARIANTS --> 之间）——逐字版比哈希，翻译版比语义锚点；
  2. 语义锚点（localization.contract.json 的 must_have）——中英任一写法均算命中；
  3. 声明行——最后一行 `localized: host=... | kept=... | changed=... | unsupported=...`。

用法：
    python scripts/verify_localized.py <file>              # 校验本地化副本
    python scripts/verify_localized.py <file> --canonical   # 校验随包参考副本（不要求声明行）
    python scripts/verify_localized.py --print-hash SKILL.md # 打印不变块哈希，用于更新契约

退出码：0 = PASS，1 = FAIL（缺什么会列出来）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONTRACT = os.path.join(os.path.dirname(HERE), "localization.contract.json")


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def extract_block(text: str, begin: str, end: str) -> str | None:
    """取两个标记之间的内容（不含标记行本身），两端去空白。"""
    b = text.find(begin)
    if b == -1:
        return None
    e = text.find(end, b + len(begin))
    if e == -1:
        return None
    return text[b + len(begin):e].strip()


def block_hash(inner: str) -> str:
    norm = "\n".join(line.rstrip() for line in inner.strip().splitlines())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def find_lang_marker(inner: str, prefix: str) -> str | None:
    m = re.search(re.escape(prefix) + r"\s*([A-Za-z0-9_-]+)", inner)
    return m.group(1) if m else None


def parse_frontmatter(text: str) -> dict | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            body = lines[1:i]
            data: dict[str, str] = {}
            for line in body:
                if ":" in line and not line.startswith((" ", "\t")):
                    k, v = line.split(":", 1)
                    data[k.strip()] = v.strip()
            return data
    return None


NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def check_frontmatter(fm: dict | None) -> tuple[list[str], list[str]]:
    """返回 (缺失项, 提示项)。没有 frontmatter 的聊天指令副本不算失败。"""
    if fm is None:
        return [], ["no frontmatter (chat-instruction copy?)"]
    missing, notes = [], []
    name = fm.get("name", "")
    desc = fm.get("description", "")
    if not name:
        missing.append("frontmatter_name")
    elif len(name) > 64:
        missing.append(f"frontmatter_name_too_long({len(name)})")
    elif not NAME_RE.match(name):
        missing.append("frontmatter_name_format")
    if not desc:
        missing.append("frontmatter_description")
    elif len(desc) > 1024:
        missing.append(f"frontmatter_description_too_long({len(desc)})")
    if "license" not in fm:
        notes.append("no license field")
    return missing, notes


def check_must_have(text: str, items: list[dict]) -> tuple[list[str], list[str]]:
    missing, notes = [], []
    for item in items:
        ident = item.get("id", "?")
        any_of = item.get("any", [])
        all_of = item.get("all", [])
        low = text.lower()
        if any_of and not any(s.lower() in low for s in any_of):
            missing.append(ident)
        if all_of and not all(s.lower() in low for s in all_of):
            missing.append(f"{ident}(needs all of: {', '.join(all_of)})")
        if not any_of and not all_of:
            notes.append(f"{ident}: empty rule in contract")
    return missing, notes


def check_declaration(text: str, decl: dict) -> list[str]:
    prefix = decl.get("prefix", "localized:")
    keys = decl.get("keys", [])
    tail = [line.strip() for line in text.splitlines() if line.strip()]
    if not tail:
        return ["declaration"]
    last = tail[-1]
    if not last.lower().startswith(prefix.lower()):
        return ["declaration"]
    missing = [k for k in keys if f"{k}" not in last]
    return [f"declaration:{k}" for k in missing]


def main() -> int:
    ap = argparse.ArgumentParser(description="校验本地化副本是否保住了不可变项")
    ap.add_argument("file", help="待校验的本地化副本")
    ap.add_argument("--contract", default=DEFAULT_CONTRACT, help="契约文件路径（默认随包）")
    ap.add_argument("--canonical", action="store_true",
                    help="校验随包参考副本：不要求 localized 声明行")
    ap.add_argument("--print-hash", action="store_true",
                    help="只打印不变块哈希（用于更新契约），不做校验")
    ap.add_argument("--quiet", action="store_true", help="只输出结果行")
    args = ap.parse_args()

    if not os.path.exists(args.file):
        print(f"FAIL  file not found: {args.file}")
        return 1
    text = read_text(args.file)

    try:
        with open(args.contract, "r", encoding="utf-8") as fh:
            contract = json.load(fh)
    except FileNotFoundError:
        if not args.print_hash:
            print(f"FAIL  contract not found: {args.contract}")
            return 1
        contract = {}  # --print-hash 用默认标记即可，首次生成契约时还没有它
    except json.JSONDecodeError as exc:
        print(f"FAIL  contract is not valid JSON: {exc}")
        return 1

    block_cfg = contract.get("block", {})
    begin = block_cfg.get("begin", "RBB:INVARIANTS:BEGIN")
    end = block_cfg.get("end", "RBB:INVARIANTS:END")
    prefix = block_cfg.get("lang_marker_prefix", "RBB:INVARIANTS:LANG:")
    want_hash = block_cfg.get("canonical_sha256", "")

    inner = extract_block(text, begin, end)
    if args.print_hash:
        if inner is None:
            print("FAIL  no invariants block found", file=sys.stderr)
            return 1
        print(block_hash(inner))
        return 0

    missing: list[str] = []
    notes: list[str] = []
    mode = "missing"

    if inner is None:
        missing.append("invariants_block")
    else:
        got = block_hash(inner)
        lang = find_lang_marker(inner, prefix)
        if want_hash and got == want_hash:
            mode = "verbatim"
        elif lang:
            mode = f"translated({lang})"
        else:
            mode = "hash_mismatch"
            missing.append("invariants_hash")

    fm_missing, fm_notes = check_frontmatter(parse_frontmatter(text))
    missing += fm_missing
    notes += fm_notes

    mh_missing, mh_notes = check_must_have(text, contract.get("must_have", []))
    missing += mh_missing
    notes += mh_notes

    if not args.canonical:
        missing += check_declaration(text, contract.get("declaration", {}))

    name = os.path.basename(args.file)
    if missing:
        print(f"FAIL  {name}  mode={mode}")
        print("MISSING: " + ", ".join(missing))
        if notes and not args.quiet:
            for n in notes:
                print(f"note: {n}")
        print("修：把缺的项补回去（不许静默删）；宿主真的做不到，写进 unsupported 并说明原因。")
        return 1

    total = len(contract.get("must_have", []))
    print(f"PASS  {name}  invariant-block={mode}  anchors={total}/{total}"
          + ("  (canonical)" if args.canonical else ""))
    if notes and not args.quiet:
        for n in notes:
            print(f"note: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
