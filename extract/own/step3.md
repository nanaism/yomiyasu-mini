### Step 3: 検査

最終稿を原文とは別のファイルに保存し、スキルのフォルダを基準に `python3 scripts/mini_check.py --source 原文.md --final 最終稿.md` を実行します（`python3` がなければ `python`）。片方をファイルにできないときは、その側を `-` にして標準入力から渡します（両方は不可）。検査のあとに本文を1字でも変えたら、もう一度実行します。

出力の2行目と最後の行が状態の行です。`yomiyasu-mini-check: ran` は最後まで実行できたことを示し、`meaning_risk=` が意味が変わる恐れの件数です。候補は Step 4 で確かめます（0件でも、意味が保たれた証明ではありません）。`not_run reason=input` は入力の誤りなので、引数を直して1回だけやり直します。`not_run reason=check_error` は部品の欠けか壊れで、実行しなかった検査として扱います。

Python がないか実行を断られたときは、Step 4 の観点を目で点検します。これは検査ではないので、検査をしたとは書きません。状態の行には `yomiyasu-mini-check: not_run reason=no_python`（Python がない）か `reason=not_allowed`（断られた）と書きます。`ran` の行は、スクリプトが出力したものだけを写します。`yomiyasu-check:` で始まる本体の検査の行は書きません。新規作成で原文がないときは実行せず、「実行しなかった検査」に「mini_check（原文がないため）」と書きます。
