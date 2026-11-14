#!/usr/bin/env python3
"""为下游 vendor 打一份可校验的发布包。

产物（放在 --out-dir）：
  reuse-before-build-v<version>.zip   git archive 出的 tag 快照，带固定前缀
  integration-seam.md                 接入口与薄适配层指南，供 vendor 直接读
  SHA256SUMS                          上面两个文件的 sha256，`sha256sum -c` 可直接验

用法：
    python scripts/make_release_bundle.py --version 1.2.8 --out-dir dist
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

__version__ = "1.2.8"

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_version() -> str:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r"^version:\s*([0-9][0-9A-Za-z._-]*)\s*$", text, re.MULTILINE)
    if not match:
        raise SystemExit("SKILL.md frontmatter 缺少 version")
    return match.group(1)


def build(version: str, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"reuse-before-build-{version}/"
    archive = out_dir / f"reuse-before-build-v{version}.zip"
    subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "archive",
            "--format=zip",
            f"--prefix={prefix}",
            "-o",
            str(archive),
            "HEAD",
        ],
        check=True,
    )

    doc = out_dir / "integration-seam.md"
    shutil.copyfile(ROOT / "references" / "integration-seam.md", doc)

    sums = out_dir / "SHA256SUMS"
    assets = [archive, doc]
    sums.write_text(
        "".join(f"{sha256_file(path)}  {path.name}\n" for path in assets),
        encoding="utf-8",
        newline="\n",
    )
    return [*assets, sums]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成可校验的 vendor 发布包")
    parser.add_argument("--version", default="", help="默认读 SKILL.md 的 version")
    parser.add_argument("--out-dir", default="dist", help="产物目录，默认 dist")
    args = parser.parse_args(argv)

    version = args.version.strip() or read_version()
    if not re.fullmatch(r"[0-9][0-9A-Za-z._-]*", version):
        print(f"版本号不合法：{version!r}", file=sys.stderr)
        return 2

    try:
        assets = build(version, Path(args.out_dir))
    except subprocess.CalledProcessError as exc:
        print(f"git archive 失败：{exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"写发布包失败：{exc}", file=sys.stderr)
        return 1

    for path in assets:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
