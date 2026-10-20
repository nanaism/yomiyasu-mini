#!/usr/bin/env python3
# yomiyasu-mini 1.0.0。nanaism/yomiyasu v2.1.1（fbe02c93877d697cc53d9377b7a45dd8a1dd99b3）から tools/generate.py で生成した。手で直さない。
# 取り出した名前と中身の sha256 は extract/scripts.json と MANIFEST.json にある。
"""試験用の CLI。2つのファイルを読み、本体と同じ normalize で比べる。"""
import argparse
import sys

__version__ = "1.0.0"
SOURCE_TAG = "v2.1.1"
SOURCE_COMMIT = "fbe02c93877d697cc53d9377b7a45dd8a1dd99b3"

import importlib.util as _mini_iu
import os as _mini_os
import sys as _mini_sys


def _mini_load(name):
    """同じフォルダの部品を1回だけ読む。"""
    try:
        folder = _mini_os.path.dirname(_mini_os.path.abspath(__file__))
    except NameError:
        raise ImportError("部品の場所が分かりません（__file__ がありません）")
    key = "yomiyasu_mini_fixture_" + name
    module = _mini_sys.modules.get(key)
    if module is None:
        spec = _mini_iu.spec_from_file_location(key, _mini_os.path.join(folder, name + ".py"))
        if spec is None:
            raise ImportError("部品 {} を読めません".format(name))
        module = _mini_iu.module_from_spec(spec)
        _mini_sys.modules[key] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            del _mini_sys.modules[key]
            raise
    return module

_mini_m = _mini_load("mini_diff_1")
for _mini_n in "_HALF_WIDTH decode_source normalize".split():
    globals()[_mini_n] = getattr(_mini_m, _mini_n)
_mini_m = _mini_load("mini_diff_2")
for _mini_n in "DOC_TYPES _normalize_choice".split():
    globals()[_mini_n] = getattr(_mini_m, _mini_n)

def normalize_doc_type(value):
    return _normalize_choice("--doc-type", value, DOC_TYPES)

# Emoji facts are pinned to Unicode 18.0, not broad Unicode block membership.
# Derived from Unicode, Inc. data (copyright 1991-2026); Unicode License V3
# copyright/permission notice must accompany the installed skill and ZIP.
# Sources: Unicode 18.0 emoji-data.txt, emoji-variation-sequences.txt,
# emoji-sequences.txt. No Unicode data file/network/package is read at runtime.
_EMOJI_DATA_VERSION = "18.0"

def main(argv=None):
    parser = argparse.ArgumentParser(prog="mini_check.py", description="試験用の CLI。")
    parser.add_argument("--source", required=True, metavar="原文")
    parser.add_argument("--final", required=True, metavar="最終稿")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    texts = []
    for path in (args.source, args.final):
        with open(path, "rb") as handle:
            texts.append(normalize(decode_source(handle.read())[0]))
    same = "yes" if texts[0] == texts[1] else "no"
    print("yomiyasu-mini-check: ran version={} same={} emoji={} doc_type={}".format(
        __version__, same, _EMOJI_DATA_VERSION, normalize_doc_type("pr")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
