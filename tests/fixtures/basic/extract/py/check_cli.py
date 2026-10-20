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
