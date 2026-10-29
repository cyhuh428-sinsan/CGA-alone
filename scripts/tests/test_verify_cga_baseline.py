import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "verify-cga-baseline.py"

class BaselineGuardTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cga-alone-guard-", dir=str(Path(__file__).resolve().parents[3]))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "--quiet")
        self.source = self.root / "source.py"
        self.source.write_text("value = 1\n", encoding="utf-8")
        self.git("add", "source.py")
        self.git("-c", "user.name=QA", "-c", "user.email=qa@example.invalid", "commit", "--quiet", "-m", "fixture baseline")
        self.source_commit = self.git("rev-parse", "HEAD").strip()
        self.baseline = self.root / "baseline.tsv"
        self.baseline.write_text(self.git("ls-files", "--stage"), encoding="utf-8")
        self.allow = self.root / "allow.json"
        self.allow.write_text("[]", encoding="utf-8")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True)

    def check(self):
        spec = importlib.util.spec_from_file_location("baseline_guard", SCRIPT)
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        try:
            report = guard.verify(self.root, self.baseline, self.allow, source_commit=self.source_commit)
        except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
            return subprocess.CompletedProcess([], 2, stdout=str(error), stderr="")
        return subprocess.CompletedProcess([], 0 if report["passed"] else 1, stdout=json.dumps(report), stderr="")

    def test_unchanged_source_passes(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_unstaged_and_staged_source_change_fails(self):
        self.source.write_text("value = 2\n", encoding="utf-8")
        self.assertNotEqual(self.check().returncode, 0)
        self.git("add", "source.py")
        self.assertNotEqual(self.check().returncode, 0)

    def test_korean_and_space_path_passes(self):
        name = "한글 파일.txt"
        (self.root / name).write_text("원본\n", encoding="utf-8")
        self.git("add", name)
        self.git("-c", "user.name=QA", "-c", "user.email=qa@example.invalid", "commit", "--quiet", "-m", "unicode fixture")
        self.source_commit = self.git("rev-parse", "HEAD").strip()
        self.baseline.write_text(self.git("ls-files", "--stage"), encoding="utf-8")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_protected_file_and_manifest_tampering_fails(self):
        self.source.write_text("value = 2\n", encoding="utf-8")
        self.git("add", "source.py")
        self.baseline.write_text(self.git("ls-files", "--stage"), encoding="utf-8")
        self.assertNotEqual(self.check().returncode, 0)

    def test_cli_uses_fixed_approved_source_commit(self):
        root = SCRIPT.parent.parent
        result = subprocess.run([sys.executable, str(SCRIPT), "--baseline", "scripts/cga-source-baseline.tsv", "--allowlist", "scripts/cga-change-allowlist.json"], cwd=root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["source_commit"], "c2d643ed8d2c0a19f80caf2709efe6199e3c96bc")

    def test_missing_source_fails(self):
        self.source.unlink()
        self.assertNotEqual(self.check().returncode, 0)

    def test_exact_approved_change_passes(self):
        self.source.write_text("value = 2\n", encoding="utf-8")
        self.allow.write_text(json.dumps([{"path":"source.py", "stage":"S01", "reason":"fixture change"}]), encoding="utf-8")
        self.assertEqual(self.check().returncode, 0)

    def test_wildcard_allowlist_fails(self):
        self.allow.write_text(json.dumps([{"path":"*", "stage":"S01", "reason":"invalid"}]), encoding="utf-8")
        self.assertNotEqual(self.check().returncode, 0)

    def test_new_tracked_product_file_requires_approval(self):
        (self.root / "extra.py").write_text("pass\n", encoding="utf-8")
        self.git("add", "extra.py")
        self.assertNotEqual(self.check().returncode, 0)

if __name__ == "__main__":
    unittest.main()
