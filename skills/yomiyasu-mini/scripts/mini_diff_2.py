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

_mini_bind("mini_diff_1", "DOC_TYPES _CHAR_ALIGN_LIMIT _HALF_WIDTH _KeySet _UNITS _WEAK_EACH _WEAK_SINGLE _affix_ratio _common_affix _image_path_start _normalize_choice _unit_pattern")

def normalize_doc_type(value):
    return _normalize_choice("--doc-type", value, DOC_TYPES)

_END = r"(?=[。、！!？?よねがけのかし]|です|$)"

_TYPE_PATTERNS = (
    ("伝聞", r"そう(?:(?<=[るうくすつぬぶむぐ]そう)|(?<=だそう)|(?<=ったそう)|(?<=んだそう)|(?<=ないそう))"
           r"(?:(?:だ|です|でした|だった|で(?=、))(?=[。、！!よね]|$)|な(?=の(?:で|に|だ|です)))"
           r"|とされ(?<!落とされ)(?<!必要とされ)(?:る|ている|ています|ており|た|ます|ました|てきた)"
           r"|という(?=[。！!]|が、|$)|といいます(?<=[るうくすつぬぶむぐただ]といいます)(?=[。！!]|$)|とのこと(?<!あとのこと)(?<!後とのこと)"
           r"|によ(?<!場合によ)(?:ると|れば)|と(?:言|い)われ(?:る|ている|ています|ており|た|ます|ました|てきた)"
           r"|と聞(?<!かと聞)(?:いた|いて(?:いる|います|おり)|きました)"),
    ("推量", r"らし(?<=[るうくすつぬぶむぐいた]らし)(?:い|かった|く(?=、))" + _END
           + r"|らし(?<!素晴らし)(?<!すばらし)(?<!めずらし)(?<!わざとらし)(?<!可愛らし)(?<!かわいらし)(?<!憎らし)(?<!馬鹿らし)"
             r"(?<!ばからし)(?<!男らし)(?<!女らし)(?<!子供らし)(?<!子どもらし)(?<!いやらし)(?<!汚らし)(?<!春らし)(?<!夏らし)(?<!秋らし)"
             r"(?<!冬らし)(?<!彼らし)"

             r"(?:い(?=[。！!]|です|でした|$|(?<!人間らしい)(?<!自分らしい)(?<!大人らしい)(?<!プロらしい)(?<!学生らしい)(?:が(?!ん)|けど|けれど))"
             r"|かった(?=[。！!]|です|でした|$|が(?!ん)|けど|けれど))"
           + r"|よう(?<!次のよう)(?<!以下のよう)(?<!下記のよう)(?<!上記のよう)(?<!左記のよう)(?<!このよう)(?<!そのよう)(?<!あのよう)(?<!どのよう)"
             r"(?:(?:だ|です|でした|だった|である|であった|で(?=、))" + _END + r"|な(?=の(?:で|に|だ|です)))"
           + r"|みたい(?:(?:だ|です|でした|だった)(?=[。！!よね]|$)|な(?=の(?:で|に|だ|です)))"
           r"|かも(?:しれ|知れ)(?:ない|ません|ず)|可能性があ(?:る|ります|った|りました)"
           r"|だろう(?<!でだろう)(?!か)|であろう|でしょう(?!か)|ではない(?:でしょう|だろう)か|はず(?:だ|です|で|でした|だった)"
           r"|と(?:見|み)られ(?:る|ている|ています|ており|た|ます)|と(?:思|おも)われ(?:る|ます|た)|と考えられ(?:る|ます|た)"),
    ("意見", r"と(?:(?:私|僕|筆者|我々|われわれ|当社|弊社|私たち)は)?(?:思|おも)(?:う|い(?:ます|ました|(?=、))|った|って(?:いる|います|いた|いました|おり))"
           r"|と(?:(?:私|僕|筆者|我々|われわれ|当社|弊社|私たち)は)?(?:考え|感じ)(?:る(?!と)|ます|ました|た|て(?:いる|います|いた|いました|おり)"

           r"|(?<![0-9０-９][件人円個回倍割%％]と考え)(?<![0-9０-９][件人円個回倍割%％]と感じ)(?=、))"
           r"|ように(?:思|感じ)(?:う|います|いました|られ)"),
    ("例え", r"まるで|あたかも|さながら|(?:ごと|如)(?<!前述のごと)(?<!上記のごと)(?<!周知のごと)(?<!以下のごと)(?<!次のごと)"
           r"(?<!前述の如)(?<!上記の如)(?<!周知の如)(?<!以下の如)(?<!次の如)[くき]"),
    ("依頼・決まり", r"(?:て|で)(?:ください|下さい)|を(?:ください|下さい)|(?:ご|お)[一-龥ぁ-んァ-ヴー]{1,8}(?:ください|下さい)"
                 r"|お願い(?<!よろしくお願い)(?<!宜しくお願い)(?:します|いたします|致します|申し上げます|できますか|できますでしょうか)"
                 r"|て(?:いただけ|もらえ)(?:ますか|ませんか)|てほしい|てもらいたい|ていただきたい"
                 r"|べき(?<!しかるべき)(?<!然るべき)(?<!驚くべき)(?<!恐るべき)(?<!来るべき)(?<!特筆すべき)(?<!注目すべき)(?!乗)"
                 r"|なければ(?:ならない|なりません|ならず|いけない|いけません)|なくては(?:ならない|なりません|ならず|いけない|いけません)"
                 r"|ないといけ(?:ない|ません)|(?:て|で)は(?:いけ|なら)(?:ない|ません)|ねばなら(?:ない|ず)"
                 r"|必要(?<!不必要)(?:があ(?:る|ります|り(?=、))|(?:です|だ)(?=[。！!]|$)"
                 r"|[にと]な(?:る(?!まで)|ります|り(?=、)|った(?!ら(?!し))|りました))"),
)
TYPE_MARKERS = OrderedDict((kind, re.compile(pattern, re.M)) for kind, pattern in _TYPE_PATTERNS)

_TYPE_LITERALS = {
    "伝聞": ("そう", "とされ", "という", "といいます", "とのこと", "によると", "によれば", "われ", "と聞"),
    "推量": ("らし", "よう", "みたい", "かも", "可能性", "だろう", "であろう", "でしょう", "はず", "られ", "われ"),
    "意見": ("と思", "とおも", "と考え", "と感じ", "は思", "はおも", "は考え", "は感じ", "ように思", "ように感じ"),
    "例え": ("まるで", "あたかも", "さながら", "ごと", "如"),
    "依頼・決まり": ("ください", "下さい", "お願い", "いただけ", "もらえ", "ほしい", "もらいた", "いただきた", "べき", "なければ",
                 "なくては", "ないといけ", "はいけ", "はなら", "ねばなら", "必要"),
}

_SIMILE_HEADS = ("まるで", "あたかも", "さながら")
_SIMILE_LIKE = re.compile(r"(?:よう|みたい)(?:であった|である|だった|でした|です|だ|な|に|で)?")
_STOPS = "。！？!?\n"
_STOP = re.compile("[" + _STOPS + "]")

_NOT_BODY = set("。、，！？!?「」『』（）() \n\u3000")
_SENTENCE_PIECE = re.compile(r"[^。！？!?\n]+[。！？!?]*[」』）)]*")

def _mark_positions(text: str):
    found = [(m.start(), kind, m.group(0)) for kind, pattern in TYPE_MARKERS.items()
             if any(literal in text for literal in _TYPE_LITERALS[kind]) for m in pattern.finditer(text)]
    heads = [(start, hit) for start, kind, hit in found if kind == "例え" and hit in _SIMILE_HEADS]
    if heads:
        guesses = {start: i for i, (start, kind, _) in enumerate(found) if kind == "推量"}
        paired = set()
        for start, hit in heads:
            stop = _STOP.search(text, start)
            like = _SIMILE_LIKE.search(text, start + len(hit), stop.start() if stop else len(text))
            if like and like.start() not in paired:
                paired.add(like.start())
                i = guesses.get(like.start())
                if i is None:
                    found.append((like.start(), "例え", like.group(0)))
                else:
                    found[i] = (like.start(), "例え", found[i][2])
    found.sort(key=lambda item: item[0])
    return found

def _marks_in(positions, spans, kinds=TYPE_MARKERS, keys=None):
    if keys is None:
        keys = [item[0] for item in positions]
    marks = OrderedDict()
    for start, end in spans:
        for _, kind, hit in positions[bisect_left(keys, start):bisect_left(keys, end)]:
            hits = marks.setdefault(kind, [])
            if hit not in hits:
                hits.append(hit)
    return OrderedDict((kind, marks[kind]) for kind in kinds if kind in marks)

def _sentence_spans(t: str):
    spans, offset, in_code = [], 0, False
    for line in t.split("\n"):
        head = line.strip()
        if head.startswith("```"):
            in_code = not in_code
        elif not in_code and head and not head.startswith("|"):
            for m in _SENTENCE_PIECE.finditer(line):
                if m.group(0).strip():
                    spans.append((offset + m.start(), offset + m.end()))
        offset += len(line) + 1
    return spans

def _slide_to_sentence_edges(opcodes, o: str, r: str):
    ops = [list(op) for op in opcodes]
    for k in range(1, len(ops) - 1):
        tag, prev, nxt = ops[k][0], ops[k - 1], ops[k + 1]
        if tag not in ("insert", "delete") or prev[0] != "equal" or nxt[0] != "equal":
            continue
        if tag == "insert":
            text, a, b, left, right = r, ops[k][3], ops[k][4], prev[4] - prev[3], nxt[4] - nxt[3]
        else:
            text, a, b, left, right = o, ops[k][1], ops[k][2], prev[2] - prev[1], nxt[2] - nxt[1]
        if text[a - 1] in _STOPS:
            continue
        shifts = []
        step = 0
        while step < min(b - a, right - 1) and text[a + step] == text[b + step]:
            step += 1
            if text[a + step - 1] in _STOPS:
                shifts.append(step)
                break
        step = 0
        while step < min(b - a, left - 1) and text[a - 1 - step] == text[b - 1 - step]:
            step += 1
            if text[a - step - 1] in _STOPS:
                shifts.append(-step)
                break
        if shifts:
            shift = min(shifts, key=abs)
            prev[2] += shift
            prev[4] += shift
            ops[k][1:] = [ops[k][1] + shift, ops[k][2] + shift, ops[k][3] + shift, ops[k][4] + shift]
            nxt[1] += shift
            nxt[3] += shift
    return [tuple(op) for op in ops]

def _bigrams(text: str):
    return {text[i:i + 2] for i in range(len(text) - 1)}

_LAST_TYPE_RANGES = [None]

def _type_changes(o: str, r: str, opcodes):
    if not opcodes:
        return []
    o_marks, r_marks = _mark_positions(o), _mark_positions(r)
    if not o_marks and not r_marks:
        _LAST_TYPE_RANGES[0] = (o, r, opcodes, None, o_marks, r_marks)
        return []
    ranges = _type_ranges(o, r, opcodes)
    _LAST_TYPE_RANGES[0] = (o, r, opcodes, ranges, o_marks, r_marks)
    o_keys, r_keys = [item[0] for item in o_marks], [item[0] for item in r_marks]
    out = []
    for texts, spans, a, b in ranges:
        before = _marks_in(o_marks, spans, keys=o_keys)
        after = _marks_in(r_marks, [(a, b)], keys=r_keys)
        lost = [{"kind": kind, "hits": hits} for kind, hits in before.items() if kind not in after]
        added = [{"kind": kind, "hits": hits} for kind, hits in after.items() if kind not in before]
        if lost or added:
            out.append({"orig": "".join(texts), "rewrite": _range_sentences(r, a, b), "lost": lost, "added": added})
    return out

def _range_sentences(r, a, b):
    left = max(r.rfind(ch, 0, a) for ch in "。！？!?\n") + 1
    right = b if b and r[b - 1] in "。！？!?" else min([i for i in (r.find(ch, b) for ch in "。！？!?\n") if i != -1] + [len(r)])
    right = right + 1 if right < len(r) and r[right] in "。！？!?" else right
    return r[left:right].strip()

def _type_ranges(o: str, r: str, opcodes):
    opcodes = _slide_to_sentence_edges(opcodes, o, r)
    starts = [op[1] for op in opcodes]

    def bare(op):
        return op[0] == "insert" and not any(ch in _STOPS for ch in r[op[3]:op[4]])

    def map_start(i):
        k = max(0, bisect_right(starts, i) - 1)
        tag, i1, i2, j1, j2 = opcodes[k]
        if i1 == i and k and opcodes[k - 1][1] == i and bare(opcodes[k - 1]):
            return opcodes[k - 1][3]
        if tag == "equal":
            return j1 + min(i - i1, j2 - j1)
        return j2 if tag == "insert" else j1

    def map_end(e):
        k = bisect_left(starts, e)
        if k < len(opcodes) and opcodes[k][1] == e and o[e - 1] not in _STOPS and bare(opcodes[k]):
            return opcodes[k][4]
        tag, i1, i2, j1, j2 = opcodes[max(0, k - 1)]
        return j1 + min(e - i1, j2 - j1) if tag == "equal" else j2

    def aligned(i, j):
        k, count = max(0, bisect_right(starts, i) - 1), 0
        while k < len(opcodes) and opcodes[k][1] < j:
            tag, i1, i2, j1, j2 = opcodes[k]
            if tag in ("equal", "replace"):
                chars = sum(ch not in _NOT_BODY for ch in o[max(i, i1):min(j, i2)])
                count += chars if tag == "equal" else chars * min(1.0, (j2 - j1) / (i2 - i1))
            k += 1
        return count

    r_spans = _sentence_spans(r)
    r_starts = [a for a, _ in r_spans]

    def owns_sentence(i, j):
        a, b = map_start(i), map_end(j)
        k = bisect_right(r_starts, a) - 1
        if b <= a or k < 0 or r_spans[k][1] <= a:
            return False
        ra, rb = r_spans[k]
        whole = sum(ch not in _NOT_BODY for ch in r[ra:rb])
        part = sum(ch not in _NOT_BODY for ch in r[max(a, ra):min(b, rb)])
        return whole > 0 and part * 5 >= whole * 3
    whole = {}
    for a, b in r_spans:
        whole.setdefault(r[a:b].strip(), (a, b))
    groups, moved, gone, found = [], [], [], []
    for s, e in _sentence_spans(o):
        text = o[s:e].strip()
        body = sum(ch not in _NOT_BODY for ch in text)
        if aligned(s, e) < min(body, max(3, -(-body // 4))) and not owns_sentence(s, e):
            if text in whole:
                a, b = whole.pop(text)
                found.append((a, b))
                moved.append(([text], [(s, e)], a, b))
            else:
                gone.append((text, s, e))
            continue
        a, b = map_start(s), map_end(e)
        if b <= a or not r[a:b].strip("。！？!?、 \n"):
            continue
        if groups and a < groups[-1][3]:
            groups[-1][0].append(text)
            groups[-1][1].append((s, e))
            groups[-1][3] = max(groups[-1][3], b)
        else:
            groups.append([[text], [(s, e)], a, b])
    for fa, fb in found:
        for g in groups:
            if g[2] < fb and fa < g[3]:
                left, right = r[g[2]:max(g[2], fa)], r[min(g[3], fb):g[3]]
                if len(left.strip("。！？!?、 \n")) >= len(right.strip("。！？!?、 \n")):
                    g[3] = max(g[2], fa)
                else:
                    g[2] = min(g[3], fb)
    groups = [g for g in groups if r[g[2]:g[3]].strip("。！？!?、 \n")]
    if gone:
        groups = _pair_gone_sentences(o, r, opcodes, groups, moved, gone, r_spans)
    _widen_to_sentences(groups, moved, r_spans)
    return [tuple(g) for g in groups] + moved

def _overlapping(items, spans):
    order = sorted(range(len(items)), key=lambda k: items[k][2])
    starts = [items[k][2] for k in order]
    reach, top = [], None
    for k in order:
        end = items[k][3]
        top = end if top is None or end > top else top
        reach.append(top)
    out = []
    for a, b in spans:
        q = bisect_left(starts, b) - 1
        found = []
        while q >= 0 and reach[q] > a:
            k = order[q]
            if items[k][3] > a:
                found.append(k)
            q -= 1
        found.sort()
        out.append([items[k] for k in found])
    return out

def _pair_gone_sentences(o, r, opcodes, groups, moved, gone, r_spans):
    def dice(x, y):
        return 2 * len(x & y) / ((len(x) + len(y)) or 1)

    r_grams = [_bigrams(r[a:b].strip()) for a, b in r_spans]
    owners = _overlapping(groups, r_spans)
    moved_over = _overlapping(moved, r_spans)
    group_grams = {}

    def grams_of(g):
        grams = group_grams.get(id(g))
        if grams is None:
            grams = group_grams[id(g)] = _bigrams("".join(g[0]))
        return grams
    owner_grams = [set().union(*[grams_of(g) for g in gs + ms]) for gs, ms in zip(owners, moved_over)]
    spans_with = {}
    for idx, grams in enumerate(r_grams):
        for gram in grams:
            spans_with.setdefault(gram, []).append(idx)
    candidates = []
    passed_by_grams = {}
    for gi, (text, _, _) in enumerate(gone):
        grams = _bigrams(text)
        key = frozenset(grams)
        passed = passed_by_grams.get(key)
        if passed is None:
            passed = passed_by_grams[key] = []
            shared_counts = Counter()
            for gram in grams:
                found = spans_with.get(gram)
                if found:
                    shared_counts.update(found)
            for idx in sorted(shared_counts):
                shared_count = shared_counts[idx]
                least = 3 if min(len(grams), len(r_grams[idx])) <= 6 else 4
                if shared_count < least or shared_count < 0.5 * min(len(grams), len(r_grams[idx])):
                    continue
                shared = grams & r_grams[idx]
                if len(shared - owner_grams[idx]) < least:
                    continue
                passed.append((dice(grams, r_grams[idx]), idx))
        candidates.extend((score, gi, idx) for score, idx in passed)
    candidates.sort(key=lambda c: (-c[0], c[1], c[2]))
    used_gone, used_r, drop = set(), {}, set()
    for score, gi, idx in candidates:
        if gi in used_gone:
            continue
        text, s, e = gone[gi]
        if idx in used_r:
            entry = used_r[idx]
            first, last = entry[1][0], entry[1][-1]
            after = o[last[1]:s].strip() == "" and o[last[0]:last[1]].rstrip()[-1:] not in "。！？!?"
            before = o[e:first[0]].strip() == "" and text[-1:] not in "。！？!?"
            if not (after or before):
                continue
            used_gone.add(gi)
            entry[1].append((s, e))
            entry[1].sort()
            entry[0][:] = [o[x:y].strip() for x, y in entry[1]]
            continue
        used_gone.add(gi)
        a, b = r_spans[idx]
        moved.append(([text], [(s, e)], a, b))
        used_r[idx] = moved[-1]
        for g in owners[idx]:
            if a <= g[2] and g[3] <= b + 1:
                if dice(_bigrams("".join(g[0])), r_grams[idx]) < min(score, 0.6):
                    drop.add(id(g))
            elif g[2] < a < g[3] <= b + 1:
                g[3] = a
            elif a <= g[2] < b < g[3]:
                g[2] = b
    return [g for g in groups if id(g) not in drop]

def _widen_to_sentences(groups, moved, r_spans):
    if not groups:
        return
    r_starts, r_ends = [a for a, _ in r_spans], [b for _, b in r_spans]
    claimed = sorted([(g[2], g[3]) for g in groups] + [(m[2], m[3]) for m in moved])
    ordered = all(ca <= cb for ca, cb in claimed)
    claimed_starts = [ca for ca, _ in claimed]
    claimed_ends = sorted(cb for _, cb in claimed)
    for g in groups:
        a, b = g[2], g[3]
        i = bisect_right(r_starts, a) - 1
        j = bisect_left(r_ends, b)
        left = r_starts[i] if 0 <= i < len(r_spans) and r_ends[i] > a else a
        right = r_ends[j] if j < len(r_spans) and r_starts[j] < b else b
        if ordered and a < b:
            k = bisect_right(claimed_ends, a)
            if k:
                left = max(left, claimed_ends[k - 1])
            k = bisect_left(claimed_starts, b)
            if k < len(claimed_starts):
                right = min(right, claimed_starts[k])
        else:
            for ca, cb in claimed:
                if (ca, cb) == (a, b):
                    continue
                if cb <= a:
                    left = max(left, cb)
                elif ca >= b:
                    right = min(right, ca)
        g[2], g[3] = min(a, left), max(b, right)

_SENTENCE_END = re.compile(r"[。！？!?]+[」』）)]*")

_PROTECTED_SPANS = {"inline_code": "inline_code", "code": "code", "autolink": "url", "bare_url": "url",
                    "link_destination": "link", "reference_definition": "link", "image": "link",
                    "frontmatter": "frontmatter", "html_block": "html", "html_token": "html"}

_PROTECTED_LINES = {"code": "code", "frontmatter": "frontmatter", "html_block": "html"}

_RISK_ORDER = {"number": 0, "negation": 1, "swap": 2, "sentence_type": 3, "protected": 4, "contrast_reversal": 5,
               "feeling": 6, "certainty": 7, "certainty_review": 8, "quote": 9, "state": 10, "promise": 11, "claim": 12,
               "promise_review": 13, "modality": 14, "modality_review": 15, "choice": 16, "causality": 17,
               "number_qualifier": 18}

def _risk(kind, subkind, old_line, new_line, old, new, detail):
    return {"kind": kind, "subkind": subkind, "old_line": old_line, "new_line": new_line,
            "old": old, "new": new, "detail": detail, "basis": None}

def _group_index(group, sentence=None, side=1):
    hunks = group.get("hunks")
    if not hunks or sentence is None:
        return group["hunk"]["index"]
    start, end = ("new_start", "new_end") if side == 1 else ("old_start", "old_end")
    for hunk in hunks:
        if hunk[start] <= sentence.line <= hunk[end]:
            return hunk["index"]
    return group["hunk"]["index"]

_DATE_UNITS = ("年", "月", "日")
_TIME_UNITS = ("時", "分", "秒")

_NEXT_UNIT = {"年": "月", "月": "日", "時": "分", "分": "秒"}

_QUANTITY_WORDS = re.compile(r"一斉|一気に|いっぺんに|別々|まとめて|一括|一度に|並列|並行|同時|複数|上限|無制限|いくつ(?=[かもで])")
_QUANTITY_SAME = {"一括": "まとめて", "一度に": "まとめて", "並行": "まとめて", "並列": "まとめて", "同時": "まとめて",
                  "一斉": "まとめて", "一気に": "まとめて", "いっぺんに": "まとめて", "いくつ": "複数"}

_QUANTITY_CLAUSE_WORDS = {_WEAK_EACH: frozenset(("複数",)), _WEAK_SINGLE: frozenset(("別々",))}
_QUANTITY_FOR = {_WEAK_EACH: frozenset(("まとめて",)),
                 _WEAK_SINGLE: frozenset(("複数", "上限", "無制限"))}

_QUANTITY_KEEP_ANY = {_WEAK_SINGLE: re.compile("同じ|同一|単一"),
                      _WEAK_EACH: re.compile("(?<![㐀-䶿一-鿿豈-﫿々〆])順(?:番)?に|個別に|一件ずつ|一つずつ|ひとつずつ")}
_QUANTITY_OTHER_NOUN = re.compile("(?:複数|いくつか|いくつも)の([㐀-䶿一-鿿豈-﫿々〆ァ-ヴーA-Za-z0-9]{1,12})")

_QUANTITY_TOPIC = re.compile(r"\s*([^、。はがを]{1,20}?)(?:は|が)")
_QUANTITY_SUBJECT = re.compile("([㐀-䶿一-鿿豈-﫿々〆ァ-ヴーA-Za-z0-9]{1,12}[りれえけげせめみいきしち]?)(?:が|は)")

_QUANTITY_CLAUSE_END = re.compile(r"[、。，．,.！？!?\n]")
_QUANTITY_NEG = re.compile(r"(?<!かまわ)(?<!構わ)(?<!問題)(?<!差し支え)(?<!少)ない|なかっ|なし|(?:では|でも|じゃ|で|ことは?)なく"
                           r"|(?<!かまい)(?<!構い)(?<!問題あり)(?<!差し支えあり)ません")
_QUANTITY_LEAD = re.compile(r"(?:に|で)?して(?![もは])")
_QUANTITY_SCOPE_END = re.compile(r"ので(?!き)|のに|(?<!あら)ため|けど|けれど|(?<=[ぁ-ゖ])ても|(?<=[んい])でも"
                                 r"|(?<=[うくぐすつぬぶむるたい])から"
                                 r"|(?<=[いきぎしちびみりっえけげせねべめれ])て(?=[㐀-䶿一-鿿豈-﫿々〆ァ-ヴ])"
                                 r"|(?<=ん)で(?=[㐀-䶿一-鿿豈-﫿々〆ァ-ヴ])")
_QUANTITY_NOT_NEG = re.compile(
    r"なければ(?:なら|なりませ|いけ|だめ)[ぁ-ゖ]{0,4}|なくては(?:なら|なりませ|いけ|だめ)[ぁ-ゖ]{0,4}|ねば(?:なら|なりませ)[ぁ-ゖ]{0,4}"
    r"|ないと(?!し[たてま]|する).*|ざるを(?:得|え)[ぁ-ゖ]{0,4}|かもしれ[ぁ-ゖ]{0,4}|に違い(?:ない|ありません)"
    r"|(?:しか|ほか|ほかは)(?:ない|なかっ|ありません)"
    r"|(?:おこ|まか|とも)な(?=[いうえわっ])|(?<=お)はな(?=[しすさせ])|(?:み|こ)な(?=[しすさせ])")
_QUANTITY_LIMIT_OFF = re.compile(
    r"上限(?:[はがもをの]|について(?:は)?)?(?:特に)?(?:な[いくしかけ]|無[いくし]|ありません"
    r"|(?:設け|定め|決め|置か|置い)[ぁ-ゖ]{0,4}?(?:ない|なかっ|ず|ません)"
    r"|なく[さしすせなっ]|撤廃|廃止|外[さしすせ]|はず[さしすせ]|取り払|取り除|取り外|解除)")

_QUANTITY_SENTENCE_END = re.compile(r"[。！？!?\n]")
_QUANTITY_CLAUSE_SPLIT = re.compile(r"[、，,]")
_QUANTITY_PARTICLE_END = re.compile(r"(?:[はもがをにでとへや]|には|では|とは|からは|までは)$")

_QUANTITY_HEAD = re.compile("[" + "㐀-䶿一-鿿豈-﫿々〆" + "ァ-ヴーA-Za-z0-9]{1,12}")

_QUANTITY_KEEP_BEFORE = {_WEAK_SINGLE: "(?:同じ|同一の?|単一の?)",
                         _WEAK_EACH: "(?:順に|順番に|個別に|一件ずつ|一つずつ|ひとつずつ)"}

_QUANTITY_CHANGE_BEFORE = {_WEAK_SINGLE: "(?:(?:複数|すべて|全て|全部|別々|いくつか|いくつも)の?|各|ごと[にの](?:別々?の)?)",
                           _WEAK_EACH: "(?:まとめて|一括(?:で|して)?|一度に|並列(?:で|に|して)?|並行(?:で|に|して)?|同時(?:に|で)?"
                                       "|一斉に|一気に|いっぺんに|複数(?:件|個|の[^、。]{1,6})?(?:を|でも)?|いくつでも|いくつも)"
                                       "(?:[^、。]{1,8}?を)?"}

def _sentence_numbers(sides, side, sentence):
    numbers, starts = sides.numbers(side)
    end = sentence.start + len(sentence.text)
    return numbers[bisect_left(starts, sentence.start):bisect_left(starts, end)]

_CLAUSE_END = re.compile(r"[、，,。．！？!?]")
_CONTEXT_WORD = re.compile(r"[一-龥々〆ヵヶ]+|[ァ-ヴー]+|[A-Za-z]+")

def _number_contexts(sides, side, sentence, numbers):
    found = Counter()
    text = sentence.text
    rows = sides.analyses[side]["lines"]
    table = sentence.line - 1 < len(rows) and rows[sentence.line - 1]["kind"] == "table"
    for index, number in enumerate(numbers):
        at = number.start - sentence.start
        if table:
            context = ("|", text.count("|", 0, at))
        else:
            head = text[:at].rstrip(" \t　")
            head = "" if not head or head[-1] in "、，," else head[-2:]
            end = numbers[index + 1].start - sentence.start if index + 1 < len(numbers) else len(text)
            tail = _CLAUSE_END.split(text[number.end - sentence.start:end], 1)[0]
            context = (head, tuple(_CONTEXT_WORD.findall(tail)[:2]))
        found[(context, number.key)] += 1
    return found

def _number_texts(sides, side, numbers, keys):
    keys = Counter(keys)
    texts = []
    for number in numbers:
        if keys[number.key] > 0:
            keys[number.key] -= 1
            texts.append(sides.texts[side][number.start:number.end])
    return texts

def _number_risks(sides, full, groups):
    out = []
    old_all, new_all = sides.all_keys(0), sides.all_keys(1)
    shown_removed, shown_added = set(), set()
    order = 0
    for group in groups:
        paired_old = set(i for i, _ in group["pairs"])
        paired_new = set(j for _, j in group["pairs"])
        for i, j in group["pairs"]:
            old, new = group["old"][i], group["new"][j]
            if old.text == new.text:
                continue
            index = _group_index(group, new)
            old_numbers = _sentence_numbers(sides, 0, old)
            new_numbers = _sentence_numbers(sides, 1, new)
            old_count = Counter(number.key for number in old_numbers)
            new_count = Counter(number.key for number in new_numbers)
            raw_removed, raw_added = old_count - new_count, new_count - old_count
            extra_old = _following_unpaired(sides, 0, group["old"], i, paired_old)
            extra_new = _following_unpaired(sides, 1, group["new"], j, paired_new)
            moved_removed = _moved_keys(extra_new, raw_added, old.text, new.text) if extra_new else None
            moved_added = _moved_keys(extra_old, raw_removed, new.text, old.text) if extra_old else None
            if moved_removed:
                raw_removed -= moved_removed
            if moved_added:
                raw_added -= moved_added
            removed, added = _cancel_notation(raw_removed, raw_added, old_numbers, new_numbers)
            shown_removed.update(raw_removed - removed)
            shown_added.update(raw_added - added)
            old_text, new_text = old.text, new.text
            if any(number.weak in _QUANTITY_FOR for number in old_numbers) or any(
                    number.weak in _QUANTITY_FOR for number in new_numbers):
                old_text = _quantity_text(group["old"], i, paired_old, old, old_numbers, new_numbers, sides.texts[1])
                new_text = _quantity_text(group["new"], j, paired_new, new, new_numbers, old_numbers, sides.texts[0])
            removed, added = _drop_weak(removed, added, old_numbers, new_numbers, old_text, new_text,
                                        sides.texts[0], sides.texts[1])
            risk = None
            if removed and added:
                risk = _risk("number", "replaced", old.line, new.line, old.text, new.text,
                             {"removed": _number_texts(sides, 0, old_numbers, removed),
                              "added": _number_texts(sides, 1, new_numbers, added)})
                shown_removed.update(removed)
                shown_added.update(added)
            elif added:
                partners = _cluster_partners(new_numbers, raw_added - added, old_numbers)
                pair_set = (_KeySet(list(old_numbers) + _unpaired_around(sides, 0, group["old"], i, paired_old))
                            if partners else None)
                fresh = Counter(dict((key, count) for key, count in added.items()
                                     if not _present(key, _notation_index(new_numbers),
                                                     pair_set if key in partners else old_all)))
                if fresh:
                    risk = _risk("number", "added", old.line, new.line, old.text, new.text,
                                 {"removed": [], "added": _number_texts(sides, 1, new_numbers, fresh)})
                    shown_added.update(fresh)
            elif removed:
                partners = _cluster_partners(old_numbers, raw_removed - removed, new_numbers)
                pair_set = (_KeySet(list(new_numbers) + _unpaired_around(sides, 1, group["new"], j, paired_new))
                            if partners else None)
                gone = Counter(dict((key, count) for key, count in removed.items()
                                    if not _present(key, _notation_index(old_numbers),
                                                    pair_set if key in partners else new_all)))
                if gone:
                    risk = _risk("number", "lost", old.line, new.line, old.text, new.text,
                                 {"removed": _number_texts(sides, 0, old_numbers, gone), "added": []})
                    shown_removed.update(gone)
            elif (old_count == new_count and not any(numbers for _, numbers in extra_old)
                  and not any(numbers for _, numbers in extra_new)
                  and _order_changed(sides, old, old_numbers, new, new_numbers)):
                risk = _risk("number", "order", old.line, new.line, old.text, new.text,
                             {"old_order": [sides.texts[0][n.start:n.end] for n in old_numbers],
                              "new_order": [sides.texts[1][n.start:n.end] for n in new_numbers]})
            if risk is not None:
                out.append((index, order, risk))
                order += 1
    for side, shown, other, subkind in ((0, shown_removed, new_all, "lost"), (1, shown_added, old_all, "added")):
        found = sides.numbers(side)[0]
        notation = _notation_index(found)
        keys = set(key for key in set(number.key for number in found) - shown if not _present(key, notation, other))
        if not keys:
            continue
        sentence_at, hunk_at = _sentence_finder(sides, side, groups), _hunk_finder(full, side)
        first = OrderedDict()
        for number in found:
            if number.key in keys and number.key not in first and not number.weak:
                hunk = hunk_at(sides.line_of(side, number.start))
                if hunk is not None:
                    first[number.key] = (number, hunk)
        by_sentence = OrderedDict()
        for number, hunk in first.values():
            sentence = sentence_at(number.start)
            by_sentence.setdefault((hunk, sentence), []).append(sides.texts[side][number.start:number.end])
        for (hunk, (line, start, text)), texts in by_sentence.items():
            detail = {"removed": texts, "added": []} if side == 0 else {"removed": [], "added": texts}
            risk = (_risk("number", subkind, line, None, text, None, detail) if side == 0
                    else _risk("number", subkind, None, line, None, text, detail))
            out.append((hunk, 1000000 + start, risk))
    return out

def _order_changed(sides, old, old_numbers, new, new_numbers):
    if [number.key for number in old_numbers] == [number.key for number in new_numbers]:
        return False
    if _number_contexts(sides, 0, old, old_numbers) == _number_contexts(sides, 1, new, new_numbers):
        return False
    if _unit_orders(old_numbers) != _unit_orders(new_numbers):
        return True
    if _strong_swapped(sides.texts[0], old, old_numbers, sides.texts[1], new, new_numbers):
        return True
    for olds, news in zip(_number_phrases(sides, 0, old, old_numbers), _number_phrases(sides, 1, new, new_numbers)):
        if sum(1 for phrase in set(olds) & set(news) if olds[phrase] != news[phrase]) >= 2:
            return True
    return False

_LEAD_MODIFIERS = ("合計", "最大", "最小", "最短", "最長", "およそ", "約", "計")

def _lead(text, sentence, number):
    end = number.start
    for word in _LEAD_MODIFIERS:
        if text.endswith(word, max(sentence.start, end - len(word)), end):
            end -= len(word)
            break
    before = text[max(sentence.start, end - 2):end]
    return "^" if not before or before.endswith(("、", "，", ",")) else before

def _strong_swapped(old_text, old, old_numbers, new_text, new, new_numbers):
    olds = [(n.key, _lead(old_text, old, n)) for n in old_numbers if not n.weak]
    news = [(n.key, _lead(new_text, new, n)) for n in new_numbers if not n.weak]
    olds = [pair for pair in olds if pair[1] != "^"]
    news = [pair for pair in news if pair[1] != "^"]
    if Counter(k for k, _ in olds) != Counter(k for k, _ in news):
        return False
    if Counter(c for _, c in olds) != Counter(c for _, c in news):
        return False
    return [k for k, _ in olds] != [k for k, _ in news] and Counter(olds) != Counter(news)

def _unit_orders(numbers):
    out = {}
    for number in numbers:
        out.setdefault(number.unit, []).append(number.key)
    return out

def _number_phrases(sides, side, sentence, numbers):
    rows = sides.analyses[side]["lines"]
    if sentence.line - 1 < len(rows) and rows[sentence.line - 1]["kind"] == "table":
        return {}, {}
    text = sentence.text
    clause, near = {}, {}
    previous = 0
    for number in numbers:
        at = number.start - sentence.start
        start = max(text.rfind(mark, 0, at) for mark in "、，,") + 1
        for found, begin in ((clause, start), (near, max(start, previous))):
            phrase = text[begin:at].strip(" \t　")
            if phrase:
                found.setdefault(phrase, Counter())[number.key] += 1
        previous = number.end - sentence.start
    return clause, near

def _cluster_partners(numbers, cancelled, others):
    partners = set()
    kept = None
    for number in numbers:
        cluster = number.cluster
        if cluster is None or not (number.key in cancelled or (not number.unit and number.notation)):
            continue
        if kept is None:
            kept = set(other.key for other in others)
        if any(key in kept or key in cancelled for key in cluster):
            partners.update(cluster)
    return partners

def _moved_keys(extra, opposite, source, partner):
    units = set(unit for (_, unit), count in opposite.items() if count > 0)
    moved = Counter()
    pair_ratio = None
    for sentence, numbers in extra:
        if not numbers:
            continue
        if units and any(number.unit in units for number in numbers):
            if pair_ratio is None:
                pair_ratio = _text_ratio(source, partner)
            if _ratio_bound(source, sentence.text) > pair_ratio and _text_ratio(source, sentence.text) > pair_ratio:
                moved.update(number.key for number in numbers)
                continue
        moved.update(number.key for number in numbers if number.unit not in units)
    return moved

def _text_ratio(a, b):
    if len(a) > _CHAR_ALIGN_LIMIT or len(b) > _CHAR_ALIGN_LIMIT:
        return _affix_ratio(a, b)
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()

def _ratio_bound(a, b):
    if len(a) > _CHAR_ALIGN_LIMIT or len(b) > _CHAR_ALIGN_LIMIT:
        return 1.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).quick_ratio()

def _unpaired_around(sides, side, sentences, index, paired):
    found = []
    position = index - 1
    while position >= 0 and position not in paired:
        found.extend(_sentence_numbers(sides, side, sentences[position]))
        position -= 1
    position = index + 1
    while position < len(sentences) and position not in paired:
        found.extend(_sentence_numbers(sides, side, sentences[position]))
        position += 1
    return found

def _quantity_text(sentences, index, paired, own, own_numbers, other_numbers, other_doc):
    joined = _with_unpaired_text(sentences, index, paired)
    if joined == own.text:
        return joined
    if any(number.weak in _QUANTITY_FOR for number in own_numbers):
        return joined
    if any(number.weak == _WEAK_EACH for number in other_numbers):
        return joined
    rest = joined.replace(own.text, "", 1)
    if any(number.weak == _WEAK_SINGLE and _weak_head(other_doc, number) in rest
           for number in other_numbers if _weak_head(other_doc, number)):
        return joined
    return own.text

def _weak_head(doc, number):
    skip = 1 if number.weak == _WEAK_SINGLE else 2
    match = _QUANTITY_HEAD.match(doc, number.end + skip) if doc else None
    return match.group(0) if match else ""

def _quantity_negated(text, position):
    end = _QUANTITY_CLAUSE_END.search(text, position)
    rest = text[position:end.start() if end else len(text)]
    lead = _QUANTITY_LEAD.match(rest)
    stop = _QUANTITY_SCOPE_END.search(rest, lead.end() if lead else 0)
    if stop is not None:
        rest = rest[:stop.start()]
    rest = _QUANTITY_NOT_NEG.sub(lambda match: "＃" * len(match.group(0)), rest)
    rest = _NEGATION_WORDS.sub(lambda match: match.group(0)[:-1] + "＃", rest)
    return _QUANTITY_NEG.search(rest) is not None or _negative_zu(rest)

def _head_clauses(text, head):
    body = text.rstrip(" \t\n。！？!?」』）)")
    if head not in body or _QUANTITY_SENTENCE_END.search(body):
        return None
    clauses = _QUANTITY_CLAUSE_SPLIT.split(body)
    picked = []
    for index, clause in enumerate(clauses):
        if head not in clause:
            continue
        picked.append(clause)
        while _QUANTITY_PARTICLE_END.search(clauses[index].strip()) and index + 1 < len(clauses):
            index += 1
            picked.append(clauses[index])
    return "、".join(picked)

def _one_sentence_without(text, head):
    body = text.rstrip(" \t\n。！？!?」』）)")
    return head not in body and not _QUANTITY_SENTENCE_END.search(body)

def _other_subject_masked(own_text, partner_text):
    topic = _QUANTITY_TOPIC.match(own_text)
    topic = topic.group(1).strip() if topic else ""
    if not topic:
        return partner_text
    clauses = []
    for clause in _QUANTITY_CLAUSE_SPLIT.split(partner_text):
        if clauses and _QUANTITY_PARTICLE_END.search(clauses[-1].strip()):
            clauses[-1] += "、" + clause
        else:
            clauses.append(clause)
    out = []
    for clause in clauses:
        subject = _QUANTITY_SUBJECT.search(clause)
        if (subject and subject.group(1) not in topic
                and topic not in clause[:subject.start(1)] + "＃" + clause[subject.end(1):]):
            clause = "＃" * len(clause)
        out.append(clause)
    return "、".join(out)

def _quantity_changed(number, doc, own_text, partner_text, partner_words):
    words = _QUANTITY_FOR.get(number.weak)
    if words is None:
        return False
    head = _weak_head(doc, number)
    if head:
        for match in re.finditer(_QUANTITY_CHANGE_BEFORE[number.weak] + re.escape(head), partner_text):
            if match.group(0) not in own_text and not _quantity_negated(partner_text, match.end()):
                return True
        if number.weak == _WEAK_SINGLE:
            for match in re.finditer(re.escape(head) + "(?:を|は|が|も)?別々", partner_text):
                if match.group(0) not in own_text and not _quantity_negated(partner_text, match.end()):
                    return True
        for match in re.finditer(_QUANTITY_KEEP_BEFORE[number.weak] + re.escape(head), partner_text):
            if not _quantity_negated(partner_text, match.end()):
                return False
        scope = _head_clauses(partner_text, head)
        if scope is None and _one_sentence_without(partner_text, head):
            if partner_words & words:
                return True
            if any(not _quantity_negated(partner_text, match.end())
                   for match in _QUANTITY_KEEP_ANY[number.weak].finditer(partner_text)):
                return False
            extra = partner_words & _QUANTITY_CLAUSE_WORDS[number.weak]
            if extra:
                extra &= _quantity_words(_other_subject_masked(own_text, partner_text))
            if extra and number.weak == _WEAK_EACH:
                masked = _QUANTITY_OTHER_NOUN.sub(
                    lambda match: match.group(0) if match.group(1) in own_text else "＃" * len(match.group(0)), partner_text)
                extra &= _quantity_words(masked)
            return bool(extra)
        if scope is not None and partner_words & words:
            partner_words = partner_words & _quantity_words(scope)
        if scope is not None and partner_words & _QUANTITY_CLAUSE_WORDS[number.weak]:
            if _QUANTITY_CLAUSE_WORDS[number.weak] & _quantity_words(scope) and (
                    number.weak != _WEAK_SINGLE or "別々に" in scope):
                return True
        return bool(partner_words & words)
    return bool(partner_words & (words | _QUANTITY_CLAUSE_WORDS[number.weak]))

def _with_unpaired_text(sentences, index, paired):
    first = index
    while first > 0 and first - 1 not in paired:
        first -= 1
    last = index
    while last + 1 < len(sentences) and last + 1 not in paired:
        last += 1
    return "".join(sentence.text for sentence in sentences[first:last + 1])

def _following_unpaired(sides, side, sentences, index, paired):
    found = []
    position = index + 1
    while position < len(sentences) and position not in paired:
        found.append((sentences[position], _sentence_numbers(sides, side, sentences[position])))
        position += 1
    return found

def _cancel_notation(removed, added, old_numbers, new_numbers):
    if not removed or not added:
        return removed, added
    removed, added = Counter(removed), Counter(added)
    for mine, other, numbers, others in ((removed, added, old_numbers, new_numbers),
                                         (added, removed, new_numbers, old_numbers)):
        other_set = None
        for number in numbers:
            if number.unit or number.notation is None or mine[number.key] <= 0:
                continue
            if other_set is None:
                other_set = _KeySet(others)
            units = sorted(unit for (value, unit), count in other.items() if value == number.value and unit and count > 0)
            match = next((unit for unit in units if _notation_match(number, other_set, unit)), None)
            if match is not None:
                mine[number.key] -= 1
                other[(number.value, match)] -= 1
    return +removed, +added

def _quantity_words(text):
    return set(_quantity_word_counts(text))

def _quantity_word_counts(text):
    counts = Counter()
    for match in _QUANTITY_WORDS.finditer(text):
        word = _QUANTITY_SAME.get(match.group(0), match.group(0))
        if word == "上限":
            if _QUANTITY_LIMIT_OFF.match(text, match.start()) is not None:
                counts[word] += 1
        elif not _quantity_negated(text, match.end()):
            counts[word] += 1
    return counts

def _drop_weak(removed, added, old_numbers, new_numbers, old_text="", new_text="", old_doc="", new_doc=""):
    old_words, new_words = _quantity_word_counts(old_text), _quantity_word_counts(new_text)
    for mine, other, numbers, partner_words, doc, own_text, partner_text in (
            (removed, added, old_numbers, set(new_words - old_words), old_doc, old_text, new_text),
            (added, removed, new_numbers, set(old_words - new_words), new_doc, new_text, old_text)):
        weak = Counter(number.key for number in numbers
                       if number.weak and not _quantity_changed(number, doc, own_text, partner_text, partner_words))
        for key, count in weak.items():
            if mine[key] > 0 and not any(count_other > 0 and unit == key[1]
                                         for (value, unit), count_other in other.items() if (value, unit) != key):
                mine[key] -= min(count, mine[key])
    return +removed, +added

def _notation_index(numbers):
    index = {}
    for number in numbers:
        if number.notation is not None:
            index.setdefault(number.key, []).append(number)
    return index

def _notation_match(number, other, unit=None):
    if number.unit or number.notation is None:
        return False
    units = other.units.get(number.value, ())
    if unit is not None:
        candidates = [unit] if unit and unit in units else []
    else:
        candidates = [candidate for candidate in units if candidate]
    if not candidates:
        return False
    group, follow, frame = number.notation
    if follow and any(follow.startswith(candidate) for candidate in candidates):
        return True
    if not group:
        return False
    joins, own_units, at = frame
    if len(group) == 1:
        allowed = set(own for own in own_units if own)
        if at and own_units[at - 1] in _NEXT_UNIT:
            allowed.add(_NEXT_UNIT[own_units[at - 1]])
        return any(candidate in allowed for candidate in candidates)
    mine = [position for position, own in enumerate(own_units) if not own].index(at)
    size = len(group)
    for cluster in other.clusters.get(number.value, ()):
        for start in range(len(cluster) - size + 1):
            picked = cluster[start:start + size]
            if tuple(value for value, _ in picked) != group:
                continue
            if picked[mine][1] not in candidates:
                continue
            if _units_fit(joins, [cluster_unit for _, cluster_unit in picked]):
                return True
    return False

def _units_fit(joins, units):
    kinds = set(joins) - set(("adjacent",))
    named = [unit for unit in units if unit]
    if kinds == set(("range",)):
        return len(set(named)) == 1
    if not named or len(named) != len(units):
        return False
    rest = kinds - set(("range",))
    if rest and rest <= set(("colon",)):
        order = _TIME_UNITS
    elif rest and rest <= set(("slash", "dash")):
        order = _DATE_UNITS
    else:
        order = _DATE_UNITS + _TIME_UNITS
    if any(unit not in order for unit in units):
        return False
    positions = [order.index(unit) for unit in units]
    resets = sum(1 for left, right in zip(positions, positions[1:]) if left >= right)
    return resets <= list(joins).count("range")

def _present(key, notation, other):
    if key in other.keys:
        return True
    if key[1]:
        return False
    return any(_notation_match(number, other) for number in notation.get(key, ()))

def _sentence_finder(sides, side, groups):
    key = "old" if side == 0 else "new"
    sentences = [sentence for group in groups for sentence in group[key]]
    starts = [sentence.start for sentence in sentences]

    def find(position):
        index = bisect_right(starts, position) - 1
        if index >= 0 and position < sentences[index].start + len(sentences[index].text):
            sentence = sentences[index]
            return (sentence.line, sentence.start, sentence.text)
        line = sides.line_of(side, position)
        return (line, sides.starts[side][line - 1], sides.lines[side][line - 1].strip())
    return find

def _hunk_finder(full, side):
    first, last = ("old_start", "old_end") if side == 0 else ("new_start", "new_end")
    hunks = full["hunks"]
    starts = [hunk[first] for hunk in hunks]

    def find(line):
        index = bisect_right(starts, line) - 1
        if index >= 0 and hunks[index][first] <= line <= hunks[index][last]:
            return hunks[index]["index"]
        return None
    return find

_NEGATION = re.compile(
    r"しないで|ません|なかっ|なけれ|ない|なく|禁止"
    r"|(?<!必)(?<!は)ず(?=[に、。]|$)"
    r"|ぬ(?=[。、]|$)"
    r"|未(?![来明])(?=[一-龥])"
    r"|不(?=要|可|明|正|足|在|備|具合|適|十分|一致|安定|許可|採用|使用|参加)"
    r"|非(?=公開|対応|表示|推奨|同期|互換|同意)"
    r"|無(?=効|料|視|関係|制限|断)")

_NEGATION_MASKED = re.compile(
    r"なければ(?:ならない|なりません|ならず|いけない|いけません)|なくては(?:ならない|なりません|いけない|いけません)"
    r"|ないと(?:いけない|いけません)|ざるを得(?:ない|ません)|ねば(?:ならない|なりません)"
    r"|かもしれ(?:ない|ません)|に違い(?:ない|ありません)|とは限(?:らない|りません)|わけでは(?:ない|ありません)"
    r"|に(?:すぎ|過ぎ)(?:ない|ません)|しか(?:ない|ありません)|ほか(?:ない|ありません)|問題(?:は|が|も)?(?:ない|なく|ありません)|有無"
    r"|(?:では|じゃ|でも)な(?=[いくかけ])|(?:では|じゃ)ありません")

_NEGATION_WORDS = re.compile(r"(?:少|危|切|仕方|間違い|もったい|つまら|くだら|たまら|情け|頼り|あっけ|はか|ぎこち|さりげ|味気|素っ気)"
                             r"(な)(?=[いくかけ])")

_ADVERB_MAZU = re.compile(r"(?<![一-龥々])まず")
_NEGATION_LIMIT = 2

_NEGATION_END_RULE = True
_END_WINDOW = 5
_PLACE_GAP = 1
_SENTENCE_TAIL = re.compile(r"[。！？!?]*[」』）)]*$")
_HIRAGANA = re.compile(r"[ぁ-ゖ]")
_WORD_CHAR = re.compile(r"[一-龥々〆ヵヶァ-ヴー]")

def _negation_marks(text):
    masked = _NEGATION_MASKED.sub(lambda match: "＃" * len(match.group(0)), text)
    masked = _NEGATION_WORDS.sub(lambda match: match.group(0)[:-1] + "＃", masked)
    masked = _ADVERB_MAZU.sub("＃＃", masked)
    return [(match.start(), match.end()) for match in _NEGATION.finditer(masked)]

def _char_opcodes(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()

_WIDEN_RIGHT = 6

def _widen(text, left, right):
    head = text[left] if left < len(text) else ""
    starts_with_word = bool(head) and bool(_WORD_CHAR.match(head))
    if not starts_with_word:
        count = 0
        while left > 0 and count < 4 and _HIRAGANA.match(text[left - 1]):
            left -= 1
            count += 1
    while left > 0 and _WORD_CHAR.match(text[left - 1]):
        left -= 1
    while starts_with_word and right < len(text) and _WORD_CHAR.match(text[right]):
        right += 1
    count = 0
    while right < len(text) and count < _WIDEN_RIGHT and _HIRAGANA.match(text[right]):
        right += 1
        count += 1
    return text[left:right]

def _covered(left, right, marks):
    return sum(max(0, min(right, b) - max(left, a)) for a, b in marks)

def _changed_places(old, new):
    if len(old) > _CHAR_ALIGN_LIMIT or len(new) > _CHAR_ALIGN_LIMIT:
        head, tail = _common_affix(old, new)
        old_end, new_end = len(old) - tail, len(new) - tail
        if old_end - head > _CHAR_ALIGN_LIMIT or new_end - head > _CHAR_ALIGN_LIMIT:
            return [(head, old_end, head, new_end)]
        opcodes = [(tag, i1 + head, i2 + head, j1 + head, j2 + head)
                   for tag, i1, i2, j1, j2 in _char_opcodes(old[head:old_end], new[head:new_end])]
    else:
        opcodes = _char_opcodes(old, new)
    places = []
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            continue
        if places and i1 - places[-1][1] <= _PLACE_GAP and j1 - places[-1][3] <= _PLACE_GAP:
            places[-1] = (places[-1][0], i2, places[-1][2], j2)
        else:
            places.append((i1, i2, j1, j2))
    return places

def _unmarked_letters(text, left, right, hits):
    return "".join(text[position] for position in range(left, right)
                   if not any(a <= position < b for a, b in hits) and not _HIRAGANA.match(text[position]))

_ZU_TO_TE = (frozenset(("さずに", "せずに", "さず", "せず")), frozenset(("して", "し")))

def _verb_stem_change(old_part, new_part):
    if not old_part or not new_part or not all(_HIRAGANA.match(ch) for ch in old_part + new_part):
        return 0
    pair = (old_part, new_part)
    for first, second in (pair, pair[::-1]):
        if first in _ZU_TO_TE[0] and second in _ZU_TO_TE[1]:
            return len(first) - 1 + len(second)
    if (old_part[0], new_part[0]) in (("す", "し"), ("し", "す")):
        return 2
    return 0

def _negation_flip(old, new):
    old_marks, new_marks = _negation_marks(old), _negation_marks(new)
    same_total = len(old_marks) == len(new_marks)
    if same_total and not old_marks:
        return None
    old_end = len(old) - len(_SENTENCE_TAIL.search(old).group(0))
    new_end = len(new) - len(_SENTENCE_TAIL.search(new).group(0))
    found, directions = None, set()
    for i1, i2, j1, j2 in _changed_places(old, new):
        old_hits = [(a, b) for a, b in old_marks if a < i2 and b > i1]
        new_hits = [(a, b) for a, b in new_marks if a < j2 and b > j1]
        if len(old_hits) == len(new_hits):
            continue
        old_part, new_part = old[i1:i2], new[j1:j2]
        rest = (i2 - i1 - _covered(i1, i2, old_hits)) + (j2 - j1 - _covered(j1, j2, new_hits))
        rest -= _verb_stem_change(old_part, new_part)
        near_end = (_NEGATION_END_RULE and i1 >= old_end - _END_WINDOW and i2 <= old_end
                    and j1 >= new_end - _END_WINDOW and j2 <= new_end
                    and _unmarked_letters(old, i1, i2, old_hits) == _unmarked_letters(new, j1, j2, new_hits))
        if rest <= _NEGATION_LIMIT or near_end:
            flip = _widen(old, i1, i2), _widen(new, j1, j2)
            if not same_total:
                return flip
            found = found or flip
            directions.add(len(new_hits) > len(old_hits))
    if len(directions) == 2:
        return found
    return None

def _negation_risks(sides, groups):
    out = []
    order = 0
    for group in groups:
        for i, j in group["pairs"]:
            old, new = group["old"][i], group["new"][j]
            if old.text == new.text:
                continue
            flip = _negation_flip(old.text, new.text)
            if flip is not None:
                out.append((_group_index(group, new), order, _risk("negation", None, old.line, new.line, old.text, new.text,
                                                                 {"old": flip[0], "new": flip[1]})))
                order += 1
    return out

_CASE_WORD = re.compile(r"[一-龥々ァ-ヴーA-Za-z0-9０-９・]{1,12}")

_HONORIFIC = re.compile(r"さん|くん|ちゃん")
_CASE_PARTICLE = re.compile(r"から|より|が|を|に|は|へ")

def _case_map(text):
    found = OrderedDict()
    for match in _CASE_WORD.finditer(text):
        word, end = match.group(0), match.end()
        honorific = _HONORIFIC.match(text, end, end + 3)
        if honorific:
            end += len(honorific.group(0))
        elif len(word) > 2 and word[-1] in "様氏":
            word = word[:-1]
        particle = _CASE_PARTICLE.match(text, end, end + 2)
        if particle and word not in found:
            found[word] = particle.group(0)
    return found

_PASSIVE = re.compile(r"(?:さ|ら)れ(?:る|た|て|ます|ました|ない)")

def _passive_rewrite(old_text, new_text, before, after, words):
    if bool(_PASSIVE.search(old_text)) == bool(_PASSIVE.search(new_text)):
        return False
    return all(set((before[word], after[word])) == set(("が", "に")) for word in words)

def _swap_risks(sides, groups):
    out = []
    order = 0
    for group in groups:
        for i, j in group["pairs"]:
            old, new = group["old"][i], group["new"][j]
            if old.text == new.text:
                continue
            before, after = _case_map(old.text), _case_map(new.text)
            common = [word for word in before if word in after]
            words = []
            for x, a in enumerate(common):
                for b in common[x + 1:]:
                    if before[a] != before[b] and after[a] == before[b] and after[b] == before[a]:
                        for word in (a, b):
                            if word not in words:
                                words.append(word)
            if words and _passive_rewrite(old.text, new.text, before, after, words):
                words = []
            if words:
                words.sort(key=common.index)
                pairs = [{"word": word, "old": before[word], "new": after[word]} for word in words]
                out.append((_group_index(group, new), order, _risk("swap", None, old.line, new.line, old.text, new.text,
                                                                 {"pairs": pairs})))
                order += 1
    return out

_QUESTION = re.compile(r"(?:[？?]|か[。？?])[」』）)]*$")

_NOT_QUESTION_KA = re.compile(r"(?:明ら|確|わず|僅|静|豊|ほ|速や|穏や|鮮や|細や|爽や|健や|和や|緩や|賑や|にぎや|華や|"
                              r"密|愚|疎|おろ|遥|はる|ほの|柔ら|滑ら|なめら|清ら|朗ら|安ら|大ま)か。[」』）)]*$")

def _is_question(text):
    text = text.rstrip()
    return bool(_QUESTION.search(text)) and not _NOT_QUESTION_KA.search(text)

_FINAL_PERIOD_IN_QUOTE = re.compile(r"。(?=[」』]+$)")

def _only_final_period_removed(old, new):
    old, new = old.rstrip(), new.rstrip()
    return _FINAL_PERIOD_IN_QUOTE.sub("", old) == new or _FINAL_PERIOD_IN_QUOTE.sub("", new) == old

def _question_risks(sides, groups):
    out = []
    order = 0
    for group in groups:
        for i, j in group["pairs"]:
            old, new = group["old"][i], group["new"][j]
            old_question, new_question = _is_question(old.text), _is_question(new.text)
            if old_question != new_question and not _only_final_period_removed(old.text, new.text):
                out.append((_group_index(group, new), order, _risk(
                    "sentence_type", "question", old.line, new.line, old.text, new.text,
                    {"old_is_question": old_question, "new_is_question": new_question})))
                order += 1
    return out

def _is_quote_row(row):
    return bool(row["quote_depth"]) or row["kind"] == "quote"

def _protected_spans(sides, side):
    found = []
    text = sides.texts[side]
    for left, right, kind in sides.analyses[side]["protected_spans"]:
        if kind not in _PROTECTED_SPANS:
            continue
        if kind == "image":
            left = _image_path_start(text, left, right)
            if left >= right:
                continue
        elif kind == "reference_definition" and right > left and text[right - 1:right] == "\n":
            right -= 1
        found.append((left, right, kind))
    found.sort()
    return found, [left for left, _, _ in found]

def _protected_risks(sides, full):
    spans = [_protected_spans(sides, 0), _protected_spans(sides, 1)]
    out = []
    for hunk in full["hunks"]:
        found = OrderedDict()

        def hit(subkind, block, side, line_no):
            entry = found.setdefault(subkind, [block, [None, None]])
            if entry[1][side] is None:
                entry[1][side] = line_no

        if hunk["segments"] is not None:
            bases = (sides.starts[0][hunk["old_start"] - 1], sides.starts[1][hunk["new_start"] - 1])
            offsets = [0, 0]
            for tag, text in hunk["segments"]:
                if tag == "=":
                    offsets[0] += len(text)
                    offsets[1] += len(text)
                    continue
                side = 0 if tag == "-" else 1
                left = bases[side] + offsets[side]
                for subkind, block, line_no in _protected_hits(sides, side, left, left + len(text), spans[side]):
                    hit(subkind, block, side, line_no)
                offsets[side] += len(text)
        elif hunk["tag"] == "replace":
            contents = [_protected_contents(sides, side, hunk, spans[side]) for side in (0, 1)]
            for subkind in OrderedDict((key, None) for key in list(contents[0]) + list(contents[1])):
                old_items, new_items = contents[0].get(subkind, []), contents[1].get(subkind, [])
                if [text for _, text, _ in old_items] == [text for _, text, _ in new_items]:
                    continue
                for side, items in ((0, old_items), (1, new_items)):
                    other = new_items if side == 0 else old_items
                    for position, (block, text, line_no) in enumerate(items):
                        if position >= len(other) or other[position][1] != text:
                            hit(subkind, block, side, line_no)
                            break
                    else:
                        if items:
                            hit(subkind, items[0][0], side, items[0][2])
        else:
            for side, first, last in ((0, hunk["old_start"], hunk["old_end"]), (1, hunk["new_start"], hunk["new_end"])):
                rows = sides.analyses[side]["lines"]
                for line_no in range(first, last + 1):
                    row = rows[line_no - 1]
                    subkind = _PROTECTED_LINES.get(row["kind"]) or ("quote" if _is_quote_row(row) else None)
                    if subkind is not None:
                        hit(subkind, row["kind"] if subkind != "quote" else "quote", side, line_no)
        one_to_one = (hunk["tag"] == "replace" and hunk["old_start"] == hunk["old_end"]
                      and hunk["new_start"] == hunk["new_end"])
        for order, (subkind, (block, (old_line, new_line))) in enumerate(found.items()):
            if one_to_one:
                old_line, new_line = hunk["old_start"], hunk["new_start"]
            old = sides.lines[0][old_line - 1] if old_line else None
            new = sides.lines[1][new_line - 1] if new_line else None
            out.append((hunk["index"], order, _risk("protected", subkind, old_line, new_line, old, new, {"block": block})))
    return out

def _protected_contents(sides, side, hunk, spans):
    first, last = ("old_start", "old_end") if side == 0 else ("new_start", "new_end")
    if hunk[last] < hunk[first]:
        return {}
    text = sides.texts[side]
    low = sides.starts[side][hunk[first] - 1]
    high = sides.starts[side][hunk[last] - 1] + len(sides.lines[side][hunk[last] - 1])
    found = OrderedDict()
    span_list, lefts = spans
    index = max(0, bisect_right(lefts, low) - 1)
    while index < len(span_list) and span_list[index][0] < high:
        left, right, kind = span_list[index]
        if right > low:
            start = max(left, low)
            found.setdefault(_PROTECTED_SPANS[kind], []).append(
                (kind, text[start:min(right, high)], sides.line_of(side, start)))
        index += 1
    rows = sides.analyses[side]["lines"]
    for line_no in range(hunk[first], hunk[last] + 1):
        if line_no - 1 < len(rows) and _is_quote_row(rows[line_no - 1]):
            found.setdefault("quote", []).append(("quote", sides.lines[side][line_no - 1], line_no))
    return found

def _protected_hits(sides, side, left, right, spans):
    found, lefts = spans
    hits = []
    index = max(0, bisect_right(lefts, left) - 1)
    while index < len(found) and found[index][0] < right:
        span_left, span_right, kind = found[index]
        if span_right > left:
            hits.append((_PROTECTED_SPANS[kind], kind, sides.line_of(side, max(left, span_left))))
        index += 1
    rows = sides.analyses[side]["lines"]
    for line_no in range(sides.line_of(side, left), sides.line_of(side, right - 1) + 1):
        if line_no - 1 < len(rows) and _is_quote_row(rows[line_no - 1]):
            hits.append(("quote", "quote", line_no))
            break
    return hits

def _find_line(sides, side, text):
    head = text.split("\n")[0]
    end = _SENTENCE_END.search(head)
    head = (head[:end.end()] if end else head).strip()[:20]
    if not head:
        return None
    for index, line in enumerate(sides.normalized_lines(side)):
        if head in line:
            return index + 1
    return None

def _marks_risks(sides, type_changes):
    return [_risk("sentence_type", "marks", _find_line(sides, 0, change["orig"]), _find_line(sides, 1, change["rewrite"]),
                  change["orig"], change["rewrite"], {"lost": change["lost"], "added": change["added"]})
            for change in (type_changes or [])]

def _modality_risks(sides, changes):
    out = []
    for change in changes or ():
        out.append(_risk("modality_review" if change["subkind"] == "ability_lost" else "modality", change["subkind"],
                         _find_line(sides, 0, change["orig"]), _find_line(sides, 1, change["rewrite"]),
                         change["orig"], change["rewrite"],
                         {"lost": change["lost"], "added": change["added"], "from": change["from"], "to": change["to"]}))
    return out

def _logic_risks(sides, changes):
    return [_risk(change["kind"], change["subkind"], _find_line(sides, 0, change["orig"]), _find_line(sides, 1, change["rewrite"]),
                  change["orig"], change["rewrite"],
                  {"from": change["from"], "to": change["to"], "old_hits": change["old_hits"], "new_hits": change["new_hits"]})
            for change in changes or ()]

_QUALIFIER_JOIN = re.compile(r"[ \t]*(?:[~〜]|から)[ \t]*|[-/:‐-–−]")

_QUALIFIER_SKIP = re.compile(r"\*{0,2}(?:[万億兆](?:" + _unit_pattern(_UNITS) + r")?)?間?")

_QUALIFIER_SHOWN = re.compile(r"[万億兆](?:" + _unit_pattern(_UNITS) + r")?")
_QUALIFIER_KATAKANA_UNIT = re.compile(r"[ァ-ヴー]{1,6}")

_QUALIFIER_PART = re.compile(r"上旬|中旬|下旬|初旬|半ば|半|末")

_QUALIFIER_AFTER = re.compile(
    r"[ 　]?(?:"
    r"(?P<approx>ほど|程度|程(?![度遠])|前後(?!関係|左右|不覚|逆|差|し|の関係|の文脈)|ぐらい|くらい|位(?![置相階牌取])|ごろ|頃"
    r"|余り(?!ま[すしせ]|そう)|余(?![裕計地分白剰談韻波興震熱力命暇生罪念儀所程技病勢光香情弊禄話聞部事日人りるっすせられさし])"
    r"|あまり(?![にな良よ多]|ま[すしせ]|そう)|近く|足らず|内外|かそこら|やそこら"
    r"|弱(?![点化体者小気音酸腰冷火毒視肉虫電震いさみめまるりっ]|く(?!らい))"
    r"|強(?![化制調度力固烈硬気行豪盗敵者風弱靭要引奪迫権大国健壮打欲情いさみめまるりっ]|く(?!らい)))"
    r"|(?P<upper_in>以下|以内|以前)|(?P<lower_in>以上|以降|以後)"
    r"|(?P<lower_ex>超え|超(?![過一-龥々〆]))|(?P<upper_ex>未満)"
    r"|(?P<bound_verb>を超[えすさし]|を上回|を下回))")

_QUALIFIER_UNIT_ONLY = frozenset(("弱", "強", "位"))

_QUALIFIER_PLACE_UNITS = frozenset(("章", "節", "項", "条", "号"))

_QUALIFIER_VERSION_BEFORE = re.compile(r"(?:[vV]|[Vv]er\.?|[Vv]ersion|バージョン)[ 　]?$")

_QUALIFIER_BEFORE = re.compile(r"(?:(?P<approx>約|およそ|おおよそ|凡そ|概ね|おおむね|ほぼ|推定|大体|だいたい))"
                               r"(?:で|、)?[ 　]*\*{0,2}$")
_QUALIFIER_BEFORE_REACH = 8

_QUALIFIER_YAKU_WORDS = frozenset(("契約", "予約", "集約", "要約", "節約", "制約", "公約", "条約", "特約", "規約", "確約",
                                   "誓約", "倹約", "婚約", "盟約", "協約", "密約", "違約", "解約", "成約", "新約", "旧約",
                                   "黙約", "簡約", "縮約", "締約"))

_QUALIFIER_YAKU_NOUNS = frozenset(("所要", "必要", "主要", "需要", "重要", "作成", "構成", "完成", "達成", "形成", "編成",
                                   "生成", "結成", "更新", "最新", "刷新", "体制", "募集", "収集", "編集", "結婚", "猶予"))

_QUALIFIER_NEAR_AFTER = re.compile(
    r"[ 　]?(?:(?P<both>より古|より新)"
    r"|(?P<upper>まで|より(?:少|前|下|短|低|早|小|手前|若)|に満たな|に届かな|を切[りっるらろれ]|を割[りっるらろれ]|のうちに"
    r"|を上限|が上限|を限度|を最大)"
    r"|(?P<lower>から|より|を下限|が下限|を最低|でも|過ぎ|すぎ|はかか|は必要|は要)"
    r"|(?P<approx>規模|見当|ちょっと|ちょい|そこそこ|ばかり|に迫|に近))")
_QUALIFIER_NEAR_BEFORE = re.compile(r"(?:(?P<upper>最大|最長|最高|最多|多くて|多くとも|多い時で|上限|最大限)"
                                    r"|(?P<lower>最低|最小|最短|少なくとも|少なくて|下限)|(?P<approx>ざっと|およそ))"
                                    r"(?:で|は|、)?[ 　]*\*{0,2}$")

_QUALIFIER_SENTENCE = {
    "approx": re.compile(r"推定|推計|概算|見込|見積|目安|想定|概数|大まか|おおまか|ざっと|と見られ|とみられ"),
    "lower": re.compile(r"以上|以降|超え|超す|超し|超過|上回|少なくとも|最低|下限"),
    "upper": re.compile(r"以下|以内|未満|下回|上限|最大|最長|超えな|超えず|超えませ|まで|満たな"),
}
_QUALIFIER_FAMILIES = ("approx", "lower", "upper", "bound")
_QUALIFIER_BOUNDS = frozenset(("lower", "upper", "bound"))

_QUALIFIER_STRICT = frozenset(("lower_in", "lower_ex", "upper_in", "upper_ex"))

def _qualifier_yaku_ok(text, start, at):
    if at <= start or text[at - 1:at + 1] not in _QUALIFIER_YAKU_WORDS:
        return True
    return at - 2 >= start and text[at - 2:at] in _QUALIFIER_YAKU_NOUNS

def _qualifier_tail(text, number, end):
    at = _QUALIFIER_SKIP.match(text, number.end, end).end()
    unit = bool(number.unit) or any(char in "万億兆" for char in text[number.end:at])
    if not number.unit and at == number.end:
        katakana = _QUALIFIER_KATAKANA_UNIT.match(text, at, end)
        if katakana is not None:
            at, unit = katakana.end(), True
    return at, unit

def _qualifier_shown_end(text, number, end):
    at, unit = number.end, bool(number.unit)
    shown = _QUALIFIER_SHOWN.match(text, at, end)
    if shown is not None:
        at, unit = shown.end(), True
    elif not number.unit:
        katakana = _QUALIFIER_KATAKANA_UNIT.match(text, at, end)
        if katakana is not None:
            at, unit = katakana.end(), True
    part = _QUALIFIER_PART.match(text, at, end) if unit else None
    return part.end() if part is not None else at

def _qualifier_after(text, at, end, number, unit, names, words):
    if unit:
        part = _QUALIFIER_PART.match(text, at, end)
        if part is not None:
            at = part.end()
    for _ in range(2):
        found = _QUALIFIER_AFTER.match(text, at, end)
        if found is None and text.startswith(("前", "後"), at) and at + 1 < end:
            found = _QUALIFIER_AFTER.match(text, at + 1, end)
        if found is None:
            break
        at = found.end()
        name, word = found.lastgroup, found.group(found.lastgroup)
        if word in _QUALIFIER_UNIT_ONLY and not unit:
            continue
        if word == "前後" and not unit and _QUALIFIER_VERSION_BEFORE.search(text, 0, number.start):
            continue
        if word == "近く" and number.unit == "号":
            continue
        if word == "以下" and number.unit in _QUALIFIER_PLACE_UNITS:
            name = "lower_in"
        names.add(name)
        words.append(word)
    return at

def _qualifier_marks(text, start, end, number):
    names, words, near = set(), [], set()
    head = text[max(start, number.start - _QUALIFIER_BEFORE_REACH):number.start]
    before = _QUALIFIER_BEFORE.search(head)
    if before is not None:
        at = number.start - len(head) + before.start()
        word = before.group("approx")
        if word != "約" or _qualifier_yaku_ok(text, start, at):
            names.add("approx")
            words.append(word)
    near_before = _QUALIFIER_NEAR_BEFORE.search(head)
    if near_before is not None:
        near.add(near_before.lastgroup)
    at, unit = _qualifier_tail(text, number, end)
    at = _qualifier_after(text, at, end, number, unit, names, words)
    near_after = _QUALIFIER_NEAR_AFTER.match(text, at, end)
    if near_after is not None:
        near.update(("lower", "upper") if near_after.lastgroup == "both" else (near_after.lastgroup,))
    return names, words, near

def _qualifier_joined(text, previous, number, end):
    if previous.end == number.start:
        return True
    at, unit = _qualifier_tail(text, previous, number.start)
    compound = any(char in "万億兆" for char in text[previous.end:at])
    at = _qualifier_after(text, at, number.start, previous, unit, set(), [])
    between = text[at:number.start].translate(_HALF_WIDTH)
    if not between:
        return compound or at == previous.end
    return "\n" not in between and _QUALIFIER_JOIN.fullmatch(between) is not None

_QUALIFIER_SENTENCE_STOP = re.compile(r"[。！？!?\n]")
_QUALIFIER_SPLIT_DECIMAL = re.compile(r"[0-9０-９]．$")

def _qualifier_reach(sides, side, sentence, numbers):
    text = sides.texts[side]
    start, end = sentence.start, sentence.start + len(sentence.text)
    reach = max([end] + [number.end for number in numbers])
    if reach > end:
        stop = _QUALIFIER_SENTENCE_STOP.search(text, reach)
        end = stop.end() if stop is not None else len(text)
    return text[start:end]

def _qualifier_states(sides, side, sentence, numbers):
    text = sides.texts[side]
    start = sentence.start
    end = start + len(_qualifier_reach(sides, side, sentence, numbers))
    marks = [_qualifier_marks(text, start, end, number) for number in numbers]
    groups = list(range(len(numbers)))
    for index in range(1, len(numbers)):
        if _qualifier_joined(text, numbers[index - 1], numbers[index], end):
            groups[index] = groups[index - 1]
    merged = OrderedDict()
    for index, (names, words, near) in enumerate(marks):
        if numbers[index].weak:
            continue
        members, names_all, words_all, near_all = merged.setdefault(groups[index], ([], set(), [], set()))
        members.append(numbers[index])
        names_all.update(names)
        words_all.extend(words)
        near_all.update(near)
    out = []
    for members, names, words, near in merged.values():
        key = members[0].key if len(members) == 1 else (tuple(m.value for m in members), members[-1].unit)
        shown = text[members[0].start:_qualifier_shown_end(text, members[-1], end)].replace("**", "")
        out.append((key, frozenset(names), tuple(words), frozenset(near), shown))
    return out

def _qualifier_change(old_names, new_names, old_near, new_near, old_words, new_words):
    def families(names):
        return set(name.split("_")[0] for name in names)

    def present(family, fams, near, words):
        has = fams | near | words
        if family == "bound":
            return bool(has & _QUALIFIER_BOUNDS)
        return family in has or (family in _QUALIFIER_BOUNDS and "bound" in fams)
    old_f, new_f = families(old_names), families(new_names)
    lost = [f for f in _QUALIFIER_FAMILIES if f in old_f and not present(f, new_f, new_near, new_words)]
    added = [f for f in _QUALIFIER_FAMILIES if f in new_f and not present(f, old_f, old_near, old_words)]
    strict = []
    for family in ("lower", "upper"):
        olds = set(name for name in old_names if name.startswith(family))
        news = set(name for name in new_names if name.startswith(family))
        if len(olds) == 1 and len(news) == 1 and olds != news and (olds | news) <= _QUALIFIER_STRICT:
            strict.append(family)
    return lost, added, strict

_K = "㐀-䶿一-鿿豈-﫿々〆"
_STIFF_KANJI = re.compile("[" + _K + "]")

_ZU_PREV = frozenset("わかさたなまらがばぱせけげてでねべめれえきぎしじちにびみりい")
_ZU_NEXT = re.compile("[、。，．" + _K + "ァ-ヴA-Za-zＡ-Ｚａ-ｚ]|に")

def _negative_zu(text):
    start = 0
    while True:
        i = text.find("ず", start)
        if i < 0:
            return False
        start = i + 1
        prev = text[i - 1] if i > 0 else ""
        if prev not in _ZU_PREV:
            continue
        if prev == "ま" and not (i >= 2 and _STIFF_KANJI.match(text[i - 2])):
            continue
        if text[max(0, i - 4):i + 1].endswith(("あえず", "かならず")):
            continue
        if i + 1 == len(text) or _ZU_NEXT.match(text, i + 1):
            return True
