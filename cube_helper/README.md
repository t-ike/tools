# Cube Helper

Cube Cobraのキューブリストから指定カテゴリのカード画像URLを取得するツールです。

## 機能

- Cube Cobraのリストページから任意のカードタイプの画像URLを取得
- ReactアプリケーションのJSONデータを解析して高精度でカード情報を抽出
- Land、Creature、Instant、Sorceryなど様々なカードタイプに対応

## 必要なもの

- Python 3.7+
- requests
- beautifulsoup4（オプション、デバッグ用）

## インストール

```bash
pip install -r ../requirements.txt
```

## 使用方法

### 🎯 推奨スクリプト（最新版）

`cube_image_extractor.py`を使用することをお勧めします：

```bash
# 土地カードの画像URLを取得
python3 cube_image_extractor.py "https://www.cubecobra.com/cube/list/your-cube-id" -c "Land"

# クリーチャーカードの画像URLを取得
python3 cube_image_extractor.py "https://www.cubecobra.com/cube/list/your-cube-id" -c "Creature"

# インスタントカードの画像URLを取得（出力ファイルを指定）
python3 cube_image_extractor.py "https://www.cubecobra.com/cube/list/your-cube-id" -c "Instant" -o instants.txt
```

### 実用例

```bash
# 提供されたキューブのLandカードを取得
python3 cube_image_extractor.py "https://www.cubecobra.com/cube/list/48c4bc57-d95c-4226-9c4d-05f140bed38c" -c "Land"
```

### オプション

- `-c, --category`: 取得するカードカテゴリ（デフォルト: Land）
- `-o, --output`: 出力ファイル名（デフォルト: `<category>_images.txt`）
- `--debug`: デバッグモード（キューブデータをJSONで保存）

## 対応するカードタイプ

- **Land** - 土地カード
- **Creature** - クリーチャーカード  
- **Instant** - インスタントカード
- **Sorcery** - ソーサリーカード
- **Enchantment** - エンチャントカード
- **Artifact** - アーティファクトカード
- **Planeswalker** - プレインズウォーカーカード

## その他のスクリプト

- `get_images.py` - 元のスクリプト（現在は動作しません）
- `extract_react_data.py` - ReactPropsデータ抽出の詳細版
- `debug_cube_structure.py` - HTML構造解析用デバッグスクリプト
