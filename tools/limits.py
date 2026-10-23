#!/usr/bin/env python3
"""yomiyasu-mini の配る一式の上限と、上限を確かめる関数。

generate.py、build_zip.py、tests/test_limits.py が同じ値を使う。標準ライブラリだけで動き、外へ通信しない。
どの関数も、問題を日本語の1行ずつのリストで返す（問題がなければ空のリスト）。

値の出どころ:
- Microsoft の文書（宣言型エージェントのカスタムスキル）の上限: SKILL.md の指示は2万字未満、.zip は50MBまで、
  1ファイルは25MBまで、ファイルはすべてのスキルを合わせて350個まで、フォルダの深さは3まで。
- 設計の目安: SKILL.md はファイル全体で18,000字以下、スクリプトは1本90KB以下。
- 設計の決め: front matter は500字以内、description は280字以内。
- 自前の目安: references/ の参照ファイルは1本100,000バイト以下（Microsoft の上限ではない。v2.2.2 から作り直したときに決めた）。
KB と MB は10進で数える（90KB は 90,000 バイト、25MB は 25,000,000 バイト）。字は Python の len で数える。
"""
import ast
import os
import re
import sys

sys.dont_write_bytecode = True

SKILL_MD_MAX_CHARS = 18000          # SKILL.md のファイル全体（front matter を含む）
SKILL_MD_BODY_LIMIT = 20000         # front matter を除いた本文はこれ未満（Microsoft の上限）
FRONT_MATTER_MAX_CHARS = 500        # --- から --- までを含む
DESCRIPTION_MAX_CHARS = 280
DESCRIPTION_SPEC_MAX_CHARS = 1024   # Agent Skills の規約
NAME_MAX_CHARS = 64
SCRIPT_MAX_BYTES = 90000            # .py 1本
REFERENCE_MAX_BYTES = 100000        # references/ の参照ファイル1本
FILE_MAX_BYTES = 25000000           # どのファイルも
ZIP_MAX_BYTES = 50000000
MAX_FILES_TOTAL = 350               # すべてのスキルを合わせた数の上限
MAX_DEPTH = 3                       # .zip の中のパスの段数（先頭のフォルダとファイル名を含める）
# 配る一式に置いてよい拡張子。拡張子のないファイル（LICENSE など）は Agent Builder に上げられないので入れない。
ALLOWED_EXTENSIONS = (".csv", ".json", ".md", ".py", ".txt", ".yaml")
FILE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# スクリプトで使わないモジュール（ネットワークと別のプロセス）
FORBIDDEN_IMPORTS = ("ftplib", "http", "smtplib", "socket", "ssl", "subprocess", "urllib", "xmlrpc")
# README に書かないこと（README には設計の狙いと測った数字だけを書く）。正規表現と、その理由。
README_FORBIDDEN = (
    (r"claude\.ai", "claude.ai で使えるとは書かない"),
    (r"未確認", "「未確認」と書かない"),
    (r"確かめていません|確認していません|試していません", "確かめていないことを書かない"),
    (r"予定|今後|近いうちに", "今後の予定や約束を書かない"),
    (r"\d{4}\s*年\s*\d{1,2}\s*月|\d{4}-\d{2}-\d{2}|\d{4}/\d{1,2}/\d{1,2}", "日付を書かない"),
    (r"Copilot\s*(で|でも)\s*(動|使え)", "試していない環境で動くとは書かない"),
    (r"Co-Authored-By|Generated with", "AI の署名を書かない"),
)
STATUS_PREFIX = "yomiyasu-mini-check:"


def split_front_matter(text):
    """先頭の --- から --- までと、そのあとの本文に分ける。front matter がなければ (None, text)。"""
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 3)
    if end < 0:
        if text.endswith("\n---"):
            return text, ""
        return None, text
    return text[:end + 5], text[end + 5:]


def parse_front_matter(block):
    """front matter の簡単な読み取り。最上位の「キー: 値」と、metadata の下の「  キー: 値」だけを読む。"""
    result = {}
    metadata = None
    for line in block.split("\n")[1:]:
        if line == "---" or not line.strip():
            continue
        if line.startswith("  ") and metadata is not None:
            key, _, value = line.strip().partition(":")
            metadata[key.strip()] = _unquote(value.strip())
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if key == "metadata" and value == "":
            metadata = {}
            result["metadata"] = metadata
        else:
            metadata = None
            result[key] = _unquote(value)
    return result


def _unquote(value):
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1]
    return value


def skill_md_problems(text, expected_name=None):
    """SKILL.md の字数と front matter の形を確かめる。"""
    problems = []
    if len(text) > SKILL_MD_MAX_CHARS:
        problems.append("SKILL.md が {:,}字あり、上限の {:,}字を超えています。".format(len(text), SKILL_MD_MAX_CHARS))
    block, body = split_front_matter(text)
    if block is None:
        problems.append("SKILL.md の先頭に front matter（--- から ---）がありません。")
        return problems
    if len(body) >= SKILL_MD_BODY_LIMIT:
        problems.append("SKILL.md の本文が {:,}字あり、{:,}字未満になっていません。".format(len(body), SKILL_MD_BODY_LIMIT))
    if len(block) > FRONT_MATTER_MAX_CHARS:
        problems.append("front matter が {}字あり、{}字を超えています。".format(len(block), FRONT_MATTER_MAX_CHARS))
    fm = parse_front_matter(block)
    name = fm.get("name", "")
    if not SKILL_NAME_RE.match(name) or len(name) > NAME_MAX_CHARS:
        problems.append("front matter の name「{}」が小文字の英数字とハイフンの形（64字以内）になっていません。".format(name))
    if expected_name is not None and name != expected_name:
        problems.append("front matter の name「{}」がフォルダの名前「{}」と違います。".format(name, expected_name))
    description = fm.get("description", "")
    if not description:
        problems.append("front matter に description がありません。")
    if len(description) > DESCRIPTION_MAX_CHARS:
        problems.append("description が {}字あり、{}字を超えています。".format(len(description), DESCRIPTION_MAX_CHARS))
    if len(description) > DESCRIPTION_SPEC_MAX_CHARS:
        problems.append("description が {}字を超えています。".format(DESCRIPTION_SPEC_MAX_CHARS))
    if "<" in description or ">" in description:
        problems.append("description に < か > があります。")
    if fm.get("license") != "MIT":
        problems.append("front matter の license が MIT ではありません。")
    metadata = fm.get("metadata")
    if not isinstance(metadata, dict) or not metadata.get("version"):
        problems.append("front matter の metadata に version がありません。")
    else:
        for key in ("source-repository", "source-tag", "source-commit"):
            if not metadata.get(key):
                problems.append("front matter の metadata に {} がありません。".format(key))
    return problems


def script_problems(text, name="script.py"):
    """スクリプト1本の大きさ、import、構文を確かめる。text は str。"""
    problems = []
    size = len(text.encode("utf-8"))
    if size > SCRIPT_MAX_BYTES:
        problems.append("{} が {:,}バイトあり、上限の {:,}バイトを超えています。".format(name, size, SCRIPT_MAX_BYTES))
    try:
        tree = ast.parse(text, name)
    except SyntaxError as error:
        problems.append("{} を Python {}.{} で読めません（{}）。".format(
            name, sys.version_info[0], sys.version_info[1], error.msg))
        return problems
    stdlib = getattr(sys, "stdlib_module_names", None)
    for module in sorted(imported_modules(tree)):
        if module in FORBIDDEN_IMPORTS:
            problems.append("{} が {} を読み込んでいます（ネットワークと別のプロセスは使いません）。".format(name, module))
        elif stdlib is not None and module not in stdlib:
            problems.append("{} が標準ライブラリにない {} を読み込んでいます。".format(name, module))
    return problems


def imported_modules(tree):
    """import と from ... import の最上位のモジュールの名前の集合。相対の import は含めない。"""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out.add(node.module.split(".")[0])
    return out


def files_problems(files, root_name, file_budget=None, exact_budget=False):
    """配る一式のファイルを確かめる。files は {フォルダの中のパス（/ 区切り）: バイト列}。

    root_name は .zip の中の先頭のフォルダの名前（yomiyasu-mini）。深さはこのフォルダとファイル名を含めて数える。"""
    problems = []
    count = len(files)
    if count > MAX_FILES_TOTAL:
        problems.append("ファイルが {}個あり、上限の {}個を超えています。".format(count, MAX_FILES_TOTAL))
    if file_budget is not None:
        if exact_budget and count != file_budget:
            problems.append("ファイルが {}個あり、決めた数（file_budget）の {}個と違います。".format(count, file_budget))
        elif count > file_budget:
            problems.append("ファイルが {}個あり、決めた数（file_budget）の {}個を超えています。".format(count, file_budget))
    if "SKILL.md" not in files:
        problems.append("SKILL.md がフォルダの直下にありません。")
    for path in sorted(files):
        data = files[path]
        parts = path.split("/")
        depth = len([root_name] + parts)
        if depth > MAX_DEPTH:
            problems.append("{} の深さが {}段あり、上限の {}段を超えています。".format(path, depth, MAX_DEPTH))
        for part in parts:
            if not FILE_NAME_RE.match(part) or part.startswith("."):
                problems.append("{} の名前に、英数字と . _ - 以外の字があるか、ドットで始まる部分があります。".format(path))
                break
        ext = os.path.splitext(parts[-1])[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            problems.append("{} の拡張子は配る一式に置けません（置けるのは {}）。".format(path, "、".join(ALLOWED_EXTENSIONS)))
        if len(data) > FILE_MAX_BYTES:
            problems.append("{} が {:,}バイトあり、上限の {:,}バイトを超えています。".format(path, len(data), FILE_MAX_BYTES))
        if parts[0] == "references" and len(data) > REFERENCE_MAX_BYTES:
            problems.append("{} が {:,}バイトあり、参照ファイルの目安の {:,}バイトを超えています。".format(
                path, len(data), REFERENCE_MAX_BYTES))
        if ext == ".py":
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                problems.append("{} が UTF-8 で読めません。".format(path))
                continue
            problems.extend(script_problems(text, path))
        if path == "SKILL.md":
            try:
                problems.extend(skill_md_problems(data.decode("utf-8"), root_name))
            except UnicodeDecodeError:
                problems.append("SKILL.md が UTF-8 で読めません。")
    return problems


def read_bundle(bundle_dir):
    """フォルダの中のファイルを {パス: バイト列} にする。シンボリックリンクとファイルでないものは問題として返す。"""
    files = {}
    problems = []
    for current, dirs, names in os.walk(bundle_dir):
        dirs.sort()
        for d in list(dirs):
            full = os.path.join(current, d)
            if os.path.islink(full):
                problems.append("{} はシンボリックリンクです。".format(os.path.relpath(full, bundle_dir)))
                dirs.remove(d)
        for name in sorted(names):
            full = os.path.join(current, name)
            rel = os.path.relpath(full, bundle_dir).replace(os.sep, "/")
            if os.path.islink(full) or not os.path.isfile(full):
                problems.append("{} はふつうのファイルではありません（シンボリックリンクなど）。".format(rel))
                continue
            with open(full, "rb") as handle:
                files[rel] = handle.read()
    return files, problems


def bundle_problems(bundle_dir, root_name=None, file_budget=None, exact_budget=False):
    """フォルダの配る一式を確かめる。"""
    root_name = root_name or os.path.basename(os.path.normpath(bundle_dir))
    files, problems = read_bundle(bundle_dir)
    return problems + files_problems(files, root_name, file_budget, exact_budget)


def zip_problems(path, root_name):
    """作った .zip を確かめる。"""
    import zipfile
    problems = []
    size = os.path.getsize(path)
    if size > ZIP_MAX_BYTES:
        problems.append(".zip が {:,}バイトあり、上限の {:,}バイトを超えています。".format(size, ZIP_MAX_BYTES))
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if names != sorted(names):
            problems.append(".zip の項目がパスの順に並んでいません。")
        files = {}
        for info in infos:
            if info.is_dir() or info.filename.endswith("/"):
                problems.append(".zip にフォルダの項目 {} があります。".format(info.filename))
                continue
            if not info.filename.startswith(root_name + "/"):
                problems.append(".zip の項目 {} が {}/ の下にありません。".format(info.filename, root_name))
                continue
            if info.file_size > FILE_MAX_BYTES:
                problems.append(".zip の項目 {} が {:,}バイトあり、上限を超えています。".format(info.filename, info.file_size))
            files[info.filename[len(root_name) + 1:]] = archive.read(info)
        problems.extend(files_problems(files, root_name))
    return problems


def readme_problems(text):
    """README に書かないことが入っていないかを確かめる。"""
    problems = []
    for pattern, reason in README_FORBIDDEN:
        for match in re.finditer(pattern, text):
            line = text.count("\n", 0, match.start()) + 1
            problems.append("README の{}行目「{}」: {}。".format(line, match.group(0), reason))
    return problems


if __name__ == "__main__":
    # 使い方: python3 tools/limits.py <配る一式のフォルダ>
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print("使い方: python3 tools/limits.py <配る一式のフォルダ>")
        sys.exit(0 if len(sys.argv) == 2 else 2)
    found = bundle_problems(sys.argv[1])
    for item in found:
        print(item)
    print("問題 {}件".format(len(found)))
    sys.exit(1 if found else 0)
