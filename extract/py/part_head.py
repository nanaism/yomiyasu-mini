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
