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

- measure_keep（27個）: A と A* の部品、意味を守る文を書き直した部品（stance-keep、logic-keep、step1-keep、step4、step4-visual）、手順と出力の形（step2-head、step2-steps、step3、output）、見出しと前書き（h1、h1-body、intro、steps-head、rules-head、rules-skill-head、dt-head）。
- SKILL.md の B の部品には drop_with を付け、rules.md と doc-types.md の同じ中身の部品が一緒に外れるようにした（DECISIONS.md 7章）。measure-design.md の群は、次の SKILL.md の部品を `--drop` に並べれば作れる。

| 群（conditions-plan.json の名前） | `--drop` に渡す id | 一緒に外れる部品（drop_with） |
|---|---|---|
| abl-G1-bunmatsu | stance | r-stance |
| abl-G2-tsunagari | logic | r-logic、r-logic-memo |
| abl-G3-shugo | subject | r-subject、r-gemini-head、r-gemini-1 |
| abl-G4-hiyu | hiyu | r-hiyu、r-slop-1、r-slop-7、r-slop-8 |
| abl-G5-kimari | selflabel、noadd-residue、noun、copy、promo | r-selflabel、r-slop-2、r-noadd、r-slop-6、r-noun、r-slop-4、r-slop-5、r-copy |
| abl-G6-bunchou | length | r-length、r-slop-9 |
| abl-G7-shoshiki | heading、deco | r-heading、r-deco |
| abl-G8-bunmyaku | step1 | doc-types.md の dt-head を除く33個 |

- G1 の言い切りの強さの文（強さを上げない、期限と必須の指示を弱めない、主語を足さない、依頼か説明か決まらない文）は stance-keep に、G2 の数と条件の文（条件・否定・因果・時系列・比重の範囲、見聞きした日時）は logic-keep に、G8 の意味の4点の記録と文の構造の点検は step1-keep に分けたので、群を外しても残る。
- G9（scripts なし）と G10（references なし）は、ファイルごと外す条件。どの SKILL.md の部品にも付いていない参照ファイルの部品（r-rephrase、r-slop-head、r-review-head、r-review-3、r-review-4）は、G10 でだけ外れる。
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
