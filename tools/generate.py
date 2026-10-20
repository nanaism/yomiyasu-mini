#!/usr/bin/env python3
"""yomiyasu-mini を、本体 yomiyasu の木と抽出表（extract/table.json）から作る道具。

標準ライブラリだけで動き、外へ通信しない。Python 3.9 以上で、どの版でも同じバイトを出す。

使い方:
  python3 -B tools/generate.py --source <本体の木> [--commit <40桁>] [--table <抽出表>] [--out <出力の根>]
                                [--check] [--accept] [--drop <id> ...] [--measure-variant]

  --source  本体の木（nanaism/yomiyasu を取り出したフォルダ）。git の木なら HEAD と抽出表のコミットを比べる。
  --commit  git の木でない写しを使うときに、そのコミットを40桁で書く。抽出表の値と違えば止める。
  --table   抽出表。既定はこのリポジトリの extract/table.json。抽出表の中のパスは、抽出表のフォルダの
            1つ上（ふつうはリポジトリ）から数える。
  --out     出力の根。既定は抽出表のフォルダの1つ上。<出力の根>/<output_dir>/ と <出力の根>/MANIFEST.json を書く。
  --check   書かずに、今あるファイルとバイトで比べる。
  --accept  中身のハッシュが変わっていても書き、抽出表のハッシュを今の値に書き換える。
  --drop    測定用。part、文書、スクリプト、写しの id を外して作る。--measure-variant と一緒にだけ使える。
  --measure-variant  測定用の写しを作る。出力先は <リポジトリ>/measurement/variants/ の下に限る。
            参照の欠けは止めずに知らせだけにし、MANIFEST.json に外した id の一覧を残す。

終了コード:
  0 生成した（--check では、今あるファイルと同じだった）。
  2 止めた。何も書いていない。見出しや名前がない、どれか決められない、置き換えや削除の回数が違う、
    コミットが合わない、閉包が足りない、参照が切れている、禁止の語がある、上限を超えた、など。
  3 中身のハッシュが変わった。見直しの一覧を出し、何も書いていない（--accept で書く）。
  4 --check で、生成したものが今あるファイルと違う。

抽出表の形（table.json。キーの順はこのとおりに保つ。--accept で書き直すときも同じ形にする）:
  format "yomiyasu-mini-extract"、format_version 1、version "1.0.0"（mini の版。本体の版とは別に数える）、
  source {repository, tag, commit（40桁）, skill_dir}、output_dir "skills/yomiyasu-mini"、file_budget（ファイルの数）、
  include ["scripts.json"]（同じフォルダの表を読み込む。source と version が同じでなければ止める）、
  front_matter {name, description {text, text_sha256, from}, license "MIT"}、
  documents [{output "SKILL.md" など, id（省略可）, parts [...]}]、
  copies [{output, from_repo | source, sha256（source のとき）, id（省略可）}]、
  forbidden_strings [...]（生成する .md と .py に入れない文字列）、
  reference_allow [{text, reason}]（参照の検査で許す文字列）、
  measure_keep [id ...]（測定で外さない part の id）。

part（どれも id を持つ。表の中で重ならない）:
  verbatim         source（本体の木からのパス）と、heading {level, text, parents} か region（"front_matter" か "file"）で
                   指した文をそのまま使う。selector は {"scope": "subtree"|"own"}（既定は subtree）か
                   {"paragraphs": [i, j]}（見出しの直下の本文を空行で分けた段落の番号。0始まり、両端を含む）か
                   {"lines": [i, j]}（見出しの直下の本文の、空でない行の番号。囲みのコードは1つと数える。
                   本体の SKILL.md は段落を空行で分けずに1行ずつ書いているので、1行だけ使うときはこちら）。
                   sha256 は選んだ元の文のもの。
  verbatim_edited  verbatim と同じ指し方に、substitutions [{old, new, count}] と
                   transforms {heading_shift: -1|0|1, drop_lines: [{pattern, count}]} を足す。
                   当てる順は drop_lines、substitutions、heading_shift。回数が count と違えば止める。
                   drop_lines で行を消したために空行が2つ続いたときは、1つにする。
                   sha256 は直す前の元の文のもの。heading_shift は 1 で # を1つ増やす（段を下げる）。
  rewritten        text（extract/rewritten/<id>.md）、text_sha256、from [{source, heading か region, selector, sha256}]。
  own              text（extract/own/<id>.md）、text_sha256、reason。
  どの part にも note と class（A、A*、B、C などの分類）と drop_with [id ...]（一緒に外す id）を書ける。
  part の文は末尾の空行を落として改行1つで終える。part どうしは空行1つでつなぐ。

scripts.json（format "yomiyasu-mini-scripts"、format_version 1、version、source、scripts [...]）の extract:
  {kind "extract", id, modules [{name, source}]（依存される側を先に書く）, roots [{module, name}],
   imports {モジュール: {名前: 出どころのモジュール}}（省略可。try の中の from ... import から自動で作る）,
   provides [名前]（自前の文が用意する名前）, allow_unresolved [{module, name, reason}],
   strip ["comments", "docstrings"], notice null | "unicode", allowed_imports [モジュール]（省略可）,
   packing {limit 80000, max_bytes 90000, parts "scripts/mini_diff_{n}.py", last "scripts/mini_check.py",
            part_head {text, text_sha256}, loader {text, text_sha256}, last_head {text, text_sha256},
            last_tail {text, text_sha256}},
   names [{module, name, stmts, sha256}]（閉包の名前の組。--accept で今の値に書き換える）}
  根の名前から symtable と ast で閉包を取り、強連結成分の順に並べ、limit バイトまで前から詰めて部品にする。
  最後の部品は last のファイルに、last_head と last_tail と一緒に入る。部品どうしは loader の _mini_load で読む。
  コメントと docstring は ast と tokenize の位置だけで落とし（ast.unparse と tokenize.untokenize は使わない）、
  続く空行は1行にまとめる。

scripts.json はもう1つの書き方も読む（format "yomiyasu-mini-extract-scripts"、1つの抽出をファイルの最上位に書く）:
  modules [{id, source, from_modules {出どころ: [名前]}}]、roots、strip {comments, docstrings, blank_lines "collapse"}、
  limits {part_body_bytes, file_bytes}、packing "scc"、allowed_imports、unicode_notice、
  own [{id, text, text_sha256, reason}]、outputs [{output, head [own の id], tail [own の id]}]（部品の数と同じ数）、
  names、watch [{module, name, stmts, sha256, reason}]（取り出さないが、変わったら見直しに出す名前）。
  この書き方では import の文を生成の道具が足さず、自前の文（head）が同じ import を持つことを確かめる。
  前の部品の名前は、自前の文に _mini_bind があれば `_mini_bind("部品", "名前 …")` で、なければ _mini_load で読む。
  自前の文が使う取り出した名前も、その名前がある部品から読む。id がなければ "scripts" と呼ぶ（--drop scripts）。

参照の検査（出力するすべての .md）: references/… と scripts/… のパス、ほかの .md と .py のファイル名、
「<ファイル>.md「…」」の中身への参照（行き先のファイルにその語句があるか）、SKILL.md の中身への参照、
本体の道具の名前、mini の CLI（packing の last_head と last_tail）にないオプション、run と verify、
本体 lint の規則の名前、「■ 」で始まる節の名前（生成した .py にないもの）が reference_allow の外にあれば止める。
--measure-variant では、行き先の欠け（ないファイル、ない語句、外したスクリプトのオプション）は知らせだけにする。
"""
import argparse
import ast
import builtins
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import symtable
import sys
import tokenize

sys.dont_write_bytecode = True
os.environ["GIT_OPTIONAL_LOCKS"] = "0"

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(TOOLS_DIR)
PROG = "yomiyasu-mini generate"
TABLE_FORMAT = "yomiyasu-mini-extract"
SCRIPTS_FORMAT = "yomiyasu-mini-scripts"
SCRIPTS_SINGLE_FORMAT = "yomiyasu-mini-extract-scripts"
MANIFEST_FORMAT = "yomiyasu-mini-manifest"
FORMAT_VERSION = 1
VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
GENERATED_NAMES = ("__version__", "SOURCE_TAG", "SOURCE_COMMIT", "_mini_m", "_mini_n")
SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
COMP_NODES = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
MAIN_TOOLS = ("yomiyasu_lint", "yomiyasu_diff", "yomiyasu_check", "yomiyasu_hook")


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


# ---------------------------------------------------------------- 共通


class Fatal(Exception):
    """先へ進めない誤り（抽出表が読めないなど）。終了コード2。"""


class Report:
    """止める理由と、見直しの一覧を集める。止める理由はすべて集めてから、まとめて出す。"""

    def __init__(self):
        self.stops = []
        self.reviews = []
        self.notes = []
        self.changed_sources = []
        self.reorder = []

    def stop(self, line, *details):
        self.stops.append((line, details))

    def review(self, line, apply, source=None):
        self.reviews.append((line, apply))
        if source and source not in self.changed_sources:
            self.changed_sources.append(source)

    def note(self, line):
        self.notes.append(line)


def sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def short(value):
    return value[:12] if isinstance(value, str) and value else "（なし）"


def safe_rel(path):
    """抽出表に書くパスとして使えるか（相対、/ 区切り、.. なし）。"""
    if not isinstance(path, str) or not path or path.startswith("/") or "\\" in path:
        return False
    parts = path.split("/")
    return all(p not in ("", ".", "..") for p in parts)


def read_strict(path):
    """UTF-8 として厳しく読む。BOM があれば止める。CRLF は LF にそろえる。(文字列, 誤りの文) を返す。"""
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except FileNotFoundError:
        return None, "ファイルがありません"
    except OSError as error:
        return None, "読めません（{}）".format(error.strerror or error)
    if data.startswith(b"\xef\xbb\xbf"):
        return None, "先頭に BOM があります"
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        return None, "UTF-8 として読めません（{}バイト目）".format(error.start)
    return text.replace("\r\n", "\n"), None


def finish(text):
    """末尾の改行を落として、改行1つで終える。"""
    return text.rstrip("\n") + "\n"


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("キー {} が2回あります".format(key))
        result[key] = value
    return result


def dump_json(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def check_keys(report, obj, allowed, label):
    if not isinstance(obj, dict):
        report.stop("FORMAT  {} がオブジェクトではありません。".format(label))
        return False
    unknown = sorted(k for k in obj if k not in allowed)
    if unknown:
        report.stop("FORMAT  {} に知らないキーがあります: {}".format(label, "、".join(unknown)))
        return False
    return True


# ---------------------------------------------------------------- Markdown


_ATX = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_SETEXT = re.compile(r"^ {0,3}(-+|=+)[ \t]*$")
_SETEXT_PREV = re.compile(r"^ {0,3}(#|[-*+] |\d+[.)] |\||>)")
_HEADING_MARK = re.compile(r"^( {0,3})(#{1,6})(?=[ \t]|$)")


class MdDoc:
    """Markdown を行に分け、囲みのコードの外の ATX 見出しを数える。"""

    def __init__(self, text):
        self.text = text
        self.lines = text.split("\n")
        self.fm = None          # front matter の (開始行, 終わりの --- の行)
        self.fm_unclosed = False
        self.headings = []      # (行, レベル, 文字列, 祖先の文字列のタプル)
        self.setext = []        # setext の見出しに読める行
        self.unclosed_fence = None
        self.in_fence = [False] * len(self.lines)
        start = 0
        if self.lines and self.lines[0].rstrip() == "---":
            for j in range(1, len(self.lines)):
                if self.lines[j].rstrip() == "---":
                    self.fm = (0, j)
                    start = j + 1
                    break
            else:
                self.fm_unclosed = True
        self.body_start = start
        fence = None
        stack = []
        for i in range(start, len(self.lines)):
            line = self.lines[i]
            m = _FENCE.match(line)
            if fence is None:
                if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                    fence = (m.group(1)[0], len(m.group(1)), i)
                    self.in_fence[i] = True
                    continue
            else:
                self.in_fence[i] = True
                if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= fence[1] and m.group(2).strip() == "":
                    fence = None
                continue
            h = _ATX.match(line)
            if h:
                level = len(h.group(1))
                text = (h.group(2) or "").strip()
                while stack and stack[-1][0] >= level:
                    stack.pop()
                self.headings.append((i, level, text, tuple(t for _, t in stack)))
                stack.append((level, text))
            elif (_SETEXT.match(line) and i > start and self.lines[i - 1].strip()
                  and not self.in_fence[i - 1] and not _SETEXT_PREV.match(self.lines[i - 1])):
                self.setext.append(i)
        if fence is not None:
            self.unclosed_fence = fence[2]

    def find(self, level, text, parents):
        return [k for k, h in enumerate(self.headings) if h[1] == level and h[2] == text and h[3] == tuple(parents)]

    def same_text(self, text):
        return [h for h in self.headings if h[2] == text]

    def section(self, k, scope):
        i, level = self.headings[k][0], self.headings[k][1]
        end = len(self.lines)
        for j, lv, _, _ in self.headings[k + 1:]:
            if scope == "own" or lv <= level:
                end = j
                break
        return i, end

    def content(self, a, b):
        return "\n".join(self.lines[a:b]).rstrip("\n") + "\n"

    def paragraphs(self, k):
        """見出しの直下の本文（own の範囲から見出しの行を除いたもの）を、空行で段落に分ける。"""
        a, b = self.section(k, "own")
        out = []
        current = None
        for i in range(a + 1, b):
            blank = not self.in_fence[i] and self.lines[i].strip() == ""
            if blank:
                if current is not None:
                    out.append(current)
                    current = None
            elif current is None:
                current = [i, i + 1]
            else:
                current[1] = i + 1
        if current is not None:
            out.append(current)
        return out

    def line_items(self, k):
        """見出しの直下の本文の、空でない行。囲みのコードは開きから閉じまでを1つと数える。"""
        a, b = self.section(k, "own")
        out = []
        i = a + 1
        while i < b:
            if self.in_fence[i]:
                j = i + 1
                while j < b and self.in_fence[j] and not self._closes(i, j):
                    j += 1
                end = j + 1 if j < b and self.in_fence[j] else j
                out.append([i, end])
                i = end
                continue
            if self.lines[i].strip():
                out.append([i, i + 1])
            i += 1
        return out

    def _closes(self, i, j):
        """i 行目で開いた囲みを j 行目が閉じるか。"""
        m_open = _FENCE.match(self.lines[i])
        m = _FENCE.match(self.lines[j])
        return bool(m_open and m and m.group(1)[0] == m_open.group(1)[0] and len(m.group(1)) >= len(m_open.group(1))
                    and m.group(2).strip() == "")

    def front_matter_text(self):
        a, b = self.fm
        return "\n".join(self.lines[a + 1:b]) + "\n"

    def keys(self):
        return [(h[1], h[3], h[2]) for h in self.headings]


def heading_label(level, text, parents):
    return "L{}「{}」({})".format(level, text, " > ".join(parents) if parents else "最上位")


def shift_headings(text, shift):
    """囲みのコードの外の ATX 見出しの # を shift 個だけ増やす（負なら減らす）。範囲を出たら None。"""
    doc = MdDoc(text)
    lines = list(doc.lines)
    for i, level, _, _ in doc.headings:
        new = level + shift
        if new < 1 or new > 6:
            return None
        lines[i] = _HEADING_MARK.sub(lambda m: m.group(1) + "#" * new, lines[i], count=1)
    return "\n".join(lines)


# ---------------------------------------------------------------- Python の取り出し


class Unit:
    """最上位の文1つ。名前を定義する文（def、class、代入、import）か、ほかの名前に付く文（添えの文）。"""

    def __init__(self, mod, node):
        self.mod = mod
        self.node = node
        self.start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
        self.end = node.end_lineno
        self.defines = []
        self.attach = None
        self.attached = []
        self.is_import = isinstance(node, (ast.Import, ast.ImportFrom))
        self.binders = {}       # import のとき、名前 → 出どころ
        self.refs = set()

    def key(self):
        return (self.mod.index, self.start)

    def raw(self):
        return "\n".join(self.mod.lines[self.start - 1:self.end]) + "\n"


def _import_binders(node):
    out = {}
    if isinstance(node, ast.Import):
        for alias in node.names:
            if alias.asname:
                out[alias.asname] = ("import", alias.name)
            else:
                top = alias.name.split(".")[0]
                out[top] = ("import", top)
    else:
        for alias in node.names:
            out[alias.asname or alias.name] = ("from", node.level, node.module or "", alias.name)
    return out


def _target_names(target):
    return [n.id for n in ast.walk(target) if isinstance(n, ast.Name)]


def _base_name(target):
    base = target
    while isinstance(base, (ast.Subscript, ast.Attribute)):
        base = base.value
    return base.id if isinstance(base, ast.Name) else None


def _bound_names(nodes):
    """最上位で名前を結ぶもの（関数やクラスの中は見ない）。"""
    out = set()
    stack = list(nodes)
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)
            continue
        if isinstance(n, (ast.Lambda,) + COMP_NODES):
            continue
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            out.add(n.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            out.update(_import_binders(n))
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
        elif type(n).__name__ in ("MatchAs", "MatchStar") and getattr(n, "name", None):
            out.add(n.name)
        elif type(n).__name__ == "MatchMapping" and getattr(n, "rest", None):
            out.add(n.rest)
        stack.extend(ast.iter_child_nodes(n))
    return out


def _outer_parts(n):
    """関数・クラス・lambda のうち、外のスコープで評価される部分（飾り、既定値、注釈、基底クラス）。"""
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
        items = list(n.decorator_list) + list(n.args.defaults) + [x for x in n.args.kw_defaults if x is not None]
        args = list(getattr(n.args, "posonlyargs", [])) + list(n.args.args) + list(n.args.kwonlyargs)
        args += [a for a in (n.args.vararg, n.args.kwarg) if a is not None]
        items += [a.annotation for a in args if a.annotation is not None]
        if n.returns is not None:
            items.append(n.returns)
        return items
    if isinstance(n, ast.ClassDef):
        return list(n.decorator_list) + list(n.bases) + [k.value for k in n.keywords]
    if isinstance(n, ast.Lambda):
        return list(n.args.defaults) + [x for x in n.args.kw_defaults if x is not None]
    return []


def module_level_loads(node):
    """入れ子の関数・クラス・lambda の本体を除いた、読む名前。内包表記の変数は除く。"""
    out = set()
    stack = [(x, frozenset()) for x in _outer_parts(node)] if isinstance(node, SCOPE_NODES) else [(node, frozenset())]
    while stack:
        n, bound = stack.pop()
        if isinstance(n, SCOPE_NODES):
            stack.extend((x, bound) for x in _outer_parts(n))
            continue
        if isinstance(n, COMP_NODES):
            targets = set()
            for gen in n.generators:
                targets.update(_target_names(gen.target))
            inner = bound | targets
            first = n.generators[0]
            stack.append((first.iter, bound))
            stack.append((first.target, inner))
            for cond in first.ifs:
                stack.append((cond, inner))
            for gen in n.generators[1:]:
                stack.append((gen.target, inner))
                stack.append((gen.iter, inner))
                for cond in gen.ifs:
                    stack.append((cond, inner))
            for part in ("elt", "key", "value"):
                if hasattr(n, part):
                    stack.append((getattr(n, part), inner))
            continue
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in bound:
            out.add(n.id)
        stack.extend((c, bound) for c in ast.iter_child_nodes(n))
    return out


def symtable_globals(src, filename):
    """入れ子のスコープごとに、参照する大域の名前。[(行, 名前の集合)]。"""
    table = symtable.symtable(src, filename, "exec")
    out = []
    stack = list(table.get_children())
    while stack:
        t = stack.pop()
        names = {s.get_name() for s in t.get_symbols() if s.is_global() and s.is_referenced()}
        out.append((t.get_lineno(), names))
        stack.extend(t.get_children())
    return out


def ignorable_name(name):
    return name.startswith(".") or (name.startswith("__") and name.endswith("__")) or hasattr(builtins, name)


def string_interior_lines(tree):
    """複数行にわたる文字列の、2行目から終わりの行まで。空行を詰めたりコメントの行を消したりしない。"""
    out = set()
    stack = [tree]
    while stack:
        n = stack.pop()
        if isinstance(n, ast.JoinedStr) or (isinstance(n, ast.Constant) and isinstance(n.value, (str, bytes))):
            if getattr(n, "end_lineno", None) and n.end_lineno > n.lineno:
                out.update(range(n.lineno + 1, n.end_lineno + 1))
            continue
        stack.extend(ast.iter_child_nodes(n))
    return out


class PyModule:
    def __init__(self, name, index, relpath, text, report):
        self.name = name
        self.index = index
        self.relpath = relpath
        self.text = text
        self.lines = text.split("\n")
        self.stem = os.path.splitext(os.path.basename(relpath))[0]
        self.ok = True
        try:
            self.tree = ast.parse(text, relpath)
        except SyntaxError as error:
            report.stop("SYNTAX  {} を読めません（{}行目: {}）。".format(relpath, error.lineno, error.msg))
            self.ok = False
            return
        self.units = []
        self.defs = {}
        self.skipped_names = set()
        self.skipped_imports = []
        self.shared_lines = set()
        body = list(self.tree.body)
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            body = body[1:]
        pending = []
        for node in body:
            u = Unit(self, node)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                u.defines = [node.name]
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if any(a.name == "*" for a in node.names):
                    self.skipped_names.update(_bound_names([node]))
                    continue
                u.binders = _import_binders(node)
                u.defines = sorted(u.binders)
            elif isinstance(node, ast.Assign):
                names = []
                others = []
                for t in node.targets:
                    if isinstance(t, (ast.Name, ast.Tuple, ast.List, ast.Starred)):
                        names.extend(_target_names(t))
                    else:
                        others.append(t)
                if names and not others:
                    u.defines = names
                elif others and not names:
                    pending.append((u, _base_name(others[0])))
                    continue
                else:
                    self.skipped_names.update(_bound_names([node]))
                    continue
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    u.defines = [node.target.id]
                else:
                    pending.append((u, _base_name(node.target)))
                    continue
            elif isinstance(node, ast.AugAssign):
                pending.append((u, node.target.id if isinstance(node.target, ast.Name) else _base_name(node.target)))
                continue
            else:
                self._skip(node)
                continue
            self.units.append(u)
            for n in u.defines:
                self.defs.setdefault(n, []).append(u)
        for u, base in pending:
            definers = [d for d in self.defs.get(base, []) if not d.is_import] if base else []
            if definers:
                u.attach = base
                self.units.append(u)
                for d in definers:
                    d.attached.append(u)
            else:
                self._skip(u.node)
        self.units.sort(key=lambda x: x.start)
        seen = {}
        for u in self.units:
            for ln in range(u.start, u.end + 1):
                if ln in seen:
                    self.shared_lines.add(u.start)
                    self.shared_lines.add(seen[ln])
                seen[ln] = u.start
        self.docstrings = self._docstrings()
        self.protected = string_interior_lines(self.tree)
        self._refs()

    def _skip(self, node):
        self.skipped_names.update(_bound_names([node]))
        for n in ast.walk(node):
            if isinstance(n, ast.ImportFrom):
                self.skipped_imports.append((n.module or "", n.level, [(a.name, a.asname) for a in n.names]))

    def _docstrings(self):
        out = {}
        for n in ast.walk(self.tree):
            if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) or not n.body:
                continue
            first = n.body[0]
            if not (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                continue
            if first.lineno == n.lineno:
                continue
            head = self.lines[first.lineno - 1].encode("utf-8")
            prefix = head[:first.col_offset].decode("utf-8", "replace")
            if prefix.strip():
                continue
            tail = self.lines[first.end_lineno - 1].encode("utf-8")[first.end_col_offset:].decode("utf-8", "replace")
            if tail.strip() and not tail.strip().startswith("#"):
                continue
            out[first.lineno] = (first.lineno, first.end_lineno, len(n.body) == 1, prefix)
        return out

    def _refs(self):
        for u in self.units:
            u.refs |= module_level_loads(u.node)
            if u.attach:
                u.refs.add(u.attach)
        starts = [u.start for u in self.units]
        import bisect
        for line, names in symtable_globals(self.text, self.relpath):
            k = bisect.bisect_right(starts, line) - 1
            if k >= 0 and self.units[k].start <= line <= self.units[k].end:
                self.units[k].refs |= names

    def notice_block(self, u):
        """文のすぐ上に続くコメントの行。"""
        lines = []
        i = u.start - 2
        while i >= 0 and self.lines[i].strip().startswith("#"):
            lines.insert(0, self.lines[i])
            i -= 1
        return lines

    def strip(self, u, opts):
        """文の字からコメントと docstring を落とし、続く空行を1行にまとめる。ほかの字は元のまま。"""
        base = u.start
        lines = self.lines[u.start - 1:u.end]
        drop = set()
        replace = {}
        if "docstrings" in opts:
            for s, (s0, e, only, indent) in self.docstrings.items():
                if u.start <= s <= u.end:
                    drop.update(range(s0, e + 1))
                    if only:
                        replace[s0] = indent + "pass"
        cuts = {}
        if "comments" in opts:
            reader = io.StringIO("\n".join(lines) + "\n").readline
            for tok in tokenize.generate_tokens(reader):
                if tok.type == tokenize.COMMENT:
                    cuts[tok.start[0] + base - 1] = tok.start[1]
        out = []
        prev_blank = False
        for i, line in enumerate(lines):
            ln = base + i
            if ln in replace:
                out.append(replace[ln])
                prev_blank = False
                continue
            if ln in drop:
                continue
            protected = ln in self.protected
            if ln in cuts:
                cut = line[:cuts[ln]].rstrip()
                if cut.strip() == "" and not protected:
                    continue
                line = cut
            if not protected and line.strip() == "":
                if prev_blank:
                    continue
                out.append("")
                prev_blank = True
                continue
            out.append(line)
            prev_blank = False
        while out and out[-1] == "":
            out.pop()
        return "\n".join(out) + "\n"


def tarjan(starts, deps, key):
    """強連結成分を、依存される側が先に来る順で返す（再帰を使わない）。"""
    index, low = {}, {}
    onstack = set()
    stack = []
    comps = []
    counter = 0
    for v0 in starts:
        if v0 in index:
            continue
        index[v0] = low[v0] = counter
        counter += 1
        stack.append(v0)
        onstack.add(v0)
        work = [(v0, iter(deps(v0)))]
        while work:
            v, it = work[-1]
            advanced = False
            for w in it:
                if w not in index:
                    index[w] = low[w] = counter
                    counter += 1
                    stack.append(w)
                    onstack.add(w)
                    work.append((w, iter(deps(w))))
                    advanced = True
                    break
                if w in onstack:
                    low[v] = min(low[v], index[w])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[v])
            if low[v] == index[v]:
                comp = []
                while True:
                    w = stack.pop()
                    onstack.discard(w)
                    comp.append(w)
                    if w is v:
                        break
                comps.append(sorted(comp, key=key))
    return comps


def entry_id(entry):
    """スクリプトの抽出の id。1つの抽出だけを書いた scripts.json は、id がなければ "scripts"。"""
    if entry.get("format") == SCRIPTS_SINGLE_FORMAT:
        return entry.get("id", "scripts")
    return entry.get("id")


def undefined_globals(src, filename, extra=()):
    """出力したソースで、どのスコープからも定義されていない大域の名前（静的な確かめ）。"""
    tree = ast.parse(src, filename)
    defined = set(extra) | _bound_names(tree.body)
    used = set(module_level_loads(tree))
    for _, names in symtable_globals(src, filename):
        used |= names
    return sorted(n for n in used if n not in defined and not ignorable_name(n))


# ---------------------------------------------------------------- 生成


class Generator:
    def __init__(self, args):
        self.args = args
        self.report = Report()
        self.tree = os.path.realpath(args.source)
        self.table_path = os.path.realpath(args.table or os.path.join(REPO_DIR, "extract", "table.json"))
        self.base = os.path.dirname(os.path.dirname(self.table_path))
        self.out_root = os.path.realpath(args.out) if args.out else self.base
        self.md_cache = {}
        self.py_cache = {}
        self.files = {}          # 出力の根からのパス → バイト列
        self.bundle = {}         # 配る一式のフォルダの中のパス → バイト列
        self.script_records = []
        self.cli_texts = []      # 自前の文（packing の last_head と last_tail）。使えるオプションはここから取る
        self.tables = []         # (パス, 読んだバイト列, オブジェクト)
        self.drop = set()

    # --- 抽出表

    def load_tables(self):
        table, raw = self._load_json(self.table_path, "抽出表")
        self.tables.append((self.table_path, raw, table))
        allowed = {"format", "format_version", "version", "source", "output_dir", "file_budget", "include",
                   "front_matter", "documents", "copies", "forbidden_strings", "reference_allow", "measure_keep", "note"}
        if not check_keys(self.report, table, allowed, "抽出表"):
            raise Fatal()
        if table.get("format") != TABLE_FORMAT or table.get("format_version") != FORMAT_VERSION:
            self.report.stop("FORMAT  抽出表の format が {} の {} ではありません。".format(TABLE_FORMAT, FORMAT_VERSION))
            raise Fatal()
        self.table = table
        self.documents = list(table.get("documents", []))
        self.scripts = []
        self.copies = list(table.get("copies", []))
        self.forbidden = list(table.get("forbidden_strings", []))
        self.allow = list(table.get("reference_allow", []))
        self.keep = list(table.get("measure_keep", []))
        for name in table.get("include", []):
            if not safe_rel(name) or "/" in name:
                self.report.stop("FORMAT  include の {} は抽出表と同じフォルダのファイルの名前にしてください。".format(name))
                continue
            path = os.path.join(os.path.dirname(self.table_path), name)
            sub, raw = self._load_json(path, name)
            self.tables.append((path, raw, sub))
            if sub.get("format") == SCRIPTS_SINGLE_FORMAT:
                # 1つの抽出だけを書いた scripts.json（キーは extract_spec で確かめる）
                if sub.get("format_version") != FORMAT_VERSION:
                    self.report.stop("FORMAT  {} の format_version が {} ではありません。".format(name, FORMAT_VERSION))
                if sub.get("source") != table.get("source"):
                    self.report.stop("SOURCE  {} の source が抽出表と違います。".format(name))
                if sub.get("version") != table.get("version"):
                    self.report.stop("SOURCE  {} の version「{}」が抽出表の「{}」と違います。".format(
                        name, sub.get("version"), table.get("version")))
                self.scripts.append(sub)
                continue
            allowed = {"format", "format_version", "version", "source", "scripts", "documents", "copies",
                       "forbidden_strings", "reference_allow", "measure_keep", "note"}
            if not check_keys(self.report, sub, allowed, name):
                continue
            if sub.get("format") not in (SCRIPTS_FORMAT, TABLE_FORMAT) or sub.get("format_version") != FORMAT_VERSION:
                self.report.stop("FORMAT  {} の format が {} か {} の {} ではありません。".format(
                    name, SCRIPTS_FORMAT, SCRIPTS_SINGLE_FORMAT, FORMAT_VERSION))
            if sub.get("source") != table.get("source"):
                self.report.stop("SOURCE  {} の source が抽出表と違います。".format(name))
            if sub.get("version") != table.get("version"):
                self.report.stop("SOURCE  {} の version「{}」が抽出表の「{}」と違います。".format(
                    name, sub.get("version"), table.get("version")))
            self.documents += list(sub.get("documents", []))
            self.scripts += list(sub.get("scripts", []))
            self.copies += list(sub.get("copies", []))
            self.forbidden += list(sub.get("forbidden_strings", []))
            self.allow += list(sub.get("reference_allow", []))
            self.keep += list(sub.get("measure_keep", []))
        self._check_header()

    def _load_json(self, path, label):
        try:
            with open(path, "rb") as handle:
                raw = handle.read()
        except OSError:
            self.report.stop("MISSING file  {} がありません: {}".format(label, path))
            raise Fatal()
        try:
            obj = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_keys)
        except (UnicodeDecodeError, ValueError) as error:
            self.report.stop("FORMAT  {} を JSON として読めません（{}）。".format(label, error))
            raise Fatal()
        if not isinstance(obj, dict):
            self.report.stop("FORMAT  {} がオブジェクトではありません。".format(label))
            raise Fatal()
        return obj, raw

    def _check_header(self):
        t = self.table
        r = self.report
        source = t.get("source")
        if not check_keys(r, source, {"repository", "tag", "commit", "skill_dir"}, "抽出表の source"):
            raise Fatal()
        for key in ("repository", "tag", "commit", "skill_dir"):
            if not isinstance(source.get(key), str) or not source.get(key):
                r.stop("FORMAT  抽出表の source に {} がありません。".format(key))
                raise Fatal()
        self.source = source
        if not COMMIT_RE.match(source["commit"]):
            r.stop("FORMAT  source の commit が40桁の小文字の16進ではありません。")
        tag = TAG_RE.match(source["tag"])
        version = VERSION_RE.match(t.get("version", "") if isinstance(t.get("version"), str) else "")
        if not tag:
            r.stop("FORMAT  source の tag「{}」が v<数>.<数>.<数> の形ではありません。".format(source["tag"]))
        if not version:
            r.stop("FORMAT  version「{}」が mini の版の形（1.0.0 のような <数>.<数>.<数>）ではありません。".format(
                t.get("version")))
        self.version = t.get("version")
        if not safe_rel(source["skill_dir"]):
            r.stop("FORMAT  source の skill_dir「{}」が相対のパスではありません。".format(source["skill_dir"]))
        out_dir = t.get("output_dir")
        if not safe_rel(out_dir):
            r.stop("FORMAT  output_dir「{}」が相対のパスではありません。".format(out_dir))
            raise Fatal()
        self.output_dir = out_dir
        self.root_name = out_dir.split("/")[-1]
        budget = t.get("file_budget")
        if not isinstance(budget, int) or isinstance(budget, bool) or budget < 1:
            r.stop("FORMAT  file_budget が1以上の整数ではありません。")
            budget = None
        self.file_budget = budget
        for item in self.forbidden:
            if not isinstance(item, str) or not item:
                r.stop("FORMAT  forbidden_strings に空か文字列でないものがあります。")
        for item in self.allow:
            if not check_keys(r, item, {"text", "reason"}, "reference_allow の項目") or not item.get("text"):
                r.stop("FORMAT  reference_allow の項目に text がありません。")
        if not version or not tag:
            raise Fatal()
        skill_md = os.path.join(self.tree, source["skill_dir"], "SKILL.md")
        text, error = read_strict(skill_md)
        if error:
            r.stop("MISSING file  {}/SKILL.md: {}".format(source["skill_dir"], error))
            return
        block, _ = limits.split_front_matter(text)
        main_version = (limits.parse_front_matter(block).get("metadata") or {}).get("version") if block else None
        if main_version != tag.group(1):
            r.stop("SOURCE  本体の SKILL.md の metadata.version「{}」が抽出表の source の tag {} と違います。".format(
                main_version, source["tag"]))

    # --- コミット

    def _git(self, *args):
        git = shutil.which("git")
        if not git:
            return None
        env = dict(os.environ, LC_ALL="C", GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
        try:
            done = subprocess.run([git, "--no-optional-locks", "-C", self.tree] + list(args), env=env,
                                  stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        except (OSError, subprocess.SubprocessError):
            return None
        if done.returncode != 0:
            return None
        return done.stdout.decode("utf-8", "replace").strip()

    def verify_commit(self):
        r = self.report
        want = self.source["commit"]
        given = self.args.commit
        if given is not None and not COMMIT_RE.match(given):
            r.stop("COMMIT  --commit「{}」が40桁の小文字の16進ではありません。".format(given))
            return
        top = self._git("rev-parse", "--show-toplevel")
        is_git = top is not None and os.path.realpath(top) == self.tree
        if is_git:
            head = self._git("rev-parse", "--verify", "HEAD^{commit}")
            if head != want:
                r.stop("COMMIT  本体の木の HEAD {} が抽出表のコミット {} と違います。".format(short(head), short(want)))
            status = self._git("status", "--porcelain", "--untracked-files=no")
            if status is None:
                r.stop("COMMIT  本体の木の git status を読めません。")
            elif status:
                r.stop("COMMIT  本体の木に、コミットしていない変更があります。")
            tagged = self._git("rev-parse", "-q", "--verify", "refs/tags/{}^{{commit}}".format(self.source["tag"]))
            if tagged and tagged != want:
                r.stop("COMMIT  本体の木のタグ {} は {} を指していて、抽出表のコミットと違います。".format(
                    self.source["tag"], short(tagged)))
            if given is not None and given != head:
                r.stop("COMMIT  --commit {} が本体の木の HEAD {} と違います。".format(short(given), short(head)))
            self.tree_commit = head
        else:
            if given is None:
                r.stop("COMMIT  本体の木が git の木ではないので、--commit にコミットを40桁で書いてください。")
                return
            if given != want:
                r.stop("COMMIT  --commit {} が抽出表のコミット {} と違います。".format(short(given), short(want)))
                return
            r.note("コミットは git で確かめていない（--commit の値を使った）")
            self.tree_commit = given

    # --- 選ぶ

    def source_path(self, rel, label):
        if not safe_rel(rel):
            self.report.stop("FORMAT  {} の source「{}」が相対のパスではありません。".format(label, rel))
            return None
        return os.path.join(self.tree, rel)

    def md(self, rel, label):
        if rel in self.md_cache:
            return self.md_cache[rel]
        path = self.source_path(rel, label)
        doc = None
        if path is not None:
            text, error = read_strict(path)
            if error:
                self.report.stop("MISSING file  {}: {}".format(rel, error))
            else:
                doc = MdDoc(text)
                if doc.fm_unclosed:
                    self.report.stop("FORMAT  {} の front matter が閉じていません。".format(rel))
                if doc.unclosed_fence is not None:
                    self.report.stop("FORMAT  {} の{}行目の囲みのコードが閉じていません。".format(rel, doc.unclosed_fence + 1))
                for i in doc.setext:
                    self.report.stop("FORMAT  {} の{}行目が setext の見出しに読めます（ATX の見出しだけを数えます）。".format(rel, i + 1))
        self.md_cache[rel] = doc
        return doc

    def select(self, spec, label):
        """part か from の項目が指す元の文を返す。(文, 説明) か None。"""
        r = self.report
        rel = spec.get("source")
        if not isinstance(rel, str):
            r.stop("FORMAT  {} に source がありません。".format(label))
            return None
        doc = self.md(rel, label)
        if doc is None:
            return None
        if "region" in spec:
            region = spec["region"]
            if "heading" in spec:
                r.stop("FORMAT  {} に region と heading の両方があります。".format(label))
                return None
            if region == "front_matter":
                if doc.fm is None:
                    r.stop("MISSING region  {}  front matter がありません。".format(rel))
                    return None
                return doc.front_matter_text(), "{} front_matter".format(rel)
            if region == "file":
                return finish(doc.text), "{} file".format(rel)
            r.stop("FORMAT  {} の region「{}」は front_matter か file にしてください。".format(label, region))
            return None
        heading = spec.get("heading")
        if not check_keys(r, heading, {"level", "text", "parents"}, label + " の heading"):
            return None
        level, text, parents = heading.get("level"), heading.get("text"), heading.get("parents", [])
        if not isinstance(level, int) or not isinstance(text, str) or not isinstance(parents, list) \
                or not all(isinstance(p, str) for p in parents):
            r.stop("FORMAT  {} の heading は level（整数）、text（文字列）、parents（文字列の並び）にしてください。".format(label))
            return None
        where = "{}  {}".format(rel, heading_label(level, text, parents))
        found = doc.find(level, text, parents)
        if not found:
            hints = ["同じ文字列の見出し: {}".format(heading_label(h[1], h[2], h[3])) for h in doc.same_text(text)]
            r.stop("MISSING heading  " + where, *hints)
            return None
        if len(found) > 1:
            r.stop("AMBIGUOUS heading  {}  当てはまる見出しが{}つあり、どれか決められません。".format(where, len(found)))
            return None
        k = found[0]
        selector = spec.get("selector")
        if selector is None:
            selector = {"scope": spec.get("scope", "subtree")}
        elif "scope" in spec:
            r.stop("FORMAT  {} に selector と scope の両方があります。".format(label))
            return None
        if not check_keys(r, selector, {"scope", "paragraphs", "lines"}, label + " の selector") or len(selector) != 1:
            r.stop("FORMAT  {} の selector は scope、paragraphs、lines のどれか1つにしてください。".format(label))
            return None
        if "scope" in selector:
            scope = selector["scope"]
            if scope not in ("subtree", "own"):
                r.stop("FORMAT  {} の scope「{}」は subtree か own にしてください。".format(label, scope))
                return None
            a, b = doc.section(k, scope)
            return doc.content(a, b), "{} {}".format(where, scope)
        unit = "paragraphs" if "paragraphs" in selector else "lines"
        pair = selector[unit]
        if not (isinstance(pair, list) and len(pair) == 2 and all(isinstance(x, int) and not isinstance(x, bool)
                                                                   for x in pair) and 0 <= pair[0] <= pair[1]):
            r.stop("FORMAT  {} の {} は [i, j]（0 <= i <= j の整数）にしてください。".format(label, unit))
            return None
        items = doc.paragraphs(k) if unit == "paragraphs" else doc.line_items(k)
        word = "段落" if unit == "paragraphs" else "行"
        if pair[1] >= len(items):
            r.stop("MISSING {}  {}  {}{}〜{} を指していますが、{}は{}つです。".format(
                unit[:-1], where, word, pair[0], pair[1], word, len(items)))
            return None
        return doc.content(items[pair[0]][0], items[pair[1]][1]), "{} {}{}〜{}".format(where, word, pair[0], pair[1])

    def own_text(self, spec, label, kind="text"):
        """抽出表から指した mini の文を読み、text_sha256 を比べる。"""
        rel = spec.get("text")
        if not safe_rel(rel):
            self.report.stop("FORMAT  {} の text「{}」が相対のパスではありません。".format(label, rel))
            return None
        text, error = read_strict(os.path.join(self.base, rel))
        if error:
            self.report.stop("MISSING file  {}: {}".format(rel, error))
            return None
        text = finish(text)
        if not text.strip():
            self.report.stop("FORMAT  {} が空です。".format(rel))
            return None
        self.check_hash(spec, "text_sha256", sha_text(text), "{:<9} {}  {}".format(kind, label, rel))
        return text

    def check_hash(self, obj, key, value, line, source=None):
        old = obj.get(key)
        if old != value:
            head = "NEW    " if old is None else "CHANGED"
            self.report.review("{} {}  {} → {}".format(head, line, short(old), short(value)),
                               lambda: obj.__setitem__(key, value), source)

    # --- 文書

    def expand_drop(self):
        ids = {}
        r = self.report

        def add(item, label, required):
            pid = entry_id(item) if isinstance(item, dict) and item.get("format") == SCRIPTS_SINGLE_FORMAT else item.get("id")
            if pid is None:
                if required:
                    r.stop("FORMAT  {} に id がありません。".format(label))
                return
            if not isinstance(pid, str) or not ID_RE.match(pid):
                r.stop("FORMAT  {} の id「{}」は英数字と . _ - にしてください。".format(label, pid))
                return
            if pid in ids:
                r.stop("FORMAT  id「{}」が2回使われています。".format(pid))
                return
            ids[pid] = item

        for d, doc in enumerate(self.documents):
            if not check_keys(r, doc, {"output", "id", "parts", "note"}, "documents[{}]".format(d)):
                continue
            add(doc, "documents[{}]".format(d), False)
            for i, part in enumerate(doc.get("parts", []) if isinstance(doc.get("parts"), list) else []):
                if isinstance(part, dict):
                    add(part, "{} part {}".format(doc.get("output"), i), True)
        for s, entry in enumerate(self.scripts):
            if isinstance(entry, dict):
                add(entry, "scripts[{}]".format(s), True)
        for c, copy in enumerate(self.copies):
            if isinstance(copy, dict):
                add(copy, "copies[{}]".format(c), False)
        self.ids = ids
        for k in self.keep:
            if k not in ids:
                r.stop("FORMAT  measure_keep の id「{}」が抽出表にありません。".format(k))
        requested = list(self.args.drop or [])
        todo = list(requested)
        while todo:
            pid = todo.pop()
            if pid in self.drop:
                continue
            if pid not in ids and not any(d.get("output") == pid for d in self.documents if isinstance(d, dict)):
                r.stop("DROP  --drop の id「{}」が抽出表にありません。".format(pid))
                continue
            if pid in self.keep:
                r.stop("DROP  id「{}」は measure_keep にあるので外せません。".format(pid))
                continue
            self.drop.add(pid)
            item = ids.get(pid, {})
            for other in item.get("drop_with", []) if isinstance(item.get("drop_with"), list) else []:
                todo.append(other)

    def dropped(self, item):
        if not isinstance(item, dict):
            return False
        pid = entry_id(item) if item.get("format") == SCRIPTS_SINGLE_FORMAT else item.get("id")
        return pid in self.drop or item.get("output") in self.drop

    def build_front_matter(self):
        r = self.report
        fm = self.table.get("front_matter")
        if not check_keys(r, fm, {"name", "description", "license", "note"}, "front_matter"):
            return None
        name = fm.get("name")
        if not isinstance(name, str) or not SKILL_NAME_RE.match(name) or len(name) > limits.NAME_MAX_CHARS:
            r.stop("FORMAT  front_matter の name「{}」が小文字の英数字とハイフンの形ではありません。".format(name))
            return None
        if name != self.root_name:
            r.stop("FORMAT  front_matter の name「{}」が output_dir のフォルダの名前「{}」と違います。".format(name, self.root_name))
        if fm.get("license") != "MIT":
            r.stop("FORMAT  front_matter の license は MIT にしてください。")
        desc = fm.get("description")
        if not check_keys(r, desc, {"text", "text_sha256", "from", "note"}, "front_matter の description"):
            return None
        text = self.own_text(desc, "front_matter description", "text")
        froms = desc.get("from", [])
        if not isinstance(froms, list):
            r.stop("FORMAT  front_matter の description の from が並びではありません。")
            froms = []
        for j, f in enumerate(froms):
            label = "front_matter description from {}".format(j)
            if not check_keys(r, f, {"source", "heading", "region", "selector", "scope", "sha256", "note"}, label):
                continue
            got = self.select(f, label)
            if got:
                self.check_hash(f, "sha256", sha_text(got[0]), "from      {}  {}".format(label, got[1]), f.get("source"))
        if text is None:
            return None
        text = text.strip()
        if "\n" in text or "\t" in text:
            r.stop("FORMAT  description は1行にしてください。")
        if "<" in text or ">" in text:
            r.stop("FORMAT  description に < か > があります。")
        if ": " in text or " #" in text or text[:1] in "-?:,[]{}#&*!|>'\"%@`" or text != text.strip():
            r.stop("FORMAT  description に YAML で区切りに読める字（「: 」「 #」や先頭の記号）があります。")
        if len(text) > limits.DESCRIPTION_SPEC_MAX_CHARS:
            r.stop("LIMIT  description が {}字を超えています。".format(limits.DESCRIPTION_SPEC_MAX_CHARS))
        lines = ["---", "name: " + name, "description: " + text, "license: MIT", "metadata:",
                 '  version: "{}"'.format(self.version),
                 '  source-repository: "{}"'.format(self.source["repository"]),
                 '  source-tag: "{}"'.format(self.source["tag"]),
                 '  source-commit: "{}"'.format(self.source["commit"]), "---"]
        return "\n".join(lines) + "\n"

    def build_part(self, out, i, part):
        r = self.report
        label = "{} part {} {}".format(out, i, part.get("id"))
        kind = part.get("kind")
        common = {"kind", "id", "note", "class", "reason", "drop_with"}
        select_keys = {"source", "heading", "region", "selector", "scope", "sha256"}
        allowed = {
            "verbatim": common | select_keys,
            "verbatim_edited": common | select_keys | {"substitutions", "transforms"},
            "rewritten": common | {"text", "text_sha256", "from"},
            "own": common | {"text", "text_sha256"},
        }
        if kind not in allowed:
            r.stop("FORMAT  {} の kind「{}」は verbatim、verbatim_edited、rewritten、own のどれかにしてください。".format(label, kind))
            return None
        if not check_keys(r, part, allowed[kind], label):
            return None
        if kind in ("verbatim", "verbatim_edited"):
            got = self.select(part, label)
            if got is None:
                return None
            original, where = got
            self.check_hash(part, "sha256", sha_text(original), "{:<9} {}  {}".format(kind, label, where),
                            part.get("source"))
            if kind == "verbatim":
                return original
            return self.apply_edits(original, part, label)
        if kind == "rewritten":
            text = self.own_text(part, label, "rewritten")
            froms = part.get("from")
            if not isinstance(froms, list) or not froms:
                r.stop("FORMAT  {} の from に元の節を1つ以上書いてください。".format(label))
                return text
            for j, f in enumerate(froms):
                flabel = "{} from {}".format(label, j)
                if not check_keys(r, f, select_keys | {"note"}, flabel):
                    continue
                got = self.select(f, flabel)
                if got:
                    self.check_hash(f, "sha256", sha_text(got[0]), "from      {}  {}".format(flabel, got[1]),
                                    f.get("source"))
            return text
        if not part.get("reason"):
            r.stop("FORMAT  {} に reason（本体に元がない理由）を書いてください。".format(label))
        return self.own_text(part, label, "own")

    def apply_edits(self, text, part, label):
        r = self.report
        transforms = part.get("transforms", {})
        if not check_keys(r, transforms, {"heading_shift", "drop_lines"}, label + " の transforms"):
            return None
        ok = True
        for d, rule in enumerate(transforms.get("drop_lines", [])):
            if not check_keys(r, rule, {"pattern", "count", "note"}, "{} の drop_lines[{}]".format(label, d)):
                ok = False
                continue
            try:
                rx = re.compile(rule.get("pattern", ""))
            except re.error as error:
                r.stop("FORMAT  {} の drop_lines[{}] の pattern を読めません（{}）。".format(label, d, error))
                ok = False
                continue
            lines = text.split("\n")
            kept = []
            removed = 0
            gap = False
            for ln in lines[:-1]:
                if rx.search(ln):
                    removed += 1
                    gap = True
                    continue
                if gap and not ln.strip() and kept and not kept[-1].strip():
                    continue
                kept.append(ln)
                gap = False
            if removed != rule.get("count"):
                r.stop("COUNT  {}  drop_lines「{}」で消える行は{}行で、count の {} と違います。".format(
                    label, rule.get("pattern"), removed, rule.get("count")))
                ok = False
            text = "\n".join(kept) + "\n"
        for s, sub in enumerate(part.get("substitutions", [])):
            if not check_keys(r, sub, {"old", "new", "count", "note"}, "{} の substitutions[{}]".format(label, s)):
                ok = False
                continue
            old, new, count = sub.get("old"), sub.get("new"), sub.get("count")
            if not isinstance(old, str) or not old or not isinstance(new, str) or not isinstance(count, int) or count < 1:
                r.stop("FORMAT  {} の substitutions[{}] は old（空でない文字列）、new、count（1以上）にしてください。".format(label, s))
                ok = False
                continue
            found = text.count(old)
            if found != count:
                r.stop("COUNT  {}  置き換え「{}」は {}か所にあり、count の {} と違います。".format(label, old, found, count))
                ok = False
                continue
            text = text.replace(old, new)
        shift = transforms.get("heading_shift", 0)
        if shift not in (-1, 0, 1) or isinstance(shift, bool):
            r.stop("FORMAT  {} の heading_shift は -1、0、1 のどれかにしてください。".format(label))
            ok = False
        elif shift:
            shifted = shift_headings(text, shift)
            if shifted is None:
                r.stop("FORMAT  {} の heading_shift で見出しのレベルが1〜6の外に出ます。".format(label))
                ok = False
            else:
                text = shifted
        if not ok:
            return None
        if not text.strip():
            r.stop("FORMAT  {} を直したら空になりました。".format(label))
            return None
        return finish(text)

    def build_documents(self):
        r = self.report
        fm = self.build_front_matter()
        outputs = []
        seen = set()
        skill = 0
        for d, doc in enumerate(self.documents):
            if not isinstance(doc, dict):
                r.stop("FORMAT  documents[{}] がオブジェクトではありません。".format(d))
                continue
            out = doc.get("output")
            if not safe_rel(out) or not out.endswith(".md"):
                r.stop("FORMAT  documents[{}] の output「{}」は .md の相対のパスにしてください。".format(d, out))
                continue
            if out in seen:
                r.stop("FORMAT  output「{}」が2回あります。".format(out))
                continue
            seen.add(out)
            if out == "SKILL.md":
                skill += 1
            if self.dropped(doc):
                if out == "SKILL.md":
                    r.stop("DROP  SKILL.md は外せません。")
                continue
            parts = doc.get("parts")
            if not isinstance(parts, list) or not parts:
                r.stop("FORMAT  {} の parts がありません。".format(out))
                continue
            texts = []
            for i, part in enumerate(parts):
                if not isinstance(part, dict):
                    r.stop("FORMAT  {} の part {} がオブジェクトではありません。".format(out, i))
                    continue
                if self.dropped(part):
                    continue
                text = self.build_part(out, i, part)
                if text is not None:
                    texts.append(text)
            if not texts:
                if self.args.measure_variant and out != "SKILL.md":
                    r.note("{} の part をすべて外したので、このファイルは作りません".format(out))
                    continue
                r.stop("FORMAT  {} に残る part がありません。".format(out))
                continue
            body = "\n".join(texts)
            if out == "SKILL.md" and fm is not None:
                body = fm + "\n" + body
            outputs.append((out, body))
        if skill != 1:
            r.stop("FORMAT  documents に SKILL.md がちょうど1つありません。")
        return outputs

    # --- スクリプト

    def py(self, rel, label):
        if rel in self.py_cache:
            return self.py_cache[rel]
        path = self.source_path(rel, label)
        text = None
        if path is not None:
            text, error = read_strict(path)
            if error:
                self.report.stop("MISSING file  {}: {}".format(rel, error))
                text = None
        self.py_cache[rel] = text
        return text

    def build_scripts(self):
        outputs = []
        for s, entry in enumerate(self.scripts):
            if not isinstance(entry, dict):
                self.report.stop("FORMAT  scripts[{}] がオブジェクトではありません。".format(s))
                continue
            if self.dropped(entry):
                continue
            label = "scripts[{}] {}".format(s, entry_id(entry))
            spec = self.extract_spec(entry, label)
            if spec is not None:
                outputs += self.build_extract(spec)
        return outputs

    def extract_spec(self, entry, label):
        """抽出の項目を、2つの書き方（scripts[] の extract と、scripts.json の1つの抽出）から同じ形にする。"""
        r = self.report
        spec = {"label": label, "id": entry_id(entry), "holder": entry}
        if entry.get("format") == SCRIPTS_SINGLE_FORMAT:
            allowed = {"format", "format_version", "version", "source", "id", "note", "modules", "roots", "strip",
                       "limits", "packing", "allowed_imports", "unicode_notice", "own", "outputs", "names", "watch",
                       "provides", "allow_unresolved"}
            if not check_keys(r, entry, allowed, label):
                return None
            modules = []
            mapping = {}
            for m in entry.get("modules") or []:
                if not check_keys(r, m, {"id", "source", "from_modules", "note"}, label + " の modules の項目"):
                    return None
                modules.append({"name": m.get("id"), "source": m.get("source")})
                for target, names in (m.get("from_modules") or {}).items():
                    if not isinstance(names, list):
                        r.stop("FORMAT  {} の from_modules の {} は名前の並びにしてください。".format(label, target))
                        return None
                    for name in names:
                        mapping.setdefault(m.get("id"), {})[name] = target
            spec["modules"] = modules
            spec["mapping"] = mapping
            strip = entry.get("strip", {"comments": True, "docstrings": True, "blank_lines": "collapse"})
            if not check_keys(r, strip, {"comments", "docstrings", "blank_lines"}, label + " の strip") \
                    or strip.get("blank_lines", "collapse") != "collapse":
                r.stop("FORMAT  {} の strip の blank_lines は collapse にしてください。".format(label))
                return None
            spec["strip"] = [k for k in ("comments", "docstrings") if strip.get(k)]
            lim = entry.get("limits") or {}
            if not check_keys(r, lim, {"part_body_bytes", "file_bytes", "note"}, label + " の limits"):
                return None
            spec["limit"] = lim.get("part_body_bytes")
            spec["max_bytes"] = lim.get("file_bytes", limits.SCRIPT_MAX_BYTES)
            if entry.get("packing", "scc") != "scc":
                r.stop("FORMAT  {} の packing は scc にしてください。".format(label))
                return None
            spec["notice"] = entry.get("unicode_notice")
            own = {}
            for item in entry.get("own") or []:
                if not check_keys(r, item, {"id", "text", "text_sha256", "reason", "note"}, label + " の own の項目"):
                    return None
                own[item.get("id")] = self.own_text(item, "{} own {}".format(spec["id"], item.get("id")), "text")
            plan = []
            for o in entry.get("outputs") or []:
                if not check_keys(r, o, {"output", "head", "tail", "note"}, label + " の outputs の項目"):
                    return None
                head, tail = [], []
                for key, target in (("head", head), ("tail", tail)):
                    for oid in o.get(key, []):
                        if oid not in own:
                            r.stop("FORMAT  {} の outputs の {} にある own の id「{}」がありません。".format(label, key, oid))
                            return None
                        if own[oid] is not None:
                            target.append(own[oid])
                plan.append({"output": o.get("output"), "head": head, "tail": tail})
            if not plan:
                r.stop("FORMAT  {} に outputs がありません。".format(label))
                return None
            spec["plan"] = plan
            spec["auto_loader"] = None
            spec["emit_imports"] = False
            spec["watch"] = entry.get("watch") or []
        else:
            allowed = {"kind", "id", "note", "modules", "imports", "roots", "provides", "allow_unresolved", "strip",
                       "notice", "allowed_imports", "packing", "names", "watch", "emit_imports"}
            if not check_keys(r, entry, allowed, label):
                return None
            if entry.get("kind") != "extract":
                r.stop("FORMAT  {} の kind は extract にしてください。".format(label))
                return None
            modules = []
            for m in entry.get("modules") or []:
                if not check_keys(r, m, {"name", "source", "note"}, label + " の modules の項目"):
                    return None
                modules.append({"name": m.get("name"), "source": m.get("source")})
            spec["modules"] = modules
            explicit = entry.get("imports", {})
            if not isinstance(explicit, dict) or not all(isinstance(v, dict) for v in explicit.values()):
                r.stop("FORMAT  {} の imports は {{モジュール: {{名前: 出どころ}}}} にしてください。".format(label))
                return None
            spec["mapping"] = explicit
            strip = entry.get("strip", ["comments", "docstrings"])
            if not isinstance(strip, list) or any(x not in ("comments", "docstrings") for x in strip):
                r.stop("FORMAT  {} の strip は comments と docstrings の並びにしてください。".format(label))
                return None
            spec["strip"] = strip
            spec["notice"] = entry.get("notice")
            packing = entry.get("packing")
            if not check_keys(r, packing, {"limit", "max_bytes", "parts", "last", "part_head", "loader", "last_head",
                                           "last_tail", "note"}, label + " の packing"):
                return None
            spec["limit"] = packing.get("limit")
            spec["max_bytes"] = packing.get("max_bytes", limits.SCRIPT_MAX_BYTES)
            own = {}
            for key in ("part_head", "loader", "last_head", "last_tail"):
                item = packing.get(key)
                if item is None:
                    own[key] = None
                    continue
                if not check_keys(r, item, {"text", "text_sha256", "note"}, "{} の packing の {}".format(label, key)):
                    return None
                own[key] = self.own_text(item, "{} packing {}".format(spec["id"], key), "text")
            last = packing.get("last")
            if not safe_rel(last) or not last.endswith(".py"):
                r.stop("FORMAT  {} の packing の last は .py の相対のパスにしてください。".format(label))
                return None
            pattern = packing.get("parts")

            def plan_for(n, own=own, last=last, pattern=pattern):
                if n > 1 and (not isinstance(pattern, str) or "{n}" not in pattern or not pattern.endswith(".py")
                              or not safe_rel(pattern.replace("{n}", "1"))):
                    return None
                parts = [{"output": pattern.replace("{n}", str(i + 1)), "head": [own["part_head"]] if own["part_head"] else [],
                          "tail": []} for i in range(n - 1)]
                parts.append({"output": last, "head": [own["last_head"]] if own["last_head"] else [],
                              "tail": [own["last_tail"]] if own["last_tail"] else []})
                return parts

            spec["plan"] = plan_for
            spec["auto_loader"] = own["loader"]
            spec["emit_imports"] = entry.get("emit_imports", True)
            spec["watch"] = entry.get("watch") or []
        spec["roots"] = entry.get("roots")
        spec["provides"] = entry.get("provides", [])
        spec["allow_unresolved"] = entry.get("allow_unresolved", [])
        spec["allowed_imports"] = entry.get("allowed_imports")
        limit, max_bytes = spec["limit"], spec["max_bytes"]
        if not isinstance(limit, int) or limit < 1 or not isinstance(max_bytes, int) \
                or max_bytes > limits.SCRIPT_MAX_BYTES:
            r.stop("FORMAT  {} の部品の上限（limit、max_bytes {}以下）を整数で書いてください。".format(
                label, limits.SCRIPT_MAX_BYTES))
            return None
        if spec["notice"] not in (None, "unicode"):
            r.stop("FORMAT  {} の Unicode の通知は null か \"unicode\" にしてください。".format(label))
            return None
        if not isinstance(spec["provides"], list) or not isinstance(spec["allow_unresolved"], list):
            r.stop("FORMAT  {} の provides と allow_unresolved は並びにしてください。".format(label))
            return None
        return spec

    def build_extract(self, spec):
        r = self.report
        label = spec["label"]
        stops_before = len(r.stops)
        strip = spec["strip"]
        # モジュール
        modules = []
        by_name = {}
        if not spec["modules"]:
            r.stop("FORMAT  {} に modules がありません。".format(label))
            return []
        for m in spec["modules"]:
            name, rel = m.get("name"), m.get("source")
            if not isinstance(name, str) or not IDENT_RE.match(name) or name in by_name:
                r.stop("FORMAT  {} のモジュールの名前「{}」が識別子でないか、重なっています。".format(label, name))
                return []
            text = self.py(rel, label)
            if text is None:
                return []
            mod = PyModule(name, len(modules), rel, text, r)
            if not mod.ok:
                return []
            modules.append(mod)
            by_name[name] = mod
        stems = {m.stem: m for m in modules}
        # 別のモジュールから読む名前（try の中の from ... import から作り、表に書いた分を足す）
        mapping = {m.name: {} for m in modules}
        for m in modules:
            for modname, level, aliases in m.skipped_imports:
                target = stems.get(modname.split(".")[-1]) if modname else None
                if target is None or target is m:
                    continue
                for name, asname in aliases:
                    if asname and asname != name:
                        r.stop("UNRESOLVED  {} の from {} import {} as {} は名前を替えているので扱えません。".format(
                            m.relpath, modname, name, asname))
                        continue
                    mapping[m.name][name] = target.name
            for u in [u for u in m.units if u.is_import and isinstance(u.node, ast.ImportFrom)]:
                target = stems.get((u.node.module or "").split(".")[-1])
                if target is not None and target is not m:
                    for name in u.defines:
                        mapping[m.name][name] = target.name
                        m.defs[name] = [x for x in m.defs[name] if x is not u]
                        if not m.defs[name]:
                            del m.defs[name]
                    m.units.remove(u)
        for modname, names in spec["mapping"].items():
            if modname not in by_name:
                r.stop("FORMAT  {} の、名前の出どころを書いたモジュール「{}」が modules にありません。".format(label, modname))
                continue
            for name, target in names.items():
                if target not in by_name:
                    r.stop("FORMAT  {} の {} の出どころ「{}」が modules にありません。".format(label, name, target))
                    continue
                mapping[modname][name] = target
        for m in modules:
            for name, target in sorted(mapping[m.name].items()):
                if by_name[target].index > m.index:
                    r.stop("FORMAT  {} の modules で、{} が読む {} を先に書いてください。".format(label, m.name, target))

        def resolve(mod, name):
            if name in mod.defs:
                return mod.defs[name]
            target = mapping[mod.name].get(name)
            if target:
                return by_name[target].defs.get(name, [])
            return []

        def binder(u, name):
            return u.binders[name] if u.is_import else ("unit", u.mod.name, u.start)

        provides = spec["provides"]
        allowed_unresolved = set()
        for a in spec["allow_unresolved"]:
            if not check_keys(r, a, {"module", "name", "reason"}, label + " の allow_unresolved の項目") or not a.get("reason"):
                r.stop("FORMAT  {} の allow_unresolved の項目に module、name、reason を書いてください。".format(label))
                continue
            allowed_unresolved.add((a.get("module"), a.get("name")))
        # 閉包
        roots = spec["roots"]
        if not isinstance(roots, list) or not roots:
            r.stop("FORMAT  {} に roots がありません。".format(label))
            return []
        stack = []
        root_units = []
        for root in roots:
            if not check_keys(r, root, {"module", "name", "note"}, label + " の roots の項目") or root.get("module") not in by_name:
                r.stop("FORMAT  {} の roots の項目「{}」のモジュールが modules にありません。".format(label, root))
                continue
            mod = by_name[root["module"]]
            found = resolve(mod, root.get("name"))
            if not found:
                r.stop("MISSING name  {}  {}".format(mod.relpath, root.get("name")))
                continue
            root_units.append(found[0])
            stack.extend(reversed(found))
        closure = set()
        while stack:
            u = stack.pop()
            if u in closure:
                continue
            closure.add(u)
            if u.mod.shared_lines and u.start in u.mod.shared_lines:
                r.stop("FORMAT  {} の{}行目は、ほかの文と同じ行にあるので行で取り出せません。".format(u.mod.relpath, u.start))
            for name in sorted(n for n in u.refs if isinstance(n, str)):
                found = resolve(u.mod, name)
                if found:
                    ids = {binder(x, name) for x in found}
                    if len(ids) > 1:
                        r.stop("DUPLICATE name  {}  {} を定義する文が{}つあります（{}行目）。".format(
                            found[0].mod.relpath, name, len(found), "、".join(str(x.start) for x in found)))
                    stack.extend(reversed(found))
                    continue
                if (u.mod.name, name) in allowed_unresolved or name in provides:
                    continue
                if name in u.mod.skipped_names:
                    r.stop("UNRESOLVED  {}  {} は名前で取り出せない文（try、if など）の中で定義されています"
                           "（{}行目の文が使う）。provides か allow_unresolved に書いてください。".format(
                               u.mod.relpath, name, u.start))
                elif not ignorable_name(name):
                    r.stop("UNDEFINED  {}  {} がどこにも定義されていません（{}行目の文が使う）。".format(
                        u.mod.relpath, name, u.start))
            stack.extend(u.attached)
        body = sorted((u for u in closure if not u.is_import), key=Unit.key)
        by_defined = {}
        for u in body:
            for name in u.defines:
                by_defined.setdefault(name, set()).add(binder(u, name))
        for name in sorted(by_defined):
            if len(by_defined[name]) > 1:
                r.stop("CLASH  {}  {} が別々のモジュールで定義されていて、1つの名前空間に入れられません。".format(label, name))
        body_by_name = {}
        for u in body:
            for name in u.defines:
                body_by_name.setdefault(name, u)
        # 名前の組の記録と、取り出さないが見張る名前
        current = []
        for u in body:
            if u.attach:
                continue
            group = [u] + sorted(u.attached, key=Unit.key)
            digest = sha_text("".join(x.raw() for x in group))
            for name in u.defines:
                current.append({"module": u.mod.name, "name": name, "stmts": len(group), "sha256": digest})
        self._review_names(spec["holder"], current, by_name, label)
        self._review_watch(spec, by_name, label)
        # 通知
        notices = {}
        for u in body:
            block = u.mod.notice_block(u)
            if any("Unicode License" in ln or "Derived from Unicode" in ln for ln in block):
                notices[u] = block
                if spec["notice"] != "unicode":
                    r.stop("NOTICE  {}  {}行目の {} は Unicode のデータ由来です。Unicode の通知を \"unicode\" にし、"
                           "copies に UNICODE-LICENSE.txt を入れてください。".format(u.mod.relpath, u.start, "、".join(u.defines)))
        if notices and not any(isinstance(c, dict) and c.get("output") == "UNICODE-LICENSE.txt" and not self.dropped(c)
                               for c in self.copies):
            r.stop("NOTICE  {}  Unicode のデータ由来の文を取り出すので、copies に UNICODE-LICENSE.txt が要ります。".format(label))
        if len(r.stops) > stops_before:
            return []
        # 並べる順と詰め方
        texts = {}
        for u in body:
            text = u.mod.strip(u, strip)
            if u in notices:
                text = "\n".join(notices[u]) + "\n" + text
            texts[u] = text
        body_set = set(body)

        def deps(u):
            out = set()
            for name in u.refs:
                for x in resolve(u.mod, name):
                    if x in body_set:
                        out.add(x)
            out.update(u.attached)
            return sorted(out, key=Unit.key)

        comps = tarjan([u for u in root_units if u in body_set] + body, deps, Unit.key)
        chunks = []
        current_chunk = []
        size = 0
        for comp in comps:
            s = sum(len(texts[u].encode("utf-8")) for u in comp)
            if current_chunk and size + s > spec["limit"]:
                chunks.append(current_chunk)
                current_chunk, size = [], 0
            current_chunk.extend(comp)
            size += s
        if current_chunk:
            chunks.append(current_chunk)
        plan = spec["plan"](len(chunks)) if callable(spec["plan"]) else spec["plan"]
        if plan is None:
            r.stop("FORMAT  {} は部品が{}つになるので、packing の parts に {{n}} を含む .py のパスを書いてください。".format(
                label, len(chunks)))
            return []
        if len(plan) != len(chunks):
            r.stop("PACKING  {}  部品は {}つになりましたが、outputs は {}つです（各部品の大きさ: {}）。outputs を直してください。".format(
                label, len(chunks), len(plan), "、".join("{:,}B".format(sum(len(texts[u].encode("utf-8")) for u in c))
                                                    for c in chunks)))
            return []
        folder = None
        for p in plan:
            if not safe_rel(p["output"]) or not p["output"].endswith(".py"):
                r.stop("FORMAT  {} の出力「{}」は .py の相対のパスにしてください。".format(label, p["output"]))
                return []
            if folder is None:
                folder = os.path.dirname(p["output"])
            elif os.path.dirname(p["output"]) != folder:
                r.stop("FORMAT  {} の部品はすべて同じフォルダに置いてください。".format(label))
                return []
        last_plan = plan[-1]
        self.cli_texts.extend(last_plan["head"] + last_plan["tail"])
        where = {}
        for k, chunk in enumerate(chunks):
            for u in chunk:
                where[u] = k
        modules_of = [p["output"].split("/")[-1][:-3] for p in plan]
        results = []
        records = []
        for k, chunk in enumerate(chunks):
            is_last = k == len(chunks) - 1
            chunk = sorted(chunk, key=Unit.key)
            out_path = plan[k]["output"]
            own_texts = plan[k]["head"] + plan[k]["tail"]
            if spec["auto_loader"] is not None:
                own_texts = own_texts + [spec["auto_loader"]]
            own_trees = []
            for t in own_texts:
                try:
                    own_trees.append((ast.parse(t), t))
                except SyntaxError as error:
                    r.stop("SYNTAX  {} の自前の文を読めません（{}行目: {}）。".format(label, error.lineno, error.msg))
                    return []
            imports = {}
            binds = {}

            def need(mod, name):
                found = resolve(mod, name)
                if not found:
                    return
                x = found[0]
                if x.is_import:
                    imports.setdefault(binder(x, name), (name, x))
                elif where[x] != k:
                    binds.setdefault(where[x], {})[name] = x

            for u in chunk:
                for name in sorted(n for n in u.refs if isinstance(n, str)):
                    need(u.mod, name)
            # 自前の文が使う、取り出した名前（根の名前を含む）も、その部品から読む
            for tree, source_text in own_trees:
                used = set(module_level_loads(tree))
                for _, names in symtable_globals(source_text, out_path):
                    used |= names
                for name in sorted(used):
                    x = body_by_name.get(name)
                    if x is not None and where[x] != k:
                        binds.setdefault(where[x], {})[name] = x
            if is_last:
                for root in roots:
                    mod = by_name.get(root.get("module"))
                    if mod is not None:
                        need(mod, root.get("name"))
            for j in binds:
                if j > k:
                    r.stop("INTERNAL  部品 {} が後ろの部品 {} の名前を使います。".format(k + 1, j + 1))
            import_units = sorted({id(x): x for _, x in imports.values()}.values(),
                                  key=lambda x: (not isinstance(x.node, ast.Import), x.mod.strip(x, strip)))
            import_texts = []
            if spec["emit_imports"]:
                for x in import_units:
                    t = x.mod.strip(x, strip)
                    if t not in import_texts:
                        import_texts.append(t)
            # 名前がぶつからないか（1つの名前が2つのものを指さないか）
            file_binders = {}

            def bind(name, ident, what):
                if name in file_binders and file_binders[name][0] != ident:
                    r.stop("CLASH  {} {}  名前 {} が2つのものを指します（{} と {}）。".format(
                        label, out_path, name, file_binders[name][1], what))
                file_binders.setdefault(name, (ident, what))

            if spec["emit_imports"]:
                for x in import_units:
                    for name, ident in x.binders.items():
                        bind(name, ident, "import")
            for u in chunk:
                for name in u.defines:
                    bind(name, binder(u, name), "取り出した定義")
            for j in sorted(binds):
                for name, x in binds[j].items():
                    bind(name, binder(x, name), "前の部品")
            for name in GENERATED_NAMES:
                bind(name, ("generated",), "生成の道具が足す名前")
            own_bound = {}
            for tree, _ in own_trees:
                ids = {}
                for node in tree.body:
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        ids.update(_import_binders(node))
                for name in sorted(_bound_names(tree.body)):
                    ident = ids.get(name, ("own",))
                    own_bound.setdefault(name, ident)
                    if name in provides:
                        continue
                    if name in file_binders and file_binders[name][0] != ident:
                        if ident == ("own",) and file_binders[name][0] == ("own",):
                            continue
                        r.stop("CLASH  {} {}  自前の文の名前 {} が{}とぶつかります。".format(
                            label, out_path, name, file_binders[name][1]))
                    file_binders.setdefault(name, (ident, "自前の文"))
            if not spec["emit_imports"]:
                for ident, (name, x) in sorted(imports.items(), key=lambda kv: kv[1][0]):
                    if own_bound.get(name) != ident:
                        r.stop("IMPORT  {} {}  取り出した文が使う {} を、自前の文が同じ import で読んでいません"
                               "（本体の {}行目）。".format(label, out_path, name, x.start))
            stanza = None
            if binds:
                if "_mini_bind" in own_bound:
                    stanza = "bind"
                elif "_mini_load" in own_bound:
                    stanza = "load"
                else:
                    r.stop("FORMAT  {} {} は前の部品を読むので、自前の文に _mini_load か _mini_bind が要ります。".format(
                        label, out_path))
                    return []
            text = self.render_script(plan[k], chunk, texts, import_texts, binds, modules_of, stanza,
                                      spec["auto_loader"] if binds else None)
            extra = set()
            for j in binds:
                extra.update(binds[j])
            try:
                compile(text, out_path, "exec")
                missing = undefined_globals(text, out_path, extra)
            except SyntaxError as error:
                r.stop("SYNTAX  生成した {} を読めません（{}行目: {}）。".format(out_path, error.lineno, error.msg))
                continue
            missing = [n for n in missing if n not in {a[1] for a in allowed_unresolved}]
            if missing:
                r.stop("UNRESOLVED  生成した {} で定義されていない名前があります: {}".format(out_path, "、".join(missing)))
            size = len(text.encode("utf-8"))
            if size > spec["max_bytes"]:
                r.stop("LIMIT  生成した {} が {:,}バイトあり、上限の {:,}バイトを超えます。".format(out_path, size, spec["max_bytes"]))
            if spec["allowed_imports"] is not None:
                used = limits.imported_modules(ast.parse(text))
                bad = sorted(m for m in used if m not in spec["allowed_imports"])
                if bad:
                    r.stop("IMPORT  生成した {} が allowed_imports にないモジュールを読みます: {}".format(out_path, "、".join(bad)))
            results.append((out_path, text))
            records.append({"output": out_path, "bytes": size, "units": len(chunk),
                            "body_bytes": sum(len(texts[u].encode("utf-8")) for u in chunk),
                            "names": ["{}:{}".format(u.mod.name, n) for u in chunk for n in u.defines],
                            "bound": ["{}:{}".format(modules_of[j], n) for j in sorted(binds) for n in sorted(binds[j])],
                            "imports": [t.rstrip("\n") for t in import_texts]})
        self.script_records.append({"id": spec["id"],
                                    "modules": [{"name": m.name, "source": m.relpath} for m in modules],
                                    "outputs": records})
        return results

    def _review_watch(self, spec, by_name, label):
        r = self.report
        for item in spec["watch"]:
            if not check_keys(r, item, {"module", "name", "stmts", "sha256", "reason", "note"}, label + " の watch の項目"):
                continue
            mod = by_name.get(item.get("module"))
            if mod is None:
                r.stop("FORMAT  {} の watch のモジュール「{}」が modules にありません。".format(label, item.get("module")))
                continue
            definers = [u for u in mod.defs.get(item.get("name"), []) if not u.is_import]
            if not definers:
                r.stop("MISSING name  {}  {}（watch）".format(mod.relpath, item.get("name")))
                continue
            u = definers[0]
            group = [u] + sorted(u.attached, key=Unit.key)
            digest = sha_text("".join(x.raw() for x in group))
            if item.get("sha256") != digest or item.get("stmts") != len(group):
                def apply(item=item, digest=digest, n=len(group)):
                    item["sha256"] = digest
                    item["stmts"] = n
                head = "NEW    " if item.get("sha256") is None else "CHANGED"
                r.review("{} watch     {}  {}:{} stmts {}→{}  {} → {}  （{}）".format(
                    head, label, os.path.basename(mod.relpath), item.get("name"), item.get("stmts"), len(group),
                    short(item.get("sha256")), short(digest), item.get("reason") or "見張る名前"), apply, mod.relpath)

    def _review_names(self, holder, current, by_name, label):
        recorded = holder.get("names")
        apply = lambda: holder.__setitem__("names", current)  # noqa: E731
        if recorded is None:
            self.report.review("NEW     name      {}  名前の組 {}件を記録します".format(label, len(current)), apply)
            return
        if not isinstance(recorded, list):
            self.report.stop("FORMAT  {} の names が並びではありません。".format(label))
            return
        rec = {}
        for item in recorded:
            if not check_keys(self.report, item, {"module", "name", "stmts", "sha256"}, label + " の names の項目"):
                return
            rec[(item.get("module"), item.get("name"))] = item
        cur = {(c["module"], c["name"]): c for c in current}
        for c in current:
            old = rec.get((c["module"], c["name"]))
            mod = by_name[c["module"]]
            where = "{}:{}".format(os.path.basename(mod.relpath), c["name"])
            if old is None:
                self.report.review("ADDED   name      {}  {} stmts {}  （なし） → {}".format(
                    label, where, c["stmts"], short(c["sha256"])), apply, mod.relpath)
            elif old.get("sha256") != c["sha256"] or old.get("stmts") != c["stmts"]:
                self.report.review("CHANGED name      {}  {} stmts {}→{}  {} → {}".format(
                    label, where, old.get("stmts"), c["stmts"], short(old.get("sha256")), short(c["sha256"])),
                    apply, mod.relpath)
        for key, old in rec.items():
            if key in cur:
                continue
            mod = by_name.get(key[0])
            if mod is None:
                self.report.stop("MISSING name  {}  names のモジュール {} が modules にありません。".format(label, key[0]))
            elif key[1] in mod.defs:
                self.report.review("REMOVED name      {}  {}:{}（閉包に入らなくなった）".format(
                    label, os.path.basename(mod.relpath), key[1]), apply, mod.relpath)
            else:
                self.report.stop("MISSING name  {}  {}".format(mod.relpath, key[1]))
        if [(c["module"], c["name"]) for c in current] != [(o.get("module"), o.get("name")) for o in recorded] \
                and not any(line.startswith(("ADDED", "REMOVED")) and label in line for line, _ in self.report.reviews):
            # 中身は同じで並びだけが違うときは、見直しにせず並びを直す（--accept のときだけ書く）
            self.report.reorder.append(apply)

    def render_script(self, plan, chunk, texts, import_texts, binds, modules_of, stanza, loader):
        heads = list(plan["head"])
        shebang = ""
        if heads and heads[0].startswith("#!"):
            first, _, rest = heads[0].partition("\n")
            shebang = first + "\n"
            heads[0] = rest if rest.strip() else ""
        src = self.source
        top = (shebang
               + "# yomiyasu-mini {}。{} {}（{}）から tools/generate.py で生成した。手で直さない。\n".format(
                   self.version, src["repository"], src["tag"], src["commit"])
               + "# 取り出した名前と中身の sha256 は extract/scripts.json と MANIFEST.json にある。\n")
        sections = [h for h in heads if h.strip()]
        sections.append('__version__ = "{}"\nSOURCE_TAG = "{}"\nSOURCE_COMMIT = "{}"\n'.format(
            self.version, src["tag"], src["commit"]))
        if import_texts:
            sections.append("".join(import_texts))
        if binds:
            lines = []
            for j in sorted(binds):
                names = " ".join(sorted(binds[j]))
                if stanza == "bind":
                    lines.append('_mini_bind("{}", "{}")\n'.format(modules_of[j], names))
                else:
                    lines.append('_mini_m = _mini_load("{}")\nfor _mini_n in "{}".split():\n'
                                 '    globals()[_mini_n] = getattr(_mini_m, _mini_n)\n'.format(modules_of[j], names))
            sections.append((loader + "\n" if loader else "") + "".join(lines))
        body = []
        prev = None
        for u in chunk:
            if prev is not None and not (prev.mod is u.mod and prev.end + 1 == u.start):
                body.append("\n")
            body.append(texts[u])
            prev = u
        sections.append("".join(body))
        sections.extend(t for t in plan["tail"] if t.strip())
        return top + "\n".join(sections)

    # --- 写し

    def build_copies(self):
        r = self.report
        outputs = []
        for c, copy in enumerate(self.copies):
            label = "copies[{}]".format(c)
            if not check_keys(r, copy, {"output", "from_repo", "source", "sha256", "id", "note"}, label):
                continue
            if self.dropped(copy):
                continue
            out = copy.get("output")
            if not safe_rel(out):
                r.stop("FORMAT  {} の output「{}」が相対のパスではありません。".format(label, out))
                continue
            if ("from_repo" in copy) == ("source" in copy):
                r.stop("FORMAT  {} には from_repo か source のどちらか1つを書いてください。".format(label))
                continue
            if "from_repo" in copy:
                rel = copy["from_repo"]
                path = os.path.join(self.base, rel) if safe_rel(rel) else None
            else:
                rel = copy["source"]
                path = self.source_path(rel, label)
            if path is None:
                r.stop("FORMAT  {} のパス「{}」が相対のパスではありません。".format(label, rel))
                continue
            try:
                with open(path, "rb") as handle:
                    data = handle.read()
            except OSError:
                r.stop("MISSING file  {}".format(rel))
                continue
            if "source" in copy:
                self.check_hash(copy, "sha256", sha_bytes(data), "copy      {}  {}".format(label, rel), rel)
            outputs.append((out, data))
        return outputs

    # --- 参照の検査

    def main_lint_rules(self):
        path = os.path.join(self.tree, self.source["skill_dir"], "scripts", "yomiyasu_lint.py")
        text, error = read_strict(path)
        if error:
            return set()
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return set()
        rule_like = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
        out = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Dict):
                for k, v in zip(n.keys, n.values):
                    if isinstance(k, ast.Constant) and k.value == "rule" and isinstance(v, ast.Constant) \
                            and isinstance(v.value, str):
                        out.add(v.value)
            elif isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "rule" for t in n.targets) \
                    and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str):
                out.add(n.value.value)
            elif isinstance(n, ast.keyword) and n.arg == "rule" and isinstance(n.value, ast.Constant) \
                    and isinstance(n.value.value, str):
                out.add(n.value.value)
        for n in tree.body:
            targets = n.targets if isinstance(n, ast.Assign) else ([n.target] if isinstance(n, ast.AnnAssign) else [])
            if any(isinstance(t, ast.Name) and "RULE" in t.id for t in targets) and n.value is not None:
                for c in ast.walk(n.value):
                    if isinstance(c, ast.Constant) and isinstance(c.value, str) and rule_like.match(c.value):
                        out.add(c.value)
        return {x for x in out if rule_like.match(x)}

    def check_references(self, md_outputs, py_texts):
        relaxed = bool(self.args.measure_variant)
        r = self.report
        files = set(self.bundle)
        md_names = {}
        for path in files:
            if path.endswith(".md"):
                md_names.setdefault(path.split("/")[-1], []).append(path)
        py_names = {p.split("/")[-1] for p in files if p.endswith(".py")}
        cli = "\n".join(self.cli_texts)
        all_py = "\n".join(py_texts)
        mini_options = set(re.findall(r"--[a-z][a-z0-9-]*", cli)) | {"--help"}
        rules = self.main_lint_rules()
        rule_rx = re.compile(r"(?<![A-Za-z0-9_])(?:{})(?![A-Za-z0-9_])".format(
            "|".join(re.escape(x) for x in sorted(rules, key=lambda x: (-len(x), x))))) if rules else None
        content_rx = re.compile(r"((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_-]+\.md)\s*(?:の\s*)?「([^」\n]+)」")
        path_rx = re.compile(r"(?<![A-Za-z0-9_./-])(?:\.\./)?((?:references|scripts)/[A-Za-z0-9_./*<>{}-]*)")
        file_rx = re.compile(r"(?<![A-Za-z0-9_./-])((?:\.\./)*(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_-]+\.(?:md|py))(?![A-Za-z0-9_])")
        texts = dict(md_outputs)
        stripped = {p: content_rx.sub("", t) for p, t in texts.items()}

        def allowed(text, s, e):
            for item in self.allow:
                a = item.get("text") or ""
                start = text.find(a)
                while start >= 0:
                    if start <= s and e <= start + len(a):
                        return True
                    start = text.find(a, start + 1)
            return False

        for path in sorted(texts):
            text = texts[path]
            found = []

            def add(m, message, missing_target=False, group=0):
                s, e = m.span(group)
                if allowed(text, s, e):
                    return
                line = text.count("\n", 0, s) + 1
                found.append((s, "REF  {}:{}  「{}」: {}".format(path, line, m.group(group), message), missing_target))

            covered = []
            for m in content_rx.finditer(text):
                target_name, phrase = m.group(1), m.group(2)
                covered.append(m.span())
                base = target_name.split("/")[-1]
                if "/" in target_name:
                    targets = [target_name] if target_name in files else []
                else:
                    targets = md_names.get(base, [])
                if not targets:
                    add(m, "mini にないファイルの中身を指しています", True)
                elif not any(phrase in stripped[t] for t in targets if t in stripped):
                    add(m, "{} に「{}」がありません".format(targets[0], phrase), True)
            for m in path_rx.finditer(text):
                ref = m.group(1).rstrip(".")
                if ref in files or (ref.endswith("/") and any(f.startswith(ref) for f in files)):
                    continue
                add(m, "mini の出力にないファイルです", True, 1)
            for m in file_rx.finditer(text):
                name = m.group(1)
                if any(a <= m.start() < b for a, b in covered):
                    continue
                if "/" in name:
                    bare = name
                    while bare.startswith("../"):
                        bare = bare[3:]
                    if bare.startswith(("references/", "scripts/")):
                        continue
                    if bare not in files:
                        add(m, "mini の出力にないファイルです", True)
                    continue
                if name == "SKILL.md":
                    tail = text[m.end():m.end() + 8]
                    if re.match(r"\s*\d+\s*章[）)、。」]", tail):
                        chapter = re.match(r"\s*(\d+)", tail).group(1)
                        skill = texts.get("SKILL.md", "")
                        if re.search(r"(?m)^## {}\. ".format(chapter), skill):
                            continue
                    add(m, "SKILL.md の中身への参照です。行き先を置き換えて記録するか、reference_allow に書いてください")
                    continue
                if name.endswith(".md") and name in md_names:
                    continue
                if name.endswith(".py") and name in py_names:
                    continue
                add(m, "mini の出力にないファイルです", True)
            for m in re.finditer(r"yomiyasu_(?:lint|diff|check|hook)", text):
                add(m, "本体の道具の名前です")
            for m in re.finditer(r"(?<![A-Za-z0-9_-])--[a-z][a-z0-9-]*", text):
                if m.group(0) not in mini_options:
                    add(m, "mini のスクリプトにないオプションです", True)
            for m in re.finditer(r"(?<![A-Za-z0-9_-])(?:run|verify)(?![A-Za-z0-9_-])", text):
                add(m, "本体の check のコマンドです")
            if rule_rx is not None:
                for m in rule_rx.finditer(text):
                    add(m, "本体 lint の規則の名前です")
            for m in re.finditer(r"■ ?[^\s「」『』`、。，．（）()：:]*", text):
                if m.group(0) not in all_py or m.group(0).strip() == "■":
                    add(m, "本体の出力の節の名前です")
            for _, message, missing in sorted(found):
                if relaxed and missing:
                    r.note("参照の欠け（測定用の写しなので止めない）: " + message[5:])
                else:
                    r.stop(message)

    def check_outputs(self, md_outputs, py_texts):
        r = self.report
        for path, text in md_outputs:
            doc = MdDoc(text)
            if doc.unclosed_fence is not None:
                r.stop("FORMAT  生成した {} の{}行目の囲みのコードが閉じていません。".format(path, doc.unclosed_fence + 1))
            for i in doc.setext:
                r.stop("FORMAT  生成した {} の{}行目が setext の見出しに読めます。".format(path, i + 1))
            keys = doc.keys()
            for key in sorted(set(keys), key=keys.index):
                if keys.count(key) > 1:
                    r.stop("FORMAT  生成した {} で、見出し {} が{}回あります（見出しで指せなくなります）。".format(
                        path, heading_label(key[0], key[2], key[1]), keys.count(key)))
        for item in self.forbidden:
            for path, text in list(md_outputs) + list(py_texts):
                if item in text:
                    line = text.count("\n", 0, text.find(item)) + 1
                    r.stop("FORBIDDEN  {}:{}  禁止の文字列「{}」があります。".format(path, line, item))

    # --- 全体

    def run(self):
        args = self.args
        r = self.report
        if args.check and args.accept:
            r.stop("USAGE  --check と --accept は一緒に使えません。")
            raise Fatal()
        if args.drop and not args.measure_variant:
            r.stop("USAGE  --drop は測定用です。--measure-variant と一緒に使ってください。")
            raise Fatal()
        if args.measure_variant:
            if args.check or args.accept:
                r.stop("USAGE  --measure-variant は --check や --accept と一緒に使えません。")
                raise Fatal()
            allowed_root = os.path.realpath(os.path.join(self.base, "measurement", "variants"))
            if not args.out or not self.out_root.startswith(allowed_root + os.sep):
                r.stop("USAGE  --measure-variant の出力先は {}/ の下のフォルダにしてください（本番の出力には書けません）。".format(
                    allowed_root))
                raise Fatal()
        if not os.path.isdir(self.tree):
            r.stop("MISSING file  本体の木がありません: {}".format(args.source))
            raise Fatal()
        self.load_tables()
        self.verify_commit()
        self.expand_drop()
        docs = self.build_documents()
        scripts = self.build_scripts()
        copies = self.build_copies()
        for path, data in [(p, t.encode("utf-8")) for p, t in docs] + [(p, t.encode("utf-8")) for p, t in scripts] \
                + copies:
            if path in self.bundle:
                r.stop("FORMAT  出力のファイル {} が2つの項目から作られます。".format(path))
            self.bundle[path] = data
        py_texts = [(p, t) for p, t in scripts]
        if not r.stops:
            self.check_references(docs, [t for _, t in py_texts])
            self.check_outputs(docs, py_texts)
            if not args.measure_variant:
                for problem in limits.files_problems(self.bundle, self.root_name, self.file_budget):
                    r.stop("LIMIT  " + problem)
        if r.stops:
            return 2
        if r.reviews and not args.accept:
            self.print_reviews()
            return 3
        if args.accept:
            for apply in r.reorder:
                apply()
        if args.accept and r.reviews:
            for _, apply in r.reviews:
                apply()
            self.print_reviews()
        table_entries = []
        new_tables = []
        for path, raw, obj in self.tables:
            data = dump_json(obj).encode("utf-8") if args.accept else raw
            new_tables.append((path, raw, data))
            table_entries.append({"path": os.path.relpath(path, self.base).replace(os.sep, "/"), "sha256": sha_bytes(data)})
        for rel, data in sorted(self.bundle.items()):
            self.files[self.output_dir + "/" + rel] = data
        manifest = self.manifest(table_entries)
        self.files["MANIFEST.json"] = dump_json(manifest).encode("utf-8")
        if args.check:
            return self.compare()
        code = self.write(new_tables)
        if code == 0:
            for note in r.notes:
                print("{}: {}".format(PROG, note), file=sys.stderr)
            print("{}: 生成しました（{}、{} {}）。ファイル {}個を {} に書きました。".format(
                PROG, self.version, self.source["tag"], self.source["commit"][:7], len(self.bundle),
                os.path.join(self.out_root, self.output_dir)))
        return code

    def manifest(self, table_entries):
        files = []
        for path in sorted(self.files, key=lambda p: p.encode("utf-8")):
            data = self.files[path]
            entry = {"path": path, "bytes": len(data)}
            try:
                entry["chars"] = len(data.decode("utf-8"))
            except UnicodeDecodeError:
                pass
            entry["sha256"] = sha_bytes(data)
            files.append(entry)
        provenance = []
        fm = self.table.get("front_matter", {})
        provenance.append({"output": "SKILL.md", "region": "front_matter", "description": fm.get("description")})
        for doc in self.documents:
            if self.dropped(doc):
                continue
            for i, part in enumerate(doc.get("parts", [])):
                if self.dropped(part):
                    continue
                item = {"output": doc.get("output"), "part": i}
                item.update(part)
                provenance.append(item)
        manifest = {"format": MANIFEST_FORMAT, "format_version": FORMAT_VERSION, "version": self.version,
                    "source": {"repository": self.source["repository"], "tag": self.source["tag"],
                               "commit": self.source["commit"]},
                    "output_dir": self.output_dir, "tables": table_entries}
        if self.args.measure_variant:
            manifest["measure_variant"] = True
            manifest["dropped"] = sorted(self.drop)
        manifest["files"] = files
        manifest["provenance"] = provenance
        manifest["scripts"] = self.script_records
        manifest["copies"] = [c for c in self.copies if not self.dropped(c)]
        return manifest

    def disk_state(self):
        out_dir = os.path.join(self.out_root, self.output_dir)
        on_disk = set()
        if os.path.isdir(out_dir):
            for current, dirs, names in os.walk(out_dir):
                dirs.sort()
                for name in names:
                    full = os.path.join(current, name)
                    on_disk.add(os.path.relpath(full, self.out_root).replace(os.sep, "/"))
        return out_dir, on_disk

    def compare(self):
        _, on_disk = self.disk_state()
        differ = []
        for path in sorted(self.files):
            full = os.path.join(self.out_root, path)
            try:
                with open(full, "rb") as handle:
                    data = handle.read()
            except OSError:
                differ.append("MISSING  " + path)
                continue
            if data != self.files[path]:
                differ.append("DIFFERS  " + path)
        for path in sorted(on_disk - set(self.files)):
            differ.append("EXTRA    " + path)
        if differ:
            print("{}: 生成したものが今のファイルと違います（{}件）。".format(PROG, len(differ)))
            for line in differ:
                print(line)
            return 4
        print("{}: 生成したものは今のファイルと同じです（{}、ファイル {}個）。".format(PROG, self.version, len(self.bundle)))
        return 0

    def write(self, new_tables):
        r = self.report
        out_dir, on_disk = self.disk_state()
        old = set()
        manifest_path = os.path.join(self.out_root, "MANIFEST.json")
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path, encoding="utf-8") as handle:
                    old = {f["path"] for f in json.load(handle).get("files", [])}
            except (OSError, ValueError, KeyError, TypeError, AttributeError):
                old = set()
        extra = sorted(on_disk - set(self.files))
        unknown = [p for p in extra if p not in old]
        for p in unknown:
            r.stop("EXTRA  {} に抽出表にないファイル {} があります。消すか移してから生成してください。".format(out_dir, p))
        if r.stops:
            return 2
        for path, raw, data in new_tables:
            if data != raw:
                _write_bytes(path, data)
        for path in sorted(self.files):
            if path == "MANIFEST.json":
                continue
            _write_bytes(os.path.join(self.out_root, path), self.files[path])
        for p in extra:
            os.remove(os.path.join(self.out_root, p))
        for current, dirs, names in sorted(os.walk(out_dir, topdown=False), reverse=True):
            if current != out_dir and not os.listdir(current):
                os.rmdir(current)
        _write_bytes(manifest_path, self.files["MANIFEST.json"])
        return 0

    def print_reviews(self):
        r = self.report
        src = self.source
        print("{}: 見直しが要る節 {}件（抽出表 {} {} → 元の木 {}）".format(
            PROG, len(r.reviews), src["tag"], src["commit"][:7], (getattr(self, "tree_commit", None) or "?")[:7]))
        for line, _ in r.reviews:
            print(line)
        if r.changed_sources:
            print("差分を見るには: git -C {} diff {} {} -- {}".format(
                self.args.source, src["tag"], getattr(self, "tree_commit", None) or "HEAD",
                " ".join(r.changed_sources)))
        if self.args.accept:
            print("--accept を付けたので、抽出表のハッシュを今の値に書き換えて生成しました。")
        else:
            print("読んで直してから、--accept を付けて生成してください。何も書いていません。")

    def print_stops(self):
        print("{}: 止めました。何も書いていません。".format(PROG), file=sys.stderr)
        for line, details in self.report.stops:
            print(line, file=sys.stderr)
            for d in details:
                print("  " + d, file=sys.stderr)


def _write_bytes(path, data):
    try:
        with open(path, "rb") as handle:
            if handle.read() == data:
                return
    except OSError:
        pass
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp = path + ".tmp-generate"
    with open(temp, "wb") as handle:
        handle.write(data)
    os.replace(temp, path)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="generate.py", description="本体 yomiyasu の木と抽出表から yomiyasu-mini を作ります。",
        epilog="終了コード: 0 成功、2 止めた、3 中身のハッシュが変わった（見直しの一覧）、4 --check で違う。")
    parser.add_argument("--source", required=True, metavar="本体の木", help="nanaism/yomiyasu を取り出したフォルダ。")
    parser.add_argument("--commit", metavar="40桁", help="git の木でない写しを使うときのコミット。")
    parser.add_argument("--table", metavar="抽出表", help="既定は extract/table.json。")
    parser.add_argument("--out", metavar="出力の根", help="既定は抽出表のフォルダの1つ上。")
    parser.add_argument("--check", action="store_true", help="書かずに、今あるファイルとバイトで比べます。")
    parser.add_argument("--accept", action="store_true", help="ハッシュが変わっていても書き、抽出表を書き換えます。")
    parser.add_argument("--drop", nargs="+", action="extend", metavar="id", help="測定用。外す id。")
    parser.add_argument("--measure-variant", action="store_true", help="測定用の写しを measurement/variants/ の下に作ります。")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    gen = Generator(args)
    try:
        code = gen.run()
    except Fatal:
        code = 2
    if code == 2:
        gen.print_stops()
    return code


if __name__ == "__main__":
    sys.exit(main())
