"""Agent Builder に上げる .zip の試験（tools/build_zip.py）。

2回作ると同じバイトになること、項目の並び、時刻、圧縮しないこと、先頭のフォルダ、中身が配る一式と同じこと、
README のロゴ（assets/）、拡張子のない LICENSE、MANIFEST.json が入らないことを確かめる。
"""
import hashlib
import json
import os
import sys
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _util  # noqa: E402

limits = _util.load_tool("limits")

# 試験用の見本（tests/fixtures/basic/expected）から作った .zip の sha256。Python 3.9 と 3.14 で同じになる。
# 見本を作り直したら、この値も書き換える。
FIXTURE_ZIP_SHA256 = "3908de2e889b537dc3d9d2736b33786596a32f2c31008b91e674d38d1ed13e78"


class ZipCheck:
    """root（MANIFEST.json と skills/yomiyasu-mini/ があるフォルダ）を持つクラスで使う。"""

    def build(self, name):
        out = os.path.join(_util.temp_dir(self), name)
        done = _util.build_zip("--root", self.root, "--out", out)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        with open(out, "rb") as handle:
            return out, handle.read()

    def test_twice_same_bytes(self):
        _, a = self.build("a.zip")
        _, b = self.build("b.zip")
        self.assertEqual(hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest())
        self.assertEqual(a, b)

    def test_entries(self):
        path, data = self.build("a.zip")
        self.assertLessEqual(len(data), limits.ZIP_MAX_BYTES)
        self.assertEqual(limits.zip_problems(path, "yomiyasu-mini"), [])
        bundle = _util.read_tree(os.path.join(self.root, _util.OUTPUT_DIR))
        manifest = _util.load_json(os.path.join(self.root, "MANIFEST.json"))
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [i.filename for i in infos]
            self.assertEqual(names, sorted(names, key=lambda n: n.encode("utf-8")))
            self.assertEqual(names, ["yomiyasu-mini/" + p for p in sorted(bundle, key=lambda n: n.encode("utf-8"))])
            for info in infos:
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                self.assertEqual(info.create_system, 3)
                self.assertEqual(info.external_attr >> 16, 0o100644)
                self.assertFalse(info.is_dir())
                self.assertEqual(archive.read(info), bundle[info.filename[len("yomiyasu-mini/"):]])
            comment = archive.comment.decode("utf-8")
        self.assertEqual(comment, "yomiyasu-mini {}; {} {} {}".format(
            manifest["version"], manifest["source"]["repository"], manifest["source"]["tag"],
            manifest["source"]["commit"]))
        for name in names:
            self.assertNotIn("assets/", name)
            self.assertNotEqual(name.split("/")[-1], "MANIFEST.json")
            self.assertNotEqual(name.split("/")[-1], "LICENSE")
            self.assertLessEqual(len(name.split("/")), limits.MAX_DEPTH)
        self.assertIn("yomiyasu-mini/SKILL.md", names)


class FixtureZipTest(ZipCheck, unittest.TestCase):
    def setUp(self):
        self.root = _util.copy_fixture(self, expected=True)

    def test_known_bytes(self):
        _, data = self.build("a.zip")
        self.assertEqual(hashlib.sha256(data).hexdigest(), FIXTURE_ZIP_SHA256)

    def test_extra_file_stops(self):
        with open(os.path.join(self.root, _util.OUTPUT_DIR, ".DS_Store"), "wb") as handle:
            handle.write(b"x")
        out = os.path.join(_util.temp_dir(self), "a.zip")
        done = _util.build_zip("--root", self.root, "--out", out)
        self.assertEqual(done.returncode, 2)
        self.assertIn(".DS_Store", done.stderr)
        self.assertFalse(os.path.exists(out))

    def test_edited_file_stops(self):
        with open(os.path.join(self.root, _util.OUTPUT_DIR, "SKILL.md"), "a", encoding="utf-8") as handle:
            handle.write("手で足した行\n")
        out = os.path.join(_util.temp_dir(self), "a.zip")
        done = _util.build_zip("--root", self.root, "--out", out)
        self.assertEqual(done.returncode, 2)
        self.assertIn("sha256", done.stderr)
        self.assertFalse(os.path.exists(out))

    def test_measure_variant_is_refused(self):
        path = os.path.join(self.root, "MANIFEST.json")
        manifest = _util.load_json(path)
        manifest["measure_variant"] = True
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle)
        done = _util.build_zip("--root", self.root, "--out", os.path.join(_util.temp_dir(self), "a.zip"))
        self.assertEqual(done.returncode, 2)

    def test_missing_manifest_stops(self):
        os.remove(os.path.join(self.root, "MANIFEST.json"))
        done = _util.build_zip("--root", self.root, "--out", os.path.join(_util.temp_dir(self), "a.zip"))
        self.assertEqual(done.returncode, 2)
        self.assertIn("MANIFEST.json", done.stderr)


class RealZipTest(ZipCheck, unittest.TestCase):
    """本番の抽出表から一時フォルダに生成したものから作る .zip。抽出表がまだなければ飛ばす。"""

    def setUp(self):
        self.root = _util.real_output(self)


class CommittedZipTest(ZipCheck, unittest.TestCase):
    """コミットする生成物（リポジトリの skills/yomiyasu-mini/ と MANIFEST.json）から作る .zip。CI と同じ形。"""

    def setUp(self):
        _util.require_real_table(self)
        _util.require_committed_output(self)
        self.root = _util.REPO


if __name__ == "__main__":
    unittest.main()
