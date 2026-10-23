"""配る一式の上限の試験（値は tools/limits.py）。

SKILL.md は18,000字以下、description は280字以下、front matter は500字以内、スクリプトは1本90,000バイト以下、
ファイルの数は file_budget と同じ、.zip の中の深さは3以内、拡張子は Microsoft の文書にあるものだけ、
1ファイル25MB以下、.zip は50MB以下、README に書かないことがない、を確かめる。
本番の生成物（skills/yomiyasu-mini/）があるときはそれを、なければ試験用の見本を確かめる。
"""
import io
import os
import shutil
import sys
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _util  # noqa: E402

limits = _util.load_tool("limits")

GOOD_FRONT = ('---\nname: yomiyasu-mini\ndescription: 試験の説明。\nlicense: MIT\nmetadata:\n  version: "1.0.0"\n'
              '  source-repository: "nanaism/yomiyasu"\n  source-tag: "v2.2.2"\n'
              '  source-commit: "488dd37c0baa67ec65bf155aced9fa1a01d261e2"\n---\n')


def skill(body="# yomiyasu-mini\n\n本文。\n", front=GOOD_FRONT):
    return front + "\n" + body


class LimitValuesTest(unittest.TestCase):
    def test_values(self):
        self.assertEqual(limits.SKILL_MD_MAX_CHARS, 18000)
        self.assertEqual(limits.SKILL_MD_BODY_LIMIT, 20000)
        self.assertEqual(limits.DESCRIPTION_MAX_CHARS, 280)
        self.assertEqual(limits.FRONT_MATTER_MAX_CHARS, 500)
        self.assertEqual(limits.SCRIPT_MAX_BYTES, 90000)
        self.assertEqual(limits.REFERENCE_MAX_BYTES, 100000)
        self.assertEqual(limits.FILE_MAX_BYTES, 25000000)
        self.assertEqual(limits.ZIP_MAX_BYTES, 50000000)
        self.assertEqual(limits.MAX_FILES_TOTAL, 350)
        self.assertEqual(limits.MAX_DEPTH, 3)

    def test_skill_md(self):
        self.assertEqual(limits.skill_md_problems(skill(), "yomiyasu-mini"), [])
        long_body = "# yomiyasu-mini\n\n" + "あ" * (18000 - len(skill("")) - 18) + "\n"
        self.assertEqual(limits.skill_md_problems(skill(long_body)), [])
        self.assertTrue(any("18,000字" in p for p in limits.skill_md_problems(skill(long_body + "あい"))))
        self.assertTrue(limits.skill_md_problems("# 見出しだけ\n"))
        bad = GOOD_FRONT.replace("試験の説明。", "あ" * 281)
        self.assertTrue(any("280字" in p for p in limits.skill_md_problems(skill(front=bad))))
        self.assertTrue(any("500字" in p for p in limits.skill_md_problems(
            skill(front=GOOD_FRONT.replace("試験の説明。", "あ" * 270).replace("license: MIT\n", "license: MIT\n" + "x: " + "y" * 200 + "\n")))))
        self.assertTrue(limits.skill_md_problems(skill(front=GOOD_FRONT.replace("name: yomiyasu-mini", "name: Yomiyasu_Mini"))))
        self.assertTrue(limits.skill_md_problems(skill(), "other-name"))
        self.assertTrue(limits.skill_md_problems(skill(front=GOOD_FRONT.replace('  source-commit: "488dd37c0baa67ec65bf155aced9fa1a01d261e2"\n', ""))))
        self.assertTrue(limits.skill_md_problems(skill(front=GOOD_FRONT.replace("試験の説明。", "<b>説明</b>"))))

    def test_files(self):
        base = {"SKILL.md": skill().encode("utf-8"), "LICENSE.txt": b"MIT\n"}
        self.assertEqual(limits.files_problems(base, "yomiyasu-mini", 2, True), [])
        cases = {
            "深さ": dict(base, **{"references/lists/x.md": b"x"}),
            "LICENSE の拡張子": dict(base, LICENSE=b"x"),
            "拡張子": dict(base, **{"a.exe": b"x"}),
            "ドット": dict(base, **{".hidden.md": b"x"}),
            "英数字": dict(base, **{"名前.md": b"x"}),
            "90,000": dict(base, **{"scripts/a.py": b"#" * 90001}),
            "socket": dict(base, **{"scripts/a.py": b"import socket\n"}),
            "subprocess": dict(base, **{"scripts/a.py": b"from subprocess import run\n"}),
            "読めません": dict(base, **{"scripts/a.py": b"def (:\n"}),
            "25,000,000": dict(base, **{"big.txt": b"x" * 25000001}),
            "100,000": dict(base, **{"references/rules.md": b"x" * 100001}),
        }
        for needle, files in cases.items():
            with self.subTest(needle=needle):
                problems = limits.files_problems(files, "yomiyasu-mini")
                self.assertTrue(any(needle in p for p in problems), problems)
        self.assertTrue(limits.files_problems({"a.md": b"x"}, "yomiyasu-mini"))
        self.assertTrue(limits.files_problems(base, "yomiyasu-mini", 3, True))
        self.assertTrue(limits.files_problems(base, "yomiyasu-mini", 1, False))
        many = dict(base, **{"f{}.txt".format(i): b"x" for i in range(349)})
        self.assertTrue(any("350" in p for p in limits.files_problems(many, "yomiyasu-mini")))
        self.assertEqual(limits.files_problems({"SKILL.md": base["SKILL.md"], "scripts/a.py": b"import json\n"}, "yomiyasu-mini"), [])
        self.assertEqual(limits.files_problems(dict(base, **{"references/rules.md": b"x" * 100000}), "yomiyasu-mini"), [])

    def test_bundle_rejects_symlink(self):
        folder = os.path.join(_util.temp_dir(self), "yomiyasu-mini")
        os.makedirs(folder)
        with open(os.path.join(folder, "SKILL.md"), "w", encoding="utf-8") as handle:
            handle.write(skill())
        os.symlink(os.path.join(folder, "SKILL.md"), os.path.join(folder, "link.md"))
        self.assertTrue(any("シンボリックリンク" in p for p in limits.bundle_problems(folder)))

    def test_zip(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("yomiyasu-mini/", b"")
            archive.writestr("yomiyasu-mini/SKILL.md", skill().encode("utf-8"))
            archive.writestr("other/x.md", b"x")
        path = os.path.join(_util.temp_dir(self), "a.zip")
        with open(path, "wb") as handle:
            handle.write(buffer.getvalue())
        problems = limits.zip_problems(path, "yomiyasu-mini")
        self.assertTrue(any("フォルダの項目" in p for p in problems), problems)
        self.assertTrue(any("other/x.md" in p for p in problems), problems)

    def test_readme_words(self):
        self.assertEqual(limits.readme_problems("Microsoft が公開している上限に合わせ、SKILL.md を18,000字以下にしています。\n"), [])
        for text in ("claude.ai で使えます", "動作は未確認です", "ほかの環境では確かめていません", "今後対応する予定です",
                     "2026年10月に公開", "2026-10-21", "Copilot で動きます", "Co-Authored-By: x"):
            with self.subTest(text=text):
                self.assertTrue(limits.readme_problems(text))


class BundleCheck:
    """配る一式のフォルダを確かめる共通の試験。bundle、budget、name を持つクラスで使う。"""

    def test_bundle_limits(self):
        self.assertEqual(limits.bundle_problems(self.bundle, "yomiyasu-mini", self.budget, exact_budget=True), [])

    def test_skill_md_and_front_matter(self):
        with open(os.path.join(self.bundle, "SKILL.md"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertLessEqual(len(text), limits.SKILL_MD_MAX_CHARS)
        block, body = limits.split_front_matter(text)
        self.assertLessEqual(len(block), limits.FRONT_MATTER_MAX_CHARS)
        fm = limits.parse_front_matter(block)
        self.assertEqual(fm["name"], "yomiyasu-mini")
        self.assertLessEqual(len(fm["description"]), limits.DESCRIPTION_MAX_CHARS)
        self.assertEqual(fm["license"], "MIT")

    def test_scripts_compile_and_help(self):
        work = os.path.join(_util.temp_dir(self), "yomiyasu-mini")
        shutil.copytree(self.bundle, work)
        scripts = os.path.join(work, "scripts")
        names = sorted(n for n in os.listdir(scripts) if n.endswith(".py")) if os.path.isdir(scripts) else []
        self.assertTrue(names)
        for name in names:
            with self.subTest(script=name):
                with open(os.path.join(scripts, name), encoding="utf-8") as handle:
                    compile(handle.read(), name, "exec")
                done = _util.run(os.path.join(scripts, name), "--help", cwd="/")
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                if name == "mini_check.py":
                    self.assertNotIn("yomiyasu-mini-check:", done.stdout.split("\n")[0])
                    self.assertNotIn("ran version=", done.stdout)
        self.assertNotIn("__pycache__", os.listdir(scripts))

    def test_forbidden_strings_absent(self):
        for path, data in sorted(_util.read_tree(self.bundle).items()):
            if path.endswith((".md", ".py")):
                text = data.decode("utf-8")
                for item in self.forbidden:
                    self.assertNotIn(item, text, path)
                self.assertNotIn("Co-Authored-By", text, path)

    def test_zip_size(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
            for path, data in sorted(_util.read_tree(self.bundle).items()):
                archive.writestr("yomiyasu-mini/" + path, data)
        self.assertLessEqual(len(buffer.getvalue()), limits.ZIP_MAX_BYTES)


class FixtureBundleTest(BundleCheck, unittest.TestCase):
    """試験用の見本（tests/fixtures/basic/expected）。本体の木がなくても回る。"""

    def setUp(self):
        self.bundle = os.path.join(_util.FIXTURES, "basic", "expected", _util.OUTPUT_DIR)
        table = _util.load_json(os.path.join(_util.FIXTURES, "basic", "extract", "table.json"))
        self.budget = table["file_budget"]
        self.forbidden = table["forbidden_strings"]


class RealBundleTest(BundleCheck, unittest.TestCase):
    """本番の抽出表（extract/table.json）から一時フォルダに生成したもの。抽出表がまだなければ飛ばす。

    コミット済みの skills/yomiyasu-mini/ がこれと同じバイトであることは、test_generate の
    RealGenerateTest.test_committed_output_matches（と CI の generate --check）が確かめる。
    """

    def setUp(self):
        root = _util.real_output(self)
        table_path = _util.REAL_TABLE
        self.bundle = os.path.join(root, _util.OUTPUT_DIR)
        table = _util.load_json(table_path)
        self.budget = table["file_budget"]
        self.forbidden = list(table.get("forbidden_strings", []))
        for path in _util.table_files(table_path)[1:]:
            self.forbidden += _util.load_json(path).get("forbidden_strings", [])

    def test_reference_files_fit_the_budget(self):
        # 参照ファイルは1本 100,000 バイト以下に収める（自前の目安。Microsoft の上限ではない）。
        # v2.2.2 の calques.md の追記で rules.md が 101,669 バイトになり、r-stance を doc-types.md に移した。
        folder = os.path.join(self.bundle, "references")
        names = sorted(n for n in os.listdir(folder) if n.endswith(".md"))
        self.assertTrue(names)
        for name in names:
            size = os.path.getsize(os.path.join(folder, name))
            self.assertLessEqual(size, limits.REFERENCE_MAX_BYTES, "references/{} が {:,}バイトあります".format(name, size))

    def test_readme_has_only_facts(self):
        path = os.path.join(_util.REPO, "README.md")
        if not os.path.isfile(path):
            self.skipTest("README.md がまだありません")
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(limits.readme_problems(handle.read()), [])


class GenerateEnforcesLimitsTest(unittest.TestCase):
    """生成の道具が、上限を超えたものを本番の出力に書かないこと。"""

    def test_oversized_skill_md_is_not_written(self):
        main = _util.require_main(self)
        tree = _util.copy_main(self, main)
        repo = _util.copy_fixture(self)
        with open(os.path.join(repo, "extract", "own", "intro.md"), "w", encoding="utf-8") as handle:
            handle.write("# yomiyasu-mini\n\n" + "あ" * 18001 + "\n")
        table = os.path.join(repo, "extract", "table.json")
        done = _util.generate("--source", tree, "--commit", _util.table_commit(table), "--table", table, "--accept")
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertIn("LIMIT", done.stderr)
        self.assertFalse(os.path.exists(os.path.join(repo, "skills")))


if __name__ == "__main__":
    unittest.main()
