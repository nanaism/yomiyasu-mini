# yomiyasu-mini 1.0.0。nanaism/yomiyasu v2.1.3（c09270bc93daab14e253fb3ef406182011b79ccb）から tools/generate.py で生成した。手で直さない。
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

__version__ = "1.0.0"
SOURCE_TAG = "v2.1.3"
SOURCE_COMMIT = "c09270bc93daab14e253fb3ef406182011b79ccb"

_ASCII_PUNCT = set('!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~')
_HTML_BLOCK_TAGS = set(('address article aside base basefont blockquote body caption center col colgroup '
                        'dd details dialog dir div dl dt fieldset figcaption figure footer form frame '
                        'frameset h1 h2 h3 h4 h5 h6 head header hr html iframe legend li link main '
                        'menu menuitem nav noframes ol optgroup option p param section source summary '
                        'table tbody td tfoot th thead title tr track ul').split())
_TAG_NAME = re.compile(r'</?[A-Za-z][A-Za-z0-9-]*')
_ATTRIBUTE_NAME = re.compile(r'[A-Za-z_:][A-Za-z0-9_.:-]*')
_AUTOLINK = re.compile(r'<(?:[A-Za-z][A-Za-z0-9+.-]{1,31}:[^<>\x00-\x20]*|'
                       r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9]'
                       r'(?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?'
                       r'(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*>)')
_CONTAINER_MARKER = re.compile(r'(?:[-+*]|\d{1,9}[.)])(?:[ \t]+|$)')
_CONTAINER_MARKER_DEFAULT = _CONTAINER_MARKER
_BARE_URL = re.compile(r'(?:https?://|www\.)[^\s<>]+')

_BLANK_TITLE_LINE = re.compile(r'(?:\r\n|\r|\n)[ \t]*(?:\r\n|\r|\n)')
_SETEXT = re.compile(r'^ {0,3}(?:=+|-+)[ \t]*$')
_THEMATIC = re.compile(r'^ {0,3}(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})$')
_INLINE_EVENTS = re.compile(r'[\\`<\[\]hw]')
_FENCE_OPEN = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')
_ATX_HEADING = re.compile(r'^ {0,3}#{1,6}(?:[ \t]+|$)')

def unicode_whitespace(ch):
    if not ch: return True
    if len(ch) > 1:
        return all(unicode_whitespace(c) for c in ch)
    return ch in '\t\n\r\f' or unicodedata.category(ch) == 'Zs'

def _escaped(text, position):
    start = position
    while start > 0 and text[start - 1] == '\\':
        start -= 1
    return (position - start) % 2 == 1

def _tag_space_end(text, start):
    pos = start
    while pos < len(text) and text[pos] in ' \t': pos += 1
    if text.startswith('\r\n', pos): pos += 2
    elif pos < len(text) and text[pos] in '\r\n': pos += 1
    while pos < len(text) and text[pos] in ' \t': pos += 1
    return pos

def _terminator_positions(text):
    return {token: [match.start() for match in re.finditer(re.escape(token), text)]
            for token in ('-->', '?>', ']]>', '>')}

def _tag_end(text, start, terminators=None):
    def closed(token, begin):
        if terminators is None:
            end = text.find(token, begin)
        else:
            positions = terminators[token]
            index = bisect_left(positions, begin)
            end = positions[index] if index < len(positions) else -1
        return None if end < 0 else end + len(token)
    if text.startswith('<!--', start):
        if text.startswith('<!-->', start): return start + 5
        if text.startswith('<!--->', start): return start + 6
        return closed('-->', start + 4)
    if text.startswith('<?', start):
        return closed('?>', start + 2)
    if text.startswith('<![CDATA[', start):
        return closed(']]>', start + 9)
    if (text.startswith('<!', start) and start + 2 < len(text)
            and text[start + 2] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'):
        return closed('>', start + 3)
    opening = _TAG_NAME.match(text, start)
    if opening is None:
        return None
    pos = opening.end()
    closing = text.startswith('</', start)
    while pos < len(text):
        space_end = _tag_space_end(text, pos)
        if space_end < len(text) and text[space_end] == '>': return space_end + 1
        if not closing and text.startswith('/>', space_end): return space_end + 2
        if closing or space_end == pos: return None
        attribute = _ATTRIBUTE_NAME.match(text, space_end)
        if attribute is None: return None
        pos = attribute.end()
        assignment = _tag_space_end(text, pos)
        if assignment >= len(text) or text[assignment] != '=':
            continue
        pos = _tag_space_end(text, assignment + 1)
        if pos >= len(text): return None
        if text[pos] in '\"\'':
            end = text.find(text[pos], pos + 1)
            if end < 0: return None
            pos = end + 1
        else:
            begin = pos
            while pos < len(text) and text[pos] not in ' \t\r\n\"\'=<>`': pos += 1
            if pos == begin: return None
    return None

def _link_end(text, opening):
    pos = opening + 1
    while pos < len(text) and text[pos] in ' \t\n\r': pos += 1
    if pos >= len(text): return None
    if text[pos] == '<':
        pos += 1
        while pos < len(text):
            if text[pos] == '\\' and pos + 1 < len(text): pos += 2; continue
            if text[pos] == '>': pos += 1; break
            if text[pos] in '<\n\r': return None
            pos += 1
        else: return None
    else:
        depth = 0
        while pos < len(text):
            ch = text[pos]
            if ch == '\\' and pos + 1 < len(text): pos += 2; continue
            if ch == '(':
                depth += 1
                if depth > 32: return None
            elif ch == ')':
                if depth == 0: return pos + 1
                depth -= 1
            elif ch in ' \t\n\r':
                if depth: return None
                break
            elif ord(ch) < 32 or ch in '<>': return None
            pos += 1
        if depth: return None
    spaces_start = pos
    while pos < len(text) and text[pos] in ' \t\n\r': pos += 1
    if pos < len(text) and text[pos] == ')': return pos + 1
    if pos == spaces_start or pos >= len(text) or text[pos] not in '\"\'(':
        return None
    closer = ')' if text[pos] == '(' else text[pos]
    pos += 1
    while pos < len(text):
        if text[pos] == '\\' and pos + 1 < len(text): pos += 2; continue
        if text[pos] == closer: pos += 1; break
        if _BLANK_TITLE_LINE.match(text, pos): return None
        if closer == ')' and text[pos] == '(': return None
        pos += 1
    else: return None
    while pos < len(text) and text[pos] in ' \t\n\r': pos += 1
    return pos + 1 if pos < len(text) and text[pos] == ')' else None

def inline_protected_spans(text):
    runs = [(m.start(), m.end()) for m in re.finditer(r'`+', text)]
    by_width = {}
    for start, end in runs:
        by_width.setdefault(end - start, []).append((start, end))
    starts_by_width = {width: [pair[0] for pair in pairs] for width, pairs in by_width.items()}
    spans = []
    brackets = []
    terminators = _terminator_positions(text) if '<' in text else None
    pos = 0
    while pos < len(text):
        event = _INLINE_EVENTS.search(text, pos)
        if event is None:
            break
        pos = event.start()
        ch = text[pos]
        if ch == '\\' and pos + 1 < len(text) and text[pos + 1] in _ASCII_PUNCT:
            spans.append((pos, pos + 2, 'escape'))
            pos += 2
            continue
        if ch == '`':
            end = pos + 1
            while end < len(text) and text[end] == '`': end += 1
            width = end - pos
            positions = starts_by_width.get(width, ())
            index = bisect_left(positions, end)
            closing = by_width[width][index][1] if index < len(positions) else None
            if closing is not None:
                spans.append((pos, closing, 'inline_code'))
                pos = closing
                continue
            pos = end
            continue
        if ch == '<':
            auto = _AUTOLINK.match(text, pos)
            if auto:
                end = auto.end()
                spans.append((pos, end, 'autolink'))
                pos = end
                continue
            end = _tag_end(text, pos, terminators)
            if end is not None:
                spans.append((pos, end, 'html_token'))
                pos = end
                continue
        if ch == '[':
            brackets.append(pos)
        elif ch == ']' and brackets:
            opening = brackets.pop()
            if pos + 1 < len(text) and text[pos + 1] == '(':
                end = _link_end(text, pos + 1)
                if end is not None:
                    if opening > 0 and text[opening - 1] == '!' and not _escaped(text, opening - 1):
                        spans.append((opening - 1, end, 'image'))
                    else:
                        spans.append((pos + 1, end, 'link_destination'))
                    pos = end
                    continue
        if text.startswith(('http://', 'https://', 'www.'), pos):
            www = text.startswith('www.', pos)
            if www and pos and not (unicode_whitespace(text[pos - 1]) or text[pos - 1] in '*_~('):
                pos += 1
                continue
            match = _BARE_URL.match(text, pos)
            if match:
                end = match.end()
                domain = re.split(r'[/?:#]', match.group(0), maxsplit=1)[0]
                segments = domain.split('.')
                valid_www = (len(segments) >= 2
                             and all(re.fullmatch(r'[A-Za-z0-9_-]+', part) for part in segments)
                             and all('_' not in part for part in segments[-2:])
                             and (pos == 0 or unicode_whitespace(text[pos - 1])
                                  or text[pos - 1] in '*_~('))
                if not www or valid_www:
                    while end > pos and text[end - 1] in '?!.,:*_~': end -= 1
                    excess = text[pos:end].count(')') - text[pos:end].count('(')
                    while excess > 0 and end > pos and text[end - 1] == ')':
                        end -= 1
                        excess -= 1
                    spans.append((pos, end, 'bare_url'))
                    pos = end
                    continue
        pos += 1
    return sorted(spans)

def _columns(text):
    columns = 0
    for ch in text:
        if ch == ' ': columns += 1
        elif ch == '\t': columns += 4 - columns % 4
        else: break
    return columns

def _containers(raw, allow_list=True):
    if (type(raw) is str and raw and raw[0] not in ' >'
            and (not allow_list or (_CONTAINER_MARKER is _CONTAINER_MARKER_DEFAULT
                                   and raw[0] not in '-+*' and not raw[0].isdigit()))):
        return 0, 0, False
    pos = 0
    quotes = 0
    list_item = False
    while pos < len(raw):
        candidate = pos
        while candidate < len(raw) and candidate - pos < 3 and raw[candidate] == ' ':
            candidate += 1
        if candidate < len(raw) and raw[candidate] == '>':
            quotes += 1
            pos = candidate + 1
            if pos < len(raw) and raw[pos] in ' \t': pos += 1
            continue
        marker = _CONTAINER_MARKER.match(raw, candidate) if allow_list else None
        if marker:
            list_item = True
            pos = marker.end()
            continue
        break
    return pos, quotes, list_item

def _physical_lines(text):
    rows = []
    start = 0
    for ending in re.finditer(r'\r\n|\r|\n', text):
        rows.append((start, text[start:ending.start()], ending.group(0)))
        start = ending.end()
    rows.append((start, text[start:], ''))
    return rows

def _table_cells(content):
    stripped = content.strip(' \t')
    starts = [0]
    ends = []
    for index, ch in enumerate(stripped):
        if ch == '|' and not _escaped(stripped, index):
            ends.append(index)
            starts.append(index + 1)
    ends.append(len(stripped))
    cells = [stripped[left:right] for left, right in zip(starts, ends)]
    if stripped.startswith('|'): cells.pop(0)
    if stripped.endswith('|') and not _escaped(stripped, len(stripped) - 1): cells.pop()
    return cells

class _RowCursor:
    def __init__(self, lines, row, column=0):
        self.lines = lines
        self.row = row
        self.column = column

    def char(self):
        line = self.lines[self.row]
        if self.column < len(line):
            return line[self.column]
        return '\n' if self.row + 1 < len(self.lines) else None

    def following(self):
        line = self.lines[self.row]
        return line[self.column + 1] if self.column + 1 < len(line) else None

    def advance(self):
        if self.column < len(self.lines[self.row]):
            self.column += 1
        elif self.row + 1 < len(self.lines):
            self.row += 1
            self.column = 0

    def escape(self):
        if self.char() == '\\' and self.following() in _ASCII_PUNCT:
            self.advance()
            self.advance()
            return True
        return False

def _reference_gap(cursor):
    seen = False
    while cursor.char() in (' ', '\t'):
        cursor.advance()
        seen = True
    if cursor.char() == '\n':
        cursor.advance()
        seen = True
        while cursor.char() in (' ', '\t'):
            cursor.advance()
    return seen

def _reference_destination(cursor):
    if cursor.char() == '<':
        cursor.advance()
        while cursor.char() is not None:
            if cursor.escape():
                continue
            if cursor.char() == '>':
                cursor.advance()
                return True
            if cursor.char() in ('<', '\n'):
                return False
            cursor.advance()
        return False
    count = 0
    depth = 0
    while cursor.char() is not None and cursor.char() not in (' ', '\t', '\n'):
        ch = cursor.char()
        if cursor.escape():
            count += 2
            continue
        if ord(ch) < 32 or ord(ch) == 127 or ch in '<>':
            return False
        if ch == '(':
            depth += 1
            if depth > 32:
                return False
        elif ch == ')':
            if depth == 0:
                return False
            depth -= 1
        cursor.advance()
        count += 1
    return count > 0 and depth == 0

def _reference_title_end(cursor):
    opener = cursor.char()
    closer = ')' if opener == '(' else opener
    cursor.advance()
    while cursor.char() is not None:
        if cursor.escape():
            continue
        ch = cursor.char()
        if ch == closer:
            cursor.advance()
            while cursor.char() in (' ', '\t'):
                cursor.advance()
            return cursor.row if cursor.char() in (None, '\n') else None
        if opener == '(' and ch == '(':
            return None
        if ch == '\n' and not cursor.lines[cursor.row + 1].strip(' \t'):
            return None
        cursor.advance()
    return None

def reference_definition_end(lines, start, paragraph_context=False):
    if paragraph_context or not 0 <= start < len(lines):
        return None
    cursor = _RowCursor(lines, start)
    spaces = 0
    while cursor.char() == ' ' and spaces < 3:
        cursor.advance()
        spaces += 1
    if cursor.char() != '[':
        return None
    cursor.advance()
    label_length = 0
    meaningful = False
    while cursor.char() is not None and cursor.char() != ']':
        ch = cursor.char()
        if cursor.escape():
            label_length += 2
            meaningful = True
        else:
            if ch == '[':
                return None
            if ch == '\n' and not cursor.lines[cursor.row + 1].strip(' \t'):
                return None
            meaningful |= ch not in ' \t\n'
            label_length += 1
            cursor.advance()
        if label_length > 999:
            return None
    if cursor.char() != ']' or not meaningful:
        return None
    cursor.advance()
    if cursor.char() != ':':
        return None
    cursor.advance()
    _reference_gap(cursor)
    if cursor.char() in (None, '\n') or not _reference_destination(cursor):
        return None
    destination_row = cursor.row
    separated = _reference_gap(cursor)
    if cursor.char() in (None, '\n'):
        return destination_row
    if not separated or cursor.char() not in ('"', "'", '('):
        return destination_row if cursor.row > destination_row else None
    title_on_later_row = cursor.row > destination_row
    title_row = _reference_title_end(cursor)
    return destination_row if title_row is None and title_on_later_row else title_row

def analyze_markdown(text, skip_frontmatter=True):
    lines = []
    blocks = []
    protected = []
    current = None
    fence = None
    html_until = None
    active_list_indent = 0
    raw_rows = _physical_lines(text)
    fm_end = 0
    if skip_frontmatter and raw_rows and raw_rows[0][1].strip() == '---':
        for index in range(1, len(raw_rows)):
            if raw_rows[index][1].strip() == '---':
                fm_end = index + 1
                break
    for index, (start, raw, ending) in enumerate(raw_rows):
        prefix, depth, list_item = _containers(raw)
        quote_prefix, quote_depth, _ = _containers(raw, allow_list=False)
        quote_content = raw[quote_prefix:]
        if (_THEMATIC.match(quote_content)
                or (current is not None and current['kind'] in ('paragraph', 'quote', 'list')
                    and _SETEXT.match(quote_content))):
            prefix, depth, list_item = quote_prefix, quote_depth, False
        if list_item:
            active_list_indent = prefix
        elif active_list_indent and depth and prefix >= active_list_indent:
            list_item = True
        elif active_list_indent and raw.strip():
            indent = len(raw) - len(raw.lstrip(' \t'))
            if depth == 0 and indent >= active_list_indent:
                prefix = active_list_indent
                list_item = True
            elif depth == 0:
                active_list_indent = 0
        content = raw[prefix:]
        stripped = content.strip(' \t')
        info = {'line': index + 1, 'raw': raw, 'start': start, 'ending': ending,
                'content_start': start + prefix, 'content': content,
                'quote_depth': depth, 'list_item': list_item, 'kind': 'paragraph'}
        if prefix:
            protected.append((start, start + prefix, 'container_prefix'))
        if index < fm_end:
            kind = 'frontmatter'
        elif fence is not None and depth < fence[2]:
            fence = None
            kind = None
        else:
            kind = None
        if kind is None and fence is not None:
            kind = 'code'
            closing = re.match(r'^ {0,3}(' + re.escape(fence[0]) + r'{'+str(fence[1])+r',})[ \t]*$', content)
            if closing: fence = None
        if kind is None and html_until is not None:
            kind = 'html_block'
            if html_until == 'blank':
                if not stripped: html_until = None
            elif re.search(html_until, content, re.I): html_until = None
        if kind is None:
            marker = _FENCE_OPEN.match(content)
            if marker and not (marker.group(1)[0] == '`' and '`' in marker.group(2)):
                kind = 'code'
                fence = (marker.group(1)[0], len(marker.group(1)), depth)
            elif _columns(content) >= 4 and (current is None or current['kind'] == 'code'):
                kind = 'code'
            elif not stripped:
                kind = 'blank'
            elif _ATX_HEADING.match(content):
                kind = 'heading'
            elif _SETEXT.match(content) and current is not None and current['kind'] in ('paragraph', 'quote', 'list'):
                current['kind'] = 'heading'
                for earlier in current['lines']: earlier['kind'] = 'heading'
                kind = 'heading_underline'
            elif _THEMATIC.match(content):
                kind = 'thematic_break'
            elif (current is not None and current['kind'] in ('paragraph', 'quote', 'list')
                  and current['lines'] and '|' in content
                  and len(_table_cells(content)) == len(_table_cells(current['lines'][-1]['content']))
                  and all(re.fullmatch(r'[ \t]*:?-+:?[ \t]*', cell) for cell in _table_cells(content))):
                if current['lines']:
                    header = current['lines'].pop()
                    header['kind'] = 'table'
                    if not current['lines']:
                        blocks.pop()
                    blocks.append({'kind': 'table', 'lines': [header]})
                    current = None
                kind = 'table'
            elif current is not None and current['kind'] == 'table' and '|' in content:
                kind = 'table'
            else:
                html_start = content.lstrip(' \t')
                if html_start.startswith('<!--'): html_until = '-->'
                elif html_start.startswith('<?'): html_until = r'\?>'
                elif html_start.startswith('<![CDATA['): html_until = r'\]\]>'
                elif re.match(r'<![A-Z]', html_start): html_until = '>'
                elif re.match(r'<(?:script|pre|style|textarea)(?:[ \t>]|$)', html_start, re.I):
                    tag = re.match(r'<([A-Za-z]+)', html_start).group(1)
                    html_until = '</' + tag + r'\s*>'
                elif re.match(r'</?([A-Za-z][A-Za-z0-9-]*)(?:[ \t/>]|$)', html_start):
                    tag = re.match(r'</?([A-Za-z][A-Za-z0-9-]*)', html_start).group(1).lower()
                    if tag in _HTML_BLOCK_TAGS: html_until = 'blank'
                    elif (current is None or current['kind'] not in ('paragraph', 'list', 'quote')):
                        end = _tag_end(html_start, 0)
                        if end is not None and not html_start[end:].strip(' \t'):
                            html_until = 'blank'
                if html_until is not None:
                    kind = 'html_block'
                    if html_until != 'blank' and re.search(html_until, content, re.I): html_until = None
                else:
                    kind = 'list' if list_item else 'quote' if depth else 'paragraph'
        info['kind'] = kind
        lines.append(info)
        if kind in ('blank', 'thematic_break', 'heading_underline'):
            current = None
            continue
        if kind in ('code', 'frontmatter', 'html_block', 'reference_definition'):
            protected.append((start, start + len(raw) + len(ending), kind))
        continue_block = (current is not None and current['kind'] == kind
                          and kind not in ('heading', 'table', 'list'))
        if continue_block and kind == 'quote' and current['lines'][0]['quote_depth'] != depth:
            continue_block = False
        if kind == 'list' and current is not None and current['kind'] == 'list' and not _containers(raw)[2]:
            continue_block = True
        if kind == 'paragraph' and current is not None and current['kind'] == 'quote' and depth == 0:
            continue_block = True
            info['kind'] = 'quote'
        if not continue_block:
            current = {'kind': info['kind'], 'lines': []}
            blocks.append(current)
        current['lines'].append(info)
    reference_blocks = []
    for block in blocks:
        rows = block['lines']
        offset = 0
        if block['kind'] in ('paragraph', 'list', 'quote', 'heading'):
            contents = [row['content'] for row in rows]
            while offset < len(rows):
                end = reference_definition_end(contents, offset)
                if end is None:
                    break
                reference_rows = rows[offset:end + 1]
                for row in reference_rows:
                    row['kind'] = 'reference_definition'
                    protected.append((row['start'], row['start'] + len(row['raw']) + len(row['ending']),
                                      'reference_definition'))
                reference_blocks.append({'kind': 'reference_definition', 'lines': reference_rows})
                offset = end + 1
        if offset < len(rows):
            reference_blocks.append({'kind': block['kind'], 'lines': rows[offset:]})
    blocks = reference_blocks
    for block in blocks:
        if block['kind'] in ('code', 'frontmatter', 'html_block', 'reference_definition'):
            continue
        first, last = block['lines'][0], block['lines'][-1]
        begin = first['start']
        finish = last['start'] + len(last['raw'])
        segment = list(text[begin:finish])
        for row in block['lines']:
            for position in range(row['start'], row['content_start']):
                segment[position - begin] = ' '
        for left, right, kind in inline_protected_spans(''.join(segment)):
            protected.append((begin + left, begin + right, kind))
    ordered = sorted(protected)
    merged = []
    for left, right, _ in ordered:
        if merged and left <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], right))
        else: merged.append((left, right))
    return {'text': text, 'lines': lines, 'blocks': blocks,
            'protected_spans': ordered, 'mask_spans': merged,
            'mask_ends': [right for _, right in merged]}

def decode_source(data):
    if isinstance(data, str):
        text = data
    else:
        text = bytes(data).decode("utf-8")
    bom = text.startswith("\ufeff")
    if bom:
        text = text[1:]
    if "\r" in text:
        crlf = text.count("\r\n")
        cr = text.count("\r") - crlf
        lf = text.count("\n") - crlf
        kinds = [name for name, count in (("lf", lf), ("crlf", crlf), ("cr", cr)) if count]
        eol = kinds[0] if len(kinds) == 1 else "mixed"
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    else:
        eol = "lf" if "\n" in text else "none"
    return text, {"bom": bom, "eol": eol}

DOC_TYPES = (
    ("pr", "PR説明", ("business.md",)),
    ("article", "技術記事", ("tech.md",)),
    ("incident", "障害報告", ("business.md",)),
    ("proposal", "提案書", ("business.md",)),
    ("minutes", "議事録", ("business.md",)),
    ("manual", "マニュアル", ("tech.md", "business.md")),
    ("slides", "スライド", ("tech.md", "business.md")),
    ("essay", "エッセイ・小説", ("essay.md",)),
    ("formal", "公用文、規程、契約書、仕様書", ("business.md", "tech.md")),
    ("promo", "紹介記事・宣伝文", ("essay.md", "business.md")),
    ("mail", "メール・チャット", ("business.md",)),
    ("paper", "論文・研究レポート", ("tech.md",)),
)

def _normalize_choice(option, value, rows):
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", str(value)).strip().lower()
    for row in rows:
        if row[0] == normalized:
            return normalized
    shown = value if str(value).strip() else "（空）"
    raise ValueError("{} に使えない値です: {}。使えるのは {}です。".format(
        option, shown, "、".join("{}（{}）".format(row[0], row[1]) for row in rows)))

def normalize_doc_type(value):
    return _normalize_choice("--doc-type", value, DOC_TYPES)

_END = r"(?=[。、！!？?よねがけのかし]|です|$)"

_NORMALIZE_BOLD = re.compile(r"\*\*(.+?)\*\*")
_NORMALIZE_LIST = re.compile(r"(?m)^\s*(?:[*\-・]|\d+[.)])\s+")
_NORMALIZE_HEADING = re.compile(r"(?m)^#+\s*")
_NORMALIZE_SPACES = re.compile(r"[ \t]+")

def normalize(t: str) -> str:
    t = _NORMALIZE_BOLD.sub(r"\1", t)
    t = _NORMALIZE_LIST.sub("", t)
    t = _NORMALIZE_HEADING.sub("", t)
    t = _NORMALIZE_SPACES.sub(" ", t)
    return t.strip()

_MATCH_SMALL_AREA = 2048
_MATCH_PROBE_MAX = 64
_MATCH_SEED_SHORT = 12
_MATCH_SEED_LONG = 40
_MATCH_SAMPLE_MIN = 24
_MATCH_SAMPLE_BUDGET_DIV = 4
_MATCH_SAM_FACTOR = 24
_MATCH_WHOLE_INDEX_MIN = 4096
_MATCH_PROBE_CACHE = 2
_MATCH_LOCAL_DIV = 8
_MATCH_AUTOMATON_MAX = 1 << 16
_MATCH_ROLLING_MIN = 256
_ROLLING_MOD = (1 << 61) - 1
_ROLLING_BASE = 1000000007

def _common_prefix_len(a, i, b, j, limit):
    if limit <= 0:
        return 0
    if a[i:i + limit] == b[j:j + limit]:
        return limit
    low, high = 0, limit
    step = 8
    while step < high and a[i:i + step] == b[j:j + step]:
        low = step
        step *= 2
    if step < high:
        high = step
    while high - low > 1:
        middle = (low + high) // 2
        if a[i + low:i + middle] == b[j + low:j + middle]:
            low = middle
        else:
            high = middle
    return low

def _common_suffix_len(a, i, b, j, limit):
    if limit <= 0:
        return 0
    if a[i - limit:i] == b[j - limit:j]:
        return limit
    low, high = 0, limit
    step = 8
    while step < high and a[i - step:i] == b[j - step:j]:
        low = step
        step *= 2
    if step < high:
        high = step
    while high - low > 1:
        middle = (low + high) // 2
        if a[i - middle:i - low] == b[j - middle:j - low]:
            low = middle
        else:
            high = middle
    return low

def _automaton_longest(a, alo, ahi, b, blo, bhi, cap):
    link = [-1]
    length = [0]
    trans = [{}]
    first = [-1]
    last = 0
    for pos in range(blo, bhi):
        c = b[pos]
        cur = len(length)
        length.append(length[last] + 1)
        link.append(0)
        trans.append({})
        first.append(pos)
        p = last
        while p != -1 and c not in trans[p]:
            trans[p][c] = cur
            p = link[p]
        if p != -1:
            q = trans[p][c]
            if length[p] + 1 == length[q]:
                link[cur] = q
            else:
                clone = len(length)
                length.append(length[p] + 1)
                link.append(link[q])
                trans.append(trans[q].copy())
                first.append(first[q])
                while p != -1 and trans[p].get(c) == q:
                    trans[p][c] = clone
                    p = link[p]
                link[q] = clone
                link[cur] = clone
        last = cur
    state = size = best = 0
    best_end = best_state = -1
    for pos in range(alo, ahi):
        c = a[pos]
        while state and c not in trans[state]:
            state = link[state]
            size = length[state]
        target = trans[state].get(c)
        if target is None:
            state = size = 0
            continue
        state = target
        size += 1
        if size > best:
            best, best_end, best_state = size, pos, state
            if best >= cap:
                break
    if not best:
        return difflib.Match(alo, blo, 0)
    return difflib.Match(best_end - best + 1, first[best_state] - best + 1, best)

def _gram_index(b, q):
    shift = len(b).bit_length()
    keep = (1 << (63 - shift)) - 1
    keys = sorted([((hash(b[j:j + q]) & keep) << shift) | j for j in range(len(b) - q + 1)])
    return array("q", keys), shift, keep, (1 << shift) - 1

def _rolling_hashes(codes, size):
    if size <= 0 or len(codes) < size:
        return
    mod, base = _ROLLING_MOD, _ROLLING_BASE
    top = pow(base, size - 1, mod)
    value = 0
    for code in codes[:size]:
        value = (value * base + code) % mod
    yield value
    for old, new in zip(codes, codes[size:]):
        value = ((value - old * top) * base + new) % mod
        yield value

class _ExactSequenceMatcher(difflib.SequenceMatcher):

    def set_seq1(self, a):
        if a is not self.__dict__.get("a"):
            self.__dict__.pop("_collision_rate", None)
        difflib.SequenceMatcher.set_seq1(self, a)

    def set_seq2(self, b):
        if b is not self.__dict__.get("b"):
            for key in ("_collision_rate", "_seed_indexes", "_probe_indexes"):
                self.__dict__.pop(key, None)
        difflib.SequenceMatcher.set_seq2(self, b)

    def _fast(self):
        return (self.isjunk is None and not self.bjunk and not self.bpopular
                and type(self.a) is str and type(self.b) is str)

    def get_matching_blocks(self):
        if self.matching_blocks is not None:
            return self.matching_blocks
        if not self._fast():
            return difflib.SequenceMatcher.get_matching_blocks(self)
        la, lb = len(self.a), len(self.b)
        queue = [(0, la, 0, lb, min(la, lb))]
        matching_blocks = []
        while queue:
            alo, ahi, blo, bhi, bound = queue.pop()
            i, j, k = x = self._longest(alo, ahi, blo, bhi, bound)
            if k:
                matching_blocks.append(x)
                if alo < i and blo < j:
                    queue.append((alo, i, blo, j, k - 1))
                if i + k < ahi and j + k < bhi:
                    queue.append((i + k, ahi, j + k, bhi, k))
        matching_blocks.sort()
        i1 = j1 = k1 = 0
        non_adjacent = []
        for i2, j2, k2 in matching_blocks:
            if i1 + k1 == i2 and j1 + k1 == j2:
                k1 += k2
            else:
                if k1:
                    non_adjacent.append((i1, j1, k1))
                i1, j1, k1 = i2, j2, k2
        if k1:
            non_adjacent.append((i1, j1, k1))
        non_adjacent.append((la, lb, 0))
        self.matching_blocks = list(map(difflib.Match._make, non_adjacent))
        return self.matching_blocks

    def find_longest_match(self, alo=0, ahi=None, blo=0, bhi=None):
        ahi = len(self.a) if ahi is None else ahi
        bhi = len(self.b) if bhi is None else bhi
        if not (self._fast() and type(alo) is int and type(ahi) is int and type(blo) is int and type(bhi) is int
                and 0 <= alo <= ahi <= len(self.a) and 0 <= blo <= bhi <= len(self.b)):
            return difflib.SequenceMatcher.find_longest_match(self, alo, ahi, blo, bhi)
        return self._longest(alo, ahi, blo, bhi, min(ahi - alo, bhi - blo))

    def _longest(self, alo, ahi, blo, bhi, bound):
        a, b = self.a, self.b
        la, lb = ahi - alo, bhi - blo
        cap = min(bound, la, lb)
        if cap <= 0:
            return difflib.Match(alo, blo, 0)
        if la * lb <= _MATCH_SMALL_AREA:
            return self._dp(alo, ahi, blo, bhi)
        if cap == la:
            j = b.find(a[alo:ahi], blo, bhi)
            if j != -1:
                return difflib.Match(alo, j, cap)
            cap -= 1
        elif cap == lb:
            i = a.find(b[blo:bhi], alo, ahi)
            if i != -1:
                return difflib.Match(i, blo, cap)
            cap -= 1
        elif cap <= _MATCH_PROBE_MAX:
            found = self._probe(alo, ahi, blo, bhi, cap)
            if found is not None:
                return found
            cap -= 1
        if cap <= 0:
            return difflib.Match(alo, blo, 0)
        length = cap
        while length >= _MATCH_SAMPLE_MIN:
            found = self._seeded(alo, ahi, blo, bhi, length, (la + lb) // _MATCH_SAMPLE_BUDGET_DIV)
            if found is None:
                break
            if found is not False:
                return found
            cap = length - 1
            length //= 2
        if la * lb * self._collision() <= _MATCH_SAM_FACTOR * (la + lb):
            return self._dp(alo, ahi, blo, bhi)
        if lb <= _MATCH_AUTOMATON_MAX:
            return _automaton_longest(a, alo, ahi, b, blo, bhi, cap)
        return self._bisect_length(alo, ahi, blo, bhi, cap)

    def _bisect_length(self, alo, ahi, blo, bhi, cap):
        low, high, found = 0, cap, None
        codes = []
        while low < high:
            middle = (low + high + 1) // 2
            match = self._first_of_length(alo, ahi, blo, bhi, middle, codes)
            if match is None:
                high = middle - 1
            else:
                low, found = middle, match
        return found if found is not None else difflib.Match(alo, blo, 0)

    def _first_of_length(self, alo, ahi, blo, bhi, size, codes):
        a, b = self.a, self.b
        if size < _MATCH_ROLLING_MIN:
            seen = {hash(b[j:j + size]) for j in range(blo, bhi - size + 1)}
            for i in range(alo, ahi - size + 1):
                gram = a[i:i + size]
                if hash(gram) in seen:
                    j = b.find(gram, blo, bhi)
                    if j != -1:
                        return difflib.Match(i, j, size)
            return None
        if not codes:
            codes.append(array("l", map(ord, a[alo:ahi])))
            codes.append(array("l", map(ord, b[blo:bhi])))
        first = {}
        for offset, value in enumerate(_rolling_hashes(codes[1], size)):
            if value not in first:
                first[value] = blo + offset
        get = first.get
        for offset, value in enumerate(_rolling_hashes(codes[0], size)):
            j = get(value)
            if j is not None:
                i = alo + offset
                gram = a[i:i + size]
                if b[j:j + size] != gram:
                    j = b.find(gram, blo, bhi)
                    if j == -1:
                        continue
                return difflib.Match(i, j, size)
        return None

    def _probe(self, alo, ahi, blo, bhi, size):
        a, b = self.a, self.b
        if bhi - blo <= _MATCH_WHOLE_INDEX_MIN:
            first = {}
            for j in range(bhi - size, blo - 1, -1):
                first[b[j:j + size]] = j
            get = first.get
            for i in range(alo, ahi - size + 1):
                j = get(a[i:i + size])
                if j is not None:
                    return difflib.Match(i, j, size)
            return None
        cache = self.__dict__.setdefault("_probe_indexes", {})
        index = cache.pop(size, None)
        if index is None:
            if (ahi - alo) + (bhi - blo) <= len(b) // _MATCH_LOCAL_DIV:
                return self._probe_local(alo, ahi, blo, bhi, size)
            while cache and len(cache) >= _MATCH_PROBE_CACHE:
                del cache[next(iter(cache))]
            index = _gram_index(b, size)
        cache[size] = index
        keys, shift, keep, low = index
        count = len(keys)
        last = bhi - size
        for i in range(alo, ahi - size + 1):
            gram = a[i:i + size]
            base = (hash(gram) & keep) << shift
            p = bisect_left(keys, base | blo)
            end = base | last
            while p < count and keys[p] <= end:
                j = keys[p] & low
                if b[j:j + size] == gram:
                    return difflib.Match(i, j, size)
                p += 1
        return None

    def _probe_local(self, alo, ahi, blo, bhi, size):
        a, b = self.a, self.b
        if bhi - blo <= ahi - alo:
            first = {}
            for j in range(bhi - size, blo - 1, -1):
                first[b[j:j + size]] = j
            get = first.get
            for i in range(alo, ahi - size + 1):
                j = get(a[i:i + size])
                if j is not None:
                    return difflib.Match(i, j, size)
            return None
        first = {}
        for i in range(ahi - size, alo - 1, -1):
            first[a[i:i + size]] = i
        get = first.get
        best = None
        for j in range(blo, bhi - size + 1):
            i = get(b[j:j + size])
            if i is not None and (best is None or i < best[0]):
                best = (i, j)
                if i == alo:
                    break
        return None if best is None else difflib.Match(best[0], best[1], size)

    def _seeded(self, alo, ahi, blo, bhi, length, budget):
        a, b = self.a, self.b
        q = _MATCH_SEED_LONG if length >= 2 * _MATCH_SEED_LONG else _MATCH_SEED_SHORT
        indexes = self.__dict__.setdefault("_seed_indexes", {})
        index = indexes.get(q)
        if index is None:
            index = indexes[q] = _gram_index(b, q)
        keys, shift, keep, low = index
        count = len(keys)
        step = length - q + 1
        last = bhi - q
        seeds = []
        total = 0
        for t in range(alo + step - 1, ahi - q + 1, step):
            gram = a[t:t + q]
            base = (hash(gram) & keep) << shift
            p = bisect_left(keys, base | blo)
            end = base | last
            while p < count and keys[p] <= end:
                u = keys[p] & low
                if b[u:u + q] == gram:
                    seeds.append((t, u))
                    total += 1
                    if total > budget:
                        return None
                p += 1
        best = None
        for t, u in seeds:
            back = _common_suffix_len(a, t, b, u, min(t - alo, u - blo))
            size = back + q + _common_prefix_len(a, t + q, b, u + q, min(ahi - t, bhi - u) - q)
            if size >= length:
                candidate = (-size, t - back, u - back)
                if best is None or candidate < best:
                    best = candidate
        if best is None:
            return False
        return difflib.Match(best[1], best[2], -best[0])

    def _collision(self):
        rate = self.__dict__.get("_collision_rate")
        if rate is None:
            count_a, count_b = Counter(self.a), Counter(self.b)
            same = sum(n * count_b.get(ch, 0) for ch, n in count_a.items())
            rate = self._collision_rate = same / float(max(1, len(self.a) * len(self.b)))
        return rate

    def _dp(self, alo, ahi, blo, bhi):
        a, b2j = self.a, self.b2j
        besti, bestj, bestsize = alo, blo, 0
        j2len = {}
        for i in range(alo, ahi):
            positions = b2j.get(a[i])
            newj2len = {}
            if positions:
                get = j2len.get
                for j in positions[bisect_left(positions, blo):bisect_left(positions, bhi)]:
                    k = newj2len[j] = get(j - 1, 0) + 1
                    if k > bestsize:
                        besti, bestj, bestsize = i - k + 1, j - k + 1, k
            j2len = newj2len
        return difflib.Match(besti, bestj, bestsize)

_CHAR_ALIGN_LIMIT = 2000

_BLOCK_ALIGN_LIMIT = 500
_CHAR_BUDGET = 200000
_PAIR_WINDOW = 4
_PAIR_RATIO = 0.45

_FRAGMENT = re.compile(r"(?:[^。！？!?．.\n]|\.(?![ \t\n]|$))*(?:[。！？!?．]+|\.+(?=[ \t\n]|$))?[」』）)]*[ \t]*\n?")

_SPACES = re.compile("[\\s\ufeff]+")
_ATX = re.compile(r"^( {0,3})(#{1,6})((?:[ \t].*)?)$")

_LIMIT_NAMES = ("long_fragment", "too_large", "budget")

def _split_lines(text):
    lines = text.split("\n")
    if text.endswith("\n"):
        lines.pop()
    return lines

def _line_starts(lines):
    starts, position = [], 0
    for line in lines:
        starts.append(position)
        position += len(line) + 1
    return starts

def _is_blank(line):
    return not line.strip()

def _analyze(text):
    analysis = analyze_markdown(text.replace("\r", " ") if "\r" in text else text)
    spans, changed = [], False
    for left, right, kind in analysis["protected_spans"]:
        if kind == "bare_url":
            end = _URL_CHARS.match(text, left).end()
            if left < end < right:
                right, changed = end, True
        spans.append((left, right, kind))
    if changed:
        analysis = dict(analysis)
        analysis["protected_spans"] = spans
    return analysis

_URL_CHARS = re.compile(r"[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]*")

def _align(old, new, similar=False):
    pairs = []
    _align_range(old, new, 0, len(old), 0, len(new), similar, pairs, 0)
    return pairs

_SMALL_GAP = 400
_GAP_WINDOW = 8
_ALIGN_DEPTH = 64

def _align_range(old, new, i1, i2, j1, j2, similar, out, depth):
    while i1 < i2 and j1 < j2 and old[i1] == new[j1]:
        out.append((i1, j1, True))
        i1, j1 = i1 + 1, j1 + 1
    tail = []
    while i1 < i2 and j1 < j2 and old[i2 - 1] == new[j2 - 1]:
        i2, j2 = i2 - 1, j2 - 1
        tail.append((i2, j2, True))
    if i1 < i2 and j1 < j2:
        anchors = _unique_anchors(old, new, i1, i2, j1, j2) if depth < _ALIGN_DEPTH else []
        if anchors:
            previous_i, previous_j = i1, j1
            for i, j in anchors:
                _align_range(old, new, previous_i, i, previous_j, j, similar, out, depth + 1)
                out.append((i, j, True))
                previous_i, previous_j = i + 1, j + 1
            _align_range(old, new, previous_i, i2, previous_j, j2, similar, out, depth + 1)
        else:
            out.extend(_fill_gap(old, new, i1, i2, j1, j2, similar))
    out.extend(reversed(tail))

def _unique_anchors(old, new, i1, i2, j1, j2):
    count_old = Counter(old[i1:i2])
    count_new = Counter(new[j1:j2])
    where = {}
    for j in range(j1, j2):
        item = new[j]
        if count_new[item] == 1 and count_old.get(item) == 1 and not _is_blank(item):
            where[item] = j
    candidates = [(i, where[old[i]]) for i in range(i1, i2) if old[i] in where]
    tails, tail_values, previous = [], [], [None] * len(candidates)
    for index, (_, j) in enumerate(candidates):
        position = bisect_left(tail_values, j)
        if position:
            previous[index] = tails[position - 1]
        if position == len(tails):
            tails.append(index)
            tail_values.append(j)
        else:
            tails[position] = index
            tail_values[position] = j
    chain = []
    index = tails[-1] if tails else None
    while index is not None:
        chain.append(candidates[index])
        index = previous[index]
    return chain[::-1]

def _fill_gap(old, new, i1, i2, j1, j2, similar):
    if i1 >= i2 or j1 >= j2:
        return []
    found = []
    if (i2 - i1) * (j2 - j1) <= _SMALL_GAP:
        matcher = difflib.SequenceMatcher(None, old[i1:i2], new[j1:j2], autojunk=False)
        for a, b, size in matcher.get_matching_blocks():
            found.extend((i1 + a + k, j1 + b + k, True) for k in range(size))
    else:
        positions = {}
        for j in range(j1, j2):
            positions.setdefault(new[j], []).append(j)
        in_old = set(old[i1:i2])
        shared = [0]
        for j in range(j1, j2):
            shared.append(shared[-1] + (new[j] in in_old))
        k = j1
        for i in range(i1, i2):
            places = positions.get(old[i])
            if not places:
                continue
            index = bisect_left(places, k)
            if index == len(places):
                continue
            place = places[index]
            if place - k < _GAP_WINDOW or shared[place - j1] - shared[k - j1] < _GAP_WINDOW:
                found.append((i, place, True))
                k = place + 1
    if not similar:
        return found
    pairs = []
    previous_i, previous_j = i1, j1
    for i, j, same in found + [(i2, j2, None)]:
        for x, y in _pair_similar(old, new, previous_i, i, previous_j, j):
            pairs.append((x, y, old[x] == new[y]))
        if same is not None:
            pairs.append((i, j, same))
        previous_i, previous_j = i + 1, j + 1
    return pairs

def _common_affix(a, b):
    limit = min(len(a), len(b))
    low, high = 0, limit
    while low < high:
        middle = (low + high + 1) // 2
        if a[:middle] == b[:middle]:
            low = middle
        else:
            high = middle - 1
    head = low
    low, high = 0, limit - head
    while low < high:
        middle = (low + high + 1) // 2
        if a[len(a) - middle:] == b[len(b) - middle:]:
            low = middle
        else:
            high = middle - 1
    return head, low

def _affix_ratio(a, b):
    if not a and not b:
        return 1.0
    head, tail = _common_affix(a, b)
    return 2.0 * (head + tail) / (len(a) + len(b))

def _pair_similar(old, new, i1, i2, j1, j2):
    pairs = []
    start = j1
    matcher = difflib.SequenceMatcher(None, "", "", autojunk=False)
    for i in range(i1, i2):
        if start >= j2:
            break
        matcher.set_seq2(old[i])
        best, best_ratio = None, 0.0
        for j in range(start, min(start + _PAIR_WINDOW, j2)):
            matcher.set_seq1(new[j])
            upper = matcher.real_quick_ratio()
            if upper < _PAIR_RATIO or upper <= best_ratio:
                continue
            upper = matcher.quick_ratio()
            if upper < _PAIR_RATIO or upper <= best_ratio:
                continue
            if len(old[i]) > _CHAR_ALIGN_LIMIT or len(new[j]) > _CHAR_ALIGN_LIMIT:
                ratio = _affix_ratio(old[i], new[j])
            else:
                ratio = matcher.ratio()
            if ratio >= _PAIR_RATIO and ratio > best_ratio:
                best, best_ratio = j, ratio
        if best is not None:
            pairs.append((i, best))
            start = best + 1
    return pairs

def _opcodes(pairs, n, m):
    blocks = []
    i = j = 0
    for x, y, _ in pairs + [(n, m, True)]:
        if x > i or y > j:
            tag = "replace" if x > i and y > j else ("delete" if x > i else "insert")
            blocks.append((tag, i, x, j, y))
        i, j = x + 1, y + 1
    return blocks

def _merge_segments(segments):
    merged = []
    for tag, text in segments:
        if not text:
            continue
        if merged and merged[-1][0] == tag:
            merged[-1][1].append(text)
        else:
            merged.append([tag, [text]])
    return [[tag, parts[0] if len(parts) == 1 else "".join(parts)] for tag, parts in merged]

def _char_segments(a, b):
    limit = min(len(a), len(b))
    head = 0
    while head < limit and a[head] == b[head]:
        head += 1
    tail = 0
    while tail < limit - head and a[len(a) - 1 - tail] == b[len(b) - 1 - tail]:
        tail += 1
    middle_a, middle_b = a[head:len(a) - tail], b[head:len(b) - tail]
    segments = [["=", a[:head]]]
    if middle_a and middle_b:
        for tag, i1, i2, j1, j2 in _ExactSequenceMatcher(None, middle_a, middle_b, autojunk=False).get_opcodes():
            if tag == "equal":
                segments.append(["=", middle_a[i1:i2]])
            else:
                segments.append(["-", middle_a[i1:i2]])
                segments.append(["+", middle_b[j1:j2]])
    else:
        segments.append(["-", middle_a])
        segments.append(["+", middle_b])
    segments.append(["=", a[len(a) - tail:]])
    return _merge_segments(segments)

def _fragments(text):
    pieces, position, size = [], 0, len(text)
    while position < size:
        end = _FRAGMENT.match(text, position).end()
        if end == position:
            end = position + 1
        pieces.append(text[position:end])
        position = end
    return pieces

def _plan_segments(a, b):
    if len(a) <= _BLOCK_ALIGN_LIMIT and len(b) <= _BLOCK_ALIGN_LIMIT:
        return len(a) + len(b), lambda: _char_segments(a, b), False
    old, new = _fragments(a), _fragments(b)
    pairs = _align(old, new, similar=True)
    cost, long_fragment = 0, False
    for i, j, same in pairs:
        if same:
            continue
        if len(old[i]) > _CHAR_ALIGN_LIMIT or len(new[j]) > _CHAR_ALIGN_LIMIT:
            long_fragment = True
        else:
            cost += len(old[i]) + len(new[j])

    def build():
        segments = []
        i = j = 0
        for x, y, same in pairs + [(len(old), len(new), None)]:
            segments.append(["-", "".join(old[i:x])])
            segments.append(["+", "".join(new[j:y])])
            if same is None:
                break
            if same:
                segments.append(["=", old[x]])
            elif len(old[x]) > _CHAR_ALIGN_LIMIT or len(new[y]) > _CHAR_ALIGN_LIMIT:
                head, tail = _common_affix(old[x], new[y])
                segments.append(["=", old[x][:head]])
                segments.append(["-", old[x][head:len(old[x]) - tail]])
                segments.append(["+", new[y][head:len(new[y]) - tail]])
                segments.append(["=", old[x][len(old[x]) - tail:]])
            else:
                segments.extend(_char_segments(old[x], new[y]))
            i, j = x + 1, y + 1
        return _merge_segments(segments)
    return cost, build, long_fragment

def _kinds(analysis, first, last):
    kinds = []
    rows = analysis["lines"]
    for index in range(first, last):
        kind = rows[index]["kind"] if index < len(rows) else "paragraph"
        if kind in ("paragraph", "list") and index < len(rows) and rows[index]["quote_depth"]:
            kind = "quote"
        if kind not in kinds:
            kinds.append(kind)
    return kinds

class _Sides:

    def __init__(self, orig, rw):
        self.texts = (orig, rw)
        self.lines = (_split_lines(orig), _split_lines(rw))
        self.starts = (_line_starts(self.lines[0]), _line_starts(self.lines[1]))
        self.analyses = (_analyze(orig), _analyze(rw))
        self._normalized = [None, None]
        self._numbers = [None, None]
        self.quiet_marks = []

    def line_of(self, side, position):
        return max(1, bisect_right(self.starts[side], position))

    def normalized_lines(self, side):
        if self._normalized[side] is None:
            self._normalized[side] = [normalize(line) for line in self.lines[side]]
        return self._normalized[side]

    def numbers(self, side):
        if self._numbers[side] is None:
            found = _find_numbers(self.texts[side], self.analyses[side])
            self._numbers[side] = (found, [number.start for number in found])
        return self._numbers[side]

    def all_keys(self, side):
        cache = self.__dict__.setdefault("_all_keys", {})
        if side not in cache:
            cache[side] = _KeySet(_find_numbers(self.texts[side], self.analyses[side], ()))
        return cache[side]

def full_diff(orig, rw, encoding_notes=None):
    return _build_full_diff(orig, rw, encoding_notes)[0]

def _build_full_diff(orig, rw, encoding_notes):
    sides = _Sides(orig, rw)
    old_lines, new_lines = sides.lines
    limits = set()
    hunks = []
    if old_lines != new_lines:
        pairs = _align(old_lines, new_lines)
        for tag, i1, i2, j1, j2 in _opcodes(pairs, len(old_lines), len(new_lines)):
            hunks.append(_make_hunk(len(hunks) + 1, tag, i1, i2, j1, j2, sides))
    _mark_moved(hunks)
    budget = _CHAR_BUDGET
    for hunk in hunks:
        if hunk["tag"] != "replace":
            continue
        cost, build, long_fragment = _plan_segments("\n".join(hunk["old_lines"]), "\n".join(hunk["new_lines"]))
        if cost > _CHAR_BUDGET:
            hunk["segments_omitted"] = "too_large"
        elif cost > budget:
            hunk["segments_omitted"] = "budget"
        else:
            budget -= cost
            hunk["segments"] = build()
            if long_fragment:
                limits.add("long_fragment")
        if hunk["segments_omitted"]:
            limits.add(hunk["segments_omitted"])
    full = {
        "encoding_notes": [dict(note) for note in (encoding_notes or [])],
        "final_newline": {"old": orig.endswith("\n"), "new": rw.endswith("\n")},
        "limits_applied": [name for name in _LIMIT_NAMES if name in limits],
        "hunks": hunks,
    }
    return full, sides

def _make_hunk(index, tag, i1, i2, j1, j2, sides):
    old_part, new_part = sides.lines[0][i1:i2], sides.lines[1][j1:j2]
    old_blocks, new_blocks = _kinds(sides.analyses[0], i1, i2), _kinds(sides.analyses[1], j1, j2)
    whitespace_only = _SPACES.sub("", "\n".join(old_part)) == _SPACES.sub("", "\n".join(new_part))
    notes = []
    if whitespace_only:
        notes.append({"kind": "whitespace_only"})
    if len(old_part) == 1 and len(new_part) == 1 and old_blocks == ["heading"] and new_blocks == ["heading"]:
        old_match, new_match = _ATX.match(old_part[0]), _ATX.match(new_part[0])
        if (old_match and new_match and old_match.group(1, 3) == new_match.group(1, 3)
                and len(old_match.group(2)) != len(new_match.group(2))):
            notes.append({"kind": "heading_level", "old": len(old_match.group(2)), "new": len(new_match.group(2))})
    return {"index": index, "tag": tag,
            "old_start": i1 + 1, "old_end": i2, "new_start": j1 + 1, "new_end": j2,
            "old_blocks": old_blocks, "new_blocks": new_blocks,
            "whitespace_only": whitespace_only, "notes": notes, "moved_to": None, "moved_from": None,
            "old_lines": old_part, "new_lines": new_part,
            "segments": None, "segments_omitted": None}

def _mark_moved(hunks):
    added = {}
    for hunk in hunks:
        for offset, line in enumerate(hunk["new_lines"]):
            if not _is_blank(line):
                added.setdefault(line, []).append((hunk, hunk["new_start"] + offset))
    if not added:
        return
    for hunk in hunks:
        for offset, line in enumerate(hunk["old_lines"]):
            if hunk["moved_to"] is not None or _is_blank(line):
                continue
            for other, line_no in added.get(line, ()):
                if other is hunk or other["moved_from"] is not None:
                    continue
                hunk["moved_to"] = other["index"]
                hunk["notes"].append({"kind": "moved_to", "hunk": other["index"], "line": line_no})
                other["moved_from"] = hunk["index"]
                other["notes"].append({"kind": "moved_from", "hunk": hunk["index"], "line": hunk["old_start"] + offset})
                break

_LINE_PREFIX = re.compile(r"(?:[ \t]{0,3}>[ \t]?|[ \t]*(?:[-*+・]|\d+[.)])[ \t]+|[ \t]{0,3}#{1,6}(?:[ \t]+|$)"

                          r"|[ \t]*(?:[(（]\d{1,9}[)）]|\d{1,9}）)[ \t　]*)")

_RISK_SENTENCE_PIECE = re.compile(r"(?:[^。！？!?．.\n]|\.(?![ \t]|$))+(?:[。！？!?．]+|\.+(?=[ \t]|$))?[」』）)]*")

_NO_SENTENCE_KINDS = ("code", "frontmatter", "html_block")

class _Sentence(tuple):
    __slots__ = ()

    def __new__(cls, text, line, start):
        return tuple.__new__(cls, (text, line, start))

    text = property(lambda self: self[0])
    line = property(lambda self: self[1])
    start = property(lambda self: self[2])

def _line_sentences(sides, side, first, last):
    sentences = []
    rows = sides.analyses[side]["lines"]
    for index in range(first, last):
        if index < len(rows) and rows[index]["kind"] in _NO_SENTENCE_KINDS:
            continue
        line = sides.lines[side][index]
        offset = 0
        while True:
            match = _LINE_PREFIX.match(line, offset)
            if not match or match.end() == offset:
                break
            offset = match.end()
        for match in _RISK_SENTENCE_PIECE.finditer(line, offset):
            text = match.group(0).strip()
            if text:
                start = match.start() + (len(match.group(0)) - len(match.group(0).lstrip()))
                sentences.append(_Sentence(text, index + 1, sides.starts[side][index] + start))
    return sentences

def _sentence_pairs(sides, full):
    groups = []
    hunks = full["hunks"]
    index = 0
    while index < len(hunks):
        run = [hunks[index]]
        while index + len(run) < len(hunks) and _blank_between(sides, run[-1], hunks[index + len(run)]):
            run.append(hunks[index + len(run)])
        if len(run) > 1 and _run_shifted(sides, run):
            old, new = [], []
            for hunk in run:
                old.extend(_line_sentences(sides, 0, hunk["old_start"] - 1, hunk["old_end"]))
                new.extend(_line_sentences(sides, 1, hunk["new_start"] - 1, hunk["new_end"]))
            pairs = []
            if old and new:
                pairs = [(i, j) for i, j, _ in _align([s.text for s in old], [s.text for s in new], similar=True)]
            merged = dict(run[0])
            merged["tag"] = "replace"
            groups.append({"hunk": merged, "hunks": run, "old": old, "new": new, "pairs": pairs})
        else:
            for hunk in run:
                groups.append(_hunk_group(sides, hunk))
        index += len(run)
    return groups

def _hunk_group(sides, hunk):
    old = _line_sentences(sides, 0, hunk["old_start"] - 1, hunk["old_end"])
    new = _line_sentences(sides, 1, hunk["new_start"] - 1, hunk["new_end"])
    pairs = []
    if hunk["tag"] == "replace" and old and new:
        if (len(old) == 1 and len(new) == 1 and hunk["old_end"] == hunk["old_start"]
                and hunk["new_end"] == hunk["new_start"]):
            pairs = [(0, 0)]
        else:
            pairs = [(i, j) for i, j, _ in _align([s.text for s in old], [s.text for s in new], similar=True)]
    return {"hunk": hunk, "old": old, "new": new, "pairs": pairs}

def _blank_between(sides, first, second):
    for side, end_key, start_key in ((0, "old_end", "old_start"), (1, "new_end", "new_start")):
        for line in sides.lines[side][first[end_key]:second[start_key] - 1]:
            if not _is_blank(line):
                return False
    return True

def _run_shifted(sides, run):
    differs = False
    replaced = 0
    for hunk in run:
        old, new = _paragraph_count(hunk["old_lines"]), _paragraph_count(hunk["new_lines"])
        if old != new:
            differs = True
        if hunk["tag"] == "replace" and old and new:
            replaced += 1
    return differs and replaced >= 2

def _paragraph_count(lines):
    count, inside = 0, False
    for line in lines:
        blank = _is_blank(line)
        if not blank and not inside:
            count += 1
        inside = not blank
    return count

_HALF_WIDTH = dict((code, code - 0xFEE0) for code in range(0xFF01, 0xFF5F))
_HALF_WIDTH[0x3000] = 0x20

_ARABIC = re.compile(r"(?<![A-Za-z0-9_])(?<![0-9][.,])[0-9]+(?:[.,][0-9]+)*")

_EMPHASIS = re.compile(r"\*+")
_THOUSANDS = re.compile(r"[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?")
_UNITS = ("週間", "時間", "か月", "ヶ月", "カ月", "ヵ月", "TB", "GB", "MB", "KB", "ms", "px", "%",
          "年", "月", "日", "時", "分", "秒", "件", "個", "人", "名", "回", "円", "倍", "割", "度", "点",
          "本", "枚", "台", "社", "週", "歳", "字", "行",
          "か所", "カ所", "ヶ所", "箇所", "種類", "章", "節", "項", "つ",
          "条", "号", "階")

_UNIT_NOT_BEFORE = {"階": "層", "条": "件"}

def _unit_pattern(units):
    return "|".join(re.escape(unit) + ("(?!" + _UNIT_NOT_BEFORE[unit] + ")" if unit in _UNIT_NOT_BEFORE else "")
                    for unit in sorted(units, key=len, reverse=True))

_UNIT = re.compile(_unit_pattern(_UNITS))

_SPACED_UNIT = re.compile(r"[ \u3000](TB|GB|MB|KB|ms|px|%)(?![A-Za-z])")

_LETTER_UNIT = re.compile(r"[A-Za-z]{1,5}(?![A-Za-z])")

_THOUSAND = re.compile(r"千")

_SAME_UNIT = {"ヶ月": "か月", "カ月": "か月", "ヵ月": "か月", "カ所": "か所", "ヶ所": "か所", "箇所": "か所"}

_KANJI_COUNTERS = ("週間", "時間", "か月", "ヶ月", "カ月", "ヵ月",
                   "年", "日", "件", "個", "人", "名", "回", "円", "倍", "割", "本", "枚", "台", "社", "歳",
                   "か所", "カ所", "ヶ所", "箇所", "種類", "章", "節", "項", "月", "つ",
                   "条", "号", "階", "分",
                   "時")
_KANJI_NUMBER = re.compile("(?<![〇一二三四五六七八九十百千])([〇一二三四五六七八九十百千]+)("
                           + _unit_pattern(_KANJI_COUNTERS) + ")")
_KANJI_DIGITS = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_KANJI_UNITS = {"十": 10, "百": 100, "千": 1000}

_KANJI_BEFORE = set("約後計全第毎各残大小長短年月週日")

_KANJI_BEFORE_WORDS = frozenset(("午前", "令和", "平成", "昭和", "大正", "明治"))

_TIME_OF_DAY_WORDS = frozenset(("午前", "午後", "深夜", "未明", "早朝", "夕方", "毎朝", "今朝", "明朝", "毎晩", "今晩",
                                "今夜", "毎夜", "夜中"))
_TIME_OF_DAY_CHARS = frozenset("朝夜晩昼")

_ICHIJI_HOUR_NEXT = frozenset("〇一二三四五六七八九十百半頃過前")
_KANJI = re.compile(r"[一-龥々〆ヵヶ]")

_WHOLE_PERIOD_WORDS = frozenset(("今日", "本日", "昨日", "明日", "終日", "当日", "前日", "翌日", "初日", "元日", "曜日",
                                 "今年", "去年", "昨年", "来年", "今月", "先月", "来月", "今週", "先週", "来週"))
_SAME_PERIOD = {"日": ("日",), "年": ("年",), "月": ("月", "か月", "ヶ月", "カ月", "ヵ月"), "週": ("週間",)}

_KANJI_CHAIN = re.compile("[〇一二三四五六七八九十百千]+(?:時間|週間|時|分|人|名|回|件|個|枚)$")

_KANJI_HOUR_BEFORE = re.compile("[〇一二三四五六七八九十百千]+(?:時|(時間|人|名|回|件|個|枚|日))$|(毎日)$")

_JIPPUN_AFTER = ("の", "、", "。", "，", "．", ",", ".", ")", "）", "」", "』", "\n", "ほど", "くらい", "ぐらい", "程度",
                 "前", "後", "以", "未満", "まで", "から", "かか", "を", "も", "が", "は", "強", "弱", "余", "ずつ", "ごと",
                 "おき", "とす", "とし", "だけ")

_JIPPUN_DE = "で"
_JIPPUN_DE_NOT = ("です", "でき", "でし")

_ICHIJI_JIPPUN_AFTER = ("まで", "から", "前", "後", "過ぎ", "すぎ", "ごろ", "頃", "以", "。", ")", "）", "」")
_KANJI_CHAIN_REACH = 12

_KANJI_EXCLUDED = re.compile(r"一時(?!間)|一度|一部|一方|一般|一緒|一切|一応|一番|一定|一致|一意|一括|一本化|一日中|一年中|一日も|"
                             r"一人ひとり|一人一人|一回り|一枚岩|十分|十人十色|万一|四六時中")
_KANJI_NUMERALS = frozenset("〇一二三四五六七八九十百千")

_BUN_NOT_BEFORE = ("の一", "の二", "の三", "の四", "の五", "の六", "の七", "の八", "の九", "の十", "の百", "の千",
                   "率", "位", "五分", "九厘")

_NIBUN_NOT_BEFORE = ("し", "す", "さ", "化")

_JUNIBUN_NOT_BEFORE = ("に", "な")

_JOU_NOT_BEFORE = ("の光", "の煙")

_KANJI_RANGE_HEAD = re.compile(r"(?<![〇一二三四五六七八九十百千])([〇一二三四五六七八九十百千]+)"
                               r"(?:[ \t]*(?:[~\u301c]|から)[ \t]*|[、・])$")
_KANJI_RANGE_REACH = 16

_NOTATION_JOIN = re.compile(r"[ \t]*(?:[~\u301c]|から)[ \t]*|[-/:\u2010-\u2013\u2212]")

_JOIN_RANGE = re.compile(r"[~\u301c]|から")

_NOTATION_SPACE = re.compile(r"[ \t]+")

_WEAK_ONE_AFTER = ("ひとつ", "一つ", "1つ")
_WEAK_ONE_BEFORE = "もう"
_WEAK_ONE_REPEATED = ("一つ", "1つ")
_WEAK_ONE_MO = re.compile(r"も(?!ら|しく|って)(?=[^。！？!?\n]*?(?:な[いくかしけ]|ません|ず|ぬ|無))")

_WEAK_ONE_PAIRED = ("の", "ずつ")
_WEAK_ONE_ONLY = "のみ"
_WEAK_SINGLE = "single"
_WEAK_EACH = "each"

_KANA_NUMBERS = {"ひとつ": ("1", "つ"), "ふたつ": ("2", "つ"), "みっつ": ("3", "つ"), "よっつ": ("4", "つ"),
                 "いつつ": ("5", "つ"), "むっつ": ("6", "つ"), "ななつ": ("7", "つ"), "やっつ": ("8", "つ"),
                 "ここのつ": ("9", "つ"), "ひとり": ("1", "人"), "ふたり": ("2", "人")}
_KANA_NUMBER = re.compile("ここのつ|ひとつ|ふたつ|みっつ|よっつ|いつつ|むっつ|ななつ|やっつ|ひとり|ふたり")
_KANA_NUMBER_NOT_NEXT = re.compile("まみ|かみ|ぶ(?!ん)|ながり|づき|き(?!り)|でに|ごと|よがり|け|り")
_KANA_NUMBER_NEXT_STRICT = ("の", "を", "が", "は", "も", "に", "で", "と", "だ", "め", "ずつ", "しか", "ほど", "まで", "くらい",
                            "ぐらい", "さえ", "こそ", "じゃ", "あ")
_KANA_NUMBER_STRICT = frozenset(("いつつ", "ここのつ"))
_KANA_NUMBER_NOT_KANJI_NEXT = {"ひとり": "言"}
_KANA_NUMBER_BEFORE = frozenset("をがはもにでとのやへ")
_KANA_NUMBER_KATAKANA = re.compile(r"[ァ-ヴー]")
_HIRAGANA_CHAR = re.compile(r"[ぁ-ゖ]")
_KANA_ONLY = "のみ"

_LIST_NUMBER = re.compile(r"^[ \t]*(?:>[ \t]*)*(?:[0-9]{1,9}[.)](?=[ \t]|$)|\([0-9]{1,9}\))", re.M)

_NUMBER_MASKED = ("code", "inline_code", "autolink", "bare_url", "link_destination", "frontmatter", "html_block",
                  "html_token", "reference_definition", "image")

def _image_path_start(text, left, right):
    middle = text.find("](", left, right)
    return right if middle < 0 else middle + 2

class _Number(tuple):
    __slots__ = ()

    def __new__(cls, start, end, value, unit, notation=None, weak=False, cluster=None):
        return tuple.__new__(cls, (start, end, value, unit, notation, weak, cluster))

    start = property(lambda self: self[0])
    end = property(lambda self: self[1])
    value = property(lambda self: self[2])
    unit = property(lambda self: self[3])
    key = property(lambda self: (self[2], self[3]))
    notation = property(lambda self: self[4])
    weak = property(lambda self: self[5])
    cluster = property(lambda self: self[6])

def _plain_number(digits):
    whole, dot, fraction = digits.partition(".")
    whole = whole.lstrip("0") or "0"
    return whole + dot + fraction

def _kanji_value(text):
    if not any(ch in _KANJI_UNITS for ch in text):
        return int("".join(str(_KANJI_DIGITS[ch]) for ch in text))
    total, current, last = 0, None, 10000
    for ch in text:
        if ch in _KANJI_UNITS:
            unit = _KANJI_UNITS[ch]
            if unit >= last:
                return None
            total += (1 if current is None else current) * unit
            current, last = None, unit
        else:
            if current is not None or ch == "〇":
                return None
            current = _KANJI_DIGITS[ch]
    return total + (current or 0)

def _number_mask(text, analysis, masked_kinds=_NUMBER_MASKED):
    chars = list(text.translate(_HALF_WIDTH))
    for left, right, kind in analysis["protected_spans"]:
        if kind == "image" and kind in masked_kinds:
            left = _image_path_start(text, left, right)
        elif kind not in masked_kinds:
            continue
        for index in range(left, min(right, len(chars))):
            if chars[index] != "\n":
                chars[index] = " "
    masked = "".join(chars)
    return _LIST_NUMBER.sub(lambda match: " " * len(match.group(0)), masked)

def _find_numbers(text, analysis, masked_kinds=_NUMBER_MASKED, unit_pattern=_UNIT):
    masked = _number_mask(text, analysis, masked_kinds)
    found = []
    taken = []
    for match in _ARABIC.finditer(masked):
        digits = match.group(0)
        after = match.end()
        thousand = _THOUSAND.match(masked, after) if "," not in digits and "." not in digits else None
        if thousand is not None:
            after = thousand.end()
        unit = unit_pattern.match(masked, after)
        if unit is None:
            emphasis = _EMPHASIS.match(masked, after)
            if emphasis is not None:
                unit = unit_pattern.match(masked, emphasis.end())
        if unit is None and thousand is None:
            unit = _SPACED_UNIT.match(masked, after)
        if unit is None and thousand is None:
            unit = _LETTER_UNIT.match(masked, after)
        unit_text = (unit.group(unit.lastindex) if unit.lastindex else unit.group(0)) if unit else ""
        follow = unit.end() if unit else after
        if thousand is not None:
            taken.append((match.start(), follow))
            found.append(_Number(match.start(), follow, str(int(digits) * 1000), _SAME_UNIT.get(unit_text, unit_text)))
            continue
        if "," in digits and not _THOUSANDS.fullmatch(digits):
            pieces, offset = digits.split(","), match.start()
            for index, piece in enumerate(pieces):
                last = index == len(pieces) - 1
                end = follow if last else offset + len(piece)
                found.append(_Number(offset, end, _plain_number(piece), _SAME_UNIT.get(unit_text, unit_text) if last else ""))
                offset += len(piece) + 1
            continue
        found.append(_Number(match.start(), follow, _plain_number(digits.replace(",", "")),
                             _SAME_UNIT.get(unit_text, unit_text)))
    kanji_text = _KANJI_EXCLUDED.sub(_kanji_excluded, masked)
    for match in _KANJI_NUMBER.finditer(kanji_text):
        if not _kanji_before_ok(kanji_text, match.start()) and not (
                match.group(2) == "時" and _hour_word_before(kanji_text, match.start())):
            continue
        if any(left <= match.start() < right for left, right in taken):
            continue
        value = _kanji_value(match.group(1))
        if value is None:
            continue
        counter = match.group(2)
        idiom = value == 1 and _whole_period(kanji_text, match.start(), counter)
        if counter == "分":
            word = match.group(0)
            idiom = (kanji_text.startswith(_BUN_NOT_BEFORE, match.end())
                     or (word == "二分" and kanji_text.startswith(_NIBUN_NOT_BEFORE, match.end()))
                     or (word == "十二分" and kanji_text.startswith(_JUNIBUN_NOT_BEFORE, match.end()))
                     or (word == "五分" and kanji_text.endswith("五分", 0, match.start())))
        elif counter == "条":
            idiom = kanji_text.startswith(_JOU_NOT_BEFORE, match.end())
        head = _KANJI_RANGE_HEAD.search(kanji_text, max(0, match.start() - _KANJI_RANGE_REACH), match.start())
        if head is not None and _kanji_head_ok(kanji_text, head, taken, found):
            found.append(_Number(head.start(1), head.end(1), str(_kanji_value(head.group(1))), ""))
        found.append(_Number(match.start(), match.end(), str(value), _SAME_UNIT.get(counter, counter), None, idiom))
    for match in _KANA_NUMBER.finditer(kanji_text):
        if _kana_number_ok(kanji_text, match):
            value, unit = _KANA_NUMBERS[match.group(0)]
            weak = not kanji_text.startswith(_KANA_ONLY, match.end())
            found.append(_Number(match.start(), match.end(), value, unit, None, weak))
    found.sort(key=lambda number: (number.start, number.end))
    return _with_notation(masked, found)

def _kana_number_ok(text, match):
    word, end = match.group(0), match.end()
    strict = word in _KANA_NUMBER_STRICT
    if strict and match.start():
        before = text[match.start() - 1]
        if _KANJI.match(before) or _KANA_NUMBER_KATAKANA.match(before) or (
                _HIRAGANA_CHAR.match(before) and before not in _KANA_NUMBER_BEFORE):
            return False
    if word == "いつつ" and match.start() and text[match.start() - 1] in "にで" and (
            end == len(text) or text[end] == "も" or not _HIRAGANA_CHAR.match(text[end])):
        return False
    if end < len(text) and text[end] == _KANA_NUMBER_NOT_KANJI_NEXT.get(word):
        return False
    if end == len(text) or not _HIRAGANA_CHAR.match(text[end]):
        return True
    if _KANA_NUMBER_NOT_NEXT.match(text, end) is not None:
        return False
    return not strict or text.startswith(_KANA_NUMBER_NEXT_STRICT, end)

def _kanji_head_ok(kanji_text, head, taken, found):
    start = head.start(1)
    if not _kanji_before_ok(kanji_text, start):
        return False
    if any(left <= start < right for left, right in taken):
        return False
    if any(number.start <= start < number.end for number in found):
        return False
    return _kanji_value(head.group(1)) is not None

def _kanji_before_ok(kanji_text, start):
    before = kanji_text[start - 1] if start else ""
    if not before or not _KANJI.match(before) or before in _KANJI_BEFORE:
        return True
    if kanji_text[max(0, start - 2):start] in _KANJI_BEFORE_WORDS:
        return True
    return _KANJI_CHAIN.search(kanji_text, max(0, start - _KANJI_CHAIN_REACH), start) is not None

def _whole_period(kanji_text, start, counter):
    if not start or counter not in _SAME_PERIOD.get(kanji_text[start - 1], ()):
        return False
    if kanji_text[max(0, start - 2):start] in _WHOLE_PERIOD_WORDS:
        return True
    return counter in ("日", "年") and (start < 2 or not _KANJI.match(kanji_text[start - 2]))

def _kanji_excluded(match):
    text = match.group(0)
    if text == "十分":
        start = match.start()
        if (start and match.string[start - 1] in _KANJI_NUMERALS) or (match.string.startswith("間", match.end())
                                                                       and not match.string.startswith("間に合", match.end())):
            return text
        hour = _KANJI_HOUR_BEFORE.search(match.string, max(0, start - _KANJI_CHAIN_REACH), start)
        if hour is not None:
            end = match.end()
            if hour.group(1) is None and hour.group(2) is None:
                if (hour.group(0) != "一時" or _hour_word_before(match.string, hour.start())
                        or match.string.startswith(_ICHIJI_JIPPUN_AFTER, end)):
                    return text
            elif (end == len(match.string) or match.string.startswith(_JIPPUN_AFTER, end)
                  or (match.string.startswith(_JIPPUN_DE, end) and not match.string.startswith(_JIPPUN_DE_NOT, end))):
                return text
    if text == "一時" and match.start() and (
            match.string[match.start() - 1] in _KANJI_NUMERALS
            or (_hour_word_before(match.string, match.start())
                and (match.end() == len(match.string) or not _KANJI.match(match.string[match.end()])
                     or match.string[match.end()] in _ICHIJI_HOUR_NEXT))):
        return text
    return "＃" * len(text)

def _hour_word_before(text, start):
    return text[max(0, start - 2):start] in _TIME_OF_DAY_WORDS or (start > 0 and text[start - 1] in _TIME_OF_DAY_CHARS)

def _join_kind(between):
    if not between:
        return "adjacent"
    if _JOIN_RANGE.search(between):
        return "range"
    if ":" in between:
        return "colon"
    if "/" in between:
        return "slash"
    return "dash"

def _with_notation(masked, found):
    groups = list(range(len(found)))
    joins = {}
    for index in range(1, len(found)):
        between = masked[found[index - 1].end:found[index].start]
        if "\n" not in between and (not between or _NOTATION_JOIN.fullmatch(between)):
            groups[index] = groups[index - 1]
            joins.setdefault(groups[index], []).append(_join_kind(between))
    members = {}
    for index, number in enumerate(found):
        members.setdefault(groups[index], []).append(number)
    out = []
    for index, number in enumerate(found):
        cluster = members[groups[index]]
        keys = tuple(member.key for member in cluster) if len(cluster) > 1 else None
        notation, weak = None, number.weak
        if not number.unit:
            group = tuple(member.value for member in cluster if not member.unit) if keys else ()
            space = _NOTATION_SPACE.match(masked, number.end)
            follow = masked[space.end():space.end() + 8].split("\n", 1)[0] if space else ""
            if group or follow:
                frame = None
                if group:
                    frame = (tuple(joins.get(groups[index], ())), tuple(member.unit for member in cluster),
                             next(at for at, member in enumerate(cluster) if member is number))
                notation = (group, follow, frame)
        elif number.key == ("1", "つ"):
            if (masked.startswith(_WEAK_ONE_AFTER, number.end) or _WEAK_ONE_MO.match(masked, number.end) is not None
                    or masked[max(0, number.start - 2):number.start] in _WEAK_ONE_REPEATED
                    or masked[max(0, number.start - len(_WEAK_ONE_BEFORE)):number.start] == _WEAK_ONE_BEFORE):
                weak = True
            elif (masked.startswith(_WEAK_ONE_PAIRED, number.end)
                  and not masked.startswith(_WEAK_ONE_ONLY, number.end)):
                weak = _WEAK_EACH if masked.startswith("ずつ", number.end) else _WEAK_SINGLE
        out.append(_Number(number.start, number.end, number.value, number.unit, notation, weak, keys)
                   if notation is not None or weak or keys else number)
    return out

class _KeySet(object):

    def __init__(self, numbers):
        self.keys = set()
        self.units = {}
        self.clusters = {}
        for number in numbers:
            self.keys.add(number.key)
            self.units.setdefault(number.value, set()).add(number.unit)
            if number.cluster is not None:
                self.clusters.setdefault(number.value, set()).add(number.cluster)
        for value, found in self.clusters.items():
            self.clusters[value] = sorted(found)
