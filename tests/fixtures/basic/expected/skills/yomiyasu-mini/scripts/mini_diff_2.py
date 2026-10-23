# yomiyasu-mini 1.0.0。nanaism/yomiyasu v2.2.2（488dd37c0baa67ec65bf155aced9fa1a01d261e2）から tools/generate.py で生成した。手で直さない。
# 取り出した名前と中身の sha256 は extract/scripts.json と MANIFEST.json にある。
"""試験用の部品。mini_check.py から読む。"""

__version__ = "1.0.0"
SOURCE_TAG = "v2.2.2"
SOURCE_COMMIT = "488dd37c0baa67ec65bf155aced9fa1a01d261e2"

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
    ("script", "台詞・脚本", ("essay.md",)),
)
