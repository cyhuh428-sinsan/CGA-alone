"""승인된 개별 파일 이외의 CGA 원본 변경을 검출한다."""
from __future__ import annotations
import argparse
import ast
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys


def git(root: Path, *args: str, data: str | None = None) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], input=data, text=True, encoding="utf-8")


def decode_git_path(name: str) -> str:
    if name.startswith(chr(34)):
        return ast.literal_eval("b" + name).decode("utf-8")
    return name


def verify(root: Path, baseline: Path, allowlist: Path) -> dict:
    expected = {}
    for line in baseline.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        metadata, name = line.split("\t", 1)
        name = decode_git_path(name)
        mode, blob, stage = metadata.split()
        if stage != "0" or name in expected:
            raise ValueError("invalid baseline entry")
        expected[name] = (mode, blob)
    if not expected:
        raise ValueError("empty baseline")
    allowed = set()
    for entry in json.loads(allowlist.read_text(encoding="utf-8")):
        name = entry["path"]
        path = PurePosixPath(name)
        if not name or path.is_absolute() or ".." in path.parts or "*" in name or "?" in name or "\\" in name or ":" in name or str(path) != name:
            raise ValueError("allowlist requires an exact project-relative path")
        if not entry.get("stage") or not entry.get("reason") or name in allowed:
            raise ValueError("allowlist requires unique path, stage and reason")
        allowed.add(name)
    indexed = {}
    for line in git(root, "ls-files", "--stage").splitlines():
        metadata, name = line.split("\t", 1)
        name = decode_git_path(name)
        mode, blob, stage = metadata.split()
        if stage != "0":
            raise ValueError("unmerged index")
        indexed[name] = (mode, blob)
    missing = sorted(name for name in expected if not (root / name).is_file() or name not in indexed)
    checked = [name for name in expected if name not in missing and name not in allowed]
    # Git applies the repository's existing clean/EOL normalization to each path.
    paths = "".join(json.dumps(name, ensure_ascii=False) + "\n" for name in checked)
    hashes = git(root, "hash-object", "--stdin-paths", data=paths).splitlines() if checked else []
    if len(hashes) != len(checked):
        raise ValueError("incomplete hash output")
    changed = sorted(name for name, blob in zip(checked, hashes) if indexed[name] != expected[name] or blob != expected[name][1])
    new_tracked = set(indexed) - set(expected)
    untracked = [decode_git_path(name) for name in git(root, "ls-files", "--others", "--exclude-standard").splitlines()]
    new_untracked = {name for name in untracked if name.startswith(("apps/", "packages/", "scripts/"))}
    unexpected = sorted((new_tracked | new_untracked) - allowed)
    return {"baseline_files": len(expected), "missing": missing, "changed_outside_allowlist": changed, "unexpected_product_files": unexpected, "passed": not (missing or changed or unexpected)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--allowlist", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        report = verify(root, root / args.baseline, root / args.allowlist)
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({"passed": False, "error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["passed"] else 1

if __name__ == "__main__":
    sys.exit(main())
