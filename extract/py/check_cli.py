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
