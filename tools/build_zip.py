#!/usr/bin/env python3
"""Agent Builder に上げる .zip を、配る一式（skills/yomiyasu-mini/）から作る。

使い方:
  python3 -B tools/build_zip.py [--root <リポジトリ>] --out dist/yomiyasu-mini-1.1.0.zip

- 入れるのは MANIFEST.json の files のうち、output_dir（skills/yomiyasu-mini/）の下にあるものだけ。
  フォルダにほかのファイル（__pycache__、.DS_Store を含む）があるか、中身が MANIFEST.json の sha256 と違えば止める。
- 項目の名前は「yomiyasu-mini/<フォルダの中のパス>」で、パスの順に並べる。フォルダの項目は入れない。
- 圧縮しない（ZIP_STORED）。時刻は 1980-01-01 00:00:00、create_system は 3、属性は 0644 に固める。
  同じ中身からは、いつ作っても同じバイトになる。
- zip のコメントに版と本体のタグとコミットを入れる。
- 作る前と作ったあとに、tools/limits.py の上限を確かめる。
終了コード: 0 作った、2 止めた（何も書いていない）。
"""
import argparse
import hashlib
import io
import json
import os
import sys
import zipfile

sys.dont_write_bytecode = True

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(TOOLS_DIR)
PROG = "yomiyasu-mini build_zip"
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def _load_limits():
    name = "yomiyasu_mini_limits"
    if name in sys.modules:
        return sys.modules[name]
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, os.path.join(TOOLS_DIR, "limits.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


limits = _load_limits()


def collect(root):
    """MANIFEST.json と配る一式を照らし、(zip の先頭のフォルダの名前, [(フォルダの中のパス, バイト列)], コメント, 問題)。"""
    problems = []
    manifest_path = os.path.join(root, "MANIFEST.json")
    try:
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError) as error:
        return None, [], "", ["MANIFEST.json を読めません（{}）。先に tools/generate.py で生成してください。".format(error)]
    if manifest.get("format") != "yomiyasu-mini-manifest":
        return None, [], "", ["MANIFEST.json の format が yomiyasu-mini-manifest ではありません。"]
    if manifest.get("measure_variant"):
        return None, [], "", ["測定用の写し（measure_variant）からは .zip を作りません。"]
    output_dir = manifest.get("output_dir", "")
    prefix = output_dir.rstrip("/") + "/"
    root_name = output_dir.rstrip("/").split("/")[-1]
    listed = {}
    for item in manifest.get("files", []):
        path = item.get("path", "")
        if path.startswith(prefix):
            listed[path[len(prefix):]] = item
    bundle_dir = os.path.join(root, output_dir)
    files, read_problems = limits.read_bundle(bundle_dir)
    problems += read_problems
    for rel in sorted(set(files) - set(listed)):
        problems.append("{}{} は MANIFEST.json にありません（__pycache__ や .DS_Store も入れません）。".format(prefix, rel))
    for rel in sorted(set(listed) - set(files)):
        problems.append("{}{} がありません。".format(prefix, rel))
    for rel in sorted(set(files) & set(listed)):
        if hashlib.sha256(files[rel]).hexdigest() != listed[rel].get("sha256"):
            problems.append("{}{} の中身が MANIFEST.json の sha256 と違います。生成し直してください。".format(prefix, rel))
    source = manifest.get("source", {})
    comment = "{} {}; {} {} {}".format(root_name, manifest.get("version"), source.get("repository"),
                                       source.get("tag"), source.get("commit"))
    entries = sorted(((rel, files[rel]) for rel in files if rel in listed), key=lambda x: x[0].encode("utf-8"))
    return root_name, entries, comment, problems


def build(root_name, entries, comment):
    """決まった形の .zip のバイト列を作る。"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.comment = comment.encode("utf-8")
        for rel, data in entries:
            info = zipfile.ZipInfo(root_name + "/" + rel, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return buffer.getvalue()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="build_zip.py", description="Agent Builder に上げる .zip を作ります。")
    parser.add_argument("--root", default=REPO_DIR, metavar="リポジトリ",
                        help="MANIFEST.json と skills/yomiyasu-mini/ があるフォルダ。既定はこのリポジトリ。")
    parser.add_argument("--out", required=True, metavar="出力の .zip")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    root_name, entries, comment, problems = collect(os.path.realpath(args.root))
    if root_name is not None:
        problems += limits.files_problems(dict(entries), root_name)
    if problems:
        print("{}: 止めました。何も書いていません。".format(PROG), file=sys.stderr)
        for line in problems:
            print(line, file=sys.stderr)
        return 2
    data = build(root_name, entries, comment)
    if len(data) > limits.ZIP_MAX_BYTES:
        print("{}: .zip が {:,}バイトになり、上限を超えます。何も書いていません。".format(PROG, len(data)), file=sys.stderr)
        return 2
    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    temp = out + ".tmp-build-zip"
    with open(temp, "wb") as handle:
        handle.write(data)
    after = limits.zip_problems(temp, root_name)
    if after:
        os.remove(temp)
        print("{}: 作った .zip が上限に合いません。消しました。".format(PROG), file=sys.stderr)
        for line in after:
            print(line, file=sys.stderr)
        return 2
    os.replace(temp, out)
    print("{}: {} を作りました（{}個、{:,}バイト、sha256 {}）。".format(
        PROG, out, len(entries), len(data), hashlib.sha256(data).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
