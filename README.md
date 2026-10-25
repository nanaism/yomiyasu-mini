<p align="center"><img src="./assets/yomiyasu-mini.png" alt="yomiyasu-mini logo" width="600"></p>

# yomiyasu mini（よみやす みに）

## これは何？

yomiyasu-mini は、AIが書いた日本語を推敲するスキル [yomiyasu](https://github.com/nanaism/yomiyasu)（以下「本体」）を、スキルの大きさに上限がある環境に入るように短くしたスキルです。本体 v2.2.2 から、抽出表と生成のスクリプトで作っています。

意味を守る決まりは SKILL.md の本文に置き、細部と事例は2つの参照ファイルに移しました。意味が変わる恐れを数える検査は、本体の `yomiyasu_diff.py` と `markdown_visibility.py` から要る定義だけを取り出したスクリプトで行います。

**使うのは [`skills/yomiyasu-mini/`](./skills/yomiyasu-mini/) の8つのファイルだけです。** このリポジトリのほかのファイルは、本体から作り直したり、本体と比べて測ったりするためのものです。

| ファイル・フォルダ | 中身 |
|---|---|
| `skills/yomiyasu-mini/SKILL.md` | スキルの本文（先頭の YAML を含めて17,668字） |
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

本体は42,982字の SKILL.md（v2.2.2）と参照ファイル、検査のための Python スクリプトでできています。スクリプトのうち lint、diff、check は、どれも1本で100KBを超えます。

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
python3 tools/build_zip.py --out dist/yomiyasu-mini-1.0.0.zip
```

`.zip` の中身は `yomiyasu-mini/` フォルダの下の8つのファイルです。`build_zip.py` は作る前と作ったあとに上の上限を確かめ、超えていれば何も書かずに止まります。同じ中身からは、いつ作っても同じバイトの `.zip` ができます。

### スキルのフォルダとして置く

`skills/yomiyasu-mini/` を、使うツールがスキルを読むフォルダに写します。測定では Codex CLI の作業フォルダの `.agents/skills/yomiyasu-mini/` に置きました。

### 頼み方

名前を出して頼みます（「yomiyasu-mini で推敲して」「$yomiyasu-mini」など）。SKILL.md の description には、名前を出さずに文章を書かせる依頼では使わないと書いています。

SKILL.md では、出力の形の指定がなければ、書き直した本文、変えたところ、確認の記録を返すように決めています。残したAIっぽいところと書き手に確かめたい点の欄は、あるときだけ付けます。確認の記録には、検査のスクリプトが出した状態の行をそのまま写します。測定（Codex CLI）では、mini の51本の返事のすべてにこの行がありました。

```text
yomiyasu-mini-check: ran version=1.0.0 base=v2.2.2@488dd37 meaning_risk=0 counted=0
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

本体から外したのは、おもに mini にない道具に関わる手順と出力の欄です。lint の規則の名前、diff の文体の硬化と勢いの検査、check の実行の記録、資料から事実を補う手順と「事実の確かめ」の欄、lint が読む語のファイル（`references/lists/`）、Step 5「提出の前の照合」がこれに当たります。ほかに、本体の「情報の不増補」の、相対の日付に日付を添える段落を入れていません。参照ファイルのうち、slop-catalog.md の3章（lint の語彙と同じ一覧）、gemini-syntax.md の調査の節と原則2〜14（SKILL.md や写した節と重なる）、persona.md と audience.md の一部の章（読む場面と決め方、読者像、例など）も写していません。部品ごとの扱いと理由は [extract/NOTES-content.md](./extract/NOTES-content.md) の8章と、[extract/table.json](./extract/table.json) の各部品の `note` にあります。

## 測った結果

本体 v2.2.2 の `tests/corpus/` の51本（`raw_ai/` 26本、`blacklist_ai/` 24本、`edge_cases/` 1本）を、本体 v2.2.2 と mini で1回ずつ推敲させました。推敲させたのは Codex CLI 0.163.0 の gpt-6-astra で、effort は high です。本体と mini で同じモデルと設定を使いました。意味が変わる恐れは本体 v2.2.2 の `yomiyasu_diff.py --fail-on meaning-risk` で、残った候補は `yomiyasu_lint.py` で数えました。

| | 本体 | mini |
|---|---|---|
| 意味が変わる恐れ（51本） | 2 | 4 |
| 書き直した文に残った warn 以上の候補（元の文では30） | 23 | 22 |
| 書き換えた量の中央値（元の文の空白を除く1,000字あたりの字数） | 21.9 | 28.0 |
| 入力トークンの中央値（1本） | 414,510 | 324,740 |

mini の意味が変わる恐れは、本体より2件多く出ました。4件のうち2件は、本体も同じ文を同じように書き直したものです。mini にだけ出た2件は1件ずつ読みました。1件は「BFFを1枚挟む」を「BFFを1層設ける」にしたもので、数は同じで、意味は変わっていません。もう1件は、提案の文末「…見えないようにします」を「…見えないようにしてください」にしたもので、言い切りの強さが1段上がっています。本体は同じ文を「…ようにしましょう」にしていました。

この51本は、測るつもりだった115本のうち、途中で止めるまでに終わった分です。測ったのは各原稿1回ずつの結果です。規則を外した写しを比べる測定は回していないので、測った数字で外した規則はありません。測り方と1件ずつの読みは [measurement/README.md](./measurement/README.md) に、1本ごとの数は [measurement/results.json](./measurement/results.json) にあります。

## 本体との違い

| | yomiyasu-mini | yomiyasu（本体） |
|---|---|---|
| SKILL.md | 17,668字 | 42,982字（v2.2.2） |
| 参照ファイル | 2本（規則と事例、文書の種類と読者） | 種類ごと、分野ごとに分かれた参照ファイルと、lint が読む語のファイル |
| 検査 | 意味が変わる恐れ（本体の diff と同じ結果） | lint（AIらしい言い回しの候補）、diff、最終稿の照合と記録 |
| 状態の行 | `yomiyasu-mini-check: ran …` | `yomiyasu-check: executed …` |

mini の検査は、本体の diff が出す意味が変わる恐れ（`meaning_risks`）を、本体と同じ結果で出します。本体の `tests/corpus/` の48組と、本体の試験から集めた3,919の入力で、本体 v2.2.2 の `yomiyasu_diff.py` と同じ結果になることを試験で確かめています。

mini には lint がありません。AIらしい言い回しや直訳語、プロジェクトの語の一覧（`.yomiyasu-words/` の `allow.txt` と `flag.txt`）の語が残っていないかは、モデルが文を読んで確かめるように SKILL.md で決めています。本体の check の実行の記録（run と verify）もないので、mini の状態の行は本体と別の形にしています。

## どちらを使えばいいか

本体を読み込める環境なら、本体をおすすめします。

mini は、スキルの大きさに上限があって本体を入れられないときに使ってください。

## 作り直すとき

本体のバージョンが上がったら、次の手順で mini を作り直せます。抽出表 `extract/table.json` と `extract/scripts.json` は、本体のファイルの場所と見出し、関数の名前で節を指し、節ごとに中身の sha256 を持っています。生成に使うのは Python 3.9 以上の標準ライブラリだけです。

1. 本体の新しい版のタグを `_main/` に取り出します（下の例は v2.2.2 です）。

   ```bash
   git clone --depth 1 --branch v2.2.2 https://github.com/nanaism/yomiyasu _main
   ```

2. 本体のバージョンが変わったら、`extract/table.json` と `extract/scripts.json` の `source`（tag と commit）を書き直します。`.github/workflows/ci.yml` の `ref` と、試験用の抽出表 `tests/fixtures/basic/extract/table.json` と `scripts.json` の `source` も同じ値にします。中身が変わったときは、mini 自身の版（`version`）も上げてください。
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
