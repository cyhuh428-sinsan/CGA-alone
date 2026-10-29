import importlib.util
import json
from pathlib import Path
import subprocess
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
        self.baseline = self.root / "baseline.tsv"
        self.baseline.write_text(self.git("ls-files", "--stage"), encoding="utf-8")
        self.allow = self.root / "allow.json"
        self.allow.write_text("[]", encoding="utf-8")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True)

    def check(self):
        return subprocess.run(["python", str(SCRIPT), "--root", str(self.root), "--baseline", str(self.baseline), "--allowlist", str(self.allow)], capture_output=True, text=True)

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
        self.baseline.write_text(self.git("ls-files", "--stage"), encoding="utf-8")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout)

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
