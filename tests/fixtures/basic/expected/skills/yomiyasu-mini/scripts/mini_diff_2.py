# yomiyasu-mini 1.0.0。nanaism/yomiyasu v2.1.3（c09270bc93daab14e253fb3ef406182011b79ccb）から tools/generate.py で生成した。手で直さない。
# 取り出した名前と中身の sha256 は extract/scripts.json と MANIFEST.json にある。
"""試験用の部品。mini_check.py から読む。"""

__version__ = "1.0.0"
SOURCE_TAG = "v2.1.3"
SOURCE_COMMIT = "c09270bc93daab14e253fb3ef406182011b79ccb"

import unicodedata

DOC_TYPES = (
    ("pr", "PR説明", ("business.md",)),
    ("article", "技術記事", ("tech.md",)),
    ("incident", "障害報告", ("business.md",)),
    ("proposal", "提案書", ("business.md",)),
    ("minutes", "議事録", ("business.md",)),
    ("manual", "マニュアル", ("tech.md", "business.md")),
    ("slides", "スライド", ("tech.md", "business.md")),
    ("essay", "エッセイ・小説", ("essay.md",)),
    ("formal", "公用文、規程、契約書、仕様書", ("business.md", "tech.md")),
    ("promo", "紹介記事・宣伝文", ("essay.md", "business.md")),
    ("mail", "メール・チャット", ("business.md",)),
    ("paper", "論文・研究レポート", ("tech.md",)),
)

def _normalize_choice(option, value, rows):
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", str(value)).strip().lower()
    for row in rows:
        if row[0] == normalized:
            return normalized
    shown = value if str(value).strip() else "（空）"
    raise ValueError("{} に使えない値です: {}。使えるのは {}です。".format(
        option, shown, "、".join("{}（{}）".format(row[0], row[1]) for row in rows)))
