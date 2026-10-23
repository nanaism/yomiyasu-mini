"""mini_check.py が、本体の yomiyasu_diff.diff() と同じ値を出すかを確かめる。

比べる値: meaning_risks（全種類）、markers、new_words、lost_words、type_changes と、--fail-on に当たる件数。
本体と mini は、この試験と同じ Python で動かす。この試験は何も生成しない。生成物は tools/generate.py で作る。

入力（どれも公開しているもの）:
- 本体の tests/corpus の組（yomiyasu_rewritten の書き直しと、元の raw_ai か blacklist_ai の文。v2.1.1 と v2.2.2 では48組）。
  文書の種類なしと pr の2通り。CLI（--json）でも同じ値になるかを見る。
- 本体の試験を一時フォルダの写しで走らせ、diff() に渡された入力をその場で集めたもの（集めた入力は保存しない）。
  走らせるのは、本文に「diff(」がある試験のファイルだけ（v2.1.1 では75本のうち36本で、集まる入力は全部を走らせたときと同じ
  3,885件。v2.2.2 では89本のうち41本で3,919件）。ファイルごとに別のプロセスと別の写しで、並べて走らせる。

場所:
- 本体の木: 環境変数 YOMIYASU_MAIN。なければ、このリポジトリの _main/（CI が本体を取り出す場所）。
- mini のスクリプト: 環境変数 YOMIYASU_MINI_SCRIPTS。なければ skills/yomiyasu-mini/scripts/。
どちらかがないときは飛ばす。YOMIYASU_REQUIRE_MAIN=1 のときは、飛ばさずに失敗にする。
本体の試験の入力を集める段を飛ばすときは YOMIYASU_PARITY_HARVEST=0、全部の試験のファイルを走らせるときは all にする。"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MAIN = Path(os.environ.get("YOMIYASU_MAIN") or REPO / "_main").resolve()
MINI_SCRIPTS = Path(os.environ.get("YOMIYASU_MINI_SCRIPTS") or REPO / "skills" / "yomiyasu-mini" / "scripts").resolve()
MAIN_SCRIPTS = MAIN / "skills" / "yomiyasu" / "scripts"
REQUIRE = os.environ.get("YOMIYASU_REQUIRE_MAIN") == "1"
KEYS = ("meaning_risks", "markers", "new_words", "lost_words", "type_changes")

# 本体の試験を写しの木で走らせ、diff() に渡された (元, 後, doc_type) を JSON に書く。別のプロセスで動かす
# （本体の試験が sys.modules や作業フォルダを変えても、この試験に響かないようにするため）。
HARVEST = r'''
import hashlib, json, os, sys, unittest
root, pattern, out = sys.argv[1], sys.argv[2], sys.argv[3]
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(root, "scripts"))
os.chdir(root)
import yomiyasu_diff as D
seen, inputs = set(), []
original = D.diff
def wrapped(orig_raw, rw_raw, stance=None, *, encoding_notes=None, doc_type=None, reader=None, **extra):
    if isinstance(orig_raw, str) and isinstance(rw_raw, str) and (doc_type is None or isinstance(doc_type, str)):
        key = hashlib.sha256(json.dumps([orig_raw, rw_raw, doc_type]).encode("ascii")).hexdigest()
        if key not in seen:
            seen.add(key)
            inputs.append([orig_raw, rw_raw, doc_type])
    # extra は本体 v2.2.0 で足された words（語の一覧）など。そのまま渡す（差分と候補は変わらない）
    return original(orig_raw, rw_raw, stance, encoding_notes=encoding_notes, doc_type=doc_type, reader=reader, **extra)
D.diff = wrapped
suite = unittest.defaultTestLoader.discover(os.path.join(root, "tests"), pattern=pattern,
                                            top_level_dir=os.path.join(root, "tests"))
with open(os.devnull, "w") as sink:
    result = unittest.TextTestRunner(stream=sink, verbosity=0).run(suite)
with open(out, "w", encoding="ascii") as handle:
    json.dump({"tests_run": result.testsRun, "inputs": inputs}, handle)
'''


def harvest(main_root):
    """本体の試験を写しで走らせ、diff() の入力を集める。[(元, 後, doc_type)] と走らせた試験の数を返す。"""
    tests = Path(main_root) / "tests"
    every = os.environ.get("YOMIYASU_PARITY_HARVEST") == "all"
    names = sorted(path.name for path in tests.glob("test_*.py")
                   if every or "diff(" in path.read_text(encoding="utf-8", errors="replace"))
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTHON")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["GIT_OPTIONAL_LOCKS"] = "0"

    def one(name):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "main")
            shutil.copytree(str(main_root), root, ignore=shutil.ignore_patterns(".git", "__pycache__", "_main"))
            out = os.path.join(tmp, "inputs.json")
            run = subprocess.run([sys.executable, "-I", "-B", "-c", HARVEST, root, name, out], cwd=root, env=env,
                                 capture_output=True, timeout=1800)
            if run.returncode != 0:
                raise AssertionError("{}: {}".format(name, run.stderr.decode("utf-8", "replace")[-2000:]))
            with open(out, encoding="ascii") as handle:
                return json.load(handle)

    with ThreadPoolExecutor(max_workers=max(1, min(4, os.cpu_count() or 1))) as pool:
        results = list(pool.map(one, names))
    seen, inputs = set(), []
    for result in results:
        for item in result["inputs"]:
            key = json.dumps(item)
            if key not in seen:
                seen.add(key)
                inputs.append(item)
    return inputs, sum(result["tests_run"] for result in results), len(names)


_STATE = {}


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[name]
        raise
    return module


def setUpModule():
    # 本体と mini のフォルダに __pycache__ を作らない（mini のフォルダは zip にそのまま入る）
    sys.dont_write_bytecode = True
    missing = []
    if not (MAIN_SCRIPTS / "yomiyasu_diff.py").is_file():
        missing.append("本体の木（{}）に skills/yomiyasu/scripts/yomiyasu_diff.py がない。YOMIYASU_MAIN で指す".format(MAIN))
    if not (MINI_SCRIPTS / "mini_check.py").is_file():
        missing.append("mini のスクリプト（{}）がまだない。tools/generate.py で生成してから回す".format(MINI_SCRIPTS))
    if missing:
        if REQUIRE:
            raise AssertionError("; ".join(missing))
        raise unittest.SkipTest("; ".join(missing))
    _STATE["main"] = _load(MAIN_SCRIPTS / "yomiyasu_diff.py", "yomiyasu_diff_main_for_mini_parity")
    _STATE["mini"] = _load(MINI_SCRIPTS / "mini_check.py", "yomiyasu_mini_check_for_parity")


def _dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _main_values(main, orig, rw, doc_type, encoding_notes=None):
    d = main.diff(orig, rw, None, encoding_notes=encoding_notes, doc_type=doc_type)
    return {key: d[key] for key in KEYS}, d["fail_on_meaning_risk_count"]


def corpus_pairs():
    corpus = MAIN / "tests" / "corpus"
    pairs = []
    for path in sorted((corpus / "yomiyasu_rewritten").glob("*.md")):
        if path.name.endswith("_bl.md"):
            source = corpus / "blacklist_ai" / (path.name[:-len("_bl.md")] + ".md")
        else:
            source = corpus / "raw_ai" / path.name
        pairs.append((source, path))
    return pairs


class CorpusParity(unittest.TestCase):
    def test_corpus_pairs_function(self):
        main, mini = _STATE["main"], _STATE["mini"]
        pairs = corpus_pairs()
        self.assertTrue(pairs, "本体の tests/corpus/yomiyasu_rewritten に組がない")
        risks = 0
        for source, final in pairs:
            self.assertTrue(source.is_file(), "元の文がない: {}".format(source))
            orig, orig_info, problem = main._read_input(str(source))
            self.assertIsNone(problem)
            rw, rw_info, problem = main._read_input(str(final))
            self.assertIsNone(problem)
            notes = main._encoding_notes(orig_info, rw_info)
            for doc_type in (None, "pr"):
                with self.subTest(pair=final.name, doc_type=doc_type):
                    want, counted = _main_values(main, orig, rw, doc_type, notes)
                    got = mini.check(orig, rw, doc_type)
                    for key in KEYS:
                        self.assertEqual(_dump(got[key]), _dump(want[key]), key)
                    self.assertEqual(mini.fail_on_count(got["meaning_risks"]), counted)
                    risks += len(want["meaning_risks"])
        self.assertGreater(risks, 0, "どの組でも恐れが出ていない（比べる意味が薄い）")

    def test_corpus_pairs_cli(self):
        main = _STATE["main"]
        script = MINI_SCRIPTS / "mini_check.py"
        for source, final in corpus_pairs():
            with self.subTest(pair=final.name):
                orig, orig_info, _ = main._read_input(str(source))
                rw, rw_info, _ = main._read_input(str(final))
                want, counted = _main_values(main, orig, rw, None, main._encoding_notes(orig_info, rw_info))
                run = subprocess.run([sys.executable, "-I", "-B", str(script), "--source", str(source), "--final", "-",
                                      "--json"], input=final.read_bytes(), capture_output=True, timeout=120,
                                     cwd=tempfile.gettempdir())
                self.assertEqual(run.returncode, 0, run.stdout.decode("utf-8", "replace")[-500:])
                got = json.loads(run.stdout.decode("utf-8"))
                self.assertEqual(got["status"], "ran")
                for key in KEYS:
                    self.assertEqual(_dump(got[key]), _dump(json.loads(_dump(want[key]))), key)
                self.assertEqual(got["counted"], counted)
                self.assertEqual(got["meaning_risk_count"], len(want["meaning_risks"]))
                self.assertEqual(got["status_line"], "yomiyasu-mini-check: ran version={} base={}@{} meaning_risk={} "
                                 "counted={}".format(got["version"], got["source"]["tag"], got["source"]["commit"][:7],
                                                     len(want["meaning_risks"]), counted))


@unittest.skipIf(os.environ.get("YOMIYASU_PARITY_HARVEST") == "0", "YOMIYASU_PARITY_HARVEST=0")
class HarvestParity(unittest.TestCase):
    def test_inputs_from_main_tests(self):
        main, mini = _STATE["main"], _STATE["mini"]
        inputs, tests_run, files = harvest(MAIN)
        self.assertGreater(tests_run, 0)
        self.assertGreater(len(inputs), 100, "本体の試験から集めた入力が少ない: {}".format(len(inputs)))
        compared = 0
        kinds = set()
        for index, (orig, rw, doc_type) in enumerate(inputs):
            try:
                want, counted = _main_values(main, orig, rw, doc_type)
            except Exception as error:
                with self.subTest(index=index, main_error=type(error).__name__):
                    with self.assertRaises(type(error)):
                        mini.check(orig, rw, doc_type)
                continue
            compared += 1
            kinds.update(risk["kind"] for risk in want["meaning_risks"])
            got = mini.check(orig, rw, doc_type)
            with self.subTest(index=index, doc_type=doc_type):
                for key in KEYS:
                    self.assertEqual(_dump(got[key]), _dump(want[key]), key)
                self.assertEqual(mini.fail_on_count(got["meaning_risks"]), counted)
        self.assertGreater(compared, 100)
        # v2.1.1 と v2.2.2 の本体の試験の入力では、meaning_risks の20種類がすべて出る
        self.assertGreaterEqual(len(kinds), 15, sorted(kinds))


class CliStatus(unittest.TestCase):
    """状態の行と終了コード（DECISIONS.md 4章）。"""

    def run_cli(self, script, *args, stdin=b""):
        run = subprocess.run([sys.executable, "-I", "-B", str(script)] + list(args), input=stdin, capture_output=True,
                             timeout=120, cwd=tempfile.gettempdir())
        return run.returncode, run.stdout.decode("utf-8").splitlines()

    def test_status_lines(self):
        source, final = corpus_pairs()[0]
        code, lines = self.run_cli(MINI_SCRIPTS / "mini_check.py", "--source", str(source), "--final", str(final))
        self.assertEqual(code, 0)
        self.assertRegex(lines[1], r"^yomiyasu-mini-check: ran version=\S+ base=\S+@[0-9a-f]{7} meaning_risk=\d+ counted=\d+$")
        self.assertEqual(lines[-1], lines[1])
        code, lines = self.run_cli(MINI_SCRIPTS / "mini_check.py", "--help")
        self.assertEqual(code, 0)
        self.assertFalse([line for line in lines if line.startswith("yomiyasu-mini-check:")])
        code, lines = self.run_cli(MINI_SCRIPTS / "mini_check.py", "--source", "-", "--final", "-")
        self.assertEqual((code, lines[1], lines[-1]), (2, "yomiyasu-mini-check: not_run reason=input",
                                                       "yomiyasu-mini-check: not_run reason=input"))

    def test_missing_or_broken_part(self):
        source, final = corpus_pairs()[0]
        parts = sorted(path.name for path in MINI_SCRIPTS.glob("mini_*.py") if path.name != "mini_check.py")
        self.assertTrue(parts)
        for name, broken in [(parts[0], None), (parts[-1], b"def broken(:\n")]:
            with tempfile.TemporaryDirectory() as tmp, self.subTest(part=name, broken=bool(broken)):
                folder = Path(tmp) / "a" / "scripts"
                shutil.copytree(str(MINI_SCRIPTS), str(folder), ignore=shutil.ignore_patterns("__pycache__"))
                if broken:
                    with open(str(folder / name), "ab") as handle:
                        handle.write(broken)
                else:
                    (folder / name).unlink()
                code, lines = self.run_cli(folder / "mini_check.py", "--source", str(source), "--final", str(final))
                self.assertEqual((code, lines[1], lines[-1]), (3, "yomiyasu-mini-check: not_run reason=check_error",
                                                               "yomiyasu-mini-check: not_run reason=check_error"))
                self.assertFalse(list(folder.rglob("__pycache__")))

    def test_no_main_status_line(self):
        for path in sorted(MINI_SCRIPTS.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("yomiyasu-check: ", text, path.name)


if __name__ == "__main__":
    unittest.main()
