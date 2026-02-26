# moxfield_fetcher

Moxfield の公開デッキから Scryfall 経由で日本語カード情報を取得し CSV 出力するツール。

## 必要ライブラリ

```bash
pip install requests cloudscraper
```

## 使い方

```bash
python3 fetch_deck.py <deck_code> [-o OUTPUT]
```

`deck_code` は Moxfield のデッキ URL に含まれる文字列です。
例: `https://www.moxfield.com/decks/AbCdEfGh` → `AbCdEfGh`

### オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `-o`, `--output` | 出力 CSV ファイル名 | `mtg_cards.csv` |
| `-m`, `--moxfield-print` | Moxfield で設定中のセットに日本語版があれば最優先で採用 | `False` |

### 実行例

```bash
# デフォルト (mtg_cards.csv)
python3 fetch_deck.py g29LKHreK0yB_ylkKo6iHQ

# ファイル名を指定
python3 fetch_deck.py g29LKHreK0yB_ylkKo6iHQ -o sidisi_deck.csv

# Moxfield で選択中のセットを優先（日本語版がある場合）
python3 fetch_deck.py g29LKHreK0yB_ylkKo6iHQ -m

# 組み合わせ
python3 fetch_deck.py g29LKHreK0yB_ylkKo6iHQ -m -o sidisi_deck.csv

# ヘルプ
python3 fetch_deck.py --help
```

## 出力

実行ディレクトリに CSV ファイル（UTF-8）を生成します。

| カラム | 内容 |
|--------|------|
| `card_name_ja` | 日本語名（なければ英語名） |
| `card_name_en` | 英語名 |
| `oracle_id` | Oracle ID |
| `set_code` | 採用セットコード |
| `is_japanese` | 日本語版を採用した場合 `True` |
| `image_url` | PNG 画像 URL |
| `scryfall_uri` | Scryfall カードページ URL |
| `all_set_codes` | 全セットコード（`\|` 区切り） |

### 両面カード

両面カード（Transform / Modal DFC など）は **表面・裏面それぞれ 1 行**出力されます。
`card_name_en` と `image_url` が各面の値になります。

## 仕様

### 取得範囲

- Moxfield デッキの **mainboard のみ** を対象とします（sideboard・maybeboard は除外）

### 日本語版の選択ロジック

1. 日本語版（`lang == "ja"`）が存在するセットに絞る
2. その中で**言語バリエーション数が最多**のセットを優先（大型セットほど多言語対応）
3. 言語数が同数の場合は `released_at` が最新のセットを選ぶ
4. 日本語版がない場合は英語版の最新を採用

### 出力順序

カードタイプ → CMC（マナコスト）→ 英語名 の順でソートされます。

| 順序 | タイプ |
|------|--------|
| 1 | Planeswalker |
| 2 | Creature（Artifact Creature 含む） |
| 3 | Sorcery |
| 4 | Instant |
| 5 | Artifact |
| 6 | Enchantment |
| 7 | その他 |
| 8 | Land |

### Cloudflare 対応

Moxfield API は Cloudflare Bot Protection が有効なため、`cloudscraper` を使用してアクセスします。
