"""Claude Code のプラグインとして入れるための設定（.claude-plugin/）の試験。

plugin.json と marketplace.json の名前とバージョンが抽出表（extract/table.json）の mini とそろっていること、
プラグインが読むスキルのフォルダに配る SKILL.md があることを確かめる。バージョンを上げたときの書き忘れを止める。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _util  # noqa: E402

PLUGIN = os.path.join(_util.REPO, ".claude-plugin", "plugin.json")
MARKETPLACE = os.path.join(_util.REPO, ".claude-plugin", "marketplace.json")


class PluginManifestTest(unittest.TestCase):
    def setUp(self):
        self.table = _util.load_json(_util.REAL_TABLE)
        self.plugin = _util.load_json(PLUGIN)
        self.marketplace = _util.load_json(MARKETPLACE)
        entries = [p for p in self.marketplace.get("plugins", []) if p.get("name") == "yomiyasu-mini"]
        self.assertEqual(len(entries), 1, "marketplace.json に yomiyasu-mini の項目が1つだけあること")
        self.entry = entries[0]

    def test_versions_match_the_table(self):
        version = self.table["version"]
        self.assertEqual(self.plugin["version"], version, "plugin.json の version を抽出表の version とそろえる")
        self.assertEqual(self.entry["version"], version, "marketplace.json の version を抽出表の version とそろえる")

    def test_names(self):
        self.assertEqual(self.plugin["name"], "yomiyasu-mini")
        self.assertEqual(self.marketplace["name"], "yomiyasu-mini")

    def test_plugin_reads_the_shipped_skill(self):
        self.assertEqual(self.entry["source"], "./")
        skills = os.path.normpath(os.path.join(_util.REPO, self.plugin["skills"]))
        self.assertEqual(skills, os.path.join(_util.REPO, "skills"))
        self.assertTrue(os.path.isfile(os.path.join(_util.REPO, _util.OUTPUT_DIR, "SKILL.md")))


if __name__ == "__main__":
    unittest.main()
