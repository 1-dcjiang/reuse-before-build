#!/usr/bin/env python3
"""为下游 vendor 打一份可校验的发布包。

产物（放在 --out-dir）：
  reuse-before-build-v<version>.zip   git archive 出的 **tag 快照**，带固定前缀
  integration-seam.md                 接入口与薄适配层指南，供 vendor 直接读
  SHA256SUMS                          上面两个文件的 sha256，`sha256sum -c` 可直接验

安全约束：
  - `--version` 必须与 SKILL.md 的 `version` 一致；
  - `v<version>` tag 必须存在，且必须指向当前 HEAD；
  - 工作区必须干净（`git status --porcelain --untracked-files=no` 为空；未跟踪的本地缓存不影响 tag 快照）；
  - 三个产物已存在时拒绝覆盖，和 repo_scan 的输出策略一致。

用法：
    python scripts/make_release_bundle.py --version 1.2.11 --out-dir dist
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

__version__ = "1.2.11"

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
        raise ValueError("SKILL.md frontmatter 缺少 version")
    return match.group(1)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _git_required(*args: str) -> str:
    proc = _git(*args)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise ValueError(f"git {' '.join(args)} 失败：{detail or '返回非零'}")
    return proc.stdout.strip()


def ensure_release_policy(version: str) -> str:
    """确认 version 与 SKILL.md、tag、HEAD、工作区四者一致，返回 tag 名。"""
    skill_version = read_version()
    if version != skill_version:
        raise ValueError(
            f"--version {version!r} 与 SKILL.md 的 {skill_version!r} 不一致；"
            "先改版本再打包，避免包名与规则版本分叉"
        )
    if _git("status", "--porcelain", "--untracked-files=no").stdout.strip():
        raise ValueError("工作区不干净：commit 或 stash 后再打发布包")
    tag = f"v{version}"
    tag_commit = _git_required("rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}")
    head_commit = _git_required("rev-parse", "HEAD")
    if tag_commit != head_commit:
        raise ValueError(f"tag {tag} 不指向当前 HEAD（{tag_commit} != {head_commit}）")
    return tag


def build(version: str, out_dir: Path) -> list[Path]:
    out_dir = Path(out_dir)
    tag = ensure_release_policy(version)
    prefix = f"reuse-before-build-{version}/"
    archive = out_dir / f"reuse-before-build-v{version}.zip"
    doc = out_dir / "integration-seam.md"
    sums = out_dir / "SHA256SUMS"
    for path in (archive, doc, sums):
        if path.exists():
            raise ValueError(f"产物已存在，拒绝覆盖：{path}")

    out_dir.mkdir(parents=True, exist_ok=True)
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
            tag,
        ],
        check=True,
    )
    if not archive.is_file():
        raise ValueError(f"git archive 没有写出 {archive}")

    shutil.copyfile(ROOT / "references" / "integration-seam.md", doc)

    sums.write_text(
        "".join(f"{sha256_file(path)}  {path.name}\n" for path in (archive, doc)),
        encoding="utf-8",
        newline="\n",
    )
    return [archive, doc, sums]


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
    except ValueError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2
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
