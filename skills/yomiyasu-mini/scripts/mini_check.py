# yomiyasu-mini 1.0.0。nanaism/yomiyasu v2.2.2（488dd37c0baa67ec65bf155aced9fa1a01d261e2）から tools/generate.py で生成した。手で直さない。
# 取り出した名前と中身の sha256 は extract/scripts.json と MANIFEST.json にある。
"""yomiyasu-mini の意味の検査。原文と最終稿を比べ、意味が変わる恐れのある場所を挙げる。
本体 yomiyasu（版は SOURCE_TAG）の diff() の meaning_risks、markers、new_words、lost_words、type_changes と同じ値を出す。
検出の定義は本体から元の字のまま取り出し、mini_diff_*.py とこのファイルに分けて入れている。標準ライブラリだけで動き、外へ通信しない。"""
import os
import re
import difflib
import unicodedata
from array import array
from bisect import bisect_left, bisect_right
from collections import Counter, OrderedDict
import json as _mini_json

_MINI_USAGE = """使い方: python3 scripts/mini_check.py --source 原文.md --final 最終稿.md [--json]
  --source、--final に - を渡すと標準入力から読む（両方は不可）。--json で JSON を出す。
出力の2行目と最後の行が状態の行（ran は検査を最後まで実行した、not_run は実行できなかった）。
終了コード: 0 実行した（恐れの件数によらない）、2 入力の誤り（reason=input）、3 部品の欠けや壊れ（reason=check_error）。"""
_MINI_NOT_RUN = {"input": (2, "入力の誤りで、意味の検査を実行できませんでした。検査はしていません。"),
                 "check_error": (3, "部品の欠けや壊れで、意味の検査を実行できませんでした。検査はしていません。")}


def _mini_status(state, **fields):
    return "yomiyasu-mini-check: " + state + "".join(" {}={}".format(key, value) for key, value in fields.items())


def _mini_print(text):
    stream = _mini_sys.stdout
    try:
        stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, OSError, ValueError):
        pass
    print(text, file=stream)


def _mini_not_run(reason, message, as_json):
    code, first = _MINI_NOT_RUN[reason]
    status = _mini_status("not_run", reason=reason)
    if as_json:
        _mini_print(_mini_json.dumps({"format": "yomiyasu-mini-check", "format_version": 1, "status": "not_run",
                                      "reason": reason, "status_line": status, "message": message},
                                     ensure_ascii=False, indent=1))
    else:
        tail = [_MINI_USAGE.split("\n")[0]] if reason == "input" else []
        _mini_print("\n".join([first, status, message] + tail + [status]))
    return code


def _mini_on_error(name, error):
    """部品を読めないとき。スクリプトなら状態の行を出して終わり、モジュールなら ImportError にする。"""
    if __name__ != "__main__":
        raise ImportError("{}.py を読めません（{}: {}）".format(name, type(error).__name__, error)) from error
    argv = _mini_sys.argv[1:]
    if "-h" in argv or "--help" in argv:
        _mini_print(_MINI_USAGE)
        raise SystemExit(0)
    message = "{}.py を読めません（{}: {}）。scripts の mini_*.py を同じ版でそろえてください。".format(
        name, type(error).__name__, error)
    raise SystemExit(_mini_not_run("check_error", message, "--json" in argv))

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

__version__ = "1.0.0"
SOURCE_TAG = "v2.2.2"
SOURCE_COMMIT = "488dd37c0baa67ec65bf155aced9fa1a01d261e2"

_mini_bind("mini_diff_1", "_ExactSequenceMatcher _Sides _line_sentences _sentence_pairs decode_source full_diff normalize")
_mini_bind("mini_diff_2", "_LAST_TYPE_RANGES _RISK_ORDER _is_question _is_quote_row _logic_risks _mark_positions _marks_in _marks_risks _modality_risks _negation_marks _negation_risks _number_risks _protected_risks _question_risks _range_sentences _risk _sentence_spans _swap_risks _type_changes _type_ranges normalize_doc_type")
_mini_bind("mini_diff_3", "_ADD_CAUSAL_RX _ADD_K _ADD_OLD_FUTURE _ADD_PAST_END _ADD_PROMISE_RX _ADD_REQUEST _ADD_STATE_ANY _AdditionDocument _BODY_MASK_KINDS _Body _Masker _addition_causal_words _certainty_risks _classify_hedge_marks _contrast_risks _feeling_risks _qualifier_risks _same_review_sentence _unpaired_neighbors")

MARKERS = {
    "依頼": r"(?:て|で)ください",
    "勧誘": r"ましょう",
    "義務": r"なければ(?:なりません|ならない)|なくては(?:なりません|ならない)|ねばならない|必要があ(?:ります|る)|べき",
    "評価": r"大切|重要|大事|不可欠|欠かせ|肝心|肝要",
    "可能": r"でき(?:ます|る|ません|ない)|(?<![しさ])(?:ら|れ)(?:ます|ません)(?=[。、がけし]|$)|(?<=[作使書読言防守残伝送続進])(?:れ|え|け|め|せ)(?:ます|る)(?=[。、がけし]|$)",
    "推量": r"でしょう|だろう|かもしれ|はず|と思(?:います|う)|ようです|らしい|おそれ|たいところ",
    "念押し": r"のです|んです|こそ|まさに|必ず|絶対|常に",
    "意志": r"(?:に|ように|ことに)し(?:ます|ている|ています)",
    "条件": r"(?<!例)(?<!たと)(?:れ|え|け|せ|て|ね|め|べ)ば(?![かり])|なら(?=[、。]|$|\s)|たら(?=[、。]|$|\s)|場合",
    "説明化": r"ことが挙げられ|ということ|ことです|ことになります",
    "つなぎ": r"まず|また(?!は)|そして|さらに|次に|最後に|ただし|しかし|つまり|そのため|ので(?!す)|によって|ことで|ことにより",
}

_MARKER_REGEXES = tuple((name, re.compile(pattern)) for name, pattern in MARKERS.items())

_MODALITY_ENDS = r"(?:る|ます|ない|ません|た|ました|なかった)"

_PERMISSION_END = r"(?=です|だ|でござ|[。、！!]|$)"
_PERMISSION_TAIL = (r"(?:も?(?:(?:よい|良い)(?![一-龥々〆ヵヶァ-ヴーA-Za-z0-9])|よろし|(?:よ|良)く(?=、)"
                    r"|いい(?=[。、]|です|でしょう|だろう|と|が|し|か|けど|よ|ね|の|$)"
                    r"|構(?:わな|いませ)|かま(?:わな|いませ)|差し?支え(?:な|あり|ござ))"
                    r"|も(?:問題(?:は)?(?:な|あり|ござ)|大丈夫|結構" + _PERMISSION_END + r"))")
_MODALITY_PATTERNS = (
    ("許可", r"(?:て(?<!とて)(?<!とって)(?<!言って)(?<!いって)(?<!全て)(?<!すべて)(?<!極めて)(?<!きわめて)(?<!初めて)(?<!改めて)"
           r"(?<!あえて)(?<!かつて)(?<!せめて)(?<!決して)(?<!総じて)(?<!概して)(?<!として)(?<!によって)(?<!について)(?<!くて)"
           r"(?!(?:(?<=いただいて)|(?<=頂いて)|(?<=もらって))も(?:よろし|いい))"
           r"|で(?<!ないで)(?<!らいで)(?:(?<=[んい]で)|(?<=[^。、！？!?\n「『（(\s]で)(?<!どうで)(?=も)))" + _PERMISSION_TAIL
           + r"|(?:れ|け)ば(?:結構" + _PERMISSION_END + r"|差し?支え(?:な|あり|ござ))|で結構" + _PERMISSION_END
           + r"|形で差し?支え(?:な|あり|ござ)"
           + r"|許可(?:する|される|します|されます)(?=[。！!]|$)"),
    ("能力", r"(?:でき|出来)(?:る(?!だけ|限り|かぎり)|ます|ない|ません|なく(?=て|な)|ず|て(?:い|おり|お)?(?:な|ませ|らず)"
           r"|(?:(?<!ができ)(?<!が出来)|(?<=ことができ)|(?<=ことが出来))(?:て(?!(?:い|おり)(?:た|ました))|(?=、)))"
           r"|不?可能(?:です|だ|である|な(?!限|かぎ)|に|(?=[。、]|$|と|で))"),
    ("能力（弱い印）", r"(?:でき|出来)(?:なかった|て(?:い|おり)(?:た|ました)|(?:(?<!ができ)(?<!が出来)|(?<=ことができ)|(?<=ことが出来))"
                  r"(?:た|ました))"
                  + r"|られ(?:(?<=[一-龥][めけえせてねべれげじみきちにひびりいぎ]られ)|(?<=[見得来寝着居]られ)|(?<=せられ))"
                  + _MODALITY_ENDS
                  + r"|(?:いただけ|頂け)" + _MODALITY_ENDS
                  + r"|得(?<=[しりきちびみいにぎじ]得)" + _MODALITY_ENDS + r"|うる(?<=[しりきちびみいにぎじ]うる)"
                  + r"|え(?:(?<=[使言払買会扱担補賄笑洗歌行]え)|(?<=[しりきちびみいにぎじ]え))" + _MODALITY_ENDS
                  + r"|け(?<=[書聞行置解動引築描歩磨裁省着]け)" + _MODALITY_ENDS
                  + r"|げ(?<=[防稼急泳脱研]げ)" + _MODALITY_ENDS
                  + r"|せ(?:(?<=[出話直消残戻外試探示移返回流隠渡通壊倒許貸押]せ)"
                    r"|(?<=減らせ|増やせ|動かせ|生かせ|活かせ|果たせ|満たせ|冷やせ|延ばせ|伸ばせ|飛ばせ|起こせ))" + _MODALITY_ENDS
                  + r"|て(?<=[待持保勝打放]て)" + _MODALITY_ENDS
                  + r"|べ(?<=[選運呼学飛遊結喜]べ)" + _MODALITY_ENDS
                  + r"|め(?:(?<=[読飲頼望掴組住]め)|(?<=楽しめ))" + _MODALITY_ENDS
                  + r"|れ(?<=[守作取送乗帰撮登通走語測計図]れ)" + _MODALITY_ENDS),
    ("不要", r"(?:なくて|ないで)" + _PERMISSION_TAIL + r"|不必?要|必要(?:は|が|も)?(?:な(?:い|く|し)|ありません|ございません)"),
    ("義務", r"なければ(?:ならない|なりません|いけない|いけません)|なくては(?:ならない|なりません|いけない|いけません)"
           r"|ないといけ(?:ない|ません)|ねばなら(?:ない|ず)"
           r"|必要(?<!不必要)(?:があ(?:る|ります)|(?:に|と)(?:なる|なります)|(?:です|だ)(?=[。！!]|$))"
           r"|べき(?<!しかるべき)(?<!然るべき)(?<!驚くべき)(?<!恐るべき)(?<!来るべき)(?<!特筆すべき)(?<!注目すべき)(?!乗)"
           r"|ものと(?:する|します)|必須"),
    ("禁止", r"(?:て|で)は(?:いけ|なら)(?:ない|ません)|禁止"),
    ("保証", r"保証(?:する|します|される|されます|いたします|致します|(?:して|されて)(?:いる|います))(?=[。、]|$)"
           r"|担保(?:する|します|される|されます)(?=[。、]|$)|必ず(?!しも)|確実に"
           r"|ことは(?:ない|ありません|ございません)(?=[。]|$)"),
)
MODALITY_MARKERS = OrderedDict((kind, re.compile(pattern, re.M)) for kind, pattern in _MODALITY_PATTERNS)

_MODALITY_LITERALS = {
    "許可": ("てよ", "でよ", "て良", "で良", "もよ", "も良", "いい", "構", "かま", "支え", "結構", "問題", "大丈夫", "許可"),
    "能力": ("でき", "出来", "可能"),
    "能力（弱い印）": ("",),
    "不要": ("なくて", "ないで", "不要", "不必要", "必要"),
    "義務": ("なければ", "なくては", "ないといけ", "ねばなら", "必要", "べき", "ものと", "必須"),
    "禁止": ("はいけ", "はなら", "禁止"),
    "保証": ("保証", "担保", "必ず", "確実に", "ことは"),
}

_ABILITY_NEGATIVE = re.compile(r"(?:でき|出来)(?:な|ませ|ず|て(?:い|おり|お)?(?:な|ませ|らず))|不可能")

_MODALITY_NAMES = (("能力", ("能力", "能力（弱い印）")), ("不要", ("不要",)), ("義務", ("義務",)), ("禁止", ("禁止",)),
                   ("保証", ("保証",)))

def _modality_positions(text):
    found = [(m.start(), kind, m.group(0)) for kind, pattern in MODALITY_MARKERS.items()
             if any(literal in text for literal in _MODALITY_LITERALS[kind]) for m in pattern.finditer(text)]
    found.sort(key=lambda item: item[0])
    return found

def _modality_names(kinds, fallback):
    names = [name for name, members in _MODALITY_NAMES if any(member in kinds for member in members)]
    return "・".join(names) if names else fallback

def _shared_ranges(o: str, r: str):
    last = _LAST_TYPE_RANGES[0]
    if last is not None and last[0] == o and last[1] == r:
        opcodes, ranges, o_marks, r_marks = last[2:]
    else:
        opcodes = _ExactSequenceMatcher(None, o, r, autojunk=False).get_opcodes()
        ranges, o_marks, r_marks = None, _mark_positions(o), _mark_positions(r)
    if ranges is None:
        ranges = _type_ranges(o, r, opcodes)
        _LAST_TYPE_RANGES[0] = (o, r, opcodes, ranges, o_marks, r_marks)
    return ranges, o_marks, r_marks

def _modality_changes(o: str, r: str):
    if o == r:
        return []
    o_pos, r_pos = _modality_positions(o), _modality_positions(r)
    if not any(kind in ("許可", "能力") for _, kind, _ in o_pos) and not any(kind == "許可" for _, kind, _ in r_pos):
        return []
    ranges, o_marks, r_marks = _shared_ranges(o, r)
    keys = [item[0] for item in o_pos], [item[0] for item in r_pos]
    type_keys = [item[0] for item in o_marks], [item[0] for item in r_marks]
    out = []
    for texts, spans, a, b in ranges:
        before = _marks_in(o_pos, spans, MODALITY_MARKERS, keys[0])
        after = _marks_in(r_pos, [(a, b)], MODALITY_MARKERS, keys[1])
        lost = [kind for kind in before if kind not in after]
        added = [kind for kind in after if kind not in before]
        found = []
        if "許可" in lost:
            found.append(("permission_lost", "許可", _modality_names(added, "断定")))
        if "許可" in added:
            found.append(("permission_added", _modality_names(lost, "断定"), "許可"))
        if ("能力" in lost and "能力（弱い印）" not in added and "許可" not in added
                and any(not _ABILITY_NEGATIVE.match(hit) for hit in before["能力"])):
            found.append(("ability_lost", "能力", _modality_names(added, "断定")))
        if not found:
            continue
        rule_before = "依頼・決まり" in _marks_in(o_marks, spans, keys=type_keys[0])
        if rule_before != ("依頼・決まり" in _marks_in(r_marks, [(a, b)], keys=type_keys[1])):
            continue
        orig, rewrite = "".join(texts), _range_sentences(r, a, b)
        for subkind, source, target in found:
            out.append({"orig": orig, "rewrite": rewrite, "subkind": subkind, "from": source, "to": target,
                        "lost": [{"kind": kind, "hits": before[kind]} for kind in lost],
                        "added": [{"kind": kind, "hits": after[kind]} for kind in added]})
    return out

_CHOICE_NOUN = r"[一-龥々ァ-ヴーA-Za-zＡ-Ｚａ-ｚ0-9０-９]"

_CHOICE_ITEM = (_CHOICE_NOUN + r"{1,15}(?:[しりきみちえけせてめれ](?<=[一-龥][しりきみちえけせてめれ])(?=[もの]))?")
_CHOICE_PHRASE = _CHOICE_ITEM + r"(?:の" + _CHOICE_ITEM + r"){0,2}"

_CHOICE_BEFORE = r"(?:(?<=" + _CHOICE_NOUN + r")|(?<=[一-龥][しりきみちえけせてめれ]))"

_RELATION_END = r"(?![一-龥々ァ-ヴー]|か(?!も)|とは(?:言|い)え|とは限ら|わけでは)"
_RELATION_PRED = (r"(?:が|は|も)?(?:ある" + _RELATION_END + r"|あり(?!ませ|えな)|あった" + _RELATION_END
                  + r"|(?:見られ|みられ|認められ|指摘され|示され|確認され)(?!な|ず|ませ)"
                  + r"|(?:強い|深い|高い)" + _RELATION_END + r")")
_RELATION_STATE = r"(?:(?:いる|いた)" + _RELATION_END + r"|います|おり|いました)"

_CAUSE_LEAD = (r"(?<=[一-龥々ァ-ヴー])"
               + "".join(r"(?<!{})".format(word) for word in ("サーバー", "ネット", "ネットワーク", "回線", "電源", "環境", "端末",
                                                             "ホスト", "ポート", "ノード", "機器", "拠点", "外部", "社内",
                                                             "電話", "窓口", "担当")))
_LOGIC_PATTERNS = (
    ("どれか一つ", r"または|もしくは|あるいは|どちらか(?!ら|と(?:いえば|言えば|いうと|言うと))|いずれか(?!ら)|どれか(?!ら)"
                 r"|片方(?:だけ|のみ)|択一"
                 r"|か(?<=[一-龥々ァ-ヴーA-Za-zＡ-Ｚａ-ｚ]か)(?<![何誰数幾]か)(?<![何数幾][一-龥]か)(?<![0-9０-９一二三四五六七八九十百千]か)"
                 r"(?!所|箇所|ヵ所|月|国|条|年|日|否|確|判|検|調|評|決|点|把|見極|吟味|試|迷|問|尋|分か|明|心配|不安|気)"
                 r"(?=" + _CHOICE_NOUN + r"{1,15}(?:[をがでにのはもと、。]|か|$))"),
    ("どれでも", r"(?:どちら|いずれ|どれ)(?:から|で|に|を)?でも"
               r"|" + _CHOICE_BEFORE + r"(?:で|から)も、?" + _CHOICE_PHRASE + r"(?:で|から)も"),
    ("どれか一つ（連体）", r"(?:いずれ|どれ|どちら)か(?:一つ|ひとつ|1つ|１つ|一方)?の" + _CHOICE_NOUN + r"{1,10}"),
    ("全部", r"両方(?!向)|双方(?!向)|どちらも|いずれも|どれも|両者とも|[二三2-3２-３]つとも"
           r"|どちらとも(?!言|い|取|と|つ|決|判|限|不|評)|(?:どちら|いずれ|どれ)(?:に|へ)も"
           r"|(?<=の)(?:すべて|全て|全部)(?!の)|(?:すべて|全て|全部)(?=[をがも]|に(?!おい|わた|渡))"
           r"|ともに(?<=[はがも]ともに)|共に(?<=[はがも]共に)|(?:どちら|いずれ|どれ)の" + _CHOICE_NOUN + r"{1,10}も(?![のう])"
           r"|" + _CHOICE_BEFORE + r"(?:に|と|へ)?も、?" + _CHOICE_PHRASE + r"(?:に|と|へ)?も(?![のう])"),
    ("全部（連体）", r"(?:すべて|全て|全部)の" + _CHOICE_NOUN + r"{1,10}|(?<![一-龥々])全(?!部)[一-龥々ァ-ヴー]{1,8}"),
    ("関連", r"相関(?=(?:関係|性)?" + _RELATION_PRED + r"|して" + _RELATION_STATE + r")"
           + r"|関連(?:性)?" + _RELATION_PRED + r"|関連して" + _RELATION_STATE
           + r"|関係(?:性)?" + _RELATION_PRED + r"|関係して" + _RELATION_STATE
           + r"|(?<=[とは])(?<!には)関(?:連|係)(?:する|します)(?=[。！!]|$|と(?:され|考えられ|いわれ|言われ|みられ|見られ))"
           r"|結び(?<!に結び)(?:つ|付)いて" + _RELATION_STATE
           + r"|(?:関わり|かかわり)(?:が|は|も)?(?:ある" + _RELATION_END + r"|あり(?!ませ)|あった" + _RELATION_END
           + r"|(?:深い|強い)" + _RELATION_END + r")"),
    ("因果", r"因果|原因|起因|要因|引き起こ[すしさせそ]|ひき起こ[すしさせそ]|もたら[すしさ]|誘発"
           r"|(?:によって|により|ことで)[^。、]{0,12}?(?:生じ|起こ|起き|発生|増え(?:る|た|て)|増加(?:し|す)|減(?:る|った|って|り)"
           r"|減少(?:し|す)|伸び(?:る|た|て)|向上(?:し|す)|改善(?:し|す)|低下(?:し|す)|上昇(?:し|す)|悪化(?:し|す))"
           r"|せい(?<=のせい|たせい|るせい|いせい)(?:で|だ|です|である)|おかげ(?:で|だ|です|である)"
           r"|影響を(?:与え|及ぼ)|" + _CAUSE_LEAD + r"につなが(?:る|り|った|ります|りました)|(?<![者師客様人員長氏家生方])を招(?:く|き|いた)"
           r"|(?<![査析験討認議論測定計証審票断索選較トそこあ])の結果、"),
    ("因果（広い）", r"によ(?:る|り|って)|影響|で(?:起き|起こ|生じ|発生)|から(?:生じ|起き|起こ|来)|ため|理由|せい|おかげ|結果"
                  r"|につなが|招|由来|きっかけ|引き金|(?<!も)ので(?![はす])|だから|ゆえ|故に"
                  r"|で[^。、]{0,8}?(?:増え|減っ|減り|増加|減少|伸び|落ち|下が|上が)"),
)
LOGIC_MARKERS = OrderedDict((kind, re.compile(pattern, re.M)) for kind, pattern in _LOGIC_PATTERNS)

_LOGIC_LITERALS = {
    "どれか一つ": ("または", "もしくは", "あるいは", "どちらか", "いずれか", "どれか", "片方", "択一", "か"),
    "どれでも": ("でも", "も"),
    "どれか一つ（連体）": ("かの", "一つの", "ひとつの", "1つの", "１つの", "一方の"),
    "全部": ("両方", "双方", "どちらも", "いずれも", "どれも", "両者とも", "つとも", "どちらとも", "すべて", "全て", "全部", "ともに",
           "共に", "も"),
    "全部（連体）": ("すべての", "全ての", "全部の", "全"),
    "関連": ("相関", "関連", "関係", "結び", "関わり", "かかわり"),
    "因果": ("因果", "原因", "起因", "要因", "起こ", "もたら", "誘発", "生じ", "起き", "発生", "増", "減", "伸び", "向上", "改善", "低下",
           "上昇", "悪化", "せい", "おかげ", "影響を", "つなが", "招", "結果"),
    "因果（広い）": ("によ", "影響", "で", "から", "ため", "理由", "せい", "おかげ", "結果", "つなが", "招", "由来", "きっかけ", "引き金",
                "ので", "だから", "ゆえ", "故に"),
}

_LOGIC_CHANGES = (("one_to_all", "choice", "どれか一つ", "全部"), ("all_to_one", "choice", "全部", "どれか一つ"),
                  ("relation_to_cause", "causality", "関連", "因果"))

_QUESTION_KA_LEFT = re.compile(r"(?:が" + _CHOICE_NOUN + r"{1,15}|有効|無効|正常|異常|最新版?|必要|不要|可能|不可|適切|妥当|正確"
                               r"|完了|対象|該当|安全|十分|問題|適用|OK|NG)$")
_QUESTION_KA_RIGHT = re.compile(_CHOICE_PHRASE + r"(?:に|へ|で|が|から|まで)?(?:確認|問い合わせ|問合せ|聞|尋|相談|確か|照会|伺|質問"
                                r"|判断|判定|調べ|調査|検証|点検|チェック|見極|報告|連絡|回答)")

_CHOICE_NOUN_CHAR = re.compile(_CHOICE_NOUN)
_CHOICE_HEAD = re.compile(r"(?:に|と|へ|で|から)?も")

def _choice_item_start(text, start):
    i, floor = start, max(0, start - 30)
    while i > floor:
        ch = text[i - 1]
        if _CHOICE_NOUN_CHAR.match(ch):
            i -= 1
        elif ch == "の" and i < start and i - 2 >= 0 and _CHOICE_NOUN_CHAR.match(text[i - 2]):
            i -= 1
        elif ch in "しりきみちえけせてめれ" and i == start and i - 2 >= 0 and "一" <= text[i - 2] <= "龥":
            i -= 1
        else:
            break
    return i

def _logic_positions(text):
    found = []
    for kind, pattern in LOGIC_MARKERS.items():
        if not any(literal in text for literal in _LOGIC_LITERALS[kind]):
            continue
        for m in pattern.finditer(text):
            start, hit = m.start(), m.group(0)
            if kind == "どれか一つ" and hit == "か":
                if (_QUESTION_KA_LEFT.search(text, max(0, start - 16), start)
                        and _QUESTION_KA_RIGHT.match(text, start + 1)):
                    continue
            elif kind in ("全部", "どれでも") and _CHOICE_HEAD.match(hit) and start and not hit.startswith("とも"):
                head = _choice_item_start(text, start)
                if head < start:
                    hit = text[head:start] + hit
            found.append((start, kind, hit))
    found.sort(key=lambda item: item[0])
    return found

def _logic_hits(positions, spans, keys):
    marks = {}
    for start, end in spans:
        for _, kind, hit in positions[bisect_left(keys, start):bisect_left(keys, end)]:
            marks.setdefault(kind, []).append(hit)
    return marks

def _logic_tails(r, ranges):
    spans = _sentence_spans(r)
    starts = [s for s, _ in spans]
    owned = [False] * len(spans)
    for _, _, a, b in ranges:
        k = max(0, bisect_right(starts, a) - 1)
        while k < len(spans) and spans[k][0] < b:
            if spans[k][1] > a:
                owned[k] = True
            k += 1
    tails = []
    for _, _, a, b in ranges:
        extra, k, end = [], bisect_left(starts, b), b
        while k < len(spans) and len(extra) < 2 and not owned[k] and "\n" not in r[end:spans[k][0]]:
            extra.append(spans[k])
            end = spans[k][1]
            k += 1
        tails.append(extra)
    return tails

def _adnominal_noun(hit):
    return hit[hit.index("の") + 1:] if "の" in hit else hit[1:]

def _unique(hits):
    out = []
    for hit in hits:
        if hit not in out:
            out.append(hit)
    return out

def _logic_changes(o: str, r: str):
    if o == r:
        return []
    o_pos, r_pos = _logic_positions(o), _logic_positions(r)
    o_kinds, r_kinds = {kind for _, kind, _ in o_pos}, {kind for _, kind, _ in r_pos}
    if "全部（連体）" in o_kinds:
        o_kinds.add("全部")
    if "全部（連体）" in r_kinds:
        r_kinds.add("全部")
    if not any(source in o_kinds and target in r_kinds for _, _, source, target in _LOGIC_CHANGES):
        return []
    ranges = _shared_ranges(o, r)[0]
    keys = [item[0] for item in o_pos], [item[0] for item in r_pos]
    tails = _logic_tails(r, ranges) if "関連" in o_kinds and "因果" in r_kinds else [[] for _ in ranges]
    out = []
    for (texts, spans, a, b), extra in zip(ranges, tails):
        before = _logic_hits(o_pos, spans, keys[0])
        after = _logic_hits(r_pos, [(a, b)], keys[1])
        nouns = {side: {_adnominal_noun(hit) for hit in hits.get("どれか一つ（連体）", ())}
                 for side, hits in (("o", before), ("r", after))}
        alls = {side: {_adnominal_noun(hit) for hit in hits.get("全部（連体）", ())} for side, hits in (("o", before), ("r", after))}
        promoted = {side: [hit.split("の")[0] if "の" in hit else hit for hit in hits.get("全部（連体）", ())
                           if _adnominal_noun(hit) in nouns[other] and _adnominal_noun(hit) not in alls[other]]
                    for side, other, hits in (("o", "r", before), ("r", "o", after))}
        alls = {"o": before.get("全部", []) + promoted["o"], "r": after.get("全部", []) + promoted["r"]}
        for subkind, kind, source, target in _LOGIC_CHANGES:
            end = b
            if subkind == "one_to_all":
                old = before.get(source, [])
                if (not old or len(alls["r"]) <= len(alls["o"]) or source in after or "どれでも" in after):
                    continue
                new_hits = [hit for hit in _unique(alls["r"]) if hit not in alls["o"]] or _unique(alls["r"])
            elif subkind == "all_to_one":
                old = alls["o"]
                if not old or target not in after or target in before or alls["r"]:
                    continue
                new_hits = _unique(after[target])
            else:
                tail = _logic_hits(r_pos, extra, keys[1]) if extra else {}
                found = after.get(target, []) + tail.get(target, [])
                old = before.get(source, [])
                if not old or not found or target in before or "因果（広い）" in before:
                    continue
                new_hits = _unique(found)
                end = b if target in after else extra[-1][1]
            out.append({"orig": "".join(texts), "rewrite": _range_sentences(r, a, end), "kind": kind, "subkind": subkind,
                        "from": source, "to": target, "old_hits": _unique(old), "new_hits": new_hits})
    return out

CONTENT = re.compile(r"[一-龥々〆ヵヶ]{2,}|[ァ-ヴー]{2,}|[A-Za-z][A-Za-z0-9_.+#/-]+")

def bold_head(where: str = "") -> str:
    return f"■ 太字にならない書き方（{where}GitHub などで ** がそのまま表示されることがある。表示可否と案の範囲を確認して直す）"

def bold_lines(problems):
    return [f"- {p['line']}行目: {p['found']} → {p['suggest'] or '（手で直す）'}（{p['how']}）" for p in problems]

_PROTECTED_LABELS = {"code": "コード", "inline_code": "インラインのコード", "url": "URL", "link": "リンク先",
                     "frontmatter": "先頭の設定", "html": "HTML", "quote": "引用"}

FAIL_ON_KINDS = ("number", "negation", "swap", "sentence_type", "citation", "certainty", "state", "promise", "modality",
                 "choice", "causality", "number_qualifier")

def fail_on_count(risks):
    return sum(1 for risk in risks
               if risk["kind"] in FAIL_ON_KINDS or (risk["kind"], risk.get("subkind")) == ("unsupported", "number"))

_QUALIFIER_LABELS = {"approx": "概数", "lower_in": "その数を含む下限", "lower_ex": "その数を含まない下限",
                     "upper_in": "その数を含む上限", "upper_ex": "その数を含まない上限",
                     "bound_verb": "動詞で言う範囲"}

def meaning_risks(orig, rw, full=None, type_changes=None, *, doc_type=None):
    doc_type = normalize_doc_type(doc_type)
    if full is None:
        full = full_diff(orig, rw)
    modality = logic = None
    if type_changes is not None:
        try:
            o, r = normalize(orig), normalize(rw)
            modality = _modality_changes(o, r)
            logic = _logic_changes(o, r)
        finally:
            _LAST_TYPE_RANGES[0] = None
    return _meaning_risks(_Sides(orig, rw), full, type_changes, doc_type=doc_type, modality=modality, logic=logic)

def _meaning_risks(sides, full, type_changes, groups=None, doc_type=None, modality=None, logic=None):
    if groups is None:
        groups = _sentence_pairs(sides, full)
    found = (_number_risks(sides, full, groups) + _negation_risks(sides, groups) + _swap_risks(sides, groups)
             + _question_risks(sides, groups) + _protected_risks(sides, full) + _contrast_risks(sides, groups)
             + _feeling_risks(sides, groups))
    found.sort(key=lambda item: (item[0], _RISK_ORDER.get(item[2]["kind"], 9), item[1]))
    all_marks = _marks_risks(sides, type_changes)
    quiet, delegated = [], []
    for mark in all_marks:
        classification = _classify_hedge_marks(mark["old"], mark["new"], mark["detail"]["lost"], mark["detail"]["added"])
        if classification in ("same", "strengthen"):
            quiet.append(mark)
            if classification == "strengthen":
                delegated.append(mark)
    quiet_ids = {id(mark) for mark in quiet}
    risks = [risk for _, _, risk in found] + [mark for mark in all_marks if id(mark) not in quiet_ids]
    sides.immutable, citations = _immutable_values(sides, risks, groups)
    citations.sort(key=lambda r: (r["old_line"] if r["old_line"] is not None else r["new_line"] or 0,
                                  r["new_line"] if r["new_line"] is not None else 0))
    risks += citations
    masks = (_Masker(sides, 0), _Masker(sides, 1))
    certainty = _certainty_risks(sides, groups, risks, masks, doc_type=doc_type)
    strengthened = [(r["old_line"], normalize(r["old"] or "").strip()) for r in certainty
                    if (r["kind"], r["subkind"]) == ("certainty", "strengthened")]
    restored_ids = set()
    for mark in delegated:
        old = normalize(mark["old"] or "").strip()
        if not any(old and text and (old in text or text in old)
                   and (mark["old_line"] is None or line == mark["old_line"]) for line, text in strengthened):
            restored_ids.add(id(mark))
    if restored_ids:
        quiet_ids -= restored_ids
        risks = ([risk for _, _, risk in found]
                 + [mark for mark in all_marks if id(mark) not in quiet_ids] + citations)
        certainty = _certainty_risks(sides, groups, risks, masks, doc_type=doc_type)
    sides.quiet_marks = [mark for mark in quiet if id(mark) in quiet_ids]
    added = (certainty + _quote_risks(sides, groups, masks) + _modality_risks(sides, modality) + _logic_risks(sides, logic)
             + _qualifier_risks(sides, groups))
    added.sort(key=lambda r: (r["old_line"] if r["old_line"] is not None else r["new_line"] or 0,
                              r["new_line"] if r["new_line"] is not None else 0))
    risks += added
    additions = _addition_risks(sides, groups, risks + sides.quiet_marks, masks)
    lost = [_Body('', r['old'], r['old_line'], 0) for r in additions if r['kind'] == 'state']
    risks = [r for r in risks if r['kind'] != 'certainty_review'
             or not any(_same_review_sentence(body, r) for body in lost)]
    additions.sort(key=lambda r: (r['old_line'] if r['old_line'] is not None else r['new_line'] or 0,
                                  r['new_line'] if r['new_line'] is not None else 0))
    return risks + additions

_CERTAINTY_LEVELS = {1: "可能性", 2: "見込み・推量", 3: "予定", 4: "断定", 5: "確実"}

_DIALOGUE = re.compile(r"^[^「」『』、。\s]{0,8}[「『].*[」』][。．]?$")
_QUOTE_CLOSE = {"「": "」", "『": "』"}

_QUOTE_DROP = re.compile(r"[\s、。，．,.!！…‥・〜~－-]|\.\.\.")

_ADD_TOPIC_STOP = ("現在", "現時点", "時点", "今回", "本日", "当日", "以下", "下記", "件")

_ADD_OLD_INTRANSITIVE = re.compile(r"(?:見つか|分か|わか|消え|変わ|増え|減|届|始ま|終わ|決ま|遅れ|止ま|動|起き|起こ|残|続|かか|間に合|替わ|上が|下が|広が|つなが|生じ|現れ|壊れ|外れ|漏れ|集ま|伸び|延び|縮)(?:る|く|う|ります|ります|きます|えます|れます|びます|ません|らない|かない|わない|ない)$")

_ADD_OLD_STATIVE = re.compile(r"(?:あり|い|おり|でき|ござい|分かり|わかり|なり)(?:ます|ません)$")

_ADD_GUARANTEE_FAM = {"ことはない": r"ことは(?:ありません|ございません|ない)",
                 "費用はかからない": r"(?:費用|料金|料(?=は|が|を|も)|負担|手数料)(?:は|が|も)?[^。]{0,8}?(?:かから|かかりません|発生し(?:ない|ません)|いただき?ません|不要|なし|ゼロ|[0０〇]円)|無料|無償|[0０〇]円",
                 "まま使える": r"まま|問題なく|支障なく|これまでどおり|これまで通り|安心",
                 "変えない": r"(?:変え|上げ|値上げし|変更し|据え置)(?:ない|ません|く)", "保証": r"保証|約束"}

_ADD_TIME_LINK = re.compile(r"(?:とき|(?<![日同当常定随一臨即瞬何毎])時)(?:に|は|、)|(?<![実交国])際(?:に|は|、)|(?:直後|最中)に")

_ADD_CONTENT = re.compile("[" + _ADD_K + "]{2,}|[ァ-ヴー]{2,}|[A-Za-z][A-Za-z0-9]+")

def _addition_topic(text, pos):
    start = max(text.rfind("。", 0, pos), text.rfind("、", 0, pos)) + 1
    words = [w for w in _ADD_CONTENT.findall(text[start:pos]) if w not in _ADD_TOPIC_STOP]
    if not words:
        words = [w for w in _ADD_CONTENT.findall(text[max(text.rfind("。", 0, pos) + 1, 0):pos]) if w not in _ADD_TOPIC_STOP]
    return words

def _addition_on_topic(topic, text):
    return not topic or any(w in text or any(w[i:i + 2] in text for i in range(len(w) - 1)) for w in topic)

def _addition_key_head(key):
    key = re.sub("^[おご]", "", key)
    m = re.match("[" + _ADD_K + "ァ-ヴー]+", key)
    if not m:
        return key[:2]
    head = m.group(0)
    if len(head) == 1 and len(key) > 1:
        head = key[:2]
    return head

_ADD_PRED_SKIP = set("来週月日年今明後前次回時分秒中内外本当弊社私様方等毎朝夕夜昼午予定針第度場合上下末初")

_ADD_PRED_SYNONYMS = {
    "直": ("修正", "修理", "訂正", "改修", "是正", "対応"), "出": ("提出", "送付", "発行", "提示", "お送"),
    "送": ("送付", "発送", "送信", "お送"), "作": ("作成", "作製", "制作", "用意", "準備"), "調": ("調査", "確認"),
    "見": ("確認", "拝見", "目を通"), "読": ("拝読", "確認"), "書": ("記載", "記入", "作成"),
    "伝": ("連絡", "報告", "知らせ", "共有"), "知": ("連絡", "報告", "通知", "案内"), "言": ("連絡", "報告", "申し", "伝え"),
    "返": ("返信", "返答", "回答", "返却"), "決": ("決定", "確定"), "変": ("変更",), "止": ("停止", "中止", "終了"),
    "始": ("開始", "着手"), "続": ("継続", "引き続"), "払": ("支払", "入金"), "届": ("お届", "配送", "納品"),
    "渡": ("お渡", "提出", "送付"), "聞": ("確認", "伺", "お聞"), "片": ("整理",), "用": ("準備", "手配"),
    "準": ("用意", "手配"), "手": ("準備", "用意"),
}

def _addition_pred_stem(text, end):
    left = text[:end]
    for _ in range(2):
        seg = re.search("[" + _ADD_K + "ァ-ヴー]*[ぁ-ん]*$", left).group(0)
        stem = frozenset(c for c in seg if re.match("[" + _ADD_K + "ァ-ヴー]", c) and c not in _ADD_PRED_SKIP)
        if stem or not seg:
            return stem
        left = left[:len(left) - len(seg)]
    return frozenset()

def _addition_old_futures(text):
    if _ADD_PAST_END.search(text.rstrip()) and not re.search(r"(?:ます|する|ない|ません)(?:が|ので|、)", text):
        return []
    if _is_question(text) or text.rstrip().endswith("か"):
        return []
    out = []
    for m in _ADD_OLD_FUTURE.finditer(text):
        if re.match(r"(?:予定|つもり|方針)(?:は|が|も)?(?:ない|なく|ありません|ございません|なし)", text[m.start():m.start() + 12]):
            continue
        s = text[max(0, m.start() - 4):m.end()]
        if _ADD_OLD_STATIVE.search(s) and not re.search(r"いたします$", s) or _ADD_OLD_INTRANSITIVE.search(s) or re.search(r"(?:です|でした|だ|である)$", s):
            continue
        out.append(_addition_pred_stem(text, m.end()))
    stripped = text.rstrip().rstrip("。")
    if re.search("[" + _ADD_K + "]{2}$", stripped):
        out.append(_addition_pred_stem(stripped, len(stripped)))
    return out

def _addition_old_negatives(text):
    return [_addition_pred_stem(text, m.end()) for m in
            re.finditer(r"(?<!あり)(?<!ござい)(?:ない|ません)(?=[。、]|$|ので|が)", text)]

def _addition_same_act(stem, part):
    if not stem:
        return True
    if any(c in part for c in stem):
        return True
    return any(word in part for c in stem for word in _ADD_PRED_SYNONYMS.get(c, ()))

def _addition_bigrams(text):
    t = re.sub(r"[\s、。，．・「」『』（）()]", "", text)
    return set(t[i:i + 2] for i in range(len(t) - 1))

def _addition_novelty(span, old_doc, old_bigrams=None):
    words = [w for w in _ADD_CONTENT.findall(span)]
    if not words:
        return 0.0
    if old_bigrams is None:
        new = [w for w in words if w not in old_doc and not any(w[i:i + 2] in old_doc for i in range(len(w) - 1))]
    else:
        new = [w for w in words if not any(w[i:i + 2] in old_bigrams for i in range(len(w) - 1))]
    return len(new) / float(len(words))

def _addition_time_to_cause(old, span):
    cause = set(_ADD_CONTENT.findall(span))
    for m in _ADD_TIME_LINK.finditer(old):
        before = old[max(old.rfind("。", 0, m.start()), old.rfind("、", 0, m.start())) + 1:m.start()]
        if cause & set(_ADD_CONTENT.findall(before)):
            return True
    return False

def _addition_cause_span(text, fam, start, end):
    if fam == "result" and not re.match(r"につなが|をもたら|に寄与|に貢献|が功", text[start:]):
        stop = text.find("。", end)
        return text[end: stop if stop >= 0 else len(text)]
    left = text[:start]
    cut = max(left.rfind("、"), left.rfind("。"), left.rfind("は"))
    return left[cut + 1:]

class _AdditionGroup:

    def __init__(self, group, masks):
        self.bodies = [[masks[side].body(s) or _Body('', s.text, s.line, s.start) for s in group[key]]
                       for side, key in enumerate(('old', 'new'))]
        self.pairs = [dict(group['pairs']), {j: i for i, j in group['pairs']}]
        self.contexts, self.texts = {}, {}
        self.future, self.negative, self.causal = None, None, None
        self.bigram_index = None
        self.covered_cache, self.joined_lines = {}, {}

    def prepare_future(self):
        if self.future is None:
            preds = {text: (_addition_old_futures(text), _addition_old_negatives(text))
                     for text in {b.text for b in self.bodies[0]}}
            self.future, self.negative = [[list(preds[b.text][n]) for b in self.bodies[0]] for n in (0, 1)]
            self.used_preds = [set() for _ in self.bodies[0]]

    def prepare_causal(self):
        if self.causal is None:
            counts = {text: len(_addition_causal_words(text))
                      for text in {b.text for b in self.bodies[0]}}
            self.causal = [counts[b.text] for b in self.bodies[0]]

    def context(self, side, index):
        key = (side, index)
        if key not in self.contexts:
            bodies, paired = self.bodies[side], self.pairs[side]
            if index is None:
                indices = [k for k in range(len(bodies)) if k not in paired]
            else:
                indices = [index] + _unpaired_neighbors(len(bodies), index, paired)
            self.contexts[key] = indices
        return self.contexts[key]

    def text(self, side, index):
        key = (side, index)
        if key not in self.texts:
            self.texts[key] = ''.join(self.bodies[side][k].text for k in self.context(side, index))
        return self.texts[key]

    def risk(self, kind, subkind, i, j, detail):
        old = self.bodies[0][i] if i is not None else None
        new = self.bodies[1][j] if j is not None else None
        return _risk(kind, subkind, old.line if old else None, new.line if new else None,
                     old.raw if old else None, new.raw if new else None, detail)

    def covered(self, text):
        if text in self.covered_cache:
            return self.covered_cache[text]
        if self.bigram_index is None:
            self.bigram_index, self.bigram_sizes = {}, []
            for k, body in enumerate(self.bodies[0]):
                grams = _addition_bigrams(body.text)
                self.bigram_sizes.append(len(grams))
                for gram in grams:
                    self.bigram_index.setdefault(gram, []).append(k)
        counts = Counter(k for gram in _addition_bigrams(text) for k in self.bigram_index.get(gram, ()))
        covered = sorted(k for k, n in counts.items() if n / float(self.bigram_sizes[k]) >= 0.4)
        self.covered_cache[text] = covered
        self.joined_lines[text] = [self.bodies[0][k].line for k in covered]
        return covered

def _addition_state_risks(doc, group):
    out = []
    for i, body in enumerate(group.bodies[0]):
        j = group.pairs[0].get(i)
        if not body.text or (j is not None and body.text == group.bodies[1][j].text):
            continue
        if any(r['old_line'] == body.line and normalize(r['old'] or '') == normalize(body.raw)
               for r in doc.by_kind.get('negation', ())):
            continue
        if any(_same_review_sentence(body, r) and any(m['kind'] in ('推量', '意見') for m in r['detail'].get('added', []))
               for r in doc.same_sentence('sentence_type', body) if r['subkind'] == 'marks'):
            continue
        lost = []
        for family, name, pos, word in doc.state_words(body.text):
            topic = _addition_topic(body.text, pos)
            near = group.context(1, j)
            if any(doc.state_kept(family, word, group.bodies[1][k].text)
                   and (k == j or _addition_on_topic(topic, group.bodies[1][k].text)) for k in near):
                continue
            if doc.counts[1][family] >= doc.counts[0][family] and any(
                    doc.state_kept(family, word, b.text) and _addition_on_topic(topic, b.text) for b in doc.bodies[1]):
                continue
            lost.append((family, word))
        if lost:
            steps = [step for r in doc.same_sentence('certainty_review', body) for step in r['detail']['steps']]
            out.append(group.risk('state', 'lost', i, j, {
                'words': [w for _, w in lost], 'families': sorted({f for f, _ in lost}), 'certainty_steps': steps}))
    return out

def _addition_promise_risk(doc, group, i, j):
    body = group.bodies[1][j]
    clauses = doc.find('promise', body.text)
    if not clauses:
        return None
    group.prepare_future()
    context = group.context(0, i)
    old_text = group.text(0, i)
    kept = []
    for sub, name, key, pos, strong in clauses:
        if sub == 'prevention':
            if doc.prevent:
                continue
        elif sub == 'guarantee':
            if re.search(_ADD_GUARANTEE_FAM[name], doc.raw):
                continue
        else:
            head = _addition_key_head(key)
            if doc.has_head(head) or (head and i is not None and re.search(
                    re.escape(head) + '(?![' + _ADD_K + 'ァ-ヴー])', old_text)):
                continue
        can_cancel = sub == 'promise' or (sub == 'guarantee' and name in ('ことはない', '変えない') and i is not None)
        if can_cancel:
            part_start = max(body.text.rfind('、', 0, pos), body.text.rfind('。', 0, pos)) + 1
            part = body.text[part_start:pos + len(key) + 4]
            paired = i
            if (name == 'ことはない' and i is not None
                    and len(_negation_marks(body.text)) > len(_negation_marks(group.bodies[0][i].text))):
                paired = None
            if not _addition_cancel(group, context, sub, part, paired):
                kept.append((sub, name, key, pos, strong))
        else:
            kept.append((sub, name, key, pos, strong))
    if i is not None and doc.same_sentence('certainty', group.bodies[0][i]):
        kept = [c for c in kept if c[0] != 'promise']
    if i is not None and not _ADD_REQUEST.search(body.text) and any(r['subkind'] == 'marks'
                             and any(m['kind'] == '依頼・決まり' for m in r['detail'].get('lost', ()))
                             and not any(m['kind'] == '依頼・決まり' for m in r['detail'].get('added', ()))
                             for r in doc.same_sentence('sentence_type', group.bodies[0][i])):
        kept = [c for c in kept if c[0] != 'promise']
    out = []
    counted = [c for c in kept if c[4]]
    weak = [c for c in kept if not c[4]]
    if counted:
        subkind = next((sub for sub in ('prevention', 'guarantee') if any(c[0] == sub for c in counted)), 'added')
        out.append(group.risk('promise', subkind, i, j, {
            'phrases': [body.text[pos:pos + max(len(key), 2) + 6] for _, _, key, pos, _ in counted],
            'names': [name for _, name, _, _, _ in counted]}))
    if weak:
        out.append(group.risk('promise_review', 'added', i, j, {
            'phrases': [body.text[pos:pos + max(len(key), 2) + 6] for _, _, key, pos, _ in weak],
            'names': [name for _, name, _, _, _ in weak]}))
    return out

def _addition_cancel(group, context, sub, part, paired):
    for k in context:
        preds = [(n, stem) for n, stem in enumerate(group.future[k])]
        if sub == 'guarantee':
            preds += [(len(group.future[k]) + n, stem) for n, stem in enumerate(group.negative[k])]
        for n, stem in preds:
            if n not in group.used_preds[k] and (k == paired or _addition_same_act(stem, part)):
                group.used_preds[k].add(n)
                return True
    return False

def _addition_claim_risks(doc, group, i, j):
    body = group.bodies[1][j]
    out, remaining = [], []
    causes = doc.find('causal', body.text)
    if causes:
        group.prepare_causal()
    for cause in causes:
        for k in group.context(0, i):
            if group.causal[k]:
                group.causal[k] -= 1
                break
        else:
            remaining.append(cause)
    if remaining:
        covered = group.covered(body.text)
        joined = len(covered) >= 2
        words = [word for family, word, start, end in remaining if joined or
                 _addition_novelty(_addition_cause_span(body.text, family, start, end), doc.old_text, doc.old_bigrams()) >= 0.5]
        reason = 'joined' if joined else 'new_content'
        if not words and i is not None:
            old = group.bodies[0][i].text
            words = [word for family, word, start, end in remaining if family == 'means'
                     and _addition_time_to_cause(old, _addition_cause_span(body.text, family, start, end))]
            reason = 'time_to_cause'
        if words:
            out.append(group.risk('claim', 'causal', i, j, {
                'words': words, 'reason': reason,
                'joined_lines': group.joined_lines[body.text] if joined else []}))
    return out

def _addition_risks(sides, groups, risks, masks):
    if not groups:
        return []
    prepared = [_AdditionGroup(source, masks) for source in groups]
    state_texts = {body.text for group in prepared for body in group.bodies[0]}
    new_texts = {body.text for group in prepared for body in group.bodies[1]}
    has_state = any(_ADD_STATE_ANY.search(text) for text in state_texts)
    patterns = [rx for _, _, rx in _ADD_PROMISE_RX] + [rx for _, rx in _ADD_CAUSAL_RX]
    if not has_state and not any(rx.search(text) for text in new_texts for rx in patterns):
        return []
    doc = _AdditionDocument(sides, masks, risks)
    out = []
    for group in prepared:
        out.extend(_addition_state_risks(doc, group))
        claims = []
        for j, body in enumerate(group.bodies[1]):
            i = group.pairs[1].get(j)
            if not body.text or (i is not None and body.text == group.bodies[0][i].text):
                continue
            promise = _addition_promise_risk(doc, group, i, j)
            if promise:
                out.extend(promise)
            claims.extend(_addition_claim_risks(doc, group, i, j))
        out.extend(claims)
    return out

def _quote_normalize(text):
    return _QUOTE_DROP.sub("", unicodedata.normalize("NFKC", text).replace("?", "？"))

def _line_quotes(text):
    stack, found, tops = [], [], []
    for position, char in enumerate(text):
        if char in _QUOTE_CLOSE:
            stack.append((position, char))
        elif char in "」』":
            depth = len(stack) - 1
            while depth >= 0 and _QUOTE_CLOSE[stack[depth][1]] != char:
                depth -= 1
            if depth < 0:
                continue
            start, opener = stack[depth]
            del stack[depth:]
            found.append((start, opener + char, text[start + 1:position]))
            if not stack:
                tops.append((start, position + 1))
    found.sort()
    return found, tops

def _blank_masked(masker, text, start):
    end = start + len(text)
    first = max(0, bisect_right(masker.lefts, start) - 1)
    chars = None
    for left, right in masker.spans[first:]:
        if left >= end:
            break
        if right <= start:
            continue
        if chars is None:
            chars = list(text)
        for k in range(max(left, start), min(right, end)):
            chars[k - start] = "\x00"
    return text if chars is None else "".join(chars)

class _QuoteSide:

    def __init__(self, sides, side, masker):
        rows = sides.analyses[side]["lines"]
        self.quotes, self.outside, self.count = {}, {}, Counter()
        by_line = OrderedDict()
        for sentence in _line_sentences(sides, side, 0, len(sides.lines[side])):
            by_line.setdefault(sentence.line, []).append(sentence)
        for line_no, sentences in by_line.items():
            row = rows[line_no - 1] if line_no - 1 < len(rows) else None
            if row is None or row["kind"] in masker.skip_kinds or _is_quote_row(row):
                continue
            line_start = sides.starts[side][line_no - 1]
            text = _blank_masked(masker, sides.lines[side][line_no - 1], line_start)
            found, tops = _line_quotes(text)
            starts = [s.start - line_start for s in sentences]
            for position, bracket, content in found:
                sentence = sentences[max(0, bisect_right(starts, position) - 1)]
                key = _quote_normalize(content)
                self.quotes.setdefault(sentence.start, []).append((key, bracket, content, sentence))
                self.count[key] += 1
            outside = list(text)
            for left, right in tops:
                outside[left:right] = "\x01" * (right - left)
            outside = "".join(outside)
            for sentence, offset in zip(sentences, starts):
                self.outside[sentence.start] = _quote_normalize(outside[offset:offset + len(sentence.text)])

def _quote_risks(sides, groups, masks=None):
    masks = masks or (_Masker(sides, 0), _Masker(sides, 1))
    old_side, new_side = _QuoteSide(sides, 0, masks[0]), _QuoteSide(sides, 1, masks[1])
    out = []
    for group in groups:
        pairs = dict(group["pairs"])
        paired_new = set(pairs.values())
        order = sorted(pairs.items())
        old_count, new_count = len(group["old"]), len(group["new"])
        for i, sentence in enumerate(group["old"]):
            quotes = old_side.quotes.get(sentence.start)
            if not quotes:
                continue
            j = pairs.get(i)
            if j is not None:
                region = [group["new"][j]] + [group["new"][k] for k in _unpaired_neighbors(new_count, j, paired_new)]
            elif new_count:
                earlier = [b for a, b in order if a < i]
                later = [b for a, b in order if a > i]
                low = earlier[-1] if earlier else 0
                high = later[0] if later else new_count - 1
                if high - low > 5:
                    middle = min(new_count - 1, i * new_count // max(1, old_count))
                    low, high = max(low, middle - 2), min(high, middle + 3)
                region = group["new"][low:high + 1]
            else:
                region = []
            region_quotes = [q for s in region for q in new_side.quotes.get(s.start, [])]
            region_keys = set(q[0] for q in region_quotes)
            outside = "\x01".join(new_side.outside.get(s.start, "") for s in region)
            partner_quotes = new_side.quotes.get(group["new"][j].start, []) if j is not None else []
            for index, (key, bracket, content, _) in enumerate(quotes):
                if len(key) < 2 or key in region_keys or key in outside:
                    continue
                if new_side.count[key] >= old_side.count[key]:
                    continue
                best, ratio = None, 0.0
                for candidate in region_quotes:
                    similarity = difflib.SequenceMatcher(None, key, candidate[0], autojunk=False).ratio()
                    if similarity > ratio:
                        best, ratio = candidate, similarity
                if ratio < 0.4 and len(partner_quotes) == len(quotes):
                    best, ratio = partner_quotes[index], 1.0
                changed = best is not None and ratio >= 0.4
                if not changed and new_side.count[key]:
                    continue
                target = best[3] if changed else (group["new"][j] if j is not None else None)
                out.append(_risk("quote", "changed" if changed else "lost", sentence.line,
                                 target.line if target else None, sentence.text, target.text if target else None,
                                 {"old_quote": content, "new_quote": best[2] if changed else None, "bracket": bracket,
                                  "dialogue": bool(_DIALOGUE.fullmatch(sides.lines[0][sentence.line - 1].strip()))}))
    return out

def _review_section(candidates, **fields):
    result = {"level": "review", "candidate_count": len(candidates), "candidates": candidates}
    result.update(fields)
    return result

def _review_candidate(subkind, old, new, detail):
    return {"subkind": subkind, "level": "review", "old_line": old.line if old else None,
            "new_line": new.line if new else None, "old": old.raw if old else None,
            "new": new.raw if new else None, "detail": detail}

_CITATION_LATIN = (r"[A-Z][a-z][A-Za-z'’.-]*(?:\s*(?:&|and)\s*[A-Z][A-Za-z'’.-]*)*"
                   r"(?:\s+et\s+al\.[,，]?\s*|[,，]\s*)")
_CITATION_JA = r"[一-鿿々〆ァ-ヴー]+(?:ほか|ら)?[,，]?\s+"
_CITATION = re.compile(
    r"\[[0-9]+(?:\s*[,、–—-]\s*[0-9]+)*\](?!\s*[([])"
    r"|[(（](?:" + _CITATION_JA + "|" + _CITATION_LATIN + r")[12][0-9]{3}[a-z]?[)）]")

_CITATION_KEY = str.maketrans({"（": "(", "）": ")", "，": ",", "、": ",", "–": "-", "—": "-", "−": "-"})

def _citation_key(text):
    return re.sub(r"\s+", "", text.translate(_CITATION_KEY))

_SCIENTIFIC_VALUE = re.compile(r"(?<![A-Za-z0-9_.])[0-9]+(?:\.[0-9]+)?[ \t　]*"
                               r"(?:[numcdkMGTμµ]?g|[numcdkμµ]?m(?:ol)?|[numcdkMμµ]?[lL]|[numkMGTμµ]?s|[kMGT]?Hz|[kMGT]?Pa|[kMGT]?W|℃|°C)(?![A-Za-z])")

_SIGNED_VALUE = re.compile(r"(?<![A-Za-z0-9_.])(?:(?<![一-鿿々〆ァ-ヴー%％)）\]])[+−-])?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)")

_STATISTIC_VALUE = re.compile(r"(?<![A-Za-z])(?:p|P|α|β|r|t|F|SD|SE)[ \t]*(?:<=|>=|[<>=≤≥])[ \t]*"
                              r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")

_EMAIL = re.compile(r"(?<![A-Za-z0-9.!#$%&'*+/=?^_`{|}~@-])[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")

_ADDRESSEE = re.compile(r"(?m)(?:^[ \t]*(?:宛先[：:][ \t]*)?|(?<=様、)[ \t]*|(?<=さん、)[ \t]*|(?<=様,)[ \t]*|(?<=さん,)[ \t]*)"
                        r"(?P<address>(?P<name>[一-鿿々〆〇○ぁ-ゖァ-ヴーA-Za-zＡ-Ｚａ-ｚ][一-鿿々〆〇○ぁ-ゖァ-ヴーA-Za-zＡ-Ｚａ-ｚ0-9０-９・＆& .　\t]{0,79}?)(?:様|さん))"
                        r"(?=[ \t　]*(?:[、，,：:！!\n]|$))")

_ADDRESSEE_FAMILY = ("婆", "爺", "母", "父", "娘", "息子", "奥", "嫁", "兄", "姉", "坊")
_VALUE_SKIP_KINDS = frozenset(("code", "frontmatter", "html_block", "reference_definition"))

def _value_tokens(sides, side, regex):
    text = sides.texts[side]
    analysis = sides.analyses[side]
    spans = sorted((a, b) for a, b, kind in analysis["protected_spans"] if kind in _BODY_MASK_KINDS)
    lefts = [a for a, _ in spans]
    out = []
    for match in regex.finditer(text):
        a, b = match.span()
        line = sides.line_of(side, a)
        if analysis["lines"][line - 1]["kind"] in _VALUE_SKIP_KINDS:
            continue
        index = max(0, bisect_right(lefts, a) - 1)
        if any(left < b and right > a for left, right in spans[index:index + 2]):
            continue
        if regex is _ADDRESSEE and match.group("name").strip() in ("皆", "みな", "たく", "お客", "お子", "お父", "お母", "お兄", "お姉", "おじい", "おばあ",
                                                                 "お疲れ", "ご苦労", "おかげ", "お陰", "お互い", "逆", "同", "有", "無"):
            continue
        value = (match.group("address") if regex is _ADDRESSEE else match.group()).strip()
        if regex is _ADDRESSEE and value.endswith(("仕様", "模様", "同様", "多様", "異様", "有様", "無様", "一様")):
            continue
        if regex is _ADDRESSEE and match.group("name").strip().endswith(_ADDRESSEE_FAMILY):
            continue
        if regex in (_SCIENTIFIC_VALUE, _STATISTIC_VALUE):
            value = re.sub(r"[ \t　]+", "", value)
        raw = sides.lines[side][line - 1]
        key = _citation_key(value) if regex is _CITATION else value
        out.append((key, _Body(value, raw, line, a)))
    return out

def _value_places(sides, groups):
    places = ({}, {})
    for g_index, group in enumerate(groups):
        for side, start_key, end_key, name in ((0, "old_start", "old_end", "old"), (1, "new_start", "new_end", "new")):
            for hunk in group.get("hunks") or [group["hunk"]]:
                for line in range(hunk[start_key], hunk[end_key] + 1):
                    places[side].setdefault(line, [g_index, []])
            for s_index, sentence in enumerate(group[name]):
                entry = places[side].get(sentence.line)
                if entry is not None:
                    entry[1].append((sentence.start, sentence.start + len(sentence.text), s_index))
    return places

def _sentence_at(ranges, position, starts_of):
    starts = starts_of.get(id(ranges))
    if starts is None:
        ordered = all(ranges[k][1] <= ranges[k + 1][0] for k in range(len(ranges) - 1))
        starts = [a for a, _, _ in ranges] if ordered else False
        starts_of[id(ranges)] = starts
    if starts is False:
        return next((s for a, b, s in ranges if a <= position < b), None)
    k = bisect_right(starts, position) - 1
    if k >= 0 and position < ranges[k][1]:
        return ranges[k][2]
    return None

def _uncancelled_tokens(old, new, places=None, groups=None):
    tagged = []
    for side, tokens in ((0, old), (1, new)):
        rows = []
        starts_of = {}
        for value, body in tokens:
            if places is None:
                rows.append((value, body, 0, None))
                continue
            entry = places[side].get(body.line)
            if entry is None:
                continue
            rows.append((value, body, entry[0], _sentence_at(entry[1], body.start, starts_of)))
        tagged.append(rows)
    alive = [[True] * len(rows) for rows in tagged]
    pair_maps = [dict(group["pairs"]) for group in groups] if groups is not None else []

    def cancel(old_key, new_key):
        waiting = {}
        for j, row in enumerate(tagged[1]):
            key = new_key(row) if alive[1][j] else None
            if key is not None:
                waiting.setdefault((key, row[0]), []).append(j)
        for i, row in enumerate(tagged[0]):
            key = old_key(row) if alive[0][i] else None
            queue = waiting.get((key, row[0])) if key is not None else None
            if queue:
                j = queue.pop(0)
                alive[0][i] = alive[1][j] = False

    if groups is not None:
        cancel(lambda row: None if row[3] is None or row[3] not in pair_maps[row[2]] else (row[2], pair_maps[row[2]][row[3]]),
               lambda row: None if row[3] is None else (row[2], row[3]))
        cancel(lambda row: row[2], lambda row: row[2])
    cancel(lambda row: 0, lambda row: 0)
    return [[(row[0], row[1]) for k, row in enumerate(rows) if alive[side][k]] for side, rows in enumerate(tagged)]

def _citation_number_covered(old, new, risks):
    a, b = old[0] if old else "", new[0] if new else ""
    if old and new and re.sub(r"[0-9]+", "", a) != re.sub(r"[0-9]+", "", b):
        return False
    if old and new:
        for risk in risks:
            if (risk["kind"] == "number" and risk["subkind"] == "order"
                    and risk.get("old_line") == old[1].line and risk.get("new_line") == new[1].line
                    and risk["detail"].get("old_order") == re.findall(r"[0-9]+", a)
                    and risk["detail"].get("new_order") == re.findall(r"[0-9]+", b)):
                return True
    for side, own, other in (("removed", old, new), ("added", new, old)):
        if own is None:
            continue
        changed = Counter(re.findall(r"[0-9]+", own[0])) - Counter(re.findall(r"[0-9]+", other[0] if other else ""))
        if not changed:
            continue
        line_key = "old_line" if side == "removed" else "new_line"
        reported = Counter()
        for risk in risks:
            if risk["kind"] == "number" and risk.get(line_key) == own[1].line:
                for item in risk["detail"].get(side, []):
                    reported.update(re.findall(r"[0-9]+", item))
        if changed - reported:
            return False
    return bool(Counter(re.findall(r"[0-9]+", a)) != Counter(re.findall(r"[0-9]+", b)))

def _immutable_values(sides, risks, groups=None):
    out, citations = [], []
    places = _value_places(sides, groups) if groups is not None else None
    for kind, regex in (("citation", _CITATION), ("addressee", _ADDRESSEE), ("email", _EMAIL),
                        ("scientific_unit", _SCIENTIFIC_VALUE), ("statistic", _STATISTIC_VALUE), ("number_sign", _SIGNED_VALUE)):
        removed, added = _uncancelled_tokens(_value_tokens(sides, 0, regex), _value_tokens(sides, 1, regex), places, groups)
        if kind == "number_sign":
            by_value = {}
            for value, body in added:
                by_value.setdefault(value.lstrip("+−-"), []).append((value, body))
            sign_pairs = []
            for own in removed:
                matches = by_value.get(own[0].lstrip("+−-"), [])
                if matches:
                    other = matches.pop(0)
                    if own[0].startswith(("-", "−")) != other[0].startswith(("-", "−")):
                        sign_pairs.append((own, other))
            removed, added = [a for a, _ in sign_pairs], [b for _, b in sign_pairs]
        for index in range(max(len(removed), len(added))):
            old = removed[index] if index < len(removed) else None
            new = added[index] if index < len(added) else None
            if kind == "statistic":
                if old is None or new is None or re.findall(r"[0-9.]+", old[0]) != re.findall(r"[0-9.]+", new[0]):
                    continue
                if re.findall(r"<=|>=|[<>=≤≥]", old[0]) == re.findall(r"<=|>=|[<>=≤≥]", new[0]):
                    continue
            if kind == "scientific_unit":
                covered = True
                for side, own in (("removed", old), ("added", new)):
                    if own is None:
                        continue
                    line_key = "old_line" if side == "removed" else "new_line"
                    if not any(r["kind"] == "number" and r.get(line_key) == own[1].line
                               and own[0] in [re.sub(r"[ \t　]+", "", v) for v in r["detail"].get(side, [])]
                               for r in risks):
                        covered = False
                if covered:
                    continue
            if kind == "citation" and _citation_number_covered(old, new, risks):
                continue
            detail = {"removed": [old[1].text] if old else [], "added": [new[1].text] if new else []}
            item = _review_candidate(kind, old[1] if old else None, new[1] if new else None, detail)
            if kind in ("citation", "scientific_unit", "statistic", "number_sign"):
                subkind = "replaced" if old and new else ("lost" if old else "added")
                citations.append(_risk("citation" if kind == "citation" else "number", subkind, item["old_line"], item["new_line"], item["old"], item["new"], detail))
            else:
                out.append(item)
    return _review_section(out, meaning_risk_count=len(citations)), citations

def _where(old_line, new_line):
    if old_line is not None and new_line is not None:
        return "（{}行目）".format(old_line) if old_line == new_line else "（元{}行目 → 後{}行目）".format(old_line, new_line)
    if old_line is not None:
        return "（元{}行目）".format(old_line)
    if new_line is not None:
        return "（後{}行目）".format(new_line)
    return ""

def _risk_line(risk):
    kind, subkind, detail = risk["kind"], risk.get("subkind"), risk.get("detail") or {}
    old_line, new_line = risk.get("old_line"), risk.get("new_line")
    where = _where(old_line, new_line)
    if kind == "state":
        return ("状態の語が消えた{}: {}。原文は、まだ決まっていない・分かっていない・済んでいないことを伝えています。"
                "決まった・済んだ・約束した形に変えていないか確かめ、変えていれば原文の状態に戻してください。".format(
                    where, "、".join(detail["words"])))
    if kind == "promise":
        label = {"added": "書き手の約束", "guarantee": "保証", "prevention": "再発防止の誓い"}[subkind]
        advice = "依頼にない誓いなら外してください。" if subkind == "prevention" else "原文と依頼にない{}なら外してください。".format(
            "約束" if subkind == "added" else "保証")
        return "原文にない{}{}: {}。{}".format(label, _where(None, new_line),
                "、".join("「{}」".format(p) for p in detail["phrases"]), advice)
    if kind in ("modality", "modality_review"):
        change = "{} → {}".format(_modality_side(detail["from"], detail["lost"]), _modality_side(detail["to"], detail["added"]))
        if subkind == "permission_lost":
            return ("許可の言い方が消えた{}: {}。原文は「〜してよい」と、してもよいことを伝えています。できることの説明や言い切りに"
                    "変えていないか確かめ、変えていれば原文の言い方に戻してください。".format(where, change))
        if subkind == "permission_added":
            return ("原文にない許可の言い方{}: {}。原文は、してもよいとは書いていません。依頼にない許可を足していないか確かめ、"
                    "足していれば原文の言い方に戻してください。".format(where, change))
        note = "" if kind == "modality" else "--fail-on には数えません。"
        return ("能力の言い方が消えた{}: {}。{}原文は「〜できる」と、できることを伝えています。「〜する」「必ず〜する」と"
                "言い切っていないか確かめ、言い切っていれば原文の言い方に戻してください。".format(where, change, note))
    if kind == "choice":
        change = "{}（{}） → {}（{}）".format(detail["from"], "、".join(detail["old_hits"]), detail["to"], "、".join(detail["new_hits"]))
        if subkind == "one_to_all":
            return ("選ぶ範囲が「どれか一つ」から「全部」に変わった{}: {}。原文は、どれか一つでよい・どれか一つに当てはまると"
                    "伝えています。全部が要る・全部に当てはまる意味に変えていないか確かめ、変えていれば原文の言い方に戻してください。"
                    .format(where, change))
        return ("選ぶ範囲が「全部」から「どれか一つ」に変わった{}: {}。原文は、全部が要る・全部に当てはまると伝えています。"
                "どれか一つでよい意味に変えていないか確かめ、変えていれば原文の言い方に戻してください。".format(where, change))
    if kind == "causality":
        return ("関連の言い方が因果の言い方に変わった{}: {}（{}） → {}（{}）。原文は、関連や相関があると述べているだけで、"
                "原因と結果とは書いていません。因果の主張に強めていないか確かめ、強めていれば原文の言い方に戻してください。".format(
                    where, detail["from"], "、".join(detail["old_hits"]), detail["to"], "、".join(detail["new_hits"])))
    if kind == "number_qualifier":
        def side(number, names, markers):
            label = "・".join(_QUALIFIER_LABELS[name] for name in names) or "印なし"
            return "{}（{}）".format(number, label) if not markers else "{}（{}: {}）".format(number, label, "、".join(markers))
        change = "{} → {}".format(side(detail["old_number"], detail["from"], detail["old_markers"]),
                                  side(detail["new_number"], detail["to"], detail["new_markers"]))
        if subkind == "lost":
            advice = ("原文は、数に概数か範囲の印を付けています。印を落として、ちょうどその数と読める書き方に変えていないか"
                      "確かめ、変えていれば原文の印を戻してください。")
        elif subkind == "added":
            advice = ("原文は、数に概数や範囲の印を付けていません。依頼にない印を足して、数の意味を変えていないか確かめ、"
                      "足していれば外してください。")
        else:
            advice = ("原文と印の種類が違います（以上と超、以下と未満は、その数を含むかどうかが違います）。数の範囲を"
                      "変えていないか確かめ、変えていれば原文の印に戻してください。")
        return "数に付いた概数・範囲の印が変わった{}: {}。{}".format(where, change, advice)
    if kind == "promise_review":
        return ("原文にない「〜します」{}: {}。--fail-on には数えません。説明や手順の文なら残し、"
                "書き手の約束として足したのなら外してください。".format(
                    _where(None, new_line), "、".join("「{}」".format(p) for p in detail["phrases"])))
    if kind == "claim":
        quoted = "、".join("「{}」".format(w) for w in detail["words"])
        reason = {"joined": "原文の別々の文を因果でつないでいます。",
                  "time_to_cause": "原文の時を言う言い方（〜時に、〜際に）を、原因の言い方に変えています。"}.get(
                      detail["reason"], "原文にない原因や効き目を足しています。")
        return ("原文にない因果のつながり{}: {}。{}原文が事実を並べていただけなら、"
                "つなぎの語を外して並べてください。".format(where, quoted, reason))
    if kind in ("certainty", "certainty_review"):
        if kind == "certainty":
            label = "確度が強まった"
        elif subkind == "strengthened":
            label = "確度が強まった恐れ（数えない変化）"
        else:
            label = "確度が弱まった"
        steps = []
        for step in detail["steps"]:
            target = "なし（断定）" if step["to"] == "断定" else step["to"]
            steps.append("{} → {}（{} → {}）".format(step["from"], target,
                         _CERTAINTY_LEVELS[step["from_level"]], _CERTAINTY_LEVELS[step["to_level"]]))
        advice = ("原文にない慎重さを足していないか確かめてください。" if subkind == "weakened"
                  else "原文の確かさに戻すか確かめてください。")
        return "{}{}: {}。{}".format(label, where, "、".join(steps), advice)
    if kind == "quote":
        prefix = "会話の" if detail["dialogue"] else ""
        bracket = detail["bracket"]
        old_quote = bracket[0] + detail["old_quote"] + bracket[1]
        if subkind == "lost":
            return "{}かぎかっこの中の言葉が推敲後にない{}: {}".format(prefix, _where(old_line, None), old_quote)
        return "{}かぎかっこの中の言葉が変わった{}: {} → {}{}{}".format(
            prefix, where, old_quote, bracket[0], detail["new_quote"], bracket[1])
    if kind == "number":
        if subkind == "lost":
            text = "消えた数値{}: {}".format(_where(old_line, None) if old_line is not None else where,
                                          "、".join(detail.get("removed", [])))
        elif subkind == "added":
            text = "元にない数値{}: {}".format(_where(None, new_line) if new_line is not None else where,
                                          "、".join(detail.get("added", [])))
        elif subkind == "order":
            text = "数値の並びが変わった{}: {} → {}".format(where, "、".join(detail.get("old_order", [])),
                                                    "、".join(detail.get("new_order", [])))
        else:
            text = "数値が変わった{}: {} → {}".format(where, "、".join(detail.get("removed", [])),
                                                "、".join(detail.get("added", [])))
        if risk.get("basis") == "material":
            text += "（資料にある値）"
        return text
    if kind == "citation":
        return "引用の印が変わった{}: {} → {}".format(where, "、".join(detail.get("removed", [])) or "なし",
                                              "、".join(detail.get("added", [])) or "なし")
    if kind == "negation":
        return "否定の有無が変わった{}: {} → {}".format(where, detail.get("old", ""), detail.get("new", ""))
    if kind == "swap":
        return "「が」「を」などが入れ替わった{}: {}".format(
            where, "、".join("{} {}→{}".format(pair["word"], pair["old"], pair["new"]) for pair in detail.get("pairs", [])))
    if kind == "sentence_type" and subkind == "question":
        if detail.get("old_is_question"):
            return "問いの文が問いでなくなった{}".format(where)
        return "問いでない文が問いになった{}".format(where)
    if kind == "protected":
        return "{}が変わった{}".format(_PROTECTED_LABELS.get(subkind, subkind), where)
    if kind == "contrast_reversal":
        return ("否定対比の主張が逆になった恐れ{}: 原文で否定されていた『{}』が、推敲後は否定のない文に出ています。"
                "主張が逆になっていないか確かめてください。".format(where, detail.get("word", "")))
    if kind == "feeling":
        return "元にない気持ちの語{}: {}".format(where, "、".join(detail.get("words", [])))
    if kind == "unsupported":
        label = "資料にない数値" if subkind == "number" else "資料にない名前"
        return "{}{}: {}".format(label, _where(None, new_line) if new_line is not None else where, detail.get("text", ""))
    return "{}{}".format(kind + ("/" + subkind if subkind else ""), where)

def _modality_side(names, items):
    if names == "断定":
        return "なし（断定）"
    members = dict(_MODALITY_NAMES)
    parts = []
    for name in names.split("・"):
        hits = [hit for item in items if item["kind"] in members.get(name, (name,)) for hit in item["hits"]]
        parts.append("{}（{}）".format(name, "、".join(hits)) if hits else name)
    return "、".join(parts)

def _risk_section(d):
    risks = d.get("meaning_risks") or []
    if not risks:
        return ""
    lines = ["■ 意味が変わる恐れ（{}件。原文と資料に照らして確かめる）".format(len(risks))]
    marks = 0
    for risk in risks:
        if (risk["kind"], risk.get("subkind")) == ("sentence_type", "marks"):
            marks += 1
            continue
        lines.append("- " + _risk_line(risk))
        if risk.get("old") is not None:
            lines.append("  元: " + risk["old"])
        if risk.get("new") is not None:
            lines.append("  後: " + risk["new"])
    if marks:
        lines.append("- 文の種類の印が変わった: {}件（下の「■ 文の種類の印が変わった文」を見る）".format(marks))
    return "\n".join(lines)

def _rule_lines(d, rewritten_only=True):
    lines = []
    if d["markers"]:
        lines.append("■ 言い回しの種類の増減（意味が変わりやすいところ）")
        for m in d["markers"]:
            lines.append(f"- {m['kind']}: {m['orig']} → {m['rewrite']}（元: {'、'.join(m['orig_hits']) or 'なし'}／後: {'、'.join(m['rewrite_hits']) or 'なし'}）")
    if d["new_words"]:
        lines.append("■ 元の文にない語: " + "、".join(d["new_words"]))
    if d["lost_words"]:
        lines.append("■ 消えた語: " + "、".join(d["lost_words"]))
    for s in d["structure"]:
        lines.append("■ " + s)
    if rewritten_only and d.get("logic"):
        lines.append("■ つながりを確かめる場所（書き直した文。何と何をつないでいるか言えるか）")
        for p in d["logic"]:
            sent = p["sentence"] if len(p["sentence"]) <= 44 else p["sentence"][:44] + "…"
            lines.append(f"- {p['kind']}: {sent}")
    e = d.get("endings") or {}
    if e.get("changes"):
        lines.append("■ 文末の種類が変わった文（立場に合う向きか見る）")
        for c in e["changes"]:
            sent = c["rewrite"] if len(c["rewrite"]) <= 44 else c["rewrite"][:44] + "…"
            lines.append(f"- {c['orig_kind']} → {c['rewrite_kind']}: {sent}")
    if d.get("type_changes"):
        lines.append("■ 文の種類の印が変わった文（伝聞・推量・意見・例え・依頼が、元の文と同じか見る）")
        for c in d["type_changes"]:
            lines.append(f"- 元: {c['orig'] if len(c['orig']) <= 60 else c['orig'][:60] + '…'}")
            lines.append(f"  後: {c['rewrite'] if len(c['rewrite']) <= 60 else c['rewrite'][:60] + '…'}")
            for label, side in (("消えた印", "lost"), ("増えた印", "added")):
                if c[side]:
                    lines.append(f"  {label}: " + "、".join(f"{m['kind']}（{'、'.join(m['hits'])}）" for m in c[side]))
    if rewritten_only and e.get("flags"):
        head = f"■ 文末の立場（{e['stance']}の文書として見た）" if e.get("stance") else "■ 文末の立場が混ざっている候補（立場を決めてから見る）"
        lines.append(head)
        for f in e["flags"]:
            lines.append(f"- {f['note']}")
            for s in f["sentences"]:
                lines.append(f"  ・{s if len(s) <= 44 else s[:44] + '…'}")
    if rewritten_only and d.get("bold"):
        lines.append(bold_head("書き直した文。"))
        lines.extend(bold_lines(d["bold"]))
    return lines

def check(orig, rw, doc_type=None):
    """本体の diff() と同じ値の meaning_risks、markers、new_words、lost_words、type_changes。
    markers 以下の3つは本体の _rule_candidates の1と2と同じ手順で作る。"""
    o, r = normalize(orig), normalize(rw)
    opcodes = _ExactSequenceMatcher(None, o, r, autojunk=False).get_opcodes() if o != r else []
    try:
        type_changes = _type_changes(o, r, opcodes)
    finally:
        _LAST_TYPE_RANGES[0] = None
    try:
        risks = meaning_risks(orig, rw, type_changes=type_changes, doc_type=doc_type)
    finally:
        _LAST_TYPE_RANGES[0] = None
    markers = []
    for name, pat in _MARKER_REGEXES:
        a, b = len(pat.findall(o)), len(pat.findall(r))
        if a != b:
            markers.append({"kind": name, "orig": a, "rewrite": b, "orig_hits": [m.group(0) for m in pat.finditer(o)],
                            "rewrite_hits": [m.group(0) for m in pat.finditer(r)]})
    o_words, r_words = set(CONTENT.findall(o)), set(CONTENT.findall(r))
    return {"meaning_risks": risks, "markers": markers,
            "new_words": sorted(w for w in r_words if w not in o_words and w not in o),
            "lost_words": sorted(w for w in o_words if w not in r_words and w not in r),
            "type_changes": type_changes}


def _mini_args(argv):
    values, as_json, i = {}, False, 0
    if "-h" in argv or "--help" in argv:
        return None, None, False, True
    while i < len(argv):
        arg = argv[i]
        name, eq, value = arg.partition("=")
        if arg == "--json":
            as_json = True
        elif name in ("--source", "--final"):
            if not eq:
                if i + 1 >= len(argv):
                    raise ValueError("{} のあとにファイルを指定してください。".format(name))
                i += 1
                value = argv[i]
            if name in values:
                raise ValueError("{} を2回指定しています。".format(name))
            if value == "":
                raise ValueError("{} の値が空です。".format(name))
            values[name] = value
        else:
            raise ValueError("使えない引数です: {}".format(arg))
        i += 1
    if "--source" not in values or "--final" not in values:
        raise ValueError("--source と --final の両方を指定してください。")
    if values["--source"] == "-" and values["--final"] == "-":
        raise ValueError("--source と --final の両方を標準入力（-）にはできません。片方はファイルで渡してください。")
    return values["--source"], values["--final"], as_json, False


def _mini_read(path):
    try:
        if path == "-":
            stream = _mini_sys.stdin
            if stream is None:
                raise ValueError("標準入力を読めません（標準入力がありません）。")
            buffer = getattr(stream, "buffer", None)
            data = buffer.read() if buffer is not None else stream.read()
        else:
            with open(path, "rb") as handle:
                data = handle.read()
        return decode_source(data)[0]
    except UnicodeDecodeError:
        raise ValueError("{} を UTF-8 として読めません。".format("標準入力" if path == "-" else path)) from None
    except OSError as error:
        raise ValueError("{} を開けません（{}）。".format(path, getattr(error, "strerror", None) or error)) from None


def main(argv=None):
    argv = list(_mini_sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    try:
        source, final, as_json, wants_help = _mini_args(argv)
        if wants_help:
            _mini_print(_MINI_USAGE)
            return 0
        orig, rw = _mini_read(source), _mini_read(final)
    except ValueError as error:
        return _mini_not_run("input", str(error), as_json)
    try:
        result = check(orig, rw)
        counted = fail_on_count(result["meaning_risks"])
        status = _mini_status("ran", version=__version__, base="{}@{}".format(SOURCE_TAG, SOURCE_COMMIT[:7]),
                              meaning_risk=len(result["meaning_risks"]), counted=counted)
        if as_json:
            text = _mini_json.dumps(dict({"format": "yomiyasu-mini-check", "format_version": 1, "status": "ran",
                                          "status_line": status, "version": __version__,
                                          "source": {"tag": SOURCE_TAG, "commit": SOURCE_COMMIT},
                                          "meaning_risk_count": len(result["meaning_risks"]), "counted": counted},
                                         **result), ensure_ascii=False, indent=1)
        else:
            lines = ["意味が変わる恐れの検査を実行しました。", status,
                     "確かめる場所の一覧で、意味が変わったという判定でも、同じだという証明でもありません。"]
            lines.append(_risk_section(result) or "■ 意味が変わる恐れ: なし")
            lines.extend(_rule_lines(dict(result, structure=[]), rewritten_only=False))
            text = "\n".join(lines + [status])
    except Exception as error:
        return _mini_not_run("check_error", "検査を最後まで実行できませんでした（{}: {}）。".format(
            type(error).__name__, error), as_json)
    _mini_print(text)
    return 0


if __name__ == "__main__":
    _mini_sys.exit(main())
