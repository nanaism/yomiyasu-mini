"""試験で共通に使うもの（tests/ はパッケージにしないので、各試験は `import _util` で読む）。

本体の木の場所: 環境変数 YOMIYASU_MAIN（CI では _main）。なければリポジトリ直下の _main/ を使う。
どちらもなければ、本体の木が要る試験は飛ばす。YOMIYASU_REQUIRE_MAIN=1 のときは、飛ばさずに失敗にする
（CI で試験が飛ばされたまま通らないようにするため）。
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
TOOLS = os.path.join(REPO, "tools")
FIXTURES = os.path.join(TESTS, "fixtures")
GENERATE = os.path.join(TOOLS, "generate.py")
BUILD_ZIP = os.path.join(TOOLS, "build_zip.py")
REAL_TABLE = os.path.join(REPO, "extract", "table.json")
OUTPUT_DIR = "skills/yomiyasu-mini"


def main_tree():
    for candidate in (os.environ.get("YOMIYASU_MAIN"), os.path.join(REPO, "_main")):
        if candidate and os.path.isfile(os.path.join(candidate, "skills", "yomiyasu", "SKILL.md")):
            return os.path.realpath(candidate)
    return None


def require_main(test):
    """本体の木を返す。なければ飛ばす（YOMIYASU_REQUIRE_MAIN=1 なら失敗にする）。"""
    tree = main_tree()
    if tree is None:
        message = "本体の木がありません。環境変数 YOMIYASU_MAIN に、取り出したフォルダを指定してください。"
        if os.environ.get("YOMIYASU_REQUIRE_MAIN") == "1":
            test.fail(message)
        raise unittest.SkipTest(message)
    return tree


def require_real_table(test):
    """リポジトリの抽出表（extract/table.json）がなければ飛ばす。"""
    if not os.path.isfile(REAL_TABLE):
        raise unittest.SkipTest("extract/table.json がまだないので、本番の抽出表の試験を飛ばします。")
    return REAL_TABLE


_REAL_OUTPUT = {}


def real_output(test):
    """本番の抽出表から一時フォルダに生成し、その根（MANIFEST.json と skills/yomiyasu-mini/ があるフォルダ）を返す。

    1つの試験の実行の中では1回だけ生成して使い回す。コミット済みの生成物がまだなくても、抽出表が作るものの
    上限と zip を確かめられるようにするため。本体の木か抽出表がなければ飛ばす。
    """
    tree = require_main(test)
    table = require_real_table(test)
    if "root" not in _REAL_OUTPUT:
        root = os.path.realpath(tempfile.mkdtemp(prefix="yomiyasu-mini-real-"))
        import atexit
        atexit.register(shutil.rmtree, root, True)
        done = generate("--source", tree, "--commit", table_commit(table), "--table", table, "--out", root)
        _REAL_OUTPUT["root"] = root
        _REAL_OUTPUT["done"] = done
    done = _REAL_OUTPUT["done"]
    if done.returncode != 0:
        test.fail("本番の抽出表から生成できませんでした（終了コード {}）。\n{}{}".format(
            done.returncode, done.stdout, done.stderr))
    return _REAL_OUTPUT["root"]


def require_committed_output(test):
    """コミットする生成物（skills/yomiyasu-mini/ と MANIFEST.json）がまだなければ飛ばす。

    YOMIYASU_REQUIRE_MAIN=1（CI）のときは、飛ばさずに失敗にする。
    """
    missing = [p for p in (os.path.join(REPO, OUTPUT_DIR), os.path.join(REPO, "MANIFEST.json"))
               if not os.path.exists(p)]
    if missing:
        message = ("extract/table.json はありますが、生成物（{}）がまだありません。"
                   "python3 -B tools/generate.py --source <本体の木> で生成してから回してください。").format(
            "、".join(os.path.relpath(p, REPO) for p in missing))
        if os.environ.get("YOMIYASU_REQUIRE_MAIN") == "1":
            test.fail(message)
        raise unittest.SkipTest(message)


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, obj):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def load_tool(name):
    """tools/ の道具をモジュールとして読む（tools/ はパッケージにしない）。"""
    key = "yomiyasu_mini_" + name
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, os.path.join(TOOLS, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[key] = module
    spec.loader.exec_module(module)
    return module


def temp_dir(test, prefix="yomiyasu-mini-test-"):
    path = os.path.realpath(tempfile.mkdtemp(prefix=prefix))
    test.addCleanup(shutil.rmtree, path, True)
    return path


def table_commit(table_path):
    return load_json(table_path)["source"]["commit"]


def copy_main(test, tree, whole=False):
    """本体の木を、.git を除いて一時フォルダに写す。whole=False なら skills/ だけ。写しの根を返す。"""
    dest = os.path.join(temp_dir(test, "yomiyasu-main-copy-"), "tree")
    ignore = shutil.ignore_patterns(".git", "__pycache__", "*.pyc")
    if whole:
        shutil.copytree(tree, dest, ignore=ignore)
    else:
        os.makedirs(dest)
        shutil.copytree(os.path.join(tree, "skills"), os.path.join(dest, "skills"), ignore=ignore)
    return dest


def copy_fixture(test, name="basic", expected=False):
    """試験用の抽出表（tests/fixtures/<name>/extract）を一時フォルダに写す。expected なら生成物の見本も写す。"""
    root = os.path.join(temp_dir(test, "yomiyasu-mini-fixture-"), "repo")
    shutil.copytree(os.path.join(FIXTURES, name, "extract"), os.path.join(root, "extract"))
    if expected:
        src = os.path.join(FIXTURES, name, "expected")
        for entry in sorted(os.listdir(src)):
            full = os.path.join(src, entry)
            if os.path.isdir(full):
                shutil.copytree(full, os.path.join(root, entry))
            else:
                shutil.copy2(full, os.path.join(root, entry))
    return root


def run(script, *args, cwd=None):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-I", "-B", script] + [str(a) for a in args], cwd=cwd or REPO, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                          encoding="utf-8", timeout=600)


def generate(*args, cwd=None):
    return run(GENERATE, *args, cwd=cwd)


def build_zip(*args, cwd=None):
    return run(BUILD_ZIP, *args, cwd=cwd)


def read_tree(root):
    """フォルダの中のファイルを {/ 区切りのパス: バイト列} にする。"""
    out = {}
    for current, dirs, names in os.walk(root):
        dirs.sort()
        for name in sorted(names):
            full = os.path.join(current, name)
            with open(full, "rb") as handle:
                out[os.path.relpath(full, root).replace(os.sep, "/")] = handle.read()
    return out


def edit(path, old, new, count=1):
    """ファイルの中の old を new に置き換える。old がちょうど count か所になければ試験の誤り。"""
    with open(path, encoding="utf-8", newline="") as handle:
        text = handle.read()
    found = text.count(old)
    if found != count:
        raise AssertionError("{} に「{}」が {}か所あり、{}か所ではありません".format(path, old, found, count))
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text.replace(old, new))


def remove_heading(path, level, text):
    """見出しの行（「#」がレベルの数だけ並ぶ行）を1つ消す。ちょうど1行でなければ試験の誤り。"""
    with open(path, encoding="utf-8", newline="") as handle:
        lines = handle.read().split("\n")
    target = "#" * level + " " + text
    found = [i for i, line in enumerate(lines) if line.rstrip() == target]
    if len(found) != 1:
        raise AssertionError("{} に見出しの行「{}」が {}行あります".format(path, target, len(found)))
    del lines[found[0]]
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write("\n".join(lines))


def headings_in_table(table_paths):
    """抽出表が見出しで指している (source, level, text, parents) をすべて集める（重なりなし、表の順）。"""
    out = []

    def visit(obj):
        if isinstance(obj, dict):
            if isinstance(obj.get("heading"), dict) and isinstance(obj.get("source"), str):
                h = obj["heading"]
                key = (obj["source"], h["level"], h["text"], tuple(h.get("parents", [])))
                if key not in out:
                    out.append(key)
            for value in obj.values():
                visit(value)
        elif isinstance(obj, list):
            for value in obj:
                visit(value)

    for path in table_paths:
        visit(load_json(path))
    return out


def table_files(table_path):
    """抽出表と include のファイルのパス。"""
    table = load_json(table_path)
    folder = os.path.dirname(table_path)
    return [table_path] + [os.path.join(folder, name) for name in table.get("include", [])]
