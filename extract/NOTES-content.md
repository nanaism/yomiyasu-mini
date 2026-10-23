# 抽出表の文書の側の決め（content 担当）

`extract/table.json` の文書の側（front_matter、documents、copies、forbidden_strings、reference_allow、measure_keep、file_budget、include）と、`extract/description.txt`、`extract/rewritten/`、`extract/own/` の決めを書く。設計は mini-development/design/ の DECISIONS.md と skill-design.md に従い、表の形は tools/generate.py の頭の説明に合わせた。

## 1. 出力と大きさ

| 出力 | 字数（Python の len） | バイト（UTF-8） | 部品の数 |
|---|---|---|---|
| SKILL.md（front matter を含む） | 16,899 | 46,713 | 38 |
| references/rules.md | 32,131 | 88,665 | 29 |
| references/doc-types.md | 33,005 | 88,161 | 34 |

- SKILL.md の上限は 18,000字、目安は 17,000字。front matter は 481字（予算 500字）、description は 271字（上限 280字）。
- SKILL.md の内訳: A と A* の部品（本体の文をそのまま写したもの）7,478字、測定で外さない書き直しと mini だけの文 4,143字、測定で外せる部品 4,759字（6章の logic の直しで42字増えた）。
- 参照ファイルは、どちらも自前の目安の 90,000 バイトの内側にある。rules.md の余りは約 1.3KB なので、足すときは大きさを測ってから足す。
- tools/generate.py（この時点の版）で、scripts.json を読まない写しの表から生成し、手元の組み立てとバイトで同じになった。止めた理由は、スクリプトがまだない写しなので `scripts/mini_check.py`、`--source`、`--final` を指す文だけだった。`--drop stance` と `--drop step1` を `--measure-variant` で回すと、drop_with の部品も一緒に外れた。`--drop meaning-keep` は measure_keep なので止まった。

## 2. 部品の書き方

- 見出しの決め方、節の範囲、sha256 の取り方、置き換えと削除の当て方は tools/generate.py の頭の説明のとおり（当てる順は drop_lines、substitutions、heading_shift。部品の末尾の空行を落とし、部品どうしは空行1つでつなぐ）。
- 行を消すと空行が2つ続く所は、部品を分けて避けた。本体の h1 の下は、段落1と2（L13、L15）を `paragraphs` で取り、見出しは own の h1 に書いた。rules.md の「段落と文の論理構造（つながり）」は、r-logic（L87、L89）と r-logic-memo（段落3の L93-95）に分けた。
- `drop_lines` の pattern は、消す行の頭の字（12字から、ほかの行と重ならなくなるまで4字ずつ延ばしたもの）を `re.escape` した `^…` の形にした。本体でその行の頭が変われば数が合わなくなり、止まる。
- `class` は A（本体の文をそのまま。行を消すだけのものを含む）、A*（参照先や mini にない欄の名前だけを置き換えたもの）、B（書き直し）、C（参照ファイルへ移したもの）、own（本体に元がないもの）。
- description は `extract/description.txt` の1行（最後に改行）。front matter の metadata は、表の version と source から generate.py が作る。
- reference_allow は1つだけ。rules.md に写した本体 L181 の「原文が「■」「・」などの記号で見出しや項目を示している場合」で、原文の記号を保つ規則なので、本体の出力の節の名前ではない。

## 3. 測定で外す単位

- measure_keep（29個）: A と A* の部品、意味を守る文を書き直した部品（stance-keep、logic-keep、step1-keep、step4、step4-visual、step4-close）、手順と出力の形（step2-head、step2-steps、step3、output）、見出しと前書き（h1、h1-body、intro、steps-head、rules-head、rules-skill-head、dt-head、dt-notation）。
- SKILL.md の B の部品には drop_with を付け、rules.md と doc-types.md の同じ中身の部品が一緒に外れるようにした（DECISIONS.md 7章）。measure-design.md の群は、次の SKILL.md の部品を `--drop` に並べれば作れる。

| 群（conditions-plan.json の名前） | `--drop` に渡す id | 一緒に外れる部品（drop_with） |
|---|---|---|
| abl-G1-bunmatsu | stance | r-stance、dt-intro-stance、per-6-stance |
| abl-G2-tsunagari | logic | r-logic、r-logic-memo |
| abl-G3-shugo | subject | r-subject、r-gemini-head、r-gemini-1 |
| abl-G4-hiyu | hiyu | r-hiyu、r-slop-1、r-slop-7、r-slop-8 |
| abl-G5-kimari | selflabel、noadd-residue、noun、copy、promo | r-selflabel、r-slop-2、r-noadd、r-slop-6、r-noun、r-slop-4、r-slop-5、r-copy |
| abl-G6-bunchou | length | r-length、r-slop-9 |
| abl-G7-shoshiki | heading、deco | r-heading、r-deco |
| abl-G8-bunmyaku | step1 | doc-types.md の dt-intro-types と、種類・分野・読者・書き手と読み手の34個（dt-script を含む）、per-6-stance |
| abl-G11-chokuyaku | calque | r-calque、step4-calque |

- G1 の言い切りの強さの文（強さを上げない、期限と必須の指示を弱めない、主語を足さない、依頼か説明か決まらない文）は stance-keep に、G2 の数と条件の文（条件・否定・因果・時系列・比重の範囲、見聞きした日時）は logic-keep に、G8 の意味の4点の記録と文の構造の点検は step1-keep に分けたので、群を外しても残る。
- G9（scripts なし）と G10（references なし）は、ファイルごと外す条件。どの SKILL.md の部品にも付いていない参照ファイルの部品（r-rephrase、r-slop-head、r-review-head、r-review-3、r-review-4）は、G10 でだけ外れる。
- 写しに残る指し先の欠け（v2.2.2 から作った写しを、見出しの名前で照らした。どれも外した群の節を、外さない部品が名前で指しているもので、外す群の性質上なくせない。指しているだけで規則は足さない。v2.1.3 の写しにも同じ種類の欠けがあった）:
  - G5: 「コピー調の抑制」4か所、「紹介記事・宣伝文の勢い」3か所、「内容に合わない大げさな名詞の整理」1か所。
  - G6: doc-types.md の「文長と読点の調整」3か所。
  - G7: 「案内用の見出し」4か所、「装飾記号の排除と太字の表示」2か所。
  - G8: rules.md から種類と分野の節へ9か所（「紹介記事・宣伝文（promo）」「エッセイ・小説（essay）」「業務・仕様・実務ドキュメント向け仕様」など）、SKILL.md から「書き手と読み手（ペルソナ）」1か所。
  - G9: SKILL.md と rules.md の mini_check.py と、その --source と --final。
  - G10: SKILL.md から references/ の2本と、その中の見出し（「言い直しテスト」「目で見る点検」など）。
  - G11: 見出しへの欠けはない。SKILL.md「Step 1」の6番目の「flag.txt の語は…直訳語と同じく書き直す」は残る（語の一覧の決まりで、直訳語の段落を指さない）。
  - G1: 見出しへの欠けはない（per-6-stance と dt-intro-stance も一緒に外れる）。
- `step4-words` は、scripts 担当が mini_check で new_words、lost_words、markers を出さないと決めたら外す部品。外しても、step4-visual の目で見る観点に「元にない語と消えた語」が残る。

## 4. 本体から変えた所

- SKILL.md の見出しの名前は、h1（yomiyasu-mini）、Step 3（「検査」）、Step 4（「（Diff検査）」を外した）の3つだけを変えた。参照ファイルに古い名前を指す文はない。Step 5 は外した（D）。
- 参照ファイルの中の本体の中身への参照（SKILL.md 1章、2章 Step 1 の表、Step 1 の1、Step 2 の5、3章、構造点検、略した節の名前、slop-catalog.md、persona.md、audience.md、domains/、doc-types/、gemini-syntax.md の原則、rephrase-test.md、review-points.md）は、すべて mini の SKILL.md の見出しか、rules.md と doc-types.md の見出しに置き換え、substitutions に記録した。SKILL.md のあとのかぎかっこの名前は、どれも mini の SKILL.md の見出しと同じ文字列にした。
- 本体の道具を指す行と句（lint の規則の名前、diff の文体の硬化と勢い、`--doc-type`、「■ 」の節、references/lists、`yomiyasu-check: not_run`、fact-recovery-details.md、完了報告）は、drop_lines か置き換えで外した。rephrase-test.md の「diff は…意味が変わる恐れとして出す」の2か所は、mini_check が本体 diff の meaning_risks を同じ値で出す前提で `scripts/mini_check.py` に替えた。
- A* の置き換えは5つの部品にある。用途と表記の「資料も検査に渡します」（mini の検査は資料を受けない）、主語と目的語の L100 の persona.md 5章、擬人化の「（gemini-syntax.md 原則3）」、不増補の出力欄の「事実の確かめ」、言い直しテストの rephrase-test.md の2か所。どれも参照先か mini にない欄だけを替え、規則の文は変えていない。
- 本体の domains/tech.md の調査の出典（人名とリンク）は、人名を書かない決まりに合わせて外した。doc-types と persona の例の中の宛名や引用の印の名前は合成の例なので、そのまま写した。
- 依頼の書き方では output と step4 は own だったが、本体に元の節があるので rewritten にし、from で本体の節のハッシュを見張るようにした。本体に元のない h1、intro、step3、step4-words などは own にした。

## 5. ほかの担当への連絡

- copies は LICENSE.txt だけにした。scripts 担当が UNICODE-LICENSE.txt を要ると決めたら、copies に次を足し、file_budget を 9 にする。
  `{"output": "UNICODE-LICENSE.txt", "source": "skills/yomiyasu/UNICODE-LICENSE.txt", "sha256": "e7a93b009565cfce55919a381437ac4db883e9da2126fa28b91d12732bc53d96"}`
- forbidden_strings は `yomiyasu-check: executed`、`yomiyasu-check: not_run`、`Co-Authored-By`、`Generated with` の4つ。生成する .md と .py の両方に当たる。
- SKILL.md の Step 3 は DECISIONS.md 4章の CLI と状態の行をそのまま書いている（`--source`、`--final`、片方だけの `-`、2行目と最後の行、ran、not_run の input と check_error、モデルが書く no_python と not_allowed）。scripts の側でこれが変わったら、own/step3.md と rewritten/output.md を直す。mini_check.py の文に `--source` と `--final` がないと、generate.py の参照の検査で止まる。
- SKILL.md が指すスクリプトは `scripts/mini_check.py` だけで、部品の mini_diff_N.py は名前で指していない。
- 手元の道具（組み立てと照合）は mini-development/impl/content/ の build.py、verify_table.py、mdsec.py。build.py が table.json を書く。

## 6. 生成物を読み手として読んで直したところ（integrate の担当）

生成した SKILL.md と参照ファイル2つを通して読み、次の5か所を抽出表で直した（A と A* の部品は、本体の節と1行ずつ比べ、置き換えと削除が記録のとおりであることを確かめた。直したのは C と B の部品だけ）。

1. r-subject: 本体では同じ節の上の段落を指していた「上の『直前から同じ対象の話が続いて読み違えない文』」が、rules.md では指す先のない「上の」になっていた。「SKILL.md『主語と目的語の明確化』の『直前から…』」に置き換えた。
2. r-gemini-head: 「この文書は」は本体の gemini-syntax.md 全体を指していた。rules.md の中では「この節は」にした。
3. r-review-4: Python がないときの状態の行（reason=no_python）だけが書いてあり、SKILL.md Step 3 の「実行を断られたときは reason=not_allowed」と食い違っていた。断られたときの行を添えた。
4. aud-head: 「（『情報の不増補』）」は、doc-types.md の決まりでは doc-types.md の見出しを指すことになるが、その見出しはない。「SKILL.md『情報の不増補（足さない）』」にした。
5. logic（B）: 本体 L84 の「その分野で定着した複合語と、報告書・公用文・論文の正式な語は詰まりとして扱わない」が、SKILL.md にも rules.md にも残っていなかった。正式な語をほどく直しを止める規則なので、項目4に1文で足した（42字）。

## 7. 本体 v2.2.2 から作り直したときの決め

抽出の元を本体 v2.2.2（タグ v2.2.2、488dd37c0baa67ec65bf155aced9fa1a01d261e2）にした。v2.2.0 からの作り直しの途中（ブランチ wip/rebase-v220 の 0638c25）を読み直して確かめ、そこから続けた。1章から6章の数は v2.1.1 から作ったときのもので、今の数はこの章の表にある。

### 7.1 生成の止まりと見直しの一覧

- 止まり（終了コード2）: r-calque の置き換え「印のついた語」→「型に当たった語」が、v2.2.1 の calques.md で4か所になった（4章の2行目に2か所、見出しの行、呼び名がそろわない行）。count を 4 にした。4か所とも、mini では lint の印ではなく型に当たった語として読めばよい文なので、同じ置き換えにした。
- 見直しの一覧（終了コード3）は4件で、どれも読んでから受け入れた。
  - front matter の from: 本体の metadata の version が 2.2.0 から 2.2.2 になっただけ。description は変わっていない。
  - step4-visual の from（本体の Step 5）: v2.2.1 で「残した印の語」を見て尋ねるか残す理由を書く文が足された。7.3 のとおり step4-visual を書き直した。
  - r-calque: v2.2.1 の4章の書き足し（意味の広い語に替えるだけにしない、見出しの印の語、その動作をする人、呼び名がそろわないとき）と、3章の flag.txt の語を広い言い方に替えない文、5章の例（入口の行の書き直しと、「全店舗に響く」の2行）。そのまま受け入れ、置き換えは上の回数の直しと、7.2 の見出しの行の置き換えだけを足した。
  - scripts の `_ExactSequenceMatcher`: v2.2.2 の diff の速さの直し（`_seeded` に `cap` を渡し、上限と同じ長さの段で最初に一致が見つかった所で止める。`_extend_seeds` をメソッドとして足した）。どちらもクラスの中なので、閉包に新しい名前は入らない。本体は出力が1字も変わらないことを確かめており、mini でも parity の試験で同じ値になった（7.5）。
- v2.2.0 で足された名前（`_FINAL_PERIOD_IN_QUOTE`、`_only_final_period_removed`。台詞の最後の「。」だけを外した組を問いの変化に数えない）は、前の担当の作り直しで閉包に入っていた。`diff` の見張りのハッシュの変化（words の引数と context.words を足しただけ）も受け入れてあり、check-cli が写している type_changes と meaning_risks の作り方は変わっていないことを本体の差分で確かめた。`_rule_candidates` は v2.1.3 から変わっていない。

### 7.2 v2.2.x の新しい材料の扱い

| 本体の材料 | mini での扱い | 理由 |
|---|---|---|
| references/calques.md（直訳語の対応表、v2.2.0、v2.2.1 で書き足し） | rules.md の「直訳語の見方と書き直し方」（r-calque、C）に全文を写し、SKILL.md Step 2 に短く書き直した段落（calque、B）を置く | 型、問い、書き直し方、例は推敲の質と意味の保持に効く本文なので、写す。lint の印を指す文は外し、印のついた語は型に当たった語と読む。mini にない slop-catalog.md 3章を指す句は「この型では見ない」だけを残す |
| calques.md 4章の見出しの行（v2.2.1） | 置き換えで「SKILL.md「案内用の見出し」と、この文書の「本文の節の細部」の同じ名前の節」を指す | 本文の語で項目名を作る決まり（v2.2.0 の見出しの比喩ラベルの行）は、mini の SKILL.md の短い「案内用の見出し」になく、rules.md の同じ名前の節（r-heading）にある |
| references/doc-types/script.md（v2.2.0） | doc-types.md の「台詞・脚本（script）」（dt-script、C）。SKILL.md Step 1 の種類の一覧は13種類で script を含み、種類の一覧の表（dt-table）にも script の行がある | 種類を決めたら読む節なので要る。lint で外す規則の行と、lint の規則の名前の句、fact-recovery-details.md を指す句は外した。dialogue_period の印の条件は、本体の lint と同じ値（台詞が10個以上、「。」で終わる台詞が半分以上）を目で数える条件に書き換えた |
| lists/katakana-terms.txt、lists/thin-evaluation.txt | 入れない | どちらも本体 lint が読む一覧で、mini には lint がない。ファイルの数を8個に保つ。rules.md のカタログ5章の行（評価を言い直すだけの文、意味の薄いカタカナ語）は、例の語を行の中に持っているので、一覧のファイルを指す句だけを外した |
| `.yomiyasu-words/` の allow.txt と flag.txt | SKILL.md Step 1 の6で、あればモデルが自分で読む。flag.txt の語は Step 2 の直訳語と同じ問いで書き直すか尋ね、Step 4 で残っていないかを目で見る | 一覧の扱いは書き手の決めなので、道具がなくても守れる。mini のスクリプトは一覧を読まないので、読んだとも数えたとも書かない |
| lint の info の規則（calque、metaphor_label、say_hedge、thin_evaluation、katakana_term、dialogue_period、narrative_density、copy_comma_noun、bare_verb_chain、project_term） | 規則の名前と「lint は〜の候補として出す」の文は、写した節から外した。直し方の文は残した | mini には lint がない。直し方は文として守れる。SKILL.md に入れたのは、本体 v2.2.0 の推敲の前後の比べ（自作の類例で、規則ごとに直せた件数を 2.1.3 と比べたもの）で直せた件数が増えた copy_comma_noun（4/8 → 8/8、copy に1文）と calque（24/40 → 31/40）。増えなかった metaphor_label（8/10 → 8/10）と bare_verb_chain（4/6 → 4/6）は rules.md の写しだけに置いた。obvious_property（1/3 → 3/3）は型の数が3つと少なく、SKILL.md の字数の目安もあるので、rules.md の「コピー調の抑制」の写しだけに置いた |
| check の kept_marks と「■ 残した印の語」（v2.2.1）、Step 5 の info の印の見直し（v2.2.0） | SKILL.md Step 4 の目で見る点検に1段落（step4-visual）。最終稿に直訳語と flag.txt の語が残っていれば Step 2 の問いで読み直し、書き直せなければ本文を残して尋ね、尋ねずに残すのは直訳語の定着した言い方と文字どおりの意味のときだけで理由を書く。「mini_check はこの語を数えないので、目で探します」と書く | mini には lint も check の記録もないので、数えた語の一覧は出せない。検査が見つけたとは書かず、目で見る観点として書く。review-points.md に足された「■ 残した印の語」の節は本体 check の出力の節の読み方なので写さず、中身は step4-visual と r-calque にある |
| SKILL.md Step 2 の直訳語の段落と v2.2.1 の calques.md 4章 | calque（B）に、意味の広い語（影響する、及ぶ）に替えるだけにしないこと、使う名前と動作に加えて動作をする人、前後の文と呼び名がそろわないときに尋ねることを足した | v2.2.1 で直した穴（H2、H3）は、本体では lint の印と check の「残した印の語」が手がかりになる。mini には印がないので、SKILL.md の本文にも短く置く |

### 7.3 rules.md を 100,000 バイトに収めた方法

- v2.2.2 の calques.md の書き足しで、rules.md は 101,669 バイトになった（v2.2.0 では 99,784 バイト）。
- 「文書の立場と文末」の細部（r-stance、4,242 バイト）を doc-types.md の最後に移し、見出しを1段上げた（heading_shift -1）。文書の立場は行き先と読み手で決めるので、書き手と読み手の節のあとに置いても読み方が変わらない。中身は1字も削っていない。
- あわせて直したもの: SKILL.md「文書の立場と文末」の細部の場所（stance）を doc-types.md にした。doc-types.md の頭（dt-head）に、SKILL.md「文書の立場と文末」の細部も置いていることを書いた。persona の6章の置き換え（per-6）で rules.md の「文書の立場と文末」を指していた所を、doc-types.md の見出し「文書の立場と文末」にした。
- ほかの案を採らなかった理由: カタログやrules.md の例を削ると、写した節の中身が減る。r-calque（8,966 バイト）や「目で見る点検」を移すと、文書の種類と読者の文書の中で話がずれる。書き直した部品を短くしても、rules.md の書き直した部品は r-review-head だけで、足りない。
- tests/test_limits.py の RealBundleTest に、参照ファイルが1本 100,000 バイト以下であることを見る試験を足した。

### 7.4 SKILL.md の字数

- 17,654字（上限 18,000字、目安 17,500字）。v2.2.0 からの作り直しの途中は 17,479字だった。増えたのは step4-visual の残した語の段落と、calque の v2.2.1 の3点。重なる文を削って（step4-visual から直訳語の観点の句を外し、step4-words を1文にまとめた）増え方を抑えたが、目安には 154字届かない。これより削るには意味を守る規則か、本体から写した A の部品を削ることになるので、目安を超えたままにした。
- 前の担当が intro から「（どの版から作ったかは、先頭の metadata の source-tag にあります）」を外していた（字数のため）。版は metadata の source-tag と source-commit に残るので、そのままにした。
- front matter 464字、description 264字。

### 7.5 大きさ（v2.2.2 から生成。Python 3.9.6 と 3.14.5 で同じバイト）

| ファイル | バイト | 字 | 部品の数 |
|---|---|---|---|
| SKILL.md | 48,668 | 17,654 | 39 |
| references/rules.md | 97,499 | 35,445 | 29 |
| references/doc-types.md | 97,054 | 36,130 | 36 |

ファイルの数は8個（SKILL.md、参照ファイル2つ、スクリプト4本、LICENSE.txt）で、file_budget と同じ。

### 7.6 測定で外す単位への影響

- calque（SKILL.md、B）は drop_with に r-calque を持つ。測定では G11（calque だけを外す）として raw_ai の26本で回す（主担当の決め。直訳語は v2.2.x の主な追加で、G3 や G4 に混ぜると効き目を分けられない）。
- r-stance は doc-types.md に移ったが、id で外すので、G1（stance）の drop_with はそのまま働く。G8（step1）の drop_with は dt-intro-types、dt-script、per-6-stance を含めて36個で、r-stance は含まない（G1 の部品のため）。

### 7.7 反証のあとに直したところ（主担当）

- 出力の雛形の「残したAIっぽいところ」の括弧を「残した前置きや結び、直訳語などがあるときだけ」に開いた。Step 4 の目で見る点検が、尋ねずに残した直訳語の理由をこの欄に書くよう求めているのに、雛形が前置きと結びだけに閉じていて食い違っていた（本体の雛形は「など」で開いている）。
- SKILL.md の直訳語の段落で、書き直しに使ってよい根拠を「原文や資料」から「原文、依頼、提供資料、文脈」にした。「情報の不増補」の根拠の4つと、本体の calques.md 4章にそろえた。
- 参照ファイルの1本 100,000 バイトの上限を tools/limits.py の REFERENCE_MAX_BYTES にし、files_problems で確かめるようにした。generate と build_zip が上限を超えた一式を止める。試験もこの値を使う。
- 測定の写しで、外した節を前書きや別の部品が指したまま残らないように、部品を分けた。配る一式の文は、下の言い直しのほかは前と同じ中身。
  - doc-types.md の前書き（dt-head）を、題と1文（dt-head）、種類・分野・読者・書き手と読み手の節の出どころ（dt-intro-types、step1 の drop_with）、最後の「文書の立場と文末」の出どころ（dt-intro-stance、stance の drop_with）、指し方の段落（dt-notation、measure_keep）に分けた。dt-notation の見出しの例と、rules-head の写した節の一覧は、どの写しでも外れない書き方にするため外した。
  - per-6（本体の persona.md 6章）の最後の項目は、本体の本文の「文書の立場と文末」の3つの文を指す（本体 v2.2.2 の SKILL.md の44行目、65行目と、40行目の「誰が、誰に、何のために…」。指し先は本体でも正しい）。mini ではこの節が SKILL.md の stance（書き直し）と doc-types.md の r-stance（44行目と65行目を含む細部）に分かれているので、項目を per-6-stance に書き直して分け、どちらの節かを書いて指した。stance と step1 の drop_with に入れ、G1 と G8 で一緒に外れる。一度、本体の指し先が古いと読み違えて別の節を指したが、反証で本体の SKILL.md にあることを確かめて戻した。
  - Step 4 の目で見る点検（step4-visual）を、観点の段落（step4-visual）、直訳語の段落（step4-calque、calque の drop_with）、最後の「直すのは1回だけ」（step4-close、measure_keep）に分けた。G11 で直訳語の段落が「Step 2 の問い」を指したまま残らないようにするため。
