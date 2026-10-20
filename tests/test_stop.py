"""生成が止まること（終了コード2）と、見直しの一覧が出ること（終了コード3）の試験。

本体の木の写し（.git を除く）を一時フォルダに作って手を入れ、--commit を付けて tools/generate.py を呼ぶ。
抽出表は tests/fixtures/basic（どの part の種類と止める条件も通る小さな表）。本番の抽出表（extract/table.json）が
あるときは、その表が見出しで指す節を1つずつ消す試験も回す。
"""
import os
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _util  # noqa: E402

SKILL = "skills/yomiyasu/SKILL.md"
PR = "skills/yomiyasu/references/doc-types/pr.md"
DIFF = "skills/yomiyasu/scripts/yomiyasu_diff.py"


class FixtureStopTest(unittest.TestCase):
    def setUp(self):
        self.main = _util.require_main(self)
        self.tree = _util.copy_main(self, self.main)
        self.repo = _util.copy_fixture(self)
        self.table = os.path.join(self.repo, "extract", "table.json")
        self.commit = _util.table_commit(self.table)

    def path(self, rel):
        return os.path.join(self.tree, rel)

    def generate(self, *extra):
        return _util.generate("--source", self.tree, "--commit", self.commit, "--table", self.table, *extra)

    def assertStopped(self, done, *needles):
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertIn("止めました。何も書いていません。", done.stderr)
        for needle in needles:
            self.assertIn(needle, done.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "skills")), "止めたのに書いている")
        self.assertFalse(os.path.exists(os.path.join(self.repo, "MANIFEST.json")), "止めたのに書いている")

    def assertReview(self, done, present, absent=()):
        self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
        self.assertIn("見直しが要る節", done.stdout)
        for needle in present:
            self.assertIn(needle, done.stdout)
        for needle in absent:
            self.assertNotIn(needle, done.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "skills")), "見直しの一覧を出したのに書いている")

    # (f) 写したままなら通り、見本と同じになる
    def test_unchanged_copy_generates(self):
        done = self.generate()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("git で確かめていない", done.stderr)
        expected = _util.read_tree(os.path.join(_util.FIXTURES, "basic", "expected"))
        got = _util.read_tree(self.repo)
        got = {k: v for k, v in got.items() if not k.startswith("extract/")}
        self.assertEqual(sorted(got), sorted(expected))
        for path in expected:
            self.assertEqual(got[path], expected[path], path)

    # (a) 指した見出しを1つずつ消すと止まる
    def test_each_heading_removed_stops(self):
        headings = _util.headings_in_table(_util.table_files(self.table))
        self.assertGreaterEqual(len(headings), 7)
        for source, level, text, _parents in headings:
            with self.subTest(heading=text):
                shutil.rmtree(self.tree)
                self.tree = _util.copy_main(self, self.main)
                _util.remove_heading(self.path(source), level, text)
                self.assertStopped(self.generate(), "MISSING heading", text)

    # (b) 見出しの文字列を1字変える、レベルを変える、同じ見出しを足す
    def test_heading_text_changed_stops(self):
        _util.edit(self.path(SKILL), "### 擬人化の解消\n", "### 擬人化を解消\n")
        self.assertStopped(self.generate(), "MISSING heading", "擬人化の解消")

    def test_heading_level_changed_stops(self):
        _util.edit(self.path(SKILL), "### 擬人化の解消\n", "#### 擬人化の解消\n")
        done = self.generate()
        self.assertStopped(done, "MISSING heading", "擬人化の解消", "同じ文字列の見出し: L4")

    def test_duplicate_heading_stops(self):
        _util.edit(self.path(SKILL), "### 比喩動詞の具体化\n", "### 擬人化の解消\n足した節。\n\n### 比喩動詞の具体化\n")
        self.assertStopped(self.generate(), "AMBIGUOUS heading", "擬人化の解消")

    # (d) 指した節の本文を1字変えると、見直しの一覧にその節だけが出る
    def test_section_changed_lists_only_that_part(self):
        _util.edit(self.path(SKILL), "道具や概念に感情や意志を持たせている", "道具や概念に感情や意思を持たせている")
        done = self.generate()
        self.assertReview(done, ["SKILL.md part 6 personify"],
                          ["keep-meaning", "subject-first", "subject-third", "provisional", "step3", "front_matter"])
        self.assertEqual(sum(1 for line in done.stdout.splitlines() if line.startswith("CHANGED")), 1)

    def test_line_changed_in_shared_section(self):
        # 主語と目的語の明確化の3行目（2番目の行の番号）だけを変える。その行を使う part と、節全体を元にした
        # rewritten の from だけが出て、1行目を使う part は出ない
        _util.edit(self.path(SKILL), "複数の述語で動作主が変わる文は、", "複数の述語で動作主の変わる文は、")
        done = self.generate()
        self.assertReview(done, ["subject-third", "subject-head from 0"], ["subject-first", "personify"])

    # 置き換え元の語が本体から消えると止まる
    def test_substitution_source_removed_stops(self):
        _util.edit(self.path(SKILL), "（gemini-syntax.md 原則3）", "")
        self.assertStopped(self.generate(), "COUNT", "（gemini-syntax.md 原則3）")

    def test_drop_lines_count_changed_stops(self):
        _util.edit(self.path(PR), "lint で外す規則: excess_list\n", "")
        self.assertStopped(self.generate(), "COUNT", "^lint で外す規則:")

    # (c) 取り出した関数の def を消す、名前を変えると止まる
    def test_function_renamed_stops(self):
        _util.edit(self.path(DIFF), "\ndef normalize(t: str) -> str:\n", "\ndef normalize_text(t: str) -> str:\n")
        self.assertStopped(self.generate(), "MISSING name", "normalize")

    def test_dependency_removed_stops(self):
        _util.edit(self.path(DIFF), '_NORMALIZE_BOLD = re.compile(r"\\*\\*(.+?)\\*\\*")\n', "")
        self.assertStopped(self.generate(), "_NORMALIZE_BOLD")

    # (e) 関数の本体を1字変える、front matter の description を変えると見直しになる
    def test_function_body_changed_reviews(self):
        _util.edit(self.path(DIFF), "    t = _NORMALIZE_SPACES.sub(\" \", t)\n    return t.strip()\n",
                   "    t = _NORMALIZE_SPACES.sub(\" \", t)\n    return t.strip(\" \\n\")\n")
        done = self.generate()
        self.assertReview(done, ["CHANGED name", "yomiyasu_diff.py:normalize"], ["_HALF_WIDTH", "decode_source"])

    def test_comment_only_change_reviews(self):
        _util.edit(self.path(DIFF), "    t = _NORMALIZE_BOLD.sub(r\"\\1\", t)          # 太字\n",
                   "    t = _NORMALIZE_BOLD.sub(r\"\\1\", t)          # 太字の印\n")
        self.assertReview(self.generate(), ["yomiyasu_diff.py:normalize"])

    def test_attached_statement_changed_reviews(self):
        _util.edit(self.path(DIFF), "_HALF_WIDTH[0x3000] = 0x20\n", "_HALF_WIDTH[0x3000] = 0x20  \n")
        self.assertReview(self.generate(), ["yomiyasu_diff.py:_HALF_WIDTH stmts 2→2"])

    def test_description_changed_reviews(self):
        _util.edit(self.path(SKILL), "意味と条件を保ち、", "意味と条件を保って、")
        self.assertReview(self.generate(), ["front_matter description from 0"], ["keep-meaning"])

    def test_copy_changed_reviews(self):
        with open(self.path("skills/yomiyasu/UNICODE-LICENSE.txt"), "a", encoding="utf-8") as handle:
            handle.write("\n")
        self.assertReview(self.generate(), ["copies[1]"])

    def test_own_text_changed_without_table_reviews(self):
        with open(os.path.join(self.repo, "extract", "own", "status.md"), "a", encoding="utf-8") as handle:
            handle.write("足した文です。\n")
        self.assertReview(self.generate(), ["SKILL.md part 9 status"])

    def test_accept_writes_and_updates_table(self):
        _util.edit(self.path(SKILL), "道具や概念に感情や意志を持たせている", "道具や概念に感情や意思を持たせている")
        self.assertEqual(self.generate().returncode, 3)
        done = self.generate("--accept")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("抽出表のハッシュを今の値に書き換えて", done.stdout)
        again = self.generate("--check")
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        with open(os.path.join(self.repo, "skills", "yomiyasu-mini", "SKILL.md"), encoding="utf-8") as handle:
            self.assertIn("感情や意思を持たせている", handle.read())

    # (g) コミットが違うと止まる
    def test_wrong_commit_stops(self):
        done = _util.generate("--source", self.tree, "--commit", "0" * 40, "--table", self.table)
        self.assertStopped(done, "COMMIT")

    def test_missing_commit_for_plain_copy_stops(self):
        done = _util.generate("--source", self.tree, "--table", self.table)
        self.assertStopped(done, "COMMIT", "--commit")

    def test_git_tree_with_other_head_stops(self):
        git = shutil.which("git")
        if not git:
            self.skipTest("git がありません")
        env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        for args in (["init", "-q"], ["add", "-A"],
                     ["-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-q", "-m", "copy"]):
            subprocess.run([git, "-C", self.tree] + args, check=True, env=env, stdout=subprocess.DEVNULL)
        done = _util.generate("--source", self.tree, "--table", self.table)
        self.assertStopped(done, "COMMIT", "HEAD")

    # Markdown の形
    def test_setext_heading_in_source_stops(self):
        _util.edit(self.path(SKILL), "### 比喩動詞の具体化\n", "下線の見出し\n---\n\n### 比喩動詞の具体化\n")
        self.assertStopped(self.generate(), "setext")

    def test_unclosed_fence_stops(self):
        with open(self.path(PR), "a", encoding="utf-8") as handle:
            handle.write("\n```\n閉じない囲み\n")
        self.assertStopped(self.generate(), "閉じていません")

    def test_bom_stops(self):
        with open(self.path(PR), "rb") as handle:
            data = handle.read()
        with open(self.path(PR), "wb") as handle:
            handle.write(b"\xef\xbb\xbf" + data)
        self.assertStopped(self.generate(), "BOM")


class FixtureTableStopTest(unittest.TestCase):
    """抽出表のほうを変えて止まることを確かめる。"""

    def setUp(self):
        self.main = _util.require_main(self)
        self.tree = _util.copy_main(self, self.main)
        self.repo = _util.copy_fixture(self)
        self.table_path = os.path.join(self.repo, "extract", "table.json")
        self.scripts_path = os.path.join(self.repo, "extract", "scripts.json")
        self.table = _util.load_json(self.table_path)
        self.scripts = _util.load_json(self.scripts_path)
        self.commit = self.table["source"]["commit"]

    def save(self):
        _util.write_json(self.table_path, self.table)
        _util.write_json(self.scripts_path, self.scripts)

    def generate(self, *extra):
        return _util.generate("--source", self.tree, "--commit", self.commit, "--table", self.table_path, *extra)

    def part(self, pid):
        for doc in self.table["documents"]:
            for part in doc["parts"]:
                if part["id"] == pid:
                    return part
        raise KeyError(pid)

    def own_file(self, name, text):
        path = os.path.join(self.repo, "extract", "own", name)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)

    def assertStopped(self, done, *needles):
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        for needle in needles:
            self.assertIn(needle, done.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "skills")))

    def test_lint_rule_name_left_in_reference_stops(self):
        self.part("pr")["substitutions"].pop(1)
        self.save()
        self.assertStopped(self.generate("--accept"), "REF", "bold_label_list", "本体 lint の規則の名前")

    def test_file_reference_left_stops(self):
        self.part("pr")["transforms"]["drop_lines"].pop(0)
        self.save()
        self.assertStopped(self.generate("--accept"), "REF", "domains/business.md")

    def test_bare_file_name_left_stops(self):
        self.part("pr")["substitutions"].pop(0)
        self.save()
        self.assertStopped(self.generate("--accept"), "REF", "audience.md")

    def test_main_tool_option_command_and_section_names_stop(self):
        self.own_file("status.md", "### 状態の行\n\n`yomiyasu_check.py run --stdin --fail-on meaning-risk` と「■ 意味が変わる恐れ」。\n")
        done = self.generate("--accept")
        self.assertStopped(done, "yomiyasu_check", "「run」", "--stdin", "--fail-on", "■ 意味が変わる恐れ")

    def test_missing_path_and_content_reference_stop(self):
        self.own_file("status.md", "### 状態の行\n\n`references/lists/hedges.txt` と SKILL.md「存在しない見出し」を見ます。\n")
        self.assertStopped(self.generate("--accept"), "references/lists/hedges.txt", "存在しない見出し")

    def test_skill_md_reference_needs_allow(self):
        self.own_file("status.md", "### 状態の行\n\nSKILL.md 2章 Step 1 の表を見ます。\n")
        self.assertStopped(self.generate("--accept"), "SKILL.md の中身への参照")
        self.table["reference_allow"] = [{"text": "SKILL.md 2章 Step 1 の表", "reason": "試験"}]
        self.save()
        done = self.generate("--accept")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_valid_content_reference_passes(self):
        self.own_file("status.md", "### 状態の行\n\nSKILL.md「最優先ルール: 意味の保持」と `references/doc-types.md` を見ます。\n")
        done = self.generate("--accept")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_forbidden_string_stops(self):
        self.own_file("status.md", "### 状態の行\n\nyomiyasu-check: executed と書かない。\n")
        self.assertStopped(self.generate("--accept"), "FORBIDDEN", "yomiyasu-check: executed")

    def test_unknown_key_stops(self):
        self.part("keep-meaning")["selecter"] = {"scope": "own"}
        self.save()
        self.assertStopped(self.generate(), "知らないキー", "selecter")

    def test_paragraph_selector_takes_only_that_paragraph(self):
        # 「Step 1: 文脈と段落の把握」の本文は空行で段落に分かれる（0: 判定の箇条書き、1: 種類の表）。表だけを選ぶ。
        part = self.part("subject-first")
        part["heading"] = {"level": 3, "text": "Step 1: 文脈と段落の把握", "parents": ["yomiyasu", "2. 実行手順"]}
        part["selector"] = {"paragraphs": [1, 1]}
        part.pop("sha256")
        self.save()
        done = self.generate("--accept")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        skill_path = os.path.join(self.tree, "skills", "yomiyasu", "SKILL.md")
        with open(skill_path, encoding="utf-8") as handle:
            lines = handle.read().split("\n")
        start = lines.index("### Step 1: 文脈と段落の把握") + 1
        while not lines[start]:
            start += 1
        blank = lines.index("", start)
        first, table_head, table_row = lines[start], lines[blank + 1], lines[blank + 3]
        self.assertTrue(table_head.lstrip().startswith("| 種類 |"), table_head)
        with open(os.path.join(self.repo, _util.OUTPUT_DIR, "SKILL.md"), encoding="utf-8") as handle:
            out = handle.read()
        self.assertIn(table_head + "\n", out)
        self.assertIn(table_row + "\n", out)
        self.assertNotIn(first, out)
        # 選んでいない段落を変えても見直しに出ない。選んだ段落を1字変えると終了コード3で、その part だけが出る。
        _util.edit(skill_path, first, first.replace("確認", "確かめ", 1))
        done = self.generate("--check")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        _util.edit(skill_path, table_row, table_row.replace("|", "| ", 1))
        done = self.generate()
        self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
        changed = [l for l in done.stdout.splitlines() if l.startswith("CHANGED")]
        self.assertEqual(len(changed), 1, done.stdout)
        self.assertIn("subject-first", changed[0])

    def test_paragraph_out_of_range_stops(self):
        self.part("subject-first")["selector"] = {"paragraphs": [1, 1]}
        self.save()
        self.assertStopped(self.generate("--accept"), "MISSING paragraph")

    def test_wrong_substitution_count_stops(self):
        self.part("subject-third")["substitutions"][0]["count"] = 2
        self.save()
        self.assertStopped(self.generate("--accept"), "COUNT")

    def test_heading_shift_out_of_range_stops(self):
        self.part("pr")["transforms"]["heading_shift"] = -1
        self.save()
        self.assertStopped(self.generate("--accept"), "heading_shift")

    def test_duplicate_output_heading_stops(self):
        self.own_file("doc-types-head.md", "# 文書の種類\n\n## PR説明（pr）\n\n重なる見出し。\n")
        self.assertStopped(self.generate("--accept"), "見出しで指せなくなります")

    def test_scripts_source_mismatch_stops(self):
        self.scripts["source"]["commit"] = "1" * 40
        self.save()
        self.assertStopped(self.generate(), "scripts.json の source が抽出表と違います")

    def test_unicode_notice_required(self):
        self.scripts["scripts"][0]["notice"] = None
        self.save()
        self.assertStopped(self.generate(), "NOTICE", "_EMOJI_DATA_VERSION")

    def test_unicode_license_copy_required(self):
        self.table["copies"] = [c for c in self.table["copies"] if c["output"] != "UNICODE-LICENSE.txt"]
        self.table["file_budget"] -= 1
        self.save()
        self.assertStopped(self.generate(), "NOTICE", "UNICODE-LICENSE.txt")

    def test_missing_root_stops(self):
        self.scripts["scripts"][0]["roots"].append({"module": "diff", "name": "_no_such_name"})
        self.save()
        self.assertStopped(self.generate(), "MISSING name", "_no_such_name")

    def test_name_from_skipped_statement_stops(self):
        self.scripts["scripts"][0]["roots"].append({"module": "diff", "name": "_IMPORT_ERROR"})
        self.save()
        self.assertStopped(self.generate(), "_IMPORT_ERROR")

    def test_old_version_form_stops(self):
        # mini の版は 1.0.0 の形。依頼書の 2.1.1-r1 の形は使わない（DECISIONS.md 9章）。
        for value in ("2.1.1-r1", "1.0", "v1.0.0", "01.0.0"):
            self.table["version"] = value
            self.scripts["version"] = value
            self.save()
            self.assertStopped(self.generate(), "FORMAT", value)

    def test_source_tag_must_match_main_version(self):
        # 本体の木の SKILL.md の metadata.version と source の tag が合わなければ止める（mini の版とは別）。
        self.table["source"]["tag"] = "v2.1.0"
        self.scripts["source"]["tag"] = "v2.1.0"
        self.save()
        self.assertStopped(self.generate(), "SOURCE", "v2.1.0")

    def test_version_clash_stops(self):
        self.scripts["scripts"][0]["roots"].append({"module": "diff", "name": "__version__"})
        self.save()
        self.assertStopped(self.generate(), "CLASH", "__version__")

    def test_script_over_limit_stops(self):
        self.scripts["scripts"][0]["packing"]["max_bytes"] = 1000
        self.save()
        self.assertStopped(self.generate(), "LIMIT", "上限の 1,000バイト")

    def test_skill_md_over_limit_stops(self):
        self.own_file("intro.md", "# yomiyasu-mini\n\n" + "あ" * 18001 + "\n")
        self.assertStopped(self.generate("--accept"), "LIMIT", "18,000")

    def test_file_budget_exceeded_stops(self):
        self.table["file_budget"] = 3
        self.save()
        self.assertStopped(self.generate(), "LIMIT", "file_budget")


class RealTableStopTest(unittest.TestCase):
    """本番の抽出表が見出しで指す節を1つずつ消すと、毎回止まる。"""

    def test_each_heading_removed_stops(self):
        main = _util.require_main(self)
        table = _util.require_real_table(self)
        headings = _util.headings_in_table(_util.table_files(table))
        self.assertTrue(headings, "本番の抽出表に見出しで指す part がありません")
        commit = _util.table_commit(table)
        for source, level, text, _parents in headings:
            with self.subTest(heading=text):
                tree = _util.copy_main(self, main, whole=True)
                out = _util.temp_dir(self)
                _util.remove_heading(os.path.join(tree, source), level, text)
                done = _util.generate("--source", tree, "--commit", commit, "--table", table, "--out", out)
                self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
                self.assertIn(text, done.stderr)
                self.assertEqual(os.listdir(out), [])


if __name__ == "__main__":
    unittest.main()
