# yomiyasu-mini 1.0.0。nanaism/yomiyasu v2.1.3（c09270bc93daab14e253fb3ef406182011b79ccb）から tools/generate.py で生成した。手で直さない。
# 取り出した名前と中身の sha256 は extract/scripts.json と MANIFEST.json にある。
"""試験用の部品。mini_check.py から読む。"""

__version__ = "1.0.0"
SOURCE_TAG = "v2.1.3"
SOURCE_COMMIT = "c09270bc93daab14e253fb3ef406182011b79ccb"

import re

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

_HALF_WIDTH = dict((code, code - 0xFEE0) for code in range(0xFF01, 0xFF5F))
_HALF_WIDTH[0x3000] = 0x20
