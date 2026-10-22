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
