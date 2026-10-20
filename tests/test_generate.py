"""生成の試験。2回生成すると同じバイトになること、--check、--accept、測定用の写し、版の記録を確かめる。

試験用の抽出表（tests/fixtures/basic）は、どの part の種類も通る小さな表で、生成物の見本（expected/）を持つ。
見本と同じになることを Python 3.9 と 3.14 の両方で確かめるので、版が違っても同じバイトになることも確かめられる。
本番の抽出表（extract/table.json）があるときは、その表でも同じことを確かめる。
"""
import json
import os
import re
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _util  # noqa: E402

FIXTURE_TABLE_FILES = ("table.json", "scripts.json")


def without_extract(tree):
    return {k: v for k, v in tree.items() if not k.startswith("extract/")}


class FixtureGenerateTest(unittest.TestCase):
    def setUp(self):
        self.main = _util.require_main(self)
        self.tree = _util.copy_main(self, self.main)
        self.commit = _util.table_commit(os.path.join(_util.FIXTURES, "basic", "extract", "table.json"))

    def generate(self, repo, *extra):
        return _util.generate("--source", self.tree, "--commit", self.commit,
                              "--table", os.path.join(repo, "extract", "table.json"), *extra)

    def test_generate_twice_gives_same_bytes(self):
        a, b = _util.copy_fixture(self), _util.copy_fixture(self)
        for repo in (a, b):
            done = self.generate(repo)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        first, second = without_extract(_util.read_tree(a)), without_extract(_util.read_tree(b))
        self.assertEqual(sorted(first), sorted(second))
        for path in first:
            self.assertEqual(first[path], second[path], path)
        again = self.generate(a)
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertEqual(without_extract(_util.read_tree(a)), first)

    def test_matches_committed_example(self):
        repo = _util.copy_fixture(self, expected=True)
        done = self.generate(repo, "--check")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("今のファイルと同じです", done.stdout)

    def test_git_tree_needs_no_commit_option(self):
        if not os.path.exists(os.path.join(self.main, ".git")):
            self.skipTest("本体の木が git の木ではありません")
        repo = _util.copy_fixture(self, expected=True)
        done = _util.generate("--source", self.main, "--table", os.path.join(repo, "extract", "table.json"), "--check")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("git で確かめていない", done.stderr)

    def test_check_reports_changed_and_extra_files(self):
        repo = _util.copy_fixture(self, expected=True)
        with open(os.path.join(repo, _util.OUTPUT_DIR, "SKILL.md"), "a", encoding="utf-8") as handle:
            handle.write("手で足した行\n")
        with open(os.path.join(repo, _util.OUTPUT_DIR, "notes.txt"), "w", encoding="utf-8") as handle:
            handle.write("紛れ込んだファイル\n")
        done = self.generate(repo, "--check")
        self.assertEqual(done.returncode, 4, done.stdout + done.stderr)
        self.assertIn("DIFFERS  skills/yomiyasu-mini/SKILL.md", done.stdout)
        self.assertIn("EXTRA    skills/yomiyasu-mini/notes.txt", done.stdout)

    def test_unknown_file_in_output_stops(self):
        repo = _util.copy_fixture(self, expected=True)
        with open(os.path.join(repo, _util.OUTPUT_DIR, ".DS_Store"), "wb") as handle:
            handle.write(b"x")
        done = self.generate(repo)
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertIn("抽出表にないファイル", done.stderr)

    def test_stale_generated_files_are_removed(self):
        repo = _util.copy_fixture(self, expected=True)
        path = os.path.join(repo, "extract", "scripts.json")
        scripts = _util.load_json(path)
        scripts["scripts"][0]["packing"]["limit"] = 80000
        _util.write_json(path, scripts)
        done = self.generate(repo)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        names = sorted(os.listdir(os.path.join(repo, _util.OUTPUT_DIR, "scripts")))
        self.assertEqual(names, ["mini_check.py"])
        manifest = _util.load_json(os.path.join(repo, "MANIFEST.json"))
        self.assertEqual(len(manifest["files"]), 5)

    def test_tables_are_written_in_canonical_form(self):
        for name in FIXTURE_TABLE_FILES:
            path = os.path.join(_util.FIXTURES, "basic", "extract", name)
            with open(path, encoding="utf-8") as handle:
                raw = handle.read()
            self.assertEqual(json.dumps(json.loads(raw), ensure_ascii=False, indent=2) + "\n", raw, name)

    def test_accept_fills_hashes_in_the_same_form(self):
        repo = _util.copy_fixture(self)
        originals = {}
        for name in FIXTURE_TABLE_FILES:
            path = os.path.join(repo, "extract", name)
            with open(path, encoding="utf-8") as handle:
                originals[name] = handle.read()
            obj = json.loads(originals[name])
            _drop_hashes(obj)
            _util.write_json(path, obj)
        done = self.generate(repo)
        self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
        self.assertIn("NEW", done.stdout)
        self.assertFalse(os.path.exists(os.path.join(repo, "skills")))
        done = self.generate(repo, "--accept")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        for name in FIXTURE_TABLE_FILES:
            with open(os.path.join(repo, "extract", name), encoding="utf-8") as handle:
                self.assertEqual(handle.read(), originals[name], name)

    def test_check_and_accept_together_is_refused(self):
        repo = _util.copy_fixture(self, expected=True)
        done = self.generate(repo, "--check", "--accept")
        self.assertEqual(done.returncode, 2)

    # 測定用の写し
    def variant_out(self, repo, name):
        return os.path.join(repo, "measurement", "variants", name)

    def test_measure_variant_with_drop(self):
        repo = _util.copy_fixture(self)
        out = self.variant_out(repo, "no-step3")
        done = self.generate(repo, "--measure-variant", "--drop", "step3", "--out", out)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        with open(os.path.join(out, _util.OUTPUT_DIR, "SKILL.md"), encoding="utf-8") as handle:
            skill = handle.read()
        self.assertNotIn("### Step 3", skill)
        self.assertNotIn("### 状態の行", skill)  # drop_with で一緒に外れる
        self.assertIn("### 最優先ルール: 意味の保持", skill)
        manifest = _util.load_json(os.path.join(out, "MANIFEST.json"))
        self.assertTrue(manifest["measure_variant"])
        self.assertEqual(manifest["dropped"], ["status", "step3"])
        self.assertFalse(os.path.exists(os.path.join(repo, "skills")), "本番の出力に書いている")
        self.assertFalse(os.path.exists(os.path.join(repo, "MANIFEST.json")), "本番の出力に書いている")

    def test_measure_variant_without_scripts_allows_missing_reference(self):
        repo = _util.copy_fixture(self)
        out = self.variant_out(repo, "no-scripts")
        done = self.generate(repo, "--measure-variant", "--drop", "check", "--out", out)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("参照の欠け", done.stderr)
        self.assertFalse(os.path.exists(os.path.join(out, _util.OUTPUT_DIR, "scripts")))

    def test_measure_variant_cannot_write_production_output(self):
        repo = _util.copy_fixture(self)
        for extra in (["--out", repo], [], ["--out", os.path.join(repo, "measurement")]):
            with self.subTest(extra=extra):
                done = self.generate(repo, "--measure-variant", "--drop", "step3", *extra)
                self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
                self.assertIn("measurement", done.stderr)
                self.assertFalse(os.path.exists(os.path.join(repo, "skills")))

    def test_drop_needs_measure_variant(self):
        repo = _util.copy_fixture(self)
        done = self.generate(repo, "--drop", "step3")
        self.assertEqual(done.returncode, 2)
        self.assertIn("--measure-variant", done.stderr)
        self.assertFalse(os.path.exists(os.path.join(repo, "skills")))

    def test_measure_keep_cannot_be_dropped(self):
        repo = _util.copy_fixture(self)
        out = self.variant_out(repo, "x")
        done = self.generate(repo, "--measure-variant", "--drop", "keep-meaning", "--out", out)
        self.assertEqual(done.returncode, 2)
        self.assertIn("measure_keep", done.stderr)
        self.assertFalse(os.path.exists(out))

    # 版と出どころの記録
    def test_version_and_source_are_stamped(self):
        limits = _util.load_tool("limits")
        table = _util.load_json(os.path.join(_util.FIXTURES, "basic", "extract", "table.json"))
        version, source = table["version"], table["source"]
        expected = os.path.join(_util.FIXTURES, "basic", "expected")
        with open(os.path.join(expected, _util.OUTPUT_DIR, "SKILL.md"), encoding="utf-8") as handle:
            block, _ = limits.split_front_matter(handle.read())
        meta = limits.parse_front_matter(block)["metadata"]
        self.assertEqual(meta, {"version": version, "source-repository": source["repository"],
                                "source-tag": source["tag"], "source-commit": source["commit"]})
        scripts = os.path.join(expected, _util.OUTPUT_DIR, "scripts")
        for name in sorted(os.listdir(scripts)):
            with open(os.path.join(scripts, name), encoding="utf-8") as handle:
                text = handle.read()
            self.assertIn('__version__ = "{}"\n'.format(version), text, name)
            self.assertIn('SOURCE_COMMIT = "{}"\n'.format(source["commit"]), text, name)
            self.assertIn("{} {}（{}）".format(source["repository"], source["tag"], source["commit"]), text, name)
        manifest = _util.load_json(os.path.join(expected, "MANIFEST.json"))
        self.assertEqual(manifest["version"], version)
        self.assertEqual(manifest["source"]["commit"], source["commit"])
        self.assertTrue(VERSION_RE.match(version))

    def test_generated_scripts_run(self):
        folder = os.path.join(_util.temp_dir(self), "scripts")
        shutil.copytree(os.path.join(_util.FIXTURES, "basic", "expected", _util.OUTPUT_DIR, "scripts"), folder)
        a = os.path.join(folder, "..", "a.md")
        with open(a, "w", encoding="utf-8") as handle:
            handle.write("**太字**の文。\n")
        done = _util.run(os.path.join(folder, "mini_check.py"), "--source", a, "--final", a, cwd=os.path.dirname(folder))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("yomiyasu-mini-check: ran version=1.0.0 same=yes emoji=18.0 doc_type=pr", done.stdout)
        self.assertEqual([n for n in os.listdir(folder) if n == "__pycache__"], [])

    def test_ci_checks_out_the_tag_in_the_table(self):
        table = _util.REAL_TABLE if os.path.isfile(_util.REAL_TABLE) else os.path.join(
            _util.FIXTURES, "basic", "extract", "table.json")
        tag = _util.load_json(table)["source"]["tag"]
        with open(os.path.join(_util.REPO, ".github", "workflows", "ci.yml"), encoding="utf-8") as handle:
            ci = handle.read()
        refs = re.findall(r"(?m)^\s*ref:\s*(\S+)\s*$", ci)
        self.assertEqual(refs, [tag])
        self.assertIn("repository: nanaism/yomiyasu", ci)


VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def _drop_hashes(obj):
    if isinstance(obj, dict):
        for key in ("sha256", "text_sha256"):
            obj.pop(key, None)
        obj.pop("names", None)
        for value in obj.values():
            _drop_hashes(value)
    elif isinstance(obj, list):
        for value in obj:
            _drop_hashes(value)


class RealGenerateTest(unittest.TestCase):
    """本番の抽出表（extract/table.json）での生成。"""

    def setUp(self):
        self.main = _util.require_main(self)
        self.table = _util.require_real_table(self)
        self.commit = _util.table_commit(self.table)

    def generate(self, *extra):
        return _util.generate("--source", self.main, "--commit", self.commit, "--table", self.table, *extra)

    def test_generate_twice_gives_same_bytes(self):
        a, b = _util.temp_dir(self), _util.temp_dir(self)
        for out in (a, b):
            done = self.generate("--out", out)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        first, second = _util.read_tree(a), _util.read_tree(b)
        self.assertEqual(sorted(first), sorted(second))
        for path in first:
            self.assertEqual(first[path], second[path], path)

    def test_committed_output_matches(self):
        _util.require_committed_output(self)
        done = self.generate("--check")
        self.assertEqual(done.returncode, 0,
                         "skills/yomiyasu-mini/ と MANIFEST.json が抽出表から作ったものと違います。"
                         "tools/generate.py で生成し直してください。\n" + done.stdout + done.stderr)

    def test_tables_are_written_in_canonical_form(self):
        for path in _util.table_files(self.table):
            with open(path, encoding="utf-8") as handle:
                raw = handle.read()
            self.assertEqual(json.dumps(json.loads(raw), ensure_ascii=False, indent=2) + "\n", raw,
                             "{} を json.dumps(ensure_ascii=False, indent=2) の形にしてください".format(path))


if __name__ == "__main__":
    unittest.main()
