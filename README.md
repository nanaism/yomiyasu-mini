<p align="center"><img src="./assets/yomiyasu-mini.png" alt="yomiyasu-mini logo" width="600"></p>

# yomiyasu mini（よみやす みに）

## これは何？

yomiyasu-mini は、AIが書いた日本語を推敲するスキル [yomiyasu](https://github.com/nanaism/yomiyasu)（以下「本体」）を、スキルの大きさに上限がある環境に入るように短くしたスキルです。本体 v2.5.0 から、抽出表と生成のスクリプトで作っています。

意味を守る決まりは SKILL.md の本文に置き、細部と事例は2つの参照ファイルに移しました。意味が変わる恐れを数える検査は、本体の `yomiyasu_diff.py` と `markdown_visibility.py` から要る定義だけを取り出したスクリプトで行います。

**使うのは [`skills/yomiyasu-mini/`](./skills/yomiyasu-mini/) の8つのファイルだけです。** このリポジトリのほかのファイルは、本体から作り直したり、本体と比べて測ったりするためのものです。

| ファイル・フォルダ | 中身 |
|---|---|
| `skills/yomiyasu-mini/SKILL.md` | スキルの本文（先頭の YAML を含めて17,959字） |
| `skills/yomiyasu-mini/references/` | `rules.md`（規則の細部と事例）と `doc-types.md`（文書の種類、分野、読者、書き手と読み手、文書の立場と文末） |
| `skills/yomiyasu-mini/scripts/` | 検査の `mini_check.py` と、本体の diff から取り出した `mini_diff_1.py`〜`mini_diff_3.py` |
| `skills/yomiyasu-mini/LICENSE.txt` | MIT ライセンス |
| `extract/`、`tools/`、`MANIFEST.json` | 本体から作り直すための抽出表、生成と `.zip` のスクリプト、生成の記録 |
| `measurement/` | 本体と比べて測った結果 |
| `tests/` | 生成、上限、本体との一致の試験 |

## こんなときに

スキルを読み込めるのに、SKILL.md の字数やファイルの数、1ファイルの大きさに上限があって、本体を入れられない環境のためのものです。

たとえば Microsoft 365 Copilot の宣言型エージェントのカスタムスキルについては、[Microsoft の文書](https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/declarative-agent-skills)に次のことが書かれています。

- SKILL.md の指示は2万字未満
- Agent Builder に上げる `.zip` は50MBまで、1ファイルは25MBまで
- ファイルはすべてのスキルを合わせて350個まで、フォルダの深さは3まで
- スクリプトはネットワークにつながらない場所で動き、パッケージを入れられない

mini は SKILL.md を先頭の YAML を含めて18,000字以下、スクリプトを1本90KB以下、参照ファイルを1本100KB以下にし、標準ライブラリだけで動くようにしています。配るファイルは8個で、`.zip` の中のパスは `yomiyasu-mini/references/rules.md` のように、先頭のフォルダとファイル名を含めて3段までです。これらの上限は生成のたびに試験で確かめています。

## なぜ作ったか

本体は46,311字の SKILL.md（v2.5.0）と参照ファイル、検査のための Python スクリプトでできています。スクリプトのうち lint、diff、check は、どれも1本で100KBを超えます。

Copilot の Agent Builder で、v2.0.0 から v2.1.0 までの本体を読み込めなかったという報告が、複数の利用者からありました。別の利用者からは、Copilot のほかのアプリで、ファイルの数やスクリプト1本の大きさで引っかかったという報告がありました。

本体は、以前に短くしたとき、推敲の質が落ち、意味を変える書き直しが戻ってきたことがあります。そのため本体は削らず、別のものとして mini を作りました。

## 使い方

### Agent Builder に上げる `.zip` を作る

```bash
git clone https://github.com/nanaism/yomiyasu-mini
```

```bash
cd yomiyasu-mini
```

```bash
python3 tools/build_zip.py --out dist/yomiyasu-mini-1.2.0.zip
```

`.zip` の中身は `yomiyasu-mini/` フォルダの下の8つのファイルです。`build_zip.py` は作る前と作ったあとに上の上限を確かめ、超えていれば何も書かずに止まります。同じ中身からは、いつ作っても同じバイトの `.zip` ができます。

### スキルのフォルダとして置く

`skills/yomiyasu-mini/` を、使うツールがスキルを読むフォルダに写します。測定では Claude Code の作業フォルダの `.claude/skills/yomiyasu-mini/` に置きました。

### 頼み方

名前を出して頼みます（「yomiyasu-mini で推敲して」「$yomiyasu-mini」など）。SKILL.md の description には、名前を出さずに文章を書かせる依頼では使わないと書いています。

SKILL.md では、出力の形の指定がなければ、書き直した本文、変えたところ、確認の記録を返すように決めています。残したAIっぽいところと書き手に確かめたい点の欄は、あるときだけ付けます。確認の記録には、検査のスクリプトが出した状態の行をそのまま写します。測定（Claude Code）では、mini の153回の返事のすべてにこの行がありました。

```text
yomiyasu-mini-check: ran version=1.2.0 base=v2.5.0@29d67cc meaning_risk=0 counted=0
```

`ran` は検査を最後まで実行したこと、`meaning_risk` は意味が変わる恐れの件数、`counted` はそのうち本体の `--fail-on meaning-risk` が数える件数です。Python がないときは `not_run reason=no_python`、実行を断られたときは `not_run reason=not_allowed` と書き、検査をしたとは書かないように決めています。

検査のスクリプトだけを動かすこともできます。

```bash
python3 skills/yomiyasu-mini/scripts/mini_check.py --source 原文.md --final 最終稿.md
```

## 入れた決まり

SKILL.md は本体と同じ「基本原則」「実行手順」「出力フォーマット」の3つの章でできています。

- 意味の保持、情報が足りないときの暫定文、専門用語と名称の扱い、言い直しテストの決まりは、参照ファイルを読めないときも SKILL.md だけで意味を守れるように、本体の文をそのまま SKILL.md に写しています。置き換えたのは、mini にない道具やファイルを指す句だけです。
- 情報を足さないことは、本体の節の最初の2段落をそのまま写し、AIへの指示が本文に残った文の段落は短く書き直しています（全文は `references/rules.md`）。
- 言い切りの強さを上げないことと、条件・否定・因果・時系列を保つことは、本体の節から短く書き直して SKILL.md に入れています。
- 比喩、主語と目的語、AIらしい言い回し、文の長さ、見出し、装飾などの節は、短く書き直して SKILL.md に置き、SKILL.md に入らなかった文と事例を `references/rules.md` に写しています。
- 文書の種類ごと（13種類）、分野ごと、読者、書き手と読み手の扱いは、`references/doc-types.md` に写しています。
- 英語の短い術語に当てた漢字1字の名詞（版、頭、印）を含む直訳語の4つの型を SKILL.md に入れ、細部と事例を `references/rules.md` に写しています。他動詞を1語だけ名詞にして「の」で受ける形（「結果の確かめ」）の段落は `references/rules.md` に写し、SKILL.md には直し方を述べる1文だけを置いています。スライドの見出しと1行の箇条で間を作るだけの読点を外す決まりと、スライドの前後に付いた依頼者あての前置きや注記を残す決まりは、`references/doc-types.md` のスライドの節に写しています。
- 本体 v2.5.0 で足された決まりのうち、コードやシステムを説明する文書の擬人化（コードや資料から動作が分かるときだけ書き直し、分からなければ残して尋ねる）、否定で終わる定義文（何であるかを先に書く）、漢語の名詞で動作を省いた文（資料から動作が分かるときだけ動作の文にする）、依頼で指定された見出しの形とまとめを保つこと、推敲で新しく置く読点を残す読点の所だけにすることは、SKILL.md にそれぞれ短い文で入れ、本体の段落の全文を `references/rules.md` に写しています。Step 4 の目で見る点検には、原文より増えた読点が残す読点に当たるかを足しました。本文に測定値を詰め込んだ文を表か箇条書きに分けるかを確かめる決まりは、`references/doc-types.md` の技術記事の分野の節に写しています。

本体から外したのは、おもに mini にない道具に関わる手順と出力の欄です。lint の規則の名前、diff の文体の硬化と勢いの検査、diff の「原文にない人や担当を足した文」の候補、check の実行の記録、資料から事実を補う手順と「事実の確かめ」の欄、lint が読む語のファイル（`references/lists/`）、Step 5「提出の前の照合」がこれに当たります。ほかに、本体の「情報の不増補」の、相対の日付に日付を添える段落を入れていません。参照ファイルのうち、slop-catalog.md の3章（lint の語彙と同じ一覧）、gemini-syntax.md の調査の節と原則2〜14（SKILL.md や写した節と重なる）、persona.md と audience.md の一部の章（読む場面と決め方、読者像、例など）も写していません。本体 v2.5.0 で足されたもののうち、lint の変更（AI の文章によく出る言い回しの規則、直訳語の型1と型3、比喩の「効く」、短い目的語の「を、」の読点）と、lint が候補に出す言い回しの扱いを並べた slop-catalog.md の10章は、mini に lint がないので入れていません。diff と check の、見出しの形が変わった所と読点が増えた推敲を示す節も入れていません。検査のスクリプトの4本が上限の近くまで詰まっていて、入れるとスクリプトがもう1本要り、配るファイルが8つを超えるためです。本体の検査のスクリプトの呼び出し方の決まり（`python3`、`python`、`py -3` の順に試すこと）と、SKILL.md の `allowed-tools` も、mini はスクリプトの名前と呼び方が本体と違うので入れていません。audience.md の11章（読者像）に足された初心者向けの口調の項目は、参照ファイルの上限（100KB）に入らないので写していません。参照ファイルを上限に収めるために、SKILL.md や rules.md のほかの節と同じ中身の段落と行、言い直しテストの否定対比の節にある mini_check が出す形と出さない形の細部、同じ型の例が残る表の行を外しました。部品ごとの扱いと理由は [extract/NOTES-content.md](./extract/NOTES-content.md) の8章と、[extract/table.json](./extract/table.json) の各部品の `note` にあります。

## 測った結果

本体 v2.5.0 の `tests/corpus/` の51本（`raw_ai/` 26本、`blacklist_ai/` 24本、`edge_cases/` 1本。mini 1.1.0 の測定と同じ51本）を、本体 v2.5.0 と mini で3回ずつ推敲させました。推敲させたのは Claude Code の claude-opus-5-5 で、effort は high です。本体と mini で同じモデルと設定を使いました。意味が変わる恐れは本体 v2.5.0 の `yomiyasu_diff.py --fail-on meaning-risk` で、残った候補は `yomiyasu_lint.py` で数えました。

| | 本体 | mini |
|---|---|---|
| 意味が変わる恐れ（`--fail-on meaning-risk` が数える件数。51本×3回の合計） | 3 | 2 |
| 意味が変わる恐れ（1回目・2回目・3回目） | 2・1・0 | 1・1・0 |
| 書き直した文に残った warn 以上の候補（1回目・2回目・3回目。元の文では30） | 22・21・22 | 22・22・23 |
| 書き換えた量の中央値（元の文の空白を除く1,000字あたりの字数。1回目・2回目・3回目） | 13.3・13.6・13.7 | 13.6・25.6・18.1 |
| 入力トークンの中央値（1本） | 277,827 | 123,589 |

測る前に決めた合格の条件は、mini の3回の合計が、同じ51本の本体の3回の合計を超えないことです。mini は2件で、本体の3件を超えていないので、この条件を満たしています。

mini の2件を1件ずつ読みました。1件は「外部APIの仕様変更やスキーマ変更が、業務ロジックの修正を伴う」を「外部APIの仕様やスキーマを変更すると業務ロジックも修正が必要になる」にした文です。変更があれば修正も要るという関係は同じですが、事実を述べる「伴う」が、必要を述べる「必要になる」に変わっています。もう1件は「1メソッド」を「1つのメソッド」にした文で、意味は変わっていません。本体の3件は提案の文末の「〜ようにします」を「〜ようにしてください」にした文（2回）と、「お願いしたいことは3点あります。」を「次の3点をお願いします。」にした文です。

測り方と1件ずつの読みは [measurement/README.md](./measurement/README.md) に、1本ごとの数は [measurement/results.json](./measurement/results.json) にあります。本体 v2.4.0 から作った mini 1.1.0 の測定は [measurement/v2.4.0/README.md](./measurement/v2.4.0/README.md) に、本体 v2.2.2 から作った mini 1.0.0 の測定は [measurement/v2.2.2/README.md](./measurement/v2.2.2/README.md) にあります。

## 本体との違い

| | yomiyasu-mini | yomiyasu（本体） |
|---|---|---|
| SKILL.md | 17,959字 | 46,311字（v2.5.0） |
| 参照ファイル | 2本（規則と事例、文書の種類と読者） | 種類ごと、分野ごとに分かれた参照ファイルと、lint が読む語のファイル |
| 検査 | 意味が変わる恐れ（本体の diff と同じ結果） | lint（AIらしい言い回しの候補）、diff、最終稿の照合と記録 |
| 状態の行 | `yomiyasu-mini-check: ran …` | `yomiyasu-check: executed …` |

mini の検査は、本体の diff が出す意味が変わる恐れ（`meaning_risks`）を、本体と同じ結果で出します。本体の `tests/corpus/` の48組と、本体の試験から集めた4,153の入力で、本体 v2.5.0 の `yomiyasu_diff.py` と同じ結果になることを試験で確かめています。

mini には lint がありません。AIらしい言い回しや直訳語、プロジェクトの語の一覧（`.yomiyasu-words/` の `allow.txt` と `flag.txt`）の語が残っていないかは、モデルが文を読んで確かめるように SKILL.md で決めています。本体の check の実行の記録（run と verify）もないので、mini の状態の行は本体と別の形にしています。

## どちらを使えばいいか

本体を読み込める環境なら、本体をおすすめします。

mini は、スキルの大きさに上限があって本体を入れられないときに使ってください。

## 作り直すとき

本体のバージョンが上がったら、次の手順で mini を作り直せます。抽出表 `extract/table.json` と `extract/scripts.json` は本体のファイルの場所と見出し、関数の名前で節を指し、節ごとに中身の sha256 を持っています。生成に使うのは Python 3.9 以上の標準ライブラリだけです。

1. 本体の新しいバージョンのタグを `_main/` に取り出します（下の例は v2.5.0 です）。

   ```bash
   git clone --depth 1 --branch v2.5.0 https://github.com/nanaism/yomiyasu _main
   ```

2. 本体のバージョンが変わったら、`extract/table.json` と `extract/scripts.json` の `source`（tag と commit）を書き直します。`.github/workflows/ci.yml` の `ref` と、試験用の抽出表 `tests/fixtures/basic/extract/table.json` と `scripts.json` の `source` も同じ値にします。中身が変わったときは、mini 自身のバージョン（`version`）も上げてください。
3. 生成します。

   ```bash
   python3 tools/generate.py --source _main
   ```

   - 終了コード 2: 抽出表が指す見出しや関数が本体にない、置き換えの回数が違う、参照が切れている、上限を超えた、などのときに、何も書かずに止まります。抽出表を直します。
   - 終了コード 3: 中身が変わった節を「見直しが要る節」として出し、何も書かずに止まります。その節を読んで部品を見直し、`--accept` を付けて作り直すと、抽出表のハッシュが書き直されます。

4. 試験用の見本を作り直します。`tests/fixtures/basic/extract/` を空のフォルダ（下の例では `fx/`）の `extract/` に写して生成し、できた `fx/skills/` と `fx/MANIFEST.json` を `tests/fixtures/basic/expected/` に、`fx/extract/` の2つの表を `tests/fixtures/basic/extract/` に写し戻します。

   ```bash
   python3 tools/generate.py --source _main --table fx/extract/table.json --out fx --accept
   ```

   ```bash
   python3 tools/build_zip.py --root fx --out fx/fixture.zip
   ```

   2つ目のコマンドが出す sha256 を、`tests/test_zip.py` の `FIXTURE_ZIP_SHA256` に書きます。
5. 確かめます。

   ```bash
   python3 tools/generate.py --source _main --check
   ```

   ```bash
   YOMIYASU_MAIN=_main python3 -m unittest discover -s tests -v
   ```

   - 終了コード 4: `--check` で、リポジトリのファイルが生成物と違います。手順3で作り直します。

`skills/yomiyasu-mini/` と `MANIFEST.json` は生成のスクリプトが書きます。手で直さないでください。

## ライセンス

MIT ライセンスです。本体の yomiyasu と同じです。
