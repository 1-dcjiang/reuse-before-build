#!/usr/bin/env python3
"""校验一份本地化副本是否保住了不可变项。

四道闸：
  1. 不变块（<!-- RBB:INVARIANTS --> 之间）——逐字版比哈希，翻译版比规则条数与逐条锚点；
  2. 规则完整性——块内编号必须正好 1..N（N≥rules_min），删条、改号都会露馅；
  3. 语义锚点（localization.contract.json 的 must_have）——中英任一写法均算命中；
  4. 声明行——`localized: host=... | kept=... | changed=... | unsupported=...`。

`--canonical` 不是开关，是自证：只对契约里列出的包内参考件生效，对任何其它文件一律拒绝（rc 2），
免得"本地化者"给自己开个后门跳过声明检查。

用法：
    python scripts/verify_localized.py <file>              # 校验本地化副本（验收就用这个，不加 flag）
    python scripts/verify_localized.py <file> --canonical   # 仅用于包内参考件，其它路径会被拒绝
    python scripts/verify_localized.py --print-hash SKILL.md # 打印不变块哈希，用于更新契约

退出码：0 = PASS，1 = FAIL（缺什么会列出来），2 = 用法错误（如对包外文件用 --canonical）。
"""

from __future__ import annotations

__version__ = "1.2.12"

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
# 随包英文正典的基线钉在代码里，不能只相信同目录、同样可被改写的契约。
CANONICAL_SHA256 = "690f0165e1f67fbb771a68c5456dcd35243e1132cfa0b0b9f287caf446143526"
CANONICAL_RULES_MIN = 5
CANONICAL_RULE_ANCHOR_IDS = frozenset({"rule_1", "rule_2", "rule_3", "rule_4", "rule_5"})
CANONICAL_MUST_HAVE_IDS = frozenset({
    "gate", "verdict_order", "deliverable", "contributing_rule",
    "public_write_gate", "quick_lane", "untrusted_section",
    "untrusted_data_not_instructions", "untrusted_container",
})
CANONICAL_DECLARATION_KEYS = ("host", "kept", "changed", "unsupported")
CANONICAL_DECLARATION_WITHIN_LAST = 8


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _marker_line(line: str, marker: str) -> bool:
    """整行锚定：说明文字或反引号里的提及不算块边界。"""
    return re.fullmatch(rf"<!--\s*{re.escape(marker)}\s*-->", line.strip()) is not None


def extract_block(text: str, begin: str, end: str) -> str | None:
    """取不变块。跳过代码围栏里的"标记示例"，并在多个候选里选规则最全的那个。"""
    lines = text.splitlines()
    fenced: list[bool] = []
    in_fence = False
    for line in lines:
        if line.strip().startswith("```"):
            in_fence = not in_fence
            fenced.append(True)
            continue
        fenced.append(in_fence)

    begins = [i for i, line in enumerate(lines) if not fenced[i] and _marker_line(line, begin)]
    ends = [i for i, line in enumerate(lines) if not fenced[i] and _marker_line(line, end)]
    candidates: list[str] = []
    for b in begins:
        e = next((x for x in ends if x > b), None)
        if e is None:
            continue
        candidates.append("\n".join(lines[b + 1:e]).strip())
    if not candidates:
        return None
    # 演示用的空块/占位块排在前面时，别让它顶替真块
    return max(candidates, key=lambda c: (len(RULE_RE.findall(c)), -candidates.index(c)))


def block_hash(inner: str) -> str:
    norm = "\n".join(line.rstrip() for line in inner.strip().splitlines())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def find_lang_marker(inner: str, prefix: str) -> str | None:
    m = re.search(re.escape(prefix) + r"\s*([A-Za-z0-9_-]+)", inner)
    return m.group(1) if m else None


RULE_RE = re.compile(r"^(\d+)\.\s+\S", re.MULTILINE)  # 只认第 0 列的编号，缩进子项不算规则


def check_rules(inner: str, rules_min: int) -> tuple[list[str], list[str], list[int]]:
    """返回 (缺失项, 提示项, 编号列表)。"""
    numbers = [int(n) for n in RULE_RE.findall(inner)]
    missing, notes = [], []
    if len(numbers) < rules_min:
        missing.append(f"rules_count({len(numbers)}<{rules_min})")
    if numbers and numbers != list(range(1, len(numbers) + 1)):
        missing.append(f"rules_numbering({','.join(map(str, numbers))})")
    if rules_min and len(numbers) > rules_min:
        notes.append(f"rules {len(numbers)} > rules_min {rules_min} (可能拆条了)")
    return missing, notes, numbers


def parse_frontmatter(text: str) -> dict | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            data: dict[str, str] = {}
            for line in lines[1:i]:
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


def _anchor_match(text_lower: str, needle: object) -> bool:
    """锚点仍是子串语义；类型不对或空串一律算不命中，不让坏契约抛栈。"""
    return isinstance(needle, str) and bool(needle.strip()) and needle.lower() in text_lower


def check_anchors(scope: str, items: list[dict], where: str) -> list[str]:
    if not isinstance(items, list):
        return [f"{where}(not_list)"]
    missing = []
    low = scope.lower()
    for item in items:
        if not isinstance(item, dict):
            missing.append(f"{where}(not_object)")
            continue
        ident = item.get("id", "?")
        any_of = item.get("any") or []
        all_of = item.get("all") or []
        if not isinstance(any_of, list) or not isinstance(all_of, list):
            missing.append(f"{where}:{ident}(anchor_spec_not_list)")
            continue
        if not any_of and not all_of:
            missing.append(f"{where}:{ident}(no any/all spec)")
            continue
        if any_of and not any(_anchor_match(low, s) for s in any_of):
            missing.append(f"{where}:{ident}")
        absent = [s for s in all_of if not _anchor_match(low, s)]
        if absent:
            missing.append(f"{where}:{ident}(needs all of: {', '.join(str(s) for s in absent)})")
    return missing


def id_set(value: object) -> frozenset[str]:
    """取契约锚点条目的 id 集合；形状不对按空集合处理。"""
    if not isinstance(value, list):
        return frozenset()
    return frozenset(
        str(item.get("id", ""))
        for item in value
        if isinstance(item, dict) and item.get("id")
    )


def contract_anchor_errors(value: object, field: str) -> list[str]:
    """契约锚点必须是对象数组，any/all 必须是非空字符串列表；坏结构在加载时就报错。"""
    if not isinstance(value, list):
        return [f"{field}(not_list)"]
    errors: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"{field}[{index}](not_object)")
            continue
        ident = str(item.get("id") or f"#{index}")
        for key in ("any", "all"):
            if key not in item:
                continue
            needles = item[key]
            if not isinstance(needles, list):
                errors.append(f"{field}:{ident}({key}_not_list)")
                continue
            for needle in needles:
                if not isinstance(needle, str) or not needle.strip():
                    errors.append(f"{field}:{ident}({key}_empty_or_non_string)")
    return errors


def contract_root_errors(contract: object) -> list[str]:
    """契约顶层与 block / declaration 的形状校验；坏结构在读取字段前就返回。"""
    if not isinstance(contract, dict):
        return ["contract(not_object)"]
    errors: list[str] = []
    if "block" in contract and not isinstance(contract["block"], dict):
        errors.append("block(not_object)")
    else:
        block = contract.get("block") or {}
        for key in ("begin", "end", "lang_marker_prefix", "canonical_file", "canonical_sha256"):
            if key in block and not isinstance(block[key], str):
                errors.append(f"block.{key}(not_string)")
        if "canonical_files" in block:
            files = block["canonical_files"]
            if not isinstance(files, list) or any(not isinstance(item, str) for item in files):
                errors.append("block.canonical_files(not_string_list)")
    if "declaration" in contract and not isinstance(contract["declaration"], dict):
        errors.append("declaration(not_object)")
    else:
        declaration = contract.get("declaration") or {}
        if "keys" in declaration:
            keys = declaration["keys"]
            if not isinstance(keys, list) or any(not isinstance(item, str) for item in keys):
                errors.append("declaration.keys(not_string_list)")
        if "prefix" in declaration and not isinstance(declaration["prefix"], str):
            errors.append("declaration.prefix(not_string)")
        if "within_last" in declaration:
            try:
                int(declaration["within_last"])
            except (TypeError, ValueError, OverflowError):
                errors.append("declaration.within_last(not_int)")
    return errors


def check_contract_baseline(contract: dict) -> list[str]:
    """契约只允许在基线之上收紧，不许把规则条数、锚点或声明字段悄悄改松。"""
    missing: list[str] = []
    missing += contract_anchor_errors(contract.get("rule_anchors"), "rule_anchors")
    missing += contract_anchor_errors(contract.get("must_have"), "must_have")
    try:
        rules_min = int(contract.get("rules_min", 0))
    except (TypeError, ValueError, OverflowError):
        rules_min = 0
    if rules_min != CANONICAL_RULES_MIN:
        missing.append(f"rules_min:{rules_min}!={CANONICAL_RULES_MIN}")
    if id_set(contract.get("rule_anchors")) != CANONICAL_RULE_ANCHOR_IDS:
        missing.append("rule_anchor_ids")
    if id_set(contract.get("must_have")) != CANONICAL_MUST_HAVE_IDS:
        missing.append("must_have_ids")
    declaration = contract.get("declaration") or {}
    if tuple(declaration.get("keys") or ()) != CANONICAL_DECLARATION_KEYS:
        missing.append("declaration_keys")
    try:
        within_last = int(declaration.get("within_last", 0))
    except (TypeError, ValueError, OverflowError):
        within_last = 0
    if within_last != CANONICAL_DECLARATION_WITHIN_LAST:
        missing.append(f"declaration_within_last:{within_last}!={CANONICAL_DECLARATION_WITHIN_LAST}")
    return missing


def check_declaration(text: str, decl: dict) -> list[str]:
    """声明行必须是文件末尾那条；代码围栏里的示例行不算（SKILL.md 自己就有一段示例）。"""
    prefix = decl.get("prefix", "localized:")
    keys = decl.get("keys", [])
    within = int(decl.get("within_last", 8))
    candidates: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line.strip():
            continue
        candidates.append(line.strip())
    # 文件末尾追加版权/生成时间不算错，只要声明行还在最后 N 个非空、非代码行里
    for line in reversed(candidates[-within:]):
        if line.lower().startswith(prefix.lower()):
            return [f"declaration:{k}" for k in keys if k not in line]
    return ["declaration"]


def main() -> int:
    ap = argparse.ArgumentParser(description="校验本地化副本是否保住了不可变项")
    ap.add_argument("file", help="待校验的本地化副本")
    ap.add_argument("--contract", default=DEFAULT_CONTRACT,
                    help="契约文件路径；只允许包内 localization.contract.json")
    ap.add_argument("--canonical", action="store_true",
                    help="仅用于包内参考件；对其它路径会被拒绝（rc 2）")
    ap.add_argument("--print-hash", action="store_true",
                    help="只打印不变块哈希（用于更新契约），不做校验")
    ap.add_argument("--quiet", action="store_true", help="只输出结果行")
    args = ap.parse_args()

    # --contract 不能指向任意文件：换成一份空契约（rules_min=0、无锚点）就能跳过全部检查。
    if os.path.realpath(args.contract) != os.path.realpath(DEFAULT_CONTRACT):
        print("REFUSED  --contract 只允许指向随包的 localization.contract.json，"
              "不允许替换成更宽松的契约。", file=sys.stderr)
        return 2

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

    root_errors = contract_root_errors(contract)
    if root_errors:
        print("FAIL  contract 顶层结构不合法：")
        print("MISSING: " + ", ".join(root_errors))
        return 1

    want_hash = str((contract.get("block") or {}).get("canonical_sha256") or "")
    if not args.print_hash and not re.fullmatch(r"[0-9a-fA-F]{64}", want_hash):
        print("FAIL  contract 缺少合法的 block.canonical_sha256（64 位十六进制）")
        return 1
    try:
        rules_floor = int(contract.get("rules_min", 0))
    except (TypeError, ValueError, OverflowError):
        rules_floor = 0
    if not args.print_hash and (rules_floor < 1 or not contract.get("must_have")):
        print("FAIL  contract 的 rules_min 必须 ≥ 1，且 must_have 不能为空")
        return 1
    if not args.print_hash and want_hash.lower() != CANONICAL_SHA256:
        print("FAIL  contract 的正典哈希与代码内置基线不一致；拒绝使用被改写的基线。")
        return 1
    if not args.print_hash:
        baseline = check_contract_baseline(contract)
        if baseline:
            print("FAIL  contract 基线被放宽")
            print("MISSING: " + ", ".join(baseline))
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

    # --canonical 只能指向契约里登记的包内参考件，避免本地化者给自己开后门
    base = os.path.dirname(os.path.abspath(args.contract))
    allowed = {os.path.realpath(os.path.join(base, f))
               for f in block_cfg.get("canonical_files", [])}
    is_ref = os.path.realpath(args.file) in allowed
    if args.canonical and not is_ref:
        print(f"REFUSED  {os.path.basename(args.file)} 不在包内参考件白名单里，"
              "不能用 --canonical；本地化副本必须带 localized: 声明行完整校验。",
              file=sys.stderr)
        return 2

    missing: list[str] = []
    notes: list[str] = []
    mode = "missing"
    rule_nums = 0

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

        r_missing, r_notes, rule_nums = check_rules(inner, int(contract.get("rules_min", 0)))
        missing += r_missing
        notes += r_notes
        missing += check_anchors(inner, contract.get("rule_anchors", []), "rule")

    fm_missing, fm_notes = check_frontmatter(parse_frontmatter(text))
    missing += fm_missing
    notes += fm_notes

    missing += check_anchors(text, contract.get("must_have", []), "anchor")

    if not (args.canonical or is_ref):
        missing += check_declaration(text, contract.get("declaration", {}))

    name = os.path.basename(args.file)
    if missing:
        print(f"FAIL  {name}  mode={mode}  rules={rule_nums}")
        print("MISSING: " + ", ".join(missing))
        if notes and not args.quiet:
            for n in notes:
                print(f"note: {n}")
        print("修：把缺的项补回去（不许静默删）；宿主真的做不到，写进 unsupported 并说明原因。")
        return 1

    total = len(contract.get("must_have", []))
    print(f"PASS  {name}  invariant-block={mode}  rules={rule_nums}/{contract.get('rules_min', '?')}"
          f"  anchors={total}/{total}" + ("  (reference copy)" if is_ref else ""))
    if notes and not args.quiet:
        for n in notes:
            print(f"note: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
