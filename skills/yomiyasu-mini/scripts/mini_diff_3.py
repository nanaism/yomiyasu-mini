# yomiyasu-mini 1.2.0。nanaism/yomiyasu v2.5.0（29d67ccb05e370b5958d72920a9cd1aa829dee80）から tools/generate.py で生成した。手で直さない。
# 取り出した名前と中身の sha256 は extract/scripts.json と MANIFEST.json にある。
"""yomiyasu-mini の意味の検査の部品。本体の yomiyasu_diff.py と markdown_visibility.py の定義を、元の字のまま入れている。
単独では使わない。同じフォルダの mini_check.py が読む。"""
import os
import re
import difflib
import unicodedata
from array import array
from bisect import bisect_left, bisect_right
from collections import Counter, OrderedDict


def _mini_on_error(name, error):
    raise ImportError("{}.py を読めません（{}: {}）".format(name, type(error).__name__, error)) from error

import hashlib as _mini_hashlib
import os as _mini_os
import sys as _mini_sys
import types as _mini_types


def _mini_load(name):
    """同じフォルダの name.py を読む。鍵に版と、フォルダの場所と中身の sha256 の頭を入れ、ほかの写しと混ぜない。
    __pycache__ は作らない。"""
    try:
        here = __file__
    except NameError:
        raise ImportError("部品の場所が分かりません（__file__ がありません）") from None
    folder = _mini_os.path.dirname(_mini_os.path.realpath(here))
    path = _mini_os.path.join(folder, name + ".py")
    with open(path, "rb") as handle:
        data = handle.read()
    digest = _mini_hashlib.sha256(folder.encode("utf-8", "surrogatepass") + b"\0" + data).hexdigest()
    key = "yomiyasu_mini_{}_{}_{}".format(__version__.replace(".", "_").replace("-", "_"), name, digest[:16])
    module = _mini_sys.modules.get(key)
    if module is None:
        module = _mini_types.ModuleType(key)
        module.__file__ = path
        code = compile(data, path, "exec", dont_inherit=True)
        _mini_sys.modules[key] = module
        try:
            exec(code, module.__dict__)
        except BaseException:
            del _mini_sys.modules[key]
            raise
    return module


def _mini_bind(name, names):
    try:
        module = _mini_load(name)
        space = globals()
        for key in names.split():
            space[key] = getattr(module, key)
    except Exception as error:
        _mini_on_error(name, error)

__version__ = "1.2.0"
SOURCE_TAG = "v2.5.0"
SOURCE_COMMIT = "29d67ccb05e370b5958d72920a9cd1aa829dee80"

_mini_bind("mini_diff_1", "_line_sentences normalize")
_mini_bind("mini_diff_2", "TYPE_MARKERS _K _QUALIFIER_SENTENCE _QUALIFIER_SPLIT_DECIMAL _STIFF_KANJI _bigrams _group_index _is_question _mark_positions _negation_marks _negative_zu _qualifier_change _qualifier_reach _qualifier_states _risk _sentence_numbers _sentence_spans")

COUNTED_TYPES = ("pr", "article", "incident", "proposal", "manual", "formal", "paper")

def _qualifier_risks(sides, groups):
    out = []
    for group in groups:
        for i, j in group["pairs"]:
            old, new = group["old"][i], group["new"][j]
            if old.text == new.text and not _QUALIFIER_SPLIT_DECIMAL.search(old.text):
                continue
            old_numbers = _sentence_numbers(sides, 0, old)
            if not old_numbers:
                continue
            new_numbers = _sentence_numbers(sides, 1, new)
            if not new_numbers:
                continue
            if old.text == new.text and (_qualifier_reach(sides, 0, old, old_numbers)
                                         == _qualifier_reach(sides, 1, new, new_numbers)):
                continue
            olds = _qualifier_states(sides, 0, old, old_numbers)
            news = _qualifier_states(sides, 1, new, new_numbers)
            old_count = Counter(state[0] for state in olds)
            new_count = Counter(state[0] for state in news)
            words = [None, None]
            for key in old_count:
                if old_count[key] != new_count.get(key):
                    continue
                old_states = [state for state in olds if state[0] == key]
                new_states = [state for state in news if state[0] == key]
                if Counter(s[1] for s in old_states) == Counter(s[1] for s in new_states):
                    continue
                if len(old_states) > 1:
                    rest = Counter(s[1] for s in new_states)
                    kept_old = []
                    for state in old_states:
                        if rest[state[1]] > 0:
                            rest[state[1]] -= 1
                        else:
                            kept_old.append(state)
                    rest = Counter(s[1] for s in old_states)
                    kept_new = []
                    for state in new_states:
                        if rest[state[1]] > 0:
                            rest[state[1]] -= 1
                        else:
                            kept_new.append(state)
                    old_states, new_states = kept_old, kept_new
                for before, after in zip(old_states, new_states):
                    if words[0] is None:
                        words = [set(f for f, regex in _QUALIFIER_SENTENCE.items() if regex.search(old.text)),
                                    set(f for f, regex in _QUALIFIER_SENTENCE.items() if regex.search(new.text))]
                    lost, added, strict = _qualifier_change(before[1], after[1], before[3], after[3], words[0], words[1])
                    if not (lost or added or strict):
                        continue
                    subkind = "lost" if lost and not added and not strict else (
                        "added" if added and not lost and not strict else "changed")
                    out.append(_risk("number_qualifier", subkind, old.line, new.line, old.text, new.text,
                                     {"old_number": before[4], "new_number": after[4], "from": sorted(before[1]), "to": sorted(after[1]),
                                      "old_markers": list(before[2]), "new_markers": list(after[2])}))
    return out

BUILTIN_LISTS = {
    "hedges": ("と考えられる", "と思われる", "可能性がある", "示唆する", "推測される", "の範囲では", "かもしれない"),
    "nominalization": (
        ("が可能", "が可能(?:です|でした|だ|である|となり|となる|となっ|になり|になる|になっ|な|に|で|。|、)"),
        ("することが可能", "することが可能"),
        ("の実施", "の実施"),
        ("を実施", "を実施(?:し|す|さ)"),
        ("を担保", "を担保"),
        ("を図る", "を図(?:る|り|っ|ら|れ)"),
        ("に資する", "に資(?:する|し|さ)"),
        ("につながる", "につなが(?:る|り|っ|ら)"),
        ("の観点から", "の観点(?:から|で|では)"),
        ("に関して", "に関(?:して|し|する)"),
        ("を行う", "を行(?:う|い|っ|わ|え)"),
        ("不可能", "(?:は|が)不可能"),
    ),
    "intensifiers": ("本当に", "とても", "すごく", "ぜひ", "絶対", "最強", "抜群", "イチオシ", "大活躍", "パンチ", "ずらり"),
    "feelings": (
        ("ほっと", "ほっと(?=し|す|で|一息|ひと息|息)"),
        ("安堵", "安堵"),
        ("安心", "安心"),
        ("肩の荷", "肩の荷"),
        ("胸をなで", "胸をなで"),
        ("うれしい", "嬉し|うれし"),
        ("喜ぶ", "喜ん|喜び|喜ば|よろこ[んびば]"),
        ("楽しい", "楽し|たのし"),
        ("面白い", "面白|おもしろ"),
        ("悔しい", "悔し|くやし"),
        ("残念", "残念"),
        ("悲しい", "悲し|かなし"),
        ("寂しい", "寂し|淋し|さびし|さみし"),
        ("がっかり", "がっかり|落胆"),
        ("驚く", "驚[いきくか]|おどろ[いきくか]|びっくり"),
        ("不安", "不安(?!定)"),
        ("心配", "心配(?!り)(?!(?:は|も)?(?:ありません|ない|いりません|いらない|要りません|要らない|無用|ご無用|なく)"
                 "|(?:に)?は及(?:びません|ばない))"),
        ("怖い", "怖[いかくがさ]|恐ろし|こわ(?:い|かっ|く(?!し|ず|れ))"),
        ("焦る", "焦っ|焦り|焦る|あせっ|あせり|あせる"),
        ("恥ずかしい", "恥ずかし|はずかし"),
        ("誇らしい", "誇らし|ほこらし"),
        ("感動", "感動"),
        ("感激", "感激"),
        ("もやもや", "もやもや|モヤモヤ"),
        ("いらいら", "いらいら|イライラ|苛立"),
        ("うんざり", "うんざり"),
        ("わくわく", "わくわく|ワクワク"),
        ("どきどき", "どきどき|ドキドキ"),
        ("満足", "満足(?!度)(?<!を満足)(?!する(?:場合|とき|こと|もの))"),
        ("感謝", "感謝", "ありがと|お礼|(?<![失無非])礼を|謝意"),
        ("ありがたい", "ありがた|有難|有り難"),
        ("申し訳", "申し訳", "すみません|すいません|お詫び|おわび|詫び|ごめん|陳謝|謝罪"),
        ("幸せ", "幸せ|しあわせ"),
        ("腹が立つ", "怒っ|怒り|腹が立|腹立"),
        ("後悔", "後悔"),
        ("戸惑う", "戸惑|とまど"),
        ("懐かしい", "懐かし|なつかし"),
        ("憂鬱", "憂鬱|ゆううつ"),
        ("落ち込む", "落ち込(?<!に落ち込)(?<![げ数率量額高要績気益価][がはの]落ち込)(?<!売上[がはの]落ち込)(?<!コスト[がはの]落ち込)"
                    "(?<!レート[がはの]落ち込)(?<!リクエスト[がはの]落ち込)(?<!スループット[がはの]落ち込)(?<!トラフィック[がはの]落ち込)"
                    "(?<!アクセス[がはの]落ち込)(?<!パフォーマンス[がはの]落ち込)(?<!ペース[がはの]落ち込)(?<!セールス[がはの]落ち込)"),
        ("つらい", "つら(?:い|かっ|く)"),
        ("切ない", "切な(?:い|かっ|く)|せつな(?:い|かっ|く)"),
        ("涙", "涙"),
        ("緊張", "緊張(?!感のある|状態|関係)"),
        ("苦しい", "苦し(?<![堅見重暑]苦し)(?:い|かっ|く|さ|み|そう)"),
        ("恐怖", "恐怖"),
        ("嫌だ", "嫌(?:な(?:気|思い|予感)|だっ|気が|になっ)"),
        ("愛おしい", "愛おし|いとおし"),
        ("心細い", "心細"),
        ("情けない", "情けな"),
        ("むなしい", "むなし|虚し"),
        ("胸が", "胸が(?:痛|熱|締め|苦し|躍|高鳴|詰ま|いっぱい)"),
    ),
}

_LIST_PATTERNS = {"nominalization": True, "intensifiers": False, "feelings": True, "hedges": False}

_LIST_THIRD_COLUMN = frozenset(("feelings",))
_LIST_CACHE = {}

_LIST_PROBLEMS = {}

_LIST_ABSENT = (FileNotFoundError, NotADirectoryError)
_LIST_PROBLEM_WIDTH = 40

def parse_list(text, pattern=False):
    if text.startswith("﻿"):
        text = text[1:]
    out = []
    for line in text.split("\n"):
        line = line.rstrip("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if pattern:
            name, _, regex = line.partition("\t")
            regex, _, third = regex.partition("\t")
            if not regex.strip():
                shown = line if len(line) <= _LIST_PROBLEM_WIDTH else line[:_LIST_PROBLEM_WIDTH] + "…"
                raise ValueError("「名前<TAB>正規表現」の形でない行があります: " + shown)
            if third.strip():
                out.append((name.strip(), regex.strip(), third.strip()))
            else:
                out.append((name.strip(), regex.strip()))
        else:
            out.append(line.strip())
    return out

def _compile_item(item):
    return (item[0],) + tuple(re.compile(regex) for regex in item[1:])

_ANY_OF_CACHE = {}

def _any_of(items):
    cached = _ANY_OF_CACHE.get(id(items))
    if cached is not None and cached[0] is items:
        return cached[1]
    regexes = [item if hasattr(item, "pattern") else item[1] for item in items]
    combined = None
    if regexes and all(regex.groups == 0 and regex.flags == re.UNICODE and isinstance(regex.pattern, str)
                       for regex in regexes):
        try:
            combined = re.compile("|".join(regex.pattern for regex in regexes))
        except re.error:
            combined = None
    if len(_ANY_OF_CACHE) >= 32:
        _ANY_OF_CACHE.clear()
    _ANY_OF_CACHE[id(items)] = (items, combined)
    return combined

def _list_problem_text(error):
    if isinstance(error, UnicodeDecodeError):
        return "UTF-8 として読めません"
    if isinstance(error, re.error):
        return "正規表現の誤り（{}）".format(error)
    if isinstance(error, OSError):
        return "ファイルを開けません（{}）".format(getattr(error, "strerror", None) or error)
    if isinstance(error, ValueError):
        return str(error)
    return "{}: {}".format(type(error).__name__, error)

def _load_list(name):
    if name in _LIST_CACHE:
        return _LIST_CACHE[name]
    pattern = _LIST_PATTERNS[name]
    items, source, problem = None, "builtin", None
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "references", "lists", name + ".txt")
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except _LIST_ABSENT:
        data = None
    except OSError as error:
        data, problem = None, _list_problem_text(error)
    if data is not None:
        try:
            parsed = parse_list(data.decode("utf-8-sig"), pattern=pattern)
            if pattern and name not in _LIST_THIRD_COLUMN and any(len(item) > 2 for item in parsed):
                raise ValueError("3つ目の欄はこの一覧では使えません")
            if name == "fact-gaps" and any(item[0] not in ("degree", "change", "effect", "figure") for item in parsed):
                raise ValueError("事実の穴の種類は degree、change、effect、figure です")
            items = [_compile_item(item) for item in parsed] if pattern else parsed
            source = "references/lists/{}.txt".format(name)
        except Exception as error:
            items, problem = None, _list_problem_text(error)
    if items is None:
        builtin = BUILTIN_LISTS[name]
        items = [_compile_item(item) for item in builtin] if pattern else list(builtin)
        source = "builtin"
    _LIST_CACHE[name] = (items, source)
    _LIST_PROBLEMS[name] = problem
    return _LIST_CACHE[name]

_BODY_SKIP_KINDS = frozenset(("code", "frontmatter", "html_block", "table", "heading", "heading_underline",
                              "reference_definition", "thematic_break", "blank"))

_BODY_MASK_KINDS = frozenset(("inline_code", "autolink", "bare_url", "link_destination", "image", "html_token"))

class _Body(tuple):
    __slots__ = ()

    def __new__(cls, text, raw, line, start):
        return tuple.__new__(cls, (text, raw, line, start))

    text = property(lambda self: self[0])
    raw = property(lambda self: self[1])
    line = property(lambda self: self[2])
    start = property(lambda self: self[3])

class _Masker:

    def __init__(self, sides, side, skip_kinds=_BODY_SKIP_KINDS):
        analysis = sides.analyses[side]
        self.rows = analysis["lines"]
        self.skip_kinds = skip_kinds
        spans = sorted((left, right) for left, right, kind in analysis["protected_spans"] if kind in _BODY_MASK_KINDS)
        self.lefts = [left for left, _ in spans]
        self.spans = spans

    def mask(self, text, start):
        end = start + len(text)
        first = max(0, bisect_right(self.lefts, start) - 1)
        pieces, cursor = [], start
        spans = self.spans
        for index in range(first, len(spans)):
            left, right = spans[index]
            if left >= end:
                break
            if right <= start:
                continue
            if left > cursor:
                pieces.append(text[cursor - start:left - start])
            cursor = max(cursor, right)
        if cursor == start:
            return text
        if cursor < end:
            pieces.append(text[cursor - start:])
        return "".join(pieces)

    def kind(self, sentence):
        index = sentence.line - 1
        return self.rows[index]["kind"] if index < len(self.rows) else None

    def body(self, sentence):
        index = sentence.line - 1
        if index < len(self.rows) and self.rows[index]["kind"] in self.skip_kinds:
            return None
        return _Body(self.mask(sentence.text, sentence.start), sentence.text, sentence.line, sentence.start)

def _all_bodies(sides, side, masker=None):
    masker = masker or _Masker(sides, side)
    sentences = _line_sentences(sides, side, 0, len(sides.lines[side]))
    return [body for body in (masker.body(sentence) for sentence in sentences) if body is not None and body.text.strip()]

_CONTRAST = re.compile(r"(?:では|じゃ|でも)(?:なく(?:て)?|ない|なかっ|ありません)|でなく(?:て)?|は(?:使わ|せ)ずに?")

_ZU_MARK = re.compile(r"は(?:使わ|せ)ず")

_NOT_ONLY = ("だけ", "ばかり", "のみ")

_RHETORICAL = re.compile(r"(?:ない|ありません)(?:か|でしょうか|だろうか|かと|のか)")

_SUBORDINATE = re.compile(r"(?:た)?(?:ので|から|ため|場合|とき|時|なら|限り|かぎり)")

_CLAUSE_BREAK = re.compile(r"[、。，,．！？!?「」『』（）()：:\n|｜]")

_TOPIC = re.compile(r"(?:(?<=[^ぁ-ゖ])|(?<=[のにとで]))は|は(?=[^ぁ-ゖ])")
_OKURI_MID = "りきけしみえちびれげせじつ"
_OKURI_TAIL = "りきけしみえちびれげせじ"

_TOKEN_OKURI_MID = _OKURI_MID + "たいめわ"

_TOKEN = re.compile("[" + _K + "]+(?:[" + _TOKEN_OKURI_MID + "][" + _K + "]+)*(?:[" + _OKURI_TAIL + "]|(?<=[" + _K + "])[さみ](?![ぁ-ゖ]))?"
                    "|[ァ-ヴー]{2,}|[A-Za-z][A-Za-z0-9_.+#-]+")

CONTRAST_WEIGHTS = ("目的", "狙い", "重要", "まず", "第一に", "ねらい", "狙っ", "狙う", "主眼", "主目的", "主な", "最優先",
                    "優先", "何より", "最も", "一番", "重視", "重点", "大事", "大切", "目指", "筆頭", "中心")

_STOP_TOKENS = frozenset(CONTRAST_WEIGHTS + ("場合", "部分", "程度", "意味", "自体", "以上", "以下", "全部", "全体", "一部",
                                             "問題", "必要", "ところ", "もの", "こと"))

_NEG_AFTER = re.compile(r"(?:では|じゃ|でも)な|でな[くい]|ではありません|ない|なく|なかっ|ません"
                        r"|以外|を除|を除い|抜き|不要|二の次|後回し")
_DEMOTE_WORD = re.compile(r"(?<=[はもがを])(?:その次|二番手|二番目|脇に置|脇役|添え物|おまけ|どうでも|そのあとに回)")
_OTHER_NOUN = "(?:[" + _K + "ァ-ヴーA-Za-z0-9]+|ほか|それ|あと|これ)"
_DEMOTE_WORD_OTHER = re.compile("(?:(?:で|て|にし|し)" + _OTHER_NOUN + "(?:の[^、。はもがを]{1,12})?"
                                "|(?:に|が|けど|から|ので)" + _OTHER_NOUN + ")[はもがを]$")

_LEXICAL_NEG = re.compile(r"対象外|範囲外|適用外|非対応|未対応|無効|廃止|禁止|除外|据え置")
_COORD_HEAD = re.compile(r"と|や|及び|および|並びに|ならびに|・")
_TOPIC_MARKS = re.compile(r"[はもが]")

_PROMOTE_TO = "".join("(?<!" + word + ")" for word in ("本番", "有効", "先頭", "上位", "主力", "正式", "標準", "既定", "中心",
                                                       "主軸", "前面", "最初", "一番", "トップ", "優先", "オン"))
_USE_A = "(?!使|用い|中心|基本|軸|前提|主体|活か|生か|ベース|重視|優先)"
_DEMOTE_REDUCE = "は減ら"
_DEMOTE = re.compile(r"(?<!に)より|の代わり|に代わ|に替え|から[^、。]{0,12}?(?:切り替|切替|移行|移し|乗り換|置き換)"
                     "|^[" + _K + "ァ-ヴーA-Za-z0-9]{0,8}(?:[ぁ-ゖ]{0,2}|の[^、。をはもがでにへと]{0,12})[をはも]" + _USE_A
                     + "[^、。を]{1,12}?(?:" + _PROMOTE_TO + "[にへ](?:切り替|切替|移行|移[しす]|乗り換|置き換|置換|入れ替|差し替"
                     "|変更|改め|転換)|で置き換)"
                     r"|(?:[うくぐすつぬぶむる]|の)前に|[はをも](?:後|あと)(?:に(?:し|す|回|まわ)|で|$)|後日|後回し"
                     r"|次回(?!も|から(?![にと]))|見送|保留|(?<!に)控え|避け|(?<!は)やめ|はやめ(?!に)"
                     r"|(?<!突き)(?<!食い)(?<!受け)(?<!引き)(?<!歯)止め|^(?:[ぁ-ゖ]{0,2}|の(?:数|回数|件数|時間|量|頻度|割合))は減ら")

_REDUCE_ITSELF = re.compile(r"[ぁ-ゖ]{0,5}?(?:こと|の(?=[がはを]))")

_DEMOTE_ANCHORED = re.compile(r"見送|保留|控え|避け|やめ|止め|次回|後日|[はをも](?:後|あと)")
_A_PHRASE = re.compile(r"の[^、。をはもがでにへと]{0,12}")
_OTHER_OBJECT = re.compile(r"(?<!こと)(?<!の)を")

_SWITCH_TO = re.compile(r"に(?:替え|代わ)")
_SWITCH_FROM = re.compile(r"[をが]|から")

_CONTRAST_SKIP_KINDS = _BODY_SKIP_KINDS - frozenset(("heading", "table"))

_ALSO_AFTER = re.compile(r"(?:だけ|ばかり|のみ)(?:では|で|じゃ)なく|のみならず|に加え|に限らず|のほか")

_COORD_AFTER = re.compile(r"及び|および|並びに|ならびに|や|・"
                          r"|と(?!い[うっ]|して|しては|は|の|同|違|異|比|な[るりっれ]|す[るれ]|し[たてま]|呼|言|考|思|見|感|聞)")

_COMPARE_CLAUSE = re.compile(r"のうち|から選|比べ|比較|両方|どちら|いずれ|調べ|(?<!と)(?<!ことを)(?<!ことが)(?<!ことも)(?<!再)再?(?:確かめ|確認)"
                             r"|検討|検証|候補|試[しすみ]")

_HYPOTHESIS = re.compile(r"疑|考え(?!られ(?:ます|る))|思っ|思い|予想|想定|見込|仮説|推測|睨")

_ADVERSATIVE_END = re.compile(r"(?:が|けど|けれど|けれども|ものの|のに|ても|でも)$")
_WEIGHT_PATTERN = re.compile("|".join(r"(?<![" + _K + r"])まず(?!い)" if word == "まず" else re.escape(word)
                                      for word in CONTRAST_WEIGHTS))

_WEIGHT_ONLY_CLAUSE = re.compile(r"^#*\s*(?:まず(?:は)?|第一に|何より(?:も)?|最優先(?:で|として)|一番に)$")

def _neg_after(after, token=""):
    if _NEG_AFTER.search(after):
        return True
    for found in _DEMOTE_WORD.finditer(after):
        if not _DEMOTE_WORD_OTHER.search(after, 0, found.start()):
            return True
    if after.startswith("外") and not token.endswith("内"):
        return True
    coordinated = _COORD_HEAD.match(after) is not None
    for found in _LEXICAL_NEG.finditer(after):
        if (coordinated and after.endswith("の", 0, found.start())
                and not _TOPIC_MARKS.search(after, 0, found.start())):
            continue
        return True
    return False

def _clause_bounds(text, position):
    left = 0
    for match in _CLAUSE_BREAK.finditer(text, 0, position):
        left = match.end()
    match = _CLAUSE_BREAK.search(text, position)
    return left, (match.start() if match else len(text))

_KATAKANA_HEAD = re.compile(r"[ァ-ヴー]")
_LATIN_HEAD = re.compile(r"[A-Za-z]")

def _is_token(token):
    if token in _STOP_TOKENS:
        return False
    if _KATAKANA_HEAD.match(token) or _LATIN_HEAD.match(token):
        return len(token) >= 2
    if len(token) == 2 and token[1] in "さみ":
        return True
    return len(_STIFF_KANJI.findall(token)) >= 2

_ADJ_NOUN = re.compile("^[" + _K + "]い([" + _K + "].*)$|^.*[いため]([" + _K + "]{2,}.*)$")

def _negated_tokens(sentence):
    out = []
    for match in _CONTRAST.finditer(sentence):
        if match.group(0).startswith(("では", "じゃ")) and _RHETORICAL.match(sentence, match.start() + 2):
            continue
        if _SUBORDINATE.match(sentence, match.end()):
            continue
        if sentence[:match.start()].endswith(_NOT_ONLY):
            continue
        left = 0
        for brk in _CLAUSE_BREAK.finditer(sentence, 0, match.start()):
            left = brk.end()
        span = sentence[left:match.start()]
        topic_cut = 0
        for topic in _TOPIC.finditer(span):
            topic_cut = topic.end()
        raw_tokens = _TOKEN.findall(span[topic_cut:])
        tokens = [token for token in raw_tokens if _is_token(token)]
        if topic_cut and raw_tokens and all(token in CONTRAST_WEIGHTS for token in raw_tokens):
            tokens = [token for token in _TOKEN.findall(span[:topic_cut]) if _is_token(token)]
        for token in tokens:
            out.append((token, match.group(0), match.end()))
            noun = _ADJ_NOUN.match(token)
            noun_text = (noun.group(1) or noun.group(2)) if noun is not None else None
            if noun_text is not None and _is_token(noun_text):
                out.append((noun_text, match.group(0), match.end()))
    return out

_SHOWN_TAIL = re.compile("[ぁ-ゖ]{1,2}$")
_SHOWN_TAIL_NOT_HEAD = frozenset("はがをのにとでもへやかよ")
_SHOWN_TAIL_PARTICLES = frozenset(("など", "まで", "ほど", "しか", "さえ", "こそ"))
_SHOWN_TAIL_MO_GA = frozenset("もが")

def _shown_word(text, token, mark_start):
    head = text[:mark_start]
    tail = _SHOWN_TAIL.search(head)
    if tail is None or not head.endswith(token, 0, tail.start()):
        return token
    kana = tail.group(0)
    if kana in _SHOWN_TAIL_PARTICLES:
        return token
    if kana[0] not in _SHOWN_TAIL_NOT_HEAD or (len(kana) == 2 and kana[0] in _SHOWN_TAIL_MO_GA and kana[1] in _OKURI_TAIL):
        return token + kana
    return token

def _demoted(text, left, position, after):
    for match in _DEMOTE.finditer(after):
        if match.start() == 0 and _SWITCH_TO.match(after) and _SWITCH_FROM.search(text, left, position):
            continue
        if (match.group(0).endswith(_DEMOTE_REDUCE) and _REDUCE_ITSELF.match(after, match.end()) is not None
                and _WEIGHT_PATTERN.search(after, match.end())):
            continue
        if _DEMOTE_ANCHORED.search(match.group(0)) and _other_object(after[:match.start()]):
            continue
        return True
    return False

def _other_object(segment):
    head = _A_PHRASE.match(segment)
    rest = segment[head.end():] if head else segment
    return _OTHER_OBJECT.search(rest, 1) is not None

def _affirmed_with_weight(text, token, clause_only=False, affirmed_side=()):
    if not _WEIGHT_PATTERN.search(text):
        return None
    start = 0
    while True:
        position = text.find(token, start)
        if position < 0:
            return None
        start = position + 1
        left, right = _clause_bounds(text, position)
        after = text[position + len(token):right]
        clause = text[left:right]
        if _neg_after(after, token) or _negative_zu(after):
            continue
        if _demoted(text, left, position, after):
            continue
        clause_weight = bool(_WEIGHT_PATTERN.search(clause))
        own_weight = clause_weight
        topic_weight = False
        if clause_only and not clause_weight and left >= 2 and text[left - 2] == "は":
            clause_weight = bool(_WEIGHT_PATTERN.search(text, _clause_bounds(text, left - 2)[0], left - 1))
            topic_weight = clause_weight
        if clause_only and not clause_weight and left >= 2:
            clause_weight = _WEIGHT_ONLY_CLAUSE.match(text[_clause_bounds(text, left - 2)[0]:left - 1].strip()) is not None
        if (clause_only and clause_weight and not own_weight and not topic_weight
                and _side_affirmed(text, position, token, right, affirmed_side)):
            continue
        if clause_only and not clause_weight:
            continue
        if _HYPOTHESIS.search(clause):
            continue
        if not clause_weight and _ADVERSATIVE_END.search(clause):
            continue
        return position

_SIDE_REPLACED = re.compile("(?:の[^、。をはもがでにへと]{0,12})?を(?:置き換|置換|差し替|入れ替|切り替|切替)")

_SIDE_REJECTED = re.compile("[をはも](?:中止|減ら|省|捨て|廃止|控え|見送|禁止|やめ|止め|取りやめ|なく[さしすせ]|削)")

def _side_affirmed(text, position, token, right, words):
    for word in words:
        start = position + len(token)
        while True:
            at = text.find(word, start, right)
            if at < 0:
                break
            start = at + 1
            if text[position + len(token):at] == "の":
                continue
            after = text[at + len(word):right]
            if after.startswith(("も", "にも", "でも")):
                continue
            if _neg_after(after, word) or _negative_zu(after) or _demoted(text, position, at, after):
                continue
            if _SIDE_REPLACED.match(after) or _SIDE_REJECTED.match(after):
                continue
            return True
    return False

def _affirmed_plain(text, token, others):
    start = 0
    while True:
        position = text.find(token, start)
        if position < 0:
            return None
        start = position + 1
        end = position + len(token)
        left, right = _clause_bounds(text, position)
        after = text[end:right]
        clause = text[left:right]
        if _HYPOTHESIS.search(clause):
            continue
        also = _ALSO_AFTER.match(after)
        if also is not None:
            rest = after[also.end():]
            if not (_neg_after(rest) or _negative_zu(rest)):
                return position
            continue
        if not _COORD_AFTER.match(after) or not any(other in text[end:] for other in others):
            continue
        if (_neg_after(after, token) or _negative_zu(after) or _demoted(text, left, position, after)
                or _COMPARE_CLAUSE.search(clause) or _ADVERSATIVE_END.search(clause)):
            continue
        return position

def _original_affirms(text, token, mark_end, mark_start):
    rest = text[mark_end:]
    positions = [found.start() for found in re.finditer(re.escape(token), rest)]
    if any(not rest.startswith("の", position + len(token)) or _continues_word(rest, position, token)
           for position in positions):
        return True
    if positions:
        left, _ = _clause_bounds(text, max(0, mark_start - 1))
        return _affirmed_with_weight(text[:left], token) is not None
    return _affirmed_with_weight(text, token) is not None

def _continues_word(text, position, token):
    if not position:
        return False
    before, head = text[position - 1], token[0]
    for pattern in (_STIFF_KANJI, _KATAKANA_HEAD, _LATIN_HEAD):
        if pattern.match(head):
            return bool(pattern.match(before))
    return False

def _b_side_phrases(text, token, mark_end):
    out = []
    rest = text[mark_end:]
    start = 0
    while True:
        index = rest.find(token + "の", start)
        if index < 0:
            return out
        start = index + 1
        follow = _TOKEN.match(rest, index + len(token) + 1)
        if follow is not None:
            out.append(token + "の" + follow.group(0))

def _head_clue(head):
    return head[0] if len(head) >= 2 and head.endswith("方") else head

def _contrast_risks(sides, groups):
    out = []
    order = 0
    maskers = None
    for group in groups:
        if group["hunk"]["tag"] == "insert" or not group["old"] or not group["new"]:
            continue
        if not any(_CONTRAST.search(sentence.text) for sentence in group["old"]):
            continue
        if maskers is None:
            maskers = (_Masker(sides, 0, skip_kinds=_CONTRAST_SKIP_KINDS), _Masker(sides, 1, skip_kinds=_CONTRAST_SKIP_KINDS))
        new_for_old, old_for_new = {}, {}
        for i, j in group["pairs"]:
            new_for_old.setdefault(i, []).append(j)
            old_for_new[j] = i
        old_texts = set(sentence.text for sentence in group["old"])
        seen = set()
        for i, sentence in enumerate(group["old"]):
            body = maskers[0].body(sentence)
            if body is None:
                continue
            heading = maskers[0].kind(sentence) == "heading"
            tokens = [item for item in _negated_tokens(body.text)
                      if not _original_affirms(body.text, item[0], item[2], item[2] - len(item[1]))]
            if not tokens:
                continue
            negated = set(token for token, _, _ in tokens)
            others = [token for token in _TOKEN.findall(body.text) if token not in negated and _is_token(token)]
            targets = new_for_old[i] if i in new_for_old else range(len(group["new"]))
            for j in targets:
                new_sentence = group["new"][j]
                new_body = maskers[1].body(new_sentence)
                if new_body is None or new_body.raw in old_texts:
                    continue
                for token, mark, mark_end in tokens:
                    probe = new_body.text
                    phrases = _b_side_phrases(body.text, token, mark_end)
                    if any(phrase not in probe and _head_clue(phrase[len(token) + 1:]) in probe for phrase in phrases):
                        continue
                    for phrase in phrases:
                        probe = probe.replace(phrase, "\uff3f" * len(phrase))
                    narrow = heading or _ZU_MARK.match(mark) is not None
                    side = [word for word in _TOKEN.findall(body.text[mark_end:]) if _is_token(word) and word not in negated]
                    if (_affirmed_with_weight(probe, token, narrow, side) is None
                            and _affirmed_plain(probe, token, others) is None):
                        continue
                    paired = old_for_new.get(j)
                    if paired is not None and paired != i:
                        other = maskers[0].body(group["old"][paired])
                        if other is not None and _affirmed_with_weight(other.text, token) is not None:
                            continue
                    key = (body.line, new_body.line, token)
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append((_group_index(group, new_sentence), order, _risk(
                        "contrast_reversal", None, body.line, new_body.line, body.raw, new_body.raw,
                        {"word": _shown_word(body.text, token, mark_end - len(mark)), "mark": mark})))
                    order += 1
    return out

def _feeling_risks(sides, groups):
    patterns, _ = _load_list("feelings")
    if not patterns or not any(group["new"] for group in groups):
        return []
    found = {}

    def absent(index):
        if index not in found:
            if "original" not in found:
                old_masker = _Masker(sides, 0, skip_kinds=frozenset(("code", "frontmatter", "html_block")))
                found["original"] = "\n".join(
                    old_masker.mask(line, sides.starts[0][number]) for number, line in enumerate(sides.lines[0])
                    if not (number < len(old_masker.rows)
                            and old_masker.rows[number]["kind"] in ("code", "frontmatter", "html_block")))
            original, item = found["original"], patterns[index]
            found[index] = not item[1].search(original) and not (len(item) > 2 and item[2].search(original))
        return found[index]
    masker = _Masker(sides, 1, skip_kinds=frozenset(("code", "frontmatter", "html_block", "table")))
    combined = _any_of(patterns)
    out = []
    order = 0
    for group in groups:
        if not group["new"]:
            continue
        old_texts = set(sentence.text for sentence in group["old"])
        old_for_new = dict((j, i) for i, j in group["pairs"])
        for j, sentence in enumerate(group["new"]):
            if sentence.text in old_texts:
                continue
            body = masker.body(sentence)
            if body is None:
                continue
            if combined is not None and combined.search(body.text) is None:
                continue
            words = []
            for index, item in enumerate(patterns):
                match = item[1].search(body.text)
                if match is not None and match.group(0) not in words and absent(index):
                    words.append(match.group(0))
            if not words:
                continue
            paired = old_for_new.get(j)
            old = group["old"][paired] if paired is not None else None
            out.append((_group_index(group, sentence), order, _risk(
                "feeling", None, old.line if old is not None else None, sentence.line,
                old.text if old is not None else None, sentence.text, {"words": words})))
            order += 1
    return out

_CERTAINTY_VERB = "[るうくすつぬぶむぐたい]"

_PREDICATE_END = r"(?=です|だ(?!け)|である|でした|だった|でござ|と(?:な|して|され)|に(?:な|し)|[。）)」』]|$)"
_PREDICATE_STEM = "(?<=[ァ-ヴー一-龥])"
_PREDICATE_BEFORE = "(?<=[るうくすつぬぶむぐたいァ-ヴー一-龥])"
_YOTEI = (r"予定(?=して(?:い|お)|しま|する(?=[。、]|$)|され)"
          r"|予定(?!外|より|通り|どおり)" + _PREDICATE_END
          + r"|" + _PREDICATE_STEM + r"予定(?=の)|" + _PREDICATE_BEFORE + r"予定(?=で(?!は)|、)|(?<=の)予定(?=で、)")
_MIKOMI = (r"見込(?:ま(?:れ|せ)|んで|む(?=[。、]|$)|め(?:る|ま)|み(?=ます))"
           r"|見込み" + _PREDICATE_END
           + r"|" + _PREDICATE_STEM + r"見込み(?=の)|" + _PREDICATE_BEFORE + r"見込み(?=で(?!は)|、)|(?<=の)見込み(?=で、)"
           + r"|見込み(?=(?:が|も|は)(?:高|大き|強|あ|立|薄|低|な))")

_APPEARANCE = (r"(?<=[きしちにひみりぎじびぴえけせてねへめれげぜべぺさ])そう(?:です|だ|な|に|で(?!す)|でした|だった)"
               r"|(?<=[るうくすつぬぶむぐいた])よう(?:だ|です|でした|だった|である)(?=[。、！!よね]|$)"
               r"|(?<=[るうくすつぬぶむぐた])らし(?:い|かった)(?=[。、！!よね]|です|$)"
               r"|(?<=[るうくすつぬぶむぐいた])みたい(?:だ|です|でした|だった)(?=[。、！!よね]|$)")
_CERTAINTY_TABLE = [
    (2, "可能性が高い", r"可能性(?:が|は|も)?(?:高|大き|十分)", True),
    (1, "かもしれない", r"かも(?:しれ|知れ)(?:ない|ません|ず|なかった|なけれ)", True),
    (1, "可能性", r"可能性(?:が|も|は)?(?:あ|ござ|考え|残|存在|否定でき|捨てきれ|拭え)", True),
    (1, "おそれ", r"(?:おそれ|恐れ|虞)(?=が|も|は|あ)", True),
    (1, "リスク", r"リスク(?:が|も)(?:あ|高|伴|残)", True),
    (1, "懸念", r"懸念(?:が|も)?(?:あ|され|残)", True),
    (1, "得る", r"(?<=[しりきちびみいえけせれべ])(?:得る|得ます|うる)", True),
    (1, "かねない", r"(?<=[しりきちびみいえけせれべ])かね(?:ない|ません|ず)", True),
    (1, "必ずしも", r"必ずしも|とは限(?:らない|らず|りません|らなかった)", True),
    (1, "ことがある", r"(?<![たっだ])こと(?:が|も)(?:ある|あり|あっ)|(?:ケース|とき)(?:が|も)(?:ある|あり|あっ|出)", False),
    (1, "場合がある", r"場合(?:が|も)(?:ある|あり|あっ)", False),
    (1, "検討", r"検討(?:中|して(?:い|お)|を(?:進め|続け|始め))", False),
    (2, "と思われる", r"と(?:思|おも)われ", True),
    (2, "と考えられる", r"と考えられ", True),
    (2, "と見られる", r"と(?:見|み)られ", True),
    (2, "と見ている", r"と(?:見|み)て(?:いる|います|おり)", True),
    (2, "見込み", _MIKOMI, True),
    (2, "予想", r"予(?:想|測)(?:され|して(?:い|お)|します|する(?=[。、]|$)|です|だ(?=[。、]|$)|であ|では)", True),
    (2, "想定", r"想定(?:され|して(?:い|お)|します|する(?=[。、]|$)|です|だ(?=[。、]|$)|であ|では)", True),
    (2, "見通し", r"見通し(?:です|だ|で|が)", True),
    (2, "推測される", r"推(?:測|定|察)(?:され|して(?:い|お)|します|する(?=[。、]|$)|です|だ(?=[。、]|$))", True),
    (2, "公算", r"公算(?:が|は|も)?(?:大き|高|強)", True),
    (2, "でしょう", r"でしょう(?!か)|だろう(?!か)|であろう", True),
    (2, "はず", r"はず(?:だ|です|で|でした|だった|の)", True),
    (2, "おそらく", r"おそらく|恐らく|たぶん|多分", True),
    (2, "示唆", r"示唆(?:する|され|して|し)", True),
    (2, "そう・よう", _APPEARANCE, True),
    (2, "傾向", r"傾向(?:が|に)(?:ある|あり|見られ)", False),
    (2, "期待できる", r"期待(?:でき|され|して(?:い|お)|します|する(?=[。、]|$))", False),
    (2, "と思う", r"と(?:思|考え)(?:います|う|る|ます|ている|ています|ており|ております|ていました)|と(?:思|おも)って(?:い|お)"
                r"|思うのは", False),
    (3, "予定", _YOTEI, True),
    (3, "計画", r"(?<=" + _CERTAINTY_VERB + ")計画(?:です|だ|で|である|が(?=あ)|も(?=あ))|計画(?:して(?:い|お)|中)", True),
    (3, "方針", r"(?<=" + _CERTAINTY_VERB + ")方針(?:です|だ|で|である)", True),
    (3, "方向", r"(?<=" + _CERTAINTY_VERB + ")方向(?:です|だ|で|である)", True),
    (3, "つもり", r"つもり(?:です|だ|で)", True),
    (5, "確実", r"(?<!ほぼ)(?<!ほとんど)確実(?:に|だ|です|で|な)", True),
    (5, "必ず", r"必ず(?!しも)", True),
    (5, "間違いなく", r"(?<!ほぼ)間違いなく|間違いありません|間違いない", True),
    (5, "確定", r"確定(?:です|だ|である|済|して(?:いる|います|おり)|しました(?!ら)|した(?!ら))", True),
    (5, "絶対に", r"絶対に", True),
]
_CERT = [(lv, name, re.compile(p), core) for lv, name, p, core in _CERTAINTY_TABLE]

_COUNTED_FROM = (1, 2)
_CERTAINTY_NEG_AFTER = re.compile(r"^[^、。]{0,4}?(?:は|が|も)?(?:な[いくかし]|ありません|ございません|低|小さ|少な|薄)")
_CERTAINTY_NEG_FORMS = re.compile(r"可能性(?:は|が|も)?(?:低|小さ|少な|な[いく]|ほぼな|ありません)|見込(?:み|め)(?:は|が)?(?:な[いく]|薄|低|ありません)"
                        r"|予定(?:は|が)?(?:な[いく]|ありません)|はず(?:が|は)(?:な|ありません)|(?:おそれ|恐れ)(?:は|が)?(?:な[いく]|ありません)"
                        r"|リスク(?:は|が)?(?:な[いく]|低|小さ|少な|ありません)|懸念(?:は|が)?(?:な[いく]|ありません)"
                        r"|(?:あり|起こり|なり|し)(?:得|え)(?:ない|ません)")

_CERTAINTY_QUESTION = re.compile(r"でしょうか[。？?]?[」』）)]*$")

def _certainty_words(text):
    return [word[:5] for word in _certainty_word_spans(text)]

def _certainty_word_spans(text):
    found, taken = [], []
    for level, name, regex, core in _CERT:
        for match in regex.finditer(text):
            if any(left < match.end() and match.start() < right for left, right in taken):
                continue
            taken.append(match.span())
            negative = name != "必ずしも" and bool(_CERTAINTY_NEG_AFTER.search(text[match.end():match.end() + 10]))
            found.append((level, name, match.start(), negative, core, match.end()))
    return sorted(found, key=lambda word: word[2])

def _certainty_negations(text, words):
    found = Counter(word[1] for word in words if word[3])
    for match in _CERTAINTY_NEG_FORMS.finditer(text):
        found[match.group(0)[:2]] += 1
    return found

def _cancel_same_level(before, after):
    rest_old, rest_new, _ = _cancel_pairs(before, after)
    return rest_old, rest_new

def _cancel_pairs(before, after):
    rest_old, rest_new, pairs = list(before), list(after), []
    for same_name in (True, False):
        for word in list(rest_old):
            for other in rest_new:
                if other[0] == word[0] and (not same_name or other[1] == word[1]):
                    rest_old.remove(word)
                    rest_new.remove(other)
                    pairs.append((word, other))
                    break
    return rest_old, rest_new, pairs

_HEDGE_CONDITION = re.compile(r"[^、。！？!?\n]{0,8}?(?:れば|たら|なら|場合|とき|時(?:は|に))")

_HEDGE_CLAUSE_STOP = re.compile(r"[、。！？!?\n，,]")
_HEDGE_CONTENT = re.compile(r"[一-龥々〆ヵヶァ-ヴA-Za-z0-9０-９Ａ-Ｚａ-ｚ]")

def _hedge_polarity(text, word, words):
    head = text.rfind("\n", 0, word[2]) + 1
    for stop in "、。！？!?，,":
        head = max(head, text.rfind(stop, 0, word[2]) + 1)
    match = _HEDGE_CLAUSE_STOP.search(text, word[5])
    tail = match.start() if match else len(text)
    return sum(1 for a, b in _negation_marks(text[head:tail])
               if not any(a + head < w[5] and b + head > w[2] or a + head == w[5] for w in words))

def _hedge_conditions(text, words):
    return sum(1 for w in words if _HEDGE_CONDITION.match(text, w[5]))

def _hedge_clause(text, start):
    head = text[max(0, start - 200):start]
    stops = [match.end() for match in _HEDGE_CLAUSE_STOP.finditer(head)]
    return set(_HEDGE_CONTENT.findall(head[stops[-1]:] if stops else head))

def _classify_hedge_marks(orig, rewrite, lost, added):
    if {mark["kind"] for mark in list(lost) + list(added)} != {"推量"}:
        return "other_kinds"
    side = 0 if lost else 1
    texts = (orig or "", rewrite or "")
    words = [_certainty_word_spans(text) for text in texts]
    hits = [[(start, start + len(hit)) for start, kind, hit in _mark_positions(text) if kind == "推量"]
            for text in texts]
    for text, ws, marks in zip(texts, words, hits):
        for start, end in _sentence_spans(text) or [(0, len(text))]:
            sentence = text[start:end].strip()
            if sentence and (_is_question(sentence) or _CERTAINTY_QUESTION.search(sentence)):
                if any(start <= w[2] < end for w in ws) or any(start <= a < end for a, _ in marks):
                    return "question"
    if _certainty_negations(texts[0], words[0]) != _certainty_negations(texts[1], words[1]):
        return "negation"
    if any(w[1] == "必ずしも" for ws in words for w in ws):
        return "negation"
    if _hedge_conditions(texts[0], words[0]) != _hedge_conditions(texts[1], words[1]):
        return "condition"
    hit_words = []
    for start, end in hits[side]:
        overlapping = [w for w in words[side] if w[2] < end and start < w[5]]
        if not overlapping:
            return "not_in_table"
        if any(w[3] for w in overlapping):
            return "negation"
        if any(w[1] == "そう・よう" and "らし" in texts[side][w[2]:w[5]] for w in overlapping):
            return "not_in_table"
        for word in overlapping:
            if word not in hit_words:
                hit_words.append(word)
    before, after = ([w for w in ws if not w[3]] for ws in words)
    rest_old, rest_new, pairs = _cancel_pairs(before, after)
    rest_old.sort(key=lambda w: (w[0], w[2]))
    rest_new.sort(key=lambda w: (w[0], w[2]))
    rest = rest_old if side == 0 else rest_new
    left = [w for w in rest if w in hit_words]
    if not left:
        if len(rest_old) != len(rest_new):
            return "unpaired"
        for pair in pairs:
            hit, other = pair if side == 0 else pair[::-1]
            if hit not in hit_words:
                continue
            if not other[4]:
                return "not_core"
            if (_hedge_polarity(texts[side], hit, words[side])
                    != _hedge_polarity(texts[1 - side], other, words[1 - side])):
                return "negation"
            clauses = _hedge_clause(texts[side], hit[2]), _hedge_clause(texts[1 - side], other[2])
            if all(clauses) and not clauses[0] & clauses[1]:
                return "unanchored"
        return "same"
    paired = min(len(rest_old), len(rest_new))
    old_base = min([w[0] for w in before] + [4])
    new_base = min([w[0] for w in after] + [4])
    outcomes = set()
    for word in left:
        index = rest.index(word)
        if index < paired:
            other = (rest_new if side == 0 else rest_old)[index]
            up = other[0] > word[0] if side == 0 else word[0] > other[0]
            outcomes.add("strengthen" if up else "weaken")
        elif side == 0:
            outcomes.add("lost" if new_base > word[0] else "consolidated")
        else:
            outcomes.add("added" if old_base > word[0] else "consolidated")
    return "mixed" if len(outcomes) > 1 else outcomes.pop()

def _cancel_with_context(rest, pools):
    kept = []
    for word in rest:
        for pool in pools:
            other = next((w for w in pool if w[0] == word[0]), None)
            if other is not None:
                pool.remove(other)
                break
        else:
            kept.append(word)
    return kept

_COUNTED_BY_DOC_TYPE_FROM = ("場合がある", "ことがある")

_CERTAINTY_FREQUENCY = re.compile(r"まれに|稀に|ときどき|時々|時折|ときおり|たまに|一部|によっては|場合によって|こともある")

_CERTAINTY_DUTY = re.compile(TYPE_MARKERS["依頼・決まり"].pattern + r"|必須|ものと(?:する|します)|こと(?=[。]|$)", re.M)

def _certainty_change(old, new, old_context=(), new_context=(), split_context=(), doc_type=None, duty=False):
    if any(_is_question(text) or _CERTAINTY_QUESTION.search(text.rstrip()) for text in (old, new)):
        return None
    before, after = _certainty_words(old), _certainty_words(new)
    if _certainty_negations(old, before) != _certainty_negations(new, after):
        return None
    before = [word for word in before if not word[3]]
    after = [word for word in after if not word[3]]
    rest_old, rest_new = _cancel_same_level(before, after)
    rest_old = _cancel_with_context(rest_old, new_context)
    rest_new = _cancel_with_context(rest_new, old_context)
    split = [(pool, word) for pool in split_context for word in pool if word[0] == 5]
    rest_new.extend(word for _, word in split)
    old_base = min([w[0] for w in before] + [4])
    new_base = min([w[0] for w in after] + [4])
    rest_old.sort(key=lambda w: (w[0], w[2]))
    rest_new.sort(key=lambda w: (w[0], w[2]))
    paired = min(len(rest_old), len(rest_new))
    transitions = list(zip(rest_old[:paired], rest_new[:paired]))
    transitions.extend((w, None) for w in rest_old[paired:] if (w[0] < 4 and new_base > w[0]) or w[0] == 5)
    transitions.extend((None, w) for w in rest_new[paired:] if (w[0] < 4 and w[0] < old_base) or w[0] == 5)
    used = [b for _, b in transitions if b is not None]
    for pool, word in split:
        if any(word is b for b in used) and word in pool:
            pool.remove(word)
    by_doc_type = doc_type in COUNTED_TYPES
    frequent = by_doc_type and bool(_CERTAINTY_FREQUENCY.search(new))
    steps = []
    for a, b in transitions:
        from_level, to_level = (a[0] if a else 4), (b[0] if b else 4)
        if from_level == to_level:
            continue
        step = {"from": a[1] if a else "断定", "to": b[1] if b else "断定",
                "from_level": from_level, "to_level": to_level,
                "counted": a is not None and a[4] and from_level in _COUNTED_FROM and to_level > from_level}
        if by_doc_type and not step["counted"] and (
                (a is not None and a[1] in _COUNTED_BY_DOC_TYPE_FROM and to_level >= 4 and not frequent)
                or (a is None and to_level == 5 and not duty)):
            step["counted"] = True
            step["counted_by"] = "doc_type"
        steps.append(step)
    if not steps:
        return None
    up = any(s["to_level"] > s["from_level"] for s in steps)
    down = any(s["to_level"] < s["from_level"] for s in steps)
    return ("certainty" if any(s["counted"] for s in steps) else "certainty_review",
            "strengthened" if up else "weakened",
            {"old_words": [w[1] for w in before], "new_words": [w[1] for w in after],
             "steps": steps, "mixed": up and down})

def _same_review_sentence(body, risk):
    if risk["old_line"] is not None and risk["old_line"] != body.line:
        return False
    text, other = normalize(body.raw).strip(), normalize(risk["old"] or "").strip()
    return text in other or other in text

def _unpaired_neighbors(count, index, paired):
    first = index
    while first > 0 and first - 1 not in paired:
        first -= 1
    last = index
    while last + 1 < count and last + 1 not in paired:
        last += 1
    return [k for k in range(first, last + 1) if k != index]

def _certainty_risks(sides, groups, risks, masks=None, doc_type=None):
    masks = masks or (_Masker(sides, 0), _Masker(sides, 1))
    marks = [r for r in risks if (r["kind"], r["subkind"]) == ("sentence_type", "marks")]
    out = []
    for group in groups:
        bodies = [[masks[side].body(s) or _Body("", s.text, s.line, s.start) for s in group[key]]
                  for side, key in enumerate(("old", "new"))]
        paired = [set(pair[side] for pair in group["pairs"]) for side in (0, 1)]
        pools = [{}, {}]

        def pool(side, index):
            if index not in pools[side]:
                pools[side][index] = [w for w in _certainty_words(bodies[side][index].text) if not w[3]]
            return pools[side][index]

        for i, j in group["pairs"]:
            old, new = bodies[0][i], bodies[1][j]
            if not old.text or not new.text or old.text == new.text:
                continue
            neighbors = [_unpaired_neighbors(len(bodies[side]), index, paired[side]) for side, index in ((0, i), (1, j))]
            contexts = [[pool(side, k) for k in neighbors[side]] for side in (0, 1)]
            old_grams = _bigrams(old.text)
            split = []
            for k in neighbors[1]:
                grams = _bigrams(bodies[1][k].text)
                if grams and len(grams & old_grams) * 2 >= len(grams):
                    split.append(pool(1, k))
            duty = bool(_CERTAINTY_DUTY.search(old.text)) or any(_CERTAINTY_DUTY.search(bodies[0][k].text) for k in neighbors[0])
            change = _certainty_change(old.text, new.text, *contexts, split_context=split, doc_type=doc_type, duty=duty)
            if change is None:
                continue
            kind, direction, detail = change
            key = "lost" if direction == "strengthened" else "added"
            if any(_same_review_sentence(old, risk)
                   and any(m["kind"] in ("推量", "意見") for m in risk["detail"].get(key, [])) for risk in marks):
                continue
            out.append(_risk(kind, direction, old.line, new.line, old.raw, new.raw, detail))
    return out

_ADD_K = "一-龥々〆ヵヶ"

_ADD_NEG = r"(?:ない|なく|ません|ず(?![つ])|なかった|ませんでした|おらず)"

_ADD_PERF_NEG = r"(?:て|で)(?:い|お)り?(?:ない|ません|らず|なかった)"

_ADD_CHU = r"(?=です|だ|でし|で、|であ|。|$|のため|とな|につき|の(?:ため|案件|項目|もの|件|状態))"

_ADD_CHU_COMMA = r"(?=、)"

_ADD_STATE = [
    ("unknown", "未確認", r"未確認"),
    ("unknown", "不明", r"(?<!ご)不明(?!瞭|点|な点)"),
    ("unknown", "未判明", r"未(?:判明|解明)"),
    ("unknown", "分からない", r"(?:分か|わか|判)(?:ら(?:ない|ず|なかった|なく)|りません|りかね)(?!(?:点|ところ|こと(?:が|は)?(?:あれ|あった)))"),
    ("unknown", "分かっていない", r"(?:分かっ|わかっ|判明し|把握し|特定し|特定でき|把握でき|確認でき|確認が取れ|確認がとれ|はっきりし|明らかになっ|つかめ|掴め)" + _ADD_PERF_NEG),
    ("unknown", "特定できない", r"(?:特定|把握|確認)(?:でき|が(?:でき|取れ|とれ))(?:ない|ません|ず|なかった)"),
    ("undecided", "未定", r"未(?:定(?!義)|決定|確定|決(?!済))"),
    ("undecided", "決まっていない", r"(?:決まっ|決め|決定し|確定し)" + _ADD_PERF_NEG + r"|決まら(?:ない|ず)|白紙"),
    ("undecided", "目処が立っていない", r"(?:目処|目途|めど|メド|見通し)(?:は|が|も)?(?:まだ)?(?:立っ" + _ADD_PERF_NEG + r"|立た(?:ない|ず)|立ちません|つい" + _ADD_PERF_NEG + r"|つか(?:ない|ず)|つきません)"),
    ("undecided", "判断できない", r"(?:判断|決定|決断)(?:が|は)?(?:でき|つか)(?:ない|ず|ません)"),
    ("investigating", "調査中", r"(?:調査|確認|照会|問い合わせ|問合せ|究明|精査)中" + _ADD_CHU),
    ("investigating", "調査中（読点）", r"(?:調査|確認|照会|問い合わせ|問合せ|究明|精査)中" + _ADD_CHU_COMMA),
    ("investigating", "調べている", r"(?:調べ|調査し|問い合わせ|照会し|精査し)(?:て|で)(?:い|お)(?:る|ます|ります|り(?=、))(?!た)"),
    ("considering", "検討中", r"(?:検討|調整|協議|相談|審議)中" + _ADD_CHU),
    ("considering", "検討中（読点）", r"(?:検討|調整|協議|相談|審議)中" + _ADD_CHU_COMMA),
    ("considering", "検討している", r"(?:検討し|調整し|協議し)(?:て|で)(?:い|お)(?:る|ます|ります|り(?=、))(?!た)"),
    ("considering", "次回話し合う", r"次回(?:に|まで(?:に)?)?(?:改めて)?(?:話し合|検討|決め|協議|相談)"),
    ("pending", "保留", r"保留|持ち越"),
    ("pending", "見送り", r"(?<!お)見送(?:り|る|ります|って|っている)"),
    ("awaiting", "待っている", r"(?:回答|返事|返信|返答|判断|連絡|承認|結果|決定|確定|入荷|許可|審査|結論|入金|納品)(?:を|の)?待(?:ち|って|つ(?=[。、]|$)|っております)"),
    ("awaiting", "待っている", r"待って(?:い|お)(?:る|ます|ります)"),
    ("not_done", "未着手", r"未(?:着手|対応|実施|完了|計測|検証|回答|提出|承認|解決|実装|反映|入金|払い?|納|発送|登録|処理|作成|公開|導入|返信|連絡|受領|到着|修正|適用|整備|返却|清算|精算)"),
    ("not_done", "まだ〜ない", r"まだ[^。、]{0,24}?(?:" + _ADD_NEG + r"|" + _ADD_PERF_NEG + r")"),
    ("not_done", "済んでいない", r"(?:済ん|終わっ|終え|手を(?:つけ|付け)|着手し|完了し)" + _ADD_PERF_NEG),
    ("not_done", "至っていない", r"(?:確認|特定|判明|解決|決定|合意|把握|実施|完了|発表|結論|実現|導入)(?:に|には)(?:まだ)?至(?:っ" + _ADD_PERF_NEG + r"|ら(?:ない|ず)|りません)"),
    ("no_plan", "予定はない", r"予定(?:は|が|も)?(?:ない|なく|ありません|ございません|なし)|予定し" + _ADD_PERF_NEG + r"|計画(?:は|が)(?:ない|ありません)"),
    ("in_progress", "対応中", r"(?:対応|作業|進行|準備|作成|修正|開発|移行|実施|実装|改修|復旧|集計|手配)中" + _ADD_CHU + r"|途中(?=です|だ|でし|。|$)"),
    ("in_progress", "対応中（読点）", r"(?:対応|作業|進行|準備|作成|修正|開発|移行|実施|実装|改修|復旧|集計|手配)中" + _ADD_CHU_COMMA),
]

_ADD_STATE_RX = [(fam, name, re.compile(p)) for fam, name, p in _ADD_STATE]

_ADD_STATE_ANY = re.compile("|".join("(?:" + p + ")" for _, _, p in _ADD_STATE))

_ADD_KEEP_EXTRA = {
    "unknown": [r"(?:明確|明らか|定か|確か)(?:で|に)?(?:は)?(?:ない|なく|ありません|なっていない|なっておりません)", r"不明確|不透明|未知数|はっきりしない|見えていない|見えておりません",
                r"存じ(?:上げ)?ません"],
    "undecided": [r"(?:決まり|決定し|確定し)(?:次第|ましたら|たら)|決まったら", r"未定"],
    "investigating": [r"(?:確認|調査)を(?:進め|続け)", r"(?:確認|調査)(?:して|を進めて)いるところ", r"現在[^。]{0,12}(?:調べ|確認し|調査し)"],
    "considering": [r"(?:検討|調整|協議)を(?:進め|続け)", r"次回(?:に|まで(?:に)?)?(?:改めて)?(?:話し合|検討|決め|協議|相談)"],
    "pending": [r"判断を待", r"いったん[^。]{0,10}?(?:保留|止め|停止|見合わせ|見送|預か|置い|置き|待)"],
    "awaiting": [r"届(?:いて|き)(?:い|お)?(?:ない|ません|らず)", r"届き次第", r"届きましたら", r"お待ち(?:し|いたし)て(?:い|お)", r"待って(?:い|お)"],
    "not_done": [r"(?:ない|ず|ぬ)まま", r"(?:されて|して|れて)(?:い|お)り?(?:ない|ません|らず)"],
    "no_plan": [],
    "in_progress": [r"進めて(?:い|お)", r"最中", r"(?:て|で)(?:いる|おる)ところ"],
}

_ADD_KEEP_CROSS = {
    "undecided": ("considering", "pending"),
    "investigating": ("unknown", "not_done", "in_progress"),
    "considering": ("undecided", "pending"),
    "pending": ("undecided", "considering", "awaiting"),
    "awaiting": ("not_done",),
    "not_done": ("in_progress", "awaiting"),
    "in_progress": ("not_done", "investigating"),
    "unknown": (),
    "no_plan": (),
}

_ADD_KEEP_EXTRA_RX = dict((k, [re.compile(p) for p in v]) for k, v in _ADD_KEEP_EXTRA.items())

_ADD_COND = re.compile(r"[^。、]{0,12}?(?:場合|なら|とき|時(?:は|に)|うちは|(?<=[けれ])ば|たら)")

_ADD_STATE_DENIED = re.compile(r"(?:では|じゃ)(?:ない|なく|ありません|ございません)|(?:の|な)[^。、]{1,10}?(?:は|が|も)(?:ありません|ない(?=[。、]|$)|ございません|なし|ゼロ|0件|０件)")

_ADD_SEND_OFF_OBJECT = re.compile(r"導入|実施|採用|開催|参加|発売|公開|リリース|購入|変更|対応|提出|出店|契約|発注|申請|更新|移行|延長|追加|掲載|配布|出荷|発表|決定|判断|今回|今年|今期|今月|計画|案|予定|検討|見直し|改定|値上げ")

_ADD_DONE = re.compile(r"済み|済ませ|完了し(?:た|ました)|判明し(?:た|ました)|特定(?:し|でき)(?:た|ました)|決まり?ました|決まった|決定し(?:た|ました)|確定し(?:た|ました)|終わ(?:った|りました)|解決し(?:た|ました)")

_ADD_PROGRESSIVE = r"(?:を|に|の)?(?:進め|続け)?(?:し|させていただい|させて|いたし)?(?:て|で)(?:い|お)(?:る|ます(?!た)|ります|り(?=、)|られ)"

_ADD_APOLOGY = re.compile(r"申し訳(?:ありません|ございません|ない)|すみません|かまいません|構いません")

_ADD_ANY_NEG = re.compile(r"(?:て|で)(?:い|お)り?(?:ない|ません|らず|なかった)|でき(?:ない|ず|ません|なかった)|(?:ない|ず)まま|困難|不能|不可能|難し|(?:分か|わか)ら|知らない|まだ|いまだ")

_ADD_PERFORMATIVE = re.compile(r"お願い|お詫び|おわび|感謝|お礼|御礼|失礼|恐縮|承知|了解|存じ|拝見|申し上げ|お祈り|祈念|歓迎")

_ADD_REPORT = re.compile(r"(?:ご)?(?:報告|共有|紹介)")

_ADD_REPORT_MAYBE = re.compile(r"(?:ご)?(?:お知らせ|案内|連絡|説明|提案|回答|返信)")

_ADD_PERF_MARK = re.compile(r"以下|下記|次の|とおり|通り|取り急ぎ|まずは|本メール|この(?:メール|場|たび)|ここに|本日は|について|の件で|件につき")

_ADD_FUTURE_MARK = re.compile(r"今後|以後|以降|次回|次の(?:版|回|リリース|会議)|来週|来月|来年|明日|明朝|本日中|今日中|今週中|月内|年内|後日|改めて|あらためて|追って|"
                          r"別途|順次|引き続き|必ず|責任を(?:もって|持って)|までに|次第|こちらで|当方で|弊社で|当社で|私(?:から|が|より|ども)|"
                          r"担当(?:者)?(?:が|から)|チームが|前日に|事前に|早急に|速やかに|至急|すぐに|のちほど|後ほど|あとで|(?:ない|ぬ)よう(?:に)?")

_ADD_LATER_MARK = re.compile(r"今後|以後|次回|来週|来月|明日|後日|改めて|あらためて|追って|別途|順次|のちほど|後ほど|あとで|次第|までに|本日中|今日中|今週中|月内|年内")

_ADD_LATER_STRONG = re.compile(r"後日|改めて|あらためて|追って|別途|のちほど|後ほど|次第|までに")

_ADD_OTHER_SUBJECT = re.compile(r"(?:先方|お客様|お客さま|貴社|御社|皆様|皆さま|皆さん|取引先|委託先|メーカー|業者)(?:が|から(?!の)|より(?!の))")

_ADD_WRITER_MARK = re.compile(r"私|わたくし|弊社|当社|当方|当店|当課|当部|当室|我々|われわれ|こちら|担当|当チーム|当センター")

_ADD_STATIVE = ("あり", "い", "なり", "おり", "でき", "ござい", "分かり", "わかり", "変わり", "始まり", "終わり", "決まり", "届き", "かかり",
            "起き", "起こり", "生じ", "減り", "増え", "消え", "見え", "聞こえ", "思い", "考え", "感じ", "存じ", "困り", "異なり", "違い",
            "続き", "残り", "当たり", "含み", "使え", "言え", "思え", "見られ", "考えられ", "限り", "要り", "いり", "入り", "済み", "済み",
            "並び", "向き", "似", "合い", "気がし", "痛み", "要し", "有し", "存し", "属し", "喜び", "悲しみ", "驚き", "願い", "勝り", "優れ", "及び", "すみ", "過ぎ", "すぎ", "頼り", "知り")

_ADD_OLD_FUTURE = re.compile(r"(?:[" + _ADD_K + "ァ-ヴー]{1,6}|[ぁ-ん]{1,3})(?:ます|ません|する|しない|します|いたします|致します|まいります|参ります|"
                         r"(?<=[るうくすつぬぶむぐ])(?=[。、]|ので|が|けど|[よねわなぞさ](?:[。、!！?？]|$)|$)|ない(?=[。、]|ので|が|[よねわ](?:[。、!！]|$)|$))"
                         r"|予定|つもり|方針|ことに(?:なり|なる|し)|たい(?=[。、]|と|です|$)|次第|ましょう")

_ADD_PROMISE = [
    ("prevention", "再発防止", r"(?P<k>再発(?:防止|しない|を防|の防止))"),
    ("prevention", "今後このようなことがないよう", r"(?P<k>(?:今後|二度と)[^。]{0,16}?(?:ない|ぬ)よう)"),
    ("prevention", "同じことが起きないよう", r"(?P<k>同(?:じ|様の)(?:ミス|誤り|こと|事態|問題|不具合)が(?:起き|起こら|発生し|生じ)(?:ない|ぬ)よう)"),
    ("prevention", "徹底", r"(?P<k>徹底)(?:いた|致)?し(?:ます|てまいります|て参ります)|(?P<k2>徹底)(?:する|します|を図)"),
    ("prevention", "気をつける", r"(?P<k>気を(?:つけ|付け|引き締め)|注意(?:を払|し)|心がけ|心掛け|肝に銘じ|努め|取り組んで)(?:ます|てまいります|て参ります|ていきます|る(?=[。]|$))"),
    ("guarantee", "ことはない", r"(?P<k>(?:る|く|う|す|つ|む|ぶ|ぐ|ぬ|い)ことは(?:ありません|ございません|ない(?=[。]|$)|一切))"),
    ("guarantee", "費用はかからない", r"(?P<k>(?:追加|別途)?(?:の)?(?:費用|料金|負担|手数料)(?:は|が|も)?(?:一切)?(?:かかりません|かからない|発生しません|発生いたしません|いただきません|ございません))|(?P<k2>(?:無料|無償)(?:で(?!す)|にて))"),
    ("guarantee", "まま使える", r"(?P<k>(?:まま|問題なく|支障なく|引き続き|これまでどおり|これまで通り|安心して)[^。]{0,16}?(?:いただけ(?:ます|る)|ご利用(?:になれ|でき)(?:ます|る)))"),
    ("guarantee", "変えない", r"(?P<k>(?:変え|上げ|値上げし|変更し|据え置)(?:ない|ません|く)(?=[。]|$))"),
    ("guarantee", "保証", r"(?P<k>保証|お約束|約束)(?:いた|致)?し(?:ます|ましょう)"
                        r"|(?P<k2>保証|担保)(?:する|される|されます|(?<=担保)します|(?<=保証)(?:して|されて)(?:いる|います))"
                        r"(?=[。、]|$)"),
    ("promise", "させていただく", r"(?P<k>[" + _ADD_K + "ァ-ヴー]{1,6}|[ぁ-ん]{1,3})させていただ(?:きます|く(?=[。、]|ので|$))"),
    ("promise", "いたします", r"(?P<k>(?:お|ご)?[" + _ADD_K + "ァ-ヴー]{1,6}(?:(?![をがはにでともへのやか])[ぁ-ん][" + _ADD_K + "]{0,2})?|(?:お|ご)[ぁ-ん" + _ADD_K + "]{1,6})(?:いた|致)し(?:ます|ましょう)(?!た)"),
    ("promise", "てまいります", r"(?P<k>[" + _ADD_K + "ァ-ヴー]{1,6}[ぁ-ん]{0,3})(?:て|で)(?:まいり|参り|いき)ます(?!た)"),
    ("promise", "お〜します", r"(?P<k>(?:お|ご)[" + _ADD_K + "ァ-ヴー]{1,6}[ぁ-ん]{0,2})(?:し|いたし)ます(?!た)"),
    ("promise", "サ変します", r"(?P<k>[" + _ADD_K + "ァ-ヴー]{2,6})(?:し|いたし)ます(?!た)(?=[。、]|ので|が|$)"),
    ("promise", "動詞ます", r"(?P<k>[" + _ADD_K + "][ぁ-ん]{0,3}?)(?:[しきぎちにびみりいえけせてねべめれげ])ます(?!た)(?=[。、]|ので|が|$)"),
    ("promise", "常体の約束", r"(?P<k>[" + _ADD_K + "ァ-ヴー]{1,6}[ぁ-ん]{0,3}?)(?:する|る|う|く|す|つ|む|ぶ|ぐ)(?=[。]|$)"),
]

_ADD_PROMISE_RX = [(sub, name, re.compile(p)) for sub, name, p in _ADD_PROMISE]

_ADD_REQUEST = re.compile(r"ください|下さい|お願い|いただけ(?:ます|ません)(?:か|でしょうか)|もらえ(?:ます|ません)か|いただきたく|いただければ|てほしい")

_ADD_INTRANSITIVE_SAHEN = ("発生", "存在", "増加", "減少", "低下", "上昇", "変化", "成功", "失敗", "到着", "経過", "一致",
                       "依存", "該当", "動作", "稼働", "機能", "関係", "影響", "相当", "共通", "意味", "比例", "集中",
                       "通過", "所属", "在籍", "改善", "向上", "悪化", "安定", "不足", "満足", "感謝")

_ADD_AGENTIVE_SAHEN = ("完了", "終了", "対応", "参加", "出席", "欠席", "開始", "反映")

_ADD_E_ROW = re.compile(r"(?:られ|れ|せ|え|け|げ|め|ね|べ|へ|ぜ|て)$")

_ADD_INTRANSITIVE_TAIL = re.compile(r"(?:わり|まり|がり|さり|たり|なり|あり|おり|ござい|い|でき|れ|られ)$")

_ADD_PAST_END = re.compile(r"(?:た|ました|でした|だった)[。]?[」』）)]*$")

_ADD_PREVENT_ANY = re.compile(r"再発|今後[^。]{0,16}(?:ない|ぬ)よう|二度と|徹底|気を(?:つけ|付け|引き締め)|注意(?:を払|し|いた)|心がけ|心掛け|肝に銘じ|努め|取り組")

_ADD_PREVENT_UNSETTLED = re.compile(r"[^。]{0,10}?(?:未定|未|検討中|調査中|調整中|ない|ありません|不要|なし|求め|要請)")

_ADD_PREVENT_ACT = re.compile(r"(?:ます|する(?=[。、]|$)|[るうくすつむぶぐ](?=[。、]|$)|こととし|ことにし|予定|てまいり|ていき)")

_ADD_PREVENT_NOT_ACT = re.compile(r"済|不要|求め|要請|指摘|依頼され|ません|ない(?=[。、]|$)|(?<!こととし)(?<!ことにし)(?:でした|ました|だった|た(?=[。]|$))")

_ADD_CAUSAL = [
    ("reason", r"(?<=[るたいだう])ため(?:に)?(?=[、]|です|でした|だ|$)|(?<=[のな])ため(?=[、])|(?<!の)ので(?!す|しょう)|(?<=[るたいだ])から(?=[、]|です|だ|こそ|では)|ことから"),
    ("means", r"によって|により|による(?:もの)?|ことで|ことにより|おかげ|せいで|が原因|を受けて|の影響で|影響により|の効果で|効果により|がきっかけ"),
    ("result", r"(?:その|この)?結果(?:、|として)|そのため|このため|これにより|これによって|それにより|したがって|よって(?=、)|"
               r"につなが(?:る|り|った|って|ります|りました)|をもたら|に寄与|に貢献|が功を奏"),
]

_ADD_CAUSAL_RX = [(fam, re.compile(p)) for fam, p in _ADD_CAUSAL]

_ADD_INQUIRY_RESULT = re.compile(r"(?:調べ|調査し|確認し|検証し|比較し|試し|測定し|計測し|分析し|検討し|話し合っ|協議し|集計し|聞い|尋ね|試験し|点検し|審査し|見直し)た$")

def _addition_state_words(text):
    found, taken = [], []
    for fam, name, rx in _ADD_STATE_RX:
        for m in rx.finditer(text):
            if any(a < m.end() and m.start() < b for a, b in taken):
                continue
            taken.append(m.span())
            if _ADD_COND.match(text, m.end()) or _ADD_STATE_DENIED.match(text, m.end()):
                continue
            clause = text[max(text.rfind("。", 0, m.start()), text.rfind("、", 0, m.start())) + 1:m.start()]
            if name.endswith("（読点）") and not re.search("[はが]", clause):
                continue
            if name == "見送り" and not _ADD_SEND_OFF_OBJECT.search(text[max(0, text.rfind("。", 0, m.start()) + 1):m.start()]) \
                    and not re.match(r"り(?:と(?:な|し|させ|いたし)|にな|です|でした|だ|。|$)", text[m.start() + 2:]):
                continue
            found.append((fam, name, m.start(), m.group(0)))
    return sorted(found, key=lambda w: w[2])

def _addition_stem_neg(word):
    m = re.match("未([" + _ADD_K + "]{1,3})", word)
    if m:
        return m.group(1)
    m = re.search("([" + _ADD_K + "ァ-ヴー]{1,4})[ぁ-ん]{0,4}(?:" + _ADD_NEG + "|" + _ADD_PERF_NEG + ")$", word)
    return m.group(1)[-2:] if m else None

def _addition_promise_clauses(text):
    if not text or re.match(r"^[^「」『』、。\s]{0,8}[「『].*[」』][。．]?$", text):
        return []
    found, taken = [], []
    stripped = text.rstrip()
    question = _is_question(stripped) or bool(re.search(r"か[」』）)]*$", stripped))
    for sub, name, rx in _ADD_PROMISE_RX:
        for m in rx.finditer(text):
            if any(a < m.end() and m.start() < b for a, b in taken):
                continue
            taken.append(m.span())
            key = m.groupdict().get("k") or m.groupdict().get("k2") or ""
            clause_start = max(text.rfind("。", 0, m.start()) + 1, 0)
            clause_end = text.find("。", m.end())
            clause = text[clause_start: clause_end if clause_end >= 0 else len(text)]
            window = text[max(0, m.start() - 2):m.end() + 8]
            if question and clause_end < 0:
                continue
            if _ADD_REQUEST.search(window) or "「" in text[:m.start()] and "」" not in text[text.rfind("「", 0, m.start()):m.start()]:
                continue
            future = bool(_ADD_FUTURE_MARK.search(clause))
            strong = (name in ("させていただく", "いたします", "てまいります", "お〜します") or future
                      or bool(_ADD_WRITER_MARK.search(clause)))
            if sub == "prevention":
                tail = text[m.end(): clause_end if clause_end >= 0 else len(text)]
                if _ADD_PREVENT_NOT_ACT.search(tail[:24]) or (key.endswith("防止") and not _ADD_PREVENT_ACT.search(tail)):
                    continue
            if sub == "promise":
                if _ADD_PERFORMATIVE.search(window[:len(window) - 8]):
                    continue
                head = re.sub("^[おご]", "", key)
                if name in ("サ変します", "動詞ます") and any(head.endswith(w) for w in _ADD_INTRANSITIVE_SAHEN):
                    continue
                if name in ("サ変します", "動詞ます") and not strong and any(head.endswith(w) for w in _ADD_AGENTIVE_SAHEN):
                    continue
                if name == "動詞ます":
                    stem = text[m.start():m.end() - 2]
                    if _ADD_INTRANSITIVE_TAIL.search(stem) or any(stem.endswith(w) for w in _ADD_STATIVE):
                        continue
                    if _ADD_E_ROW.search(stem) and not _ADD_FUTURE_MARK.search(clause):
                        continue
                if name == "常体の約束":
                    stem = text[m.start():m.end()]
                    if (not _ADD_FUTURE_MARK.search(clause) or re.search(r"(?:れる|られる|できる|なる|ある|いる|える|める|わる|まる|がる)$", stem)
                            or re.search(r"(?:ます|です|でしょう)$", stem)):
                        continue
                later = bool(_ADD_LATER_MARK.search(clause))
                if _ADD_REPORT.search(key) and (not later or _ADD_PERF_MARK.search(clause) and not _ADD_LATER_STRONG.search(clause)):
                    continue
                if _ADD_REPORT_MAYBE.search(key) and _ADD_PERF_MARK.search(clause) and not future:
                    continue
                if _ADD_OTHER_SUBJECT.search(clause):
                    continue
            found.append((sub, name, key, m.start(), strong or sub != "promise"))
    return found

def _addition_find_all(table, text):
    found, taken = [], []
    for fam, rx in table:
        for m in rx.finditer(text):
            if any(a < m.end() and m.start() < b for a, b in taken):
                continue
            taken.append(m.span())
            found.append((fam, m.group(0), m.start(), m.end()))
    return sorted(found, key=lambda w: w[2])

def _addition_causal_words(text):
    return [w for w in _addition_find_all(_ADD_CAUSAL_RX, text)
            if not (w[1].startswith("結果") and _ADD_INQUIRY_RESULT.search(text[:w[2]]))]

class _AdditionDocument:

    def __init__(self, sides, masks, risks):
        self.raw = sides.texts[0]
        self.bodies = [_all_bodies(sides, side, masks[side]) for side in (0, 1)]
        self.old_text = "".join(b.text for b in self.bodies[0])
        self.nonpast = "".join(t for t in re.split(r"(?<=[。\n])", self.raw)
                              if not _ADD_PAST_END.search(t.rstrip()))
        self.prevent = any(not _ADD_PREVENT_UNSETTLED.match(self.raw, m.end()) for m in _ADD_PREVENT_ANY.finditer(self.raw))
        self.states, self.kept, self.heads, self.matches = {}, {}, {}, {}
        self._old_bigrams = None
        self.counts = [Counter(w[0] for b in bodies for w in self.state_words(b.text)) for bodies in self.bodies]
        self.by_kind = {}
        for risk in risks:
            self.by_kind.setdefault(risk['kind'], []).append(risk)

    def old_bigrams(self):
        if self._old_bigrams is None:
            text = self.old_text
            self._old_bigrams = {text[k:k + 2] for k in range(len(text) - 1)}
        return self._old_bigrams

    def find(self, name, text):
        key = (name, text)
        if key not in self.matches:
            if name == 'promise':
                found = _addition_promise_clauses(text)
            else:
                found = _addition_causal_words(text)
            self.matches[key] = found
        return self.matches[key]

    def state_words(self, text):
        if text not in self.states:
            self.states[text] = _addition_state_words(text) if _ADD_STATE_ANY.search(text) else []
        return self.states[text]

    def state_kept(self, family, word, text):
        key = (family, word, text)
        if key not in self.kept:
            families = (family,) + _ADD_KEEP_CROSS.get(family, ())
            kept = any(w[0] in families for w in self.state_words(text))
            kept = kept or any(rx.search(text) for rx in _ADD_KEEP_EXTRA_RX.get(family, ()))
            if not kept and word.endswith('中') and family in ('investigating', 'considering', 'in_progress'):
                kept = bool(re.search(re.escape(word[:-1]) + _ADD_PROGRESSIVE, text))
            if family in ('unknown', 'not_done') and not _ADD_DONE.search(text):
                kept = kept or bool(_ADD_ANY_NEG.search(_ADD_APOLOGY.sub('', text)))
            stem = _addition_stem_neg(word)
            if not kept and stem:
                kept = bool(re.search(re.escape(stem) + '[^。、]{0,8}?(?:' + _ADD_NEG + '|' + _ADD_PERF_NEG + ')', text))
            self.kept[key] = kept
        return self.kept[key]

    def same_sentence(self, kind, body):
        return [r for r in self.by_kind.get(kind, ()) if _same_review_sentence(body, r)]

    def has_head(self, head):
        if head not in self.heads:
            self.heads[head] = bool(head and re.search(re.escape(head) + '(?![' + _ADD_K + 'ァ-ヴー])', self.nonpast))
        return self.heads[head]

_GAP_DEGREE = re.compile(
    r"大幅(?:に|な|の)|劇的(?:に|な)|飛躍的(?:に|な)|格段(?:に|の)|著し(?:く|い)|圧倒的(?:に|な)|桁違い|段違い"
    r"|大きく(?=改善|向上|短縮|削減|減|増|変わ|変え|速|下が|上が|低下|上昇|低減|前進|進歩)"
    r"|大きな(?=改善|効果|成果|前進|進歩|変化|向上)")

_GAP_CHANGE = re.compile(
    r"(?:短く|長く|速く|早く|遅く|軽く|重く|多く|少なく|高く|低く|広く|狭く|細かく|厳しく|緩く|ゆるく)"
    r"(?:し(?:ました|ます|ています|ていました)|なり(?:ました|ます)|なって(?:います|いました))"
    r"|(?:増や|減ら|延ば|伸ば|縮め|引き上げ|引き下げ)(?:し(?:ました|ます|ています)|ます|ました)"
    r"|(?:短縮|削減|増加|減少|向上|高速化|軽量化|低減|縮小|拡大|延長|増強|緩和)"
    r"(?:し(?:ました|ます|ています)|され(?:ました|ます|ています)|でき(?:ました|ます)|しました|します"
    r"|した(?=[。]|$)|する(?=[。]|$))")

_GAP_EFFECT = re.compile(
    r"(?:信頼性|安定性|品質|性能|パフォーマンス|使い勝手|利便性|生産性|効率|保守性|可読性|開発体験|体験|満足度|安全性|堅牢性)"
    r"(?:が|を)(?:向上|高ま|高め|改善|上が|上げ|支え|底上げ|強化)"
    r"|(?:混乱|影響|リスク|負担|手間|ダウンタイム|ばらつき)(?:を|が)(?:最小限|最小|低減|軽減|抑え|減ら)"
    r"|(?:改善|最適化|効率化|強化|刷新)(?:しました|します|を行いました|を行います|を実施しました|を図りました|を図ります)"
    r"|シームレス(?:に|な)"
    r"|(?:柔軟な|より良い|最適な)(?:選択肢|運用|対応|体験)")

_GAP_FIGURE = re.compile(
    r"土台(?:づくり|作り)?|(?<!基)礎(?!石)|基盤づくり|第一歩|大きな一歩|一歩前進|連鎖を断ち切|断ち切り"
    r"|道を(?:開|拓|ひら)(?!け)|扉を(?:開|ひら)(?!け)|(?:鍵|カギ)を握|武器(?:に|と)な|強力な武器|景色が(?:変わ|一変)|新たな(?:地平|ステージ|次元)"
    r"|次の(?:ステージ|次元)|底上げ|盤石|追い風|起爆剤|羅針盤|架け橋|屋台骨|息を吹き込|命を吹き込"
    r"|静かに(?:壊れ|失敗|落ち)|黙って(?:無視|捨て|スキップ|破棄|止ま)")

BUILTIN_LISTS["fact-gaps"] = tuple((kind, pattern.pattern) for kind, pattern in
                                  (("figure", _GAP_FIGURE), ("effect", _GAP_EFFECT), ("degree", _GAP_DEGREE), ("change", _GAP_CHANGE)))
_LIST_PATTERNS["fact-gaps"] = True
