# Cube Helper - Image URL Extractor

Cube Cobra APIを使用してキューブリストから指定色カテゴリのカード画像URLを取得するツールです。

## 機能

- **Cube Cobra API統合**: 最新かつ正確なカードデータを直接取得
- **色カテゴリ対応**: White、Blue、Black、Red、Green、Colorless、Multicolored、Lands
- **複数カテゴリ指定**: カンマ区切りで複数の色を同時指定可能
- **全カード取得**: "all" 指定で全カードの画像URLを一括取得
- **両面カード対応**: 表面・裏面の両方の画像URLを自動取得
- **Proxyedタグ除外**: プロキシカードを除外して実際のカードのみ取得
- **outputディレクトリ管理**: 出力ファイルを自動的にoutput/ディレクトリに整理

## 必要なもの

- Python 3.7+
- requests
- pathlib (標準ライブラリ)

## インストール

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本的な使い方

```bash
# 白いカードの画像URLを取得
python3 cube_image_extractor.py "https://www.cubecobra.com/cube/list/your-cube-id" --color "White"

# 土地カードの画像URLを取得
python3 cube_image_extractor.py "https://www.cubecobra.com/cube/list/your-cube-id" --color "Lands"

# 出力ファイル名を指定
python3 cube_image_extractor.py "https://www.cubecobra.com/cube/list/your-cube-id" --color "Blue" -o blue_cards.txt
```

### 複数カテゴリ指定

```bash
# 白と青のカードを同時取得
python3 cube_image_extractor.py "https://www.cubecobra.com/cube/list/your-cube-id" --color "White,Blue"

# 単色カード全て（5色）を取得
python3 cube_image_extractor.py "https://www.cubecobra.com/cube/list/your-cube-id" --color "White,Blue,Black,Red,Green"
```

### 全カード取得

```bash
# キューブ内の全カードを取得（両面カード含む）
python3 cube_image_extractor.py "https://www.cubecobra.com/cube/list/your-cube-id" --color "all"
```

### Proxyedタグ除外

```bash
# プロキシカードを除外して実際のカードのみ取得
python3 cube_image_extractor.py "https://www.cubecobra.com/cube/list/your-cube-id" --color "White" --exclude-proxyed
```

### 実用例

```bash
# PowerLSV Cubeから白いカードを取得
python3 cube_image_extractor.py "https://www.cubecobra.com/cube/list/48c4bc57-d95c-4226-9c4d-05f140bed38c" --color "White"

# 全カードを取得（両面カード込み527+15=542枚）
python3 cube_image_extractor.py "https://www.cubecobra.com/cube/list/48c4bc57-d95c-4226-9c4d-05f140bed38c" --color "all"

# プロキシ除外で実際のカードのみ取得
python3 cube_image_extractor.py "https://www.cubecobra.com/cube/list/48c4bc57-d95c-4226-9c4d-05f140bed38c" --color "all" --exclude-proxyed
```

## コマンドライン引数

| 引数 | 説明 | 例 |
|------|------|-----|
| `url` | Cube CobraのキューブリストURL (必須) | `"https://www.cubecobra.com/cube/list/your-cube-id"` |
| `--color` | 取得する色カテゴリ (必須) | `"White"`, `"White,Blue"`, `"all"` |
| `-o, --output` | 出力ファイル名 (オプション) | `white_cards.txt` |
| `--exclude-proxyed` | Proxyedタグ付きカードを除外 | フラグ（指定するだけ） |

## 対応する色カテゴリ

| カテゴリ | 説明 | 期待枚数例* |
|----------|------|-------------|
| **White** | 白いカード | 62枚 |
| **Blue** | 青いカード | 72枚 |
| **Black** | 黒いカード | 66枚 |
| **Red** | 赤いカード | 56枚 |
| **Green** | 緑のカード | 49枚 |
| **Colorless** | 無色カード | 55枚 |
| **Multicolored** | 多色カード | 74枚 |
| **Lands** | 土地カード | 93枚 |
| **all** | 全カード | 527枚 + 両面15枚 = 542URL |

*PowerLSV Cubeでの実績値

## 機能詳細

### 🎴 両面カード対応
- 変身カード、両面プレインズウォーカーなど両面を持つカードの表面・裏面両方を自動検出
- 15枚の両面カードから合計30個の画像URLを取得

### 🚫 Proxyedタグ除外
- `--exclude-proxyed` オプションでプロキシカードを除外
- 実際に印刷が必要なカードのみを抽出可能

### 📁 ファイル管理
- 全ての出力ファイルは自動的に `output/` ディレクトリに保存
- `output/` ディレクトリは `.gitignore` で除外済み
- ファイル名は自動生成（例: `white_images.txt`, `white_blue_images.txt`）

### 🔍 統計情報表示
```
📊 各カテゴリの内訳:
  Blue: 72枚
  White: 62枚

🔄 両面カード (1枚):
  1: Dion, Bahamut's Dominant
```

## 出力形式

各行に1つの画像URLが出力されます：

```
https://cards.scryfall.io/png/front/3/f/3f87ab94-1feb-4b2e-aab7-b27e73b53509.png?1744674128
https://cards.scryfall.io/png/front/8/1/81bc5db4-5de3-4fab-b59e-f062226c2cd5.png?1645877014
https://cards.scryfall.io/png/back/2/b/2bb67ecf-4b87-4254-bc00-18d36e729f98.png?1762509654
```

## トラブルシューティング

### よくある問題

1. **APIエラー**: キューブIDが正しいか確認
2. **0枚取得**: 色カテゴリ名の大文字小文字を確認
3. **権限エラー**: output/ディレクトリの書き込み権限を確認

### ヘルプ表示

```bash
python3 cube_image_extractor.py --help
```

## 関連ツール

- **proxy_pdf_maker**: 取得した画像URLからプロキシカードPDFを生成するツール