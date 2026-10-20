# スクリプトの抽出の記録（extract/scripts.json と extract/py/）

mini のスクリプトは、本体 v2.1.1（fbe02c9）の `skills/yomiyasu/scripts/yomiyasu_diff.py` と `markdown_visibility.py` から、意味が変わる恐れ（meaning_risks）の検出に要る定義だけを取り出したものです。取り出した定義は元の字のままで、docstring とコメントを落とし、続く空行を1行にまとめています。生成は `tools/generate.py` が `extract/scripts.json` を読んで行います。

## 1. 抽出表 extract/scripts.json

- 書き方は `format "yomiyasu-mini-extract-scripts"`（1つの抽出をファイルの最上位に書く形）。`version` と `source` は table.json と同じ値にする（違えば生成が止まる）。
- `modules`: `vis`（markdown_visibility.py）と `diff`（yomiyasu_diff.py）。`from_modules` は、diff が vis から読み込む8つの名前（本体の try の中の from … import と同じ）。
- `roots`: 閉包の根の名前16個。meaning_risks のための12個（full_diff、_sentence_pairs、_Sides、normalize、decode_source、normalize_doc_type、_type_changes、_ExactSequenceMatcher、_meaning_risks、meaning_risks、FAIL_ON_KINDS、fail_on_count）と、下の2章で足した4個（_MARKER_REGEXES、CONTENT、_risk_section、_rule_lines）。
- `limits`: 部品1本の取り出した文は 80,000 バイトまで（`part_body_bytes`）。頭の自前の文と CLI を足したファイルは 90,000 バイトまで（`file_bytes`）。どの部品に入れるかは、閉包を強連結成分の順に並べて前から詰めて決める（`packing "scc"`）。結果は MANIFEST.json に出る。
- `allowed_imports`: array、bisect、collections、difflib、hashlib、json、os、re、sys、types、unicodedata。
- `own`: 自前の文4つ（extract/py/）。`outputs` で、部品3本の頭に part-head と loader、mini_check.py の頭に check-head と loader、末尾に check-cli を置く。
- `names`: 閉包の名前の組618個と、それぞれの文の数と sha256。
- `watch`: 取り出さないが、変わったら見直しに出す名前2つ（diff と _rule_candidates）。check-cli がこの2つの手順を写しているため。

## 2. 「元の文にない語」「消えた語」「言い回しの種類の増減」を出すかの決め

決め: 出す。mini_check.py は、本体の diff() の meaning_risks に加えて、markers、new_words、lost_words、type_changes を、本体と同じ値で出す。

測った大きさ（docstring・コメント・空行を落としたバイト。設計の試作の数え方）:

| 足すもの | 足す大きさ | 入る名前 |
|---|---|---|
| meaning_risks だけ（もとの閉包） | 294,901 | 618定義 |
| markers、new_words、lost_words に要る名前 | 1,444 | MARKERS、_MARKER_REGEXES、CONTENT |
| 人向けの行（_risk_section） | 12,858 | _risk_line、_where、_modality_side ほか |
| 人向けの行（_rule_lines） | 2,987 | _rule_lines、bold_head、bold_lines |
| _rule_candidates をまるごと取り出す場合 | 43,375 | stance_flags、logic_points、bold_problems など78定義 |
| _hedges（出さない。下の注） | 2,001 | _hedges、_list_info |

部品への詰め方で比べた結果（1本の取り出した文を 80,000 バイトまで）:

| 案 | 取り出す文の合計 | 部品 |
|---|---|---|
| 採った案（markers、new_words、lost_words は check-cli で作る） | 312,015 | 4本（79,637 / 79,970 / 76,001 / 76,407） |
| _rule_candidates をまるごと取り出す | 353,962 | 5本。上限を 87,000 にしても5本 |

- markers、new_words、lost_words は、本体の `_rule_candidates` の「1. 種類ごとの数の増減」と「2. 元にない語・消えた語」の手順を check-cli に写して作る（約1 KB）。_rule_candidates をまるごと取り出すと、文末の立場、つながり、太字、構造の検査まで入り、4本に収まらない。
- 写した手順が本体とずれないように、`watch` に _rule_candidates と diff の sha256 を記録している。本体の版が変わってこの2つの中身が変わると、生成が見直しの一覧を出して止まる。
- 生成した4本の大きさ（v2.1.1 から生成、Python 3.9.6 と 3.14.5 で同じバイト）: mini_diff_1.py 82,175、mini_diff_2.py 82,354、mini_diff_3.py 81,272、mini_check.py 85,757（取り出した文は 79,611 / 79,618 / 78,429 / 74,360）。どれも 90,000 以下で、mini_check.py の余りは 4,243 バイト。
- 人向けの出力は、本体の `_risk_section` と `_rule_lines` をそのまま使うので、本体の diff のレポートと同じ文になる（例: 「数値が変わった（2行目）: 5日 → 10日」「■ 元の文にない語: 必須、火曜」）。`_rule_lines` は書き直した文だけを見る候補（つながり、文末の立場、太字）を出さない形（rewritten_only=False）で呼び、構造の候補は空にする。

注（_hedges を出さない理由）: 足す大きさは 2,001 バイトで入るが、次の3つの理由で出さない。
1. 本体の diff()["hedges"] には一覧の出どころ（`"list": "references/lists/hedges.txt"`）が入る。mini は references/lists/ を持たないので、同じ値にならない。
2. _hedges は _meaning_risks が途中で作る `sides.quiet_marks` を読むので、check() を meaning_risks() の呼び出しから diff() の中の手順の写しに変える必要がある。
3. SKILL.md の Step 4 はこの候補を使っていない。慎重な言い方は doc-types.md の paper の節で、目で見る観点として書いている。

## 3. Unicode のデータ由来のコード

取り出したコードに、Unicode のデータから作った表は入っていない。UNICODE-LICENSE.txt は要らない。

- 本体で Unicode のデータ由来の表は、yomiyasu_lint.py の絵文字の表（_EMOJI_DATA_VERSION とその下の表。「Derived from Unicode, Inc. data」の通知がある）だけで、lint は mini に入れていない。
- 取り出した yomiyasu_diff.py と markdown_visibility.py の定義には、この通知も、コードポイントの表を写したものもない。文字の分類は実行時に標準ライブラリの unicodedata（category、normalize）で取る。漢字の範囲の正規表現（`_K` など）と全角を半角にする対応（`_HALF_WIDTH`、0xFF01〜0xFF5E と 0x3000）は、ブロックの範囲を書いた式で、データのファイルから作った表ではない。
- そのため scripts.json の `unicode_notice` は null。

## 4. 自前の文（extract/py/）

- `part_head.py`: 部品の docstring と import。部品を読めないときは ImportError にする（_mini_on_error）。
- `loader.py`: 同じフォルダの部品を読む `_mini_load` と、名前を付け替える `_mini_bind`。
  - 場所は `__file__` の realpath から決める。スキルのフォルダをどこに写しても、作業フォルダがどこでも動く。sys.path は変えない。
  - 読み込みは compile と exec で行い、__pycache__ を作らない。
  - sys.modules の鍵は `yomiyasu_mini_<版>_<部品の名前>_<フォルダの場所と中身の sha256 の頭16桁>`。版の違う写し、中身の違う写し、別のフォルダの写しを、同じプロセスで混ぜない。同じフォルダの同じ中身は1回だけ読む（部品どうしが同じ _LAST_TYPE_RANGES を使うため）。
  - `__file__` がない実行（exec など）では「部品の場所が分かりません」の ImportError にする。
- `check_head.py`: mini_check.py の docstring、import、使い方の文、状態の行の作り方。部品を読めないときは、スクリプトとして実行していれば状態の行 `not_run reason=check_error` を出して終了コード3、モジュールとして読んでいれば ImportError。
- `check_cli.py`: `check(orig, rw, doc_type=None)` と CLI。

## 5. mini_check.py の使い方と状態の行（DECISIONS.md 4章）

- `python3 scripts/mini_check.py --source 原文.md --final 最終稿.md [--json]`。`--source=…` の形も読む。
- `--source -` か `--final -` で、片方を標準入力から読む。両方を `-` にすると入力の誤り。
- `--help`（`-h`）は使い方だけを出し、状態の行を出さずに終了コード0。
- 状態の行は、出力の2行目と最後の行に同じものを出す。
  - 実行できた: `yomiyasu-mini-check: ran version=1.0.0 base=v2.1.1@fbe02c9 meaning_risk=<件数> counted=<本体の --fail-on meaning-risk に当たる件数>`。終了コード0（恐れの件数によらない）。
  - 入力の誤り（ファイルがない、UTF-8 でない、引数が足りない、使えない引数、両方が標準入力）: `yomiyasu-mini-check: not_run reason=input`、終了コード2。
  - 部品の欠けや壊れ、検査の途中の誤り: `yomiyasu-mini-check: not_run reason=check_error`、終了コード3。
- `--json` では JSON だけを出す。`status`（ran か not_run）、`status_line`（上と同じ状態の行）、`version`、`source`（tag と commit）、`meaning_risk_count`、`counted`、`meaning_risks`、`markers`、`new_words`、`lost_words`、`type_changes`。
- 入力は本体と同じ decode_source で読む（BOM を外し、改行を LF にそろえる）。標準入力がバイト列を読めないときは文字列で読む（本体の _read_input と同じ）。
- 本体の `yomiyasu-check:` で始まる行は出さない。`--fail-on` は持たない。

## 6. 本体と同じ値かの確かめ

tests/test_parity.py が、生成した mini_check.py の `check()` と本体の `diff()` を、同じ Python で比べる。比べる値は meaning_risks、markers、new_words、lost_words、type_changes と、--fail-on に当たる件数。JSON にして（sort_keys）完全に一致することを見る。CLI（`--final -` と `--json`）の値と、状態の行と終了コードも見る。

手元での結果（v2.1.1 から生成した4本。Python 3.9.6 と 3.14.5 の両方で同じ結果）:

| 入力 | 文書の種類 | 比べた数 | 本体の恐れ | 数える恐れ | 食い違い |
|---|---|---|---|---|---|
| 本体の tests/corpus の組 | なし | 48組 | 20 | 13 | 0 |
| 本体の tests/corpus の組 | pr | 48組 | 20 | 13 | 0 |
| 本体の試験が diff() に渡した入力（36ファイル、1,312件の試験から集めた） | 試験のとおり | 3,885件 | 2,297（20種類すべて） | — | 0 |
| 手元の推敲の組（公開しない） | なし | 1,715組 | 739 | 483 | 0 |
| 手元の推敲の組（公開しない） | pr | 1,715組 | 739 | 489 | 0 |

- 48組のうち、markers が出た組は41、new_words は46、lost_words は47、type_changes は5。1,715組では markers 627組、new_words 868組、lost_words 683組、type_changes 158件。
- 3,885件の種類ごとの件数: number 663、sentence_type 280、contrast_reversal 262、number_qualifier 241、protected 138、certainty_review 100、promise_review 79、claim 69、quote 62、negation 59、feeling 58、choice 49、promise 48、modality 39、causality 33、certainty 33、modality_review 31、state 26、swap 18、citation 9。
- test_parity.py の6件は、3.9.6 と 3.14.5 のどちらでも通った（1回 約200秒。ほとんどが本体の試験を走らせて入力を集める時間）。
- 1,715組の処理時間の合計: 本体の diff() 14.6秒、mini の check() 11.6秒（3.9.6）。3.14.5 では 10.9秒と 8.9秒。

試験の回し方: `YOMIYASU_MAIN=<本体 v2.1.1 の木> python3 -B -m unittest discover -s tests -p test_parity.py`。本体の木がなければ `_main/` を見て、どちらもなければ飛ばす（YOMIYASU_REQUIRE_MAIN=1 なら失敗）。生成物がまだなければ飛ばす。本体の試験の入力を集める段は、`YOMIYASU_PARITY_HARVEST=0` で飛ばせる。集めた入力はどこにも保存しない。
