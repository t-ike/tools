# プロキシカード PDF 生成ツール

GitHubの[iMasanari/proxy-card-print](https://github.com/iMasanari/proxy-card-print)の仕組みを参考にした、画像URLから高品質なプロキシカードPDFを生成するPythonスクリプトです。

## 🎯 特徴

- **正確なカードサイズ**: 縦88mm × 横63mm（実際の印刷サイズと一致）
- **A4サイズ対応**: 1ページに9枚のカードを最適配置
- **高品質PDF生成**: 350DPIベースの高解像度処理
- **バッチ処理**: 複数URLを12ページ単位で自動分割してPDF生成（9枚×12 = 108枚ずつ）
- **並列ダウンロード**: 画像の高速並列取得
- **エラー処理**: 失敗した画像は自動的にプレースホルダーに置換
- **カット線付き**: 印刷後の切り出し用ガイドライン

## 📋 要件

- Python 3.7+
- 必要なライブラリ:
  ```bash
  python3 -m pip install pillow reportlab requests
  ```

## 🚀 使用方法

### 1. 基本実行

```bash
python3 proxy_card_generator.py
```

実行すると2つの設定選択が表示されます：

**画像フィット方法の選択:**
```
�️ 画像のフィット方法を選択してください：
1. 完全フィット（推奨）: 枠を完全に埋める（アスペクト比無視）
2. アスペクト比保持: 画像比率を保ってクロップ
```

- **完全フィット**: カードの枠を100%埋めて隙間なく印刷（推奨）
- **アスペクト比保持**: 元画像の比率を維持（一部余白が発生する可能性）

**URLデータ入力方法の選択:**
```
�📋 URLリストの入力方法を選択してください：
1. ファイルから読み込み
2. 手動入力  
3. テストデータを使用
```

### 2. ファイルから読み込み（推奨）

URLリストをテキストファイルに保存して一括処理：

**urls.txt の例:**
```
https://cards.scryfall.io/large/front/3/3/3398df92-8b6f-4966-b97c-528eeabac678.jpg
https://cards.scryfall.io/large/front/f/e/feefe9f0-24a6-461c-9ef1-86c5a6f33b83.jpg
https://cards.scryfall.io/large/front/9/5/95f27eeb-6f14-4db3-adb9-9be5ed76b34b.jpg
# コメント行は無視されます
https://cards.scryfall.io/large/front/a/4/a457f404-ddf1-40fa-b0f0-23c8598533f4.jpg
```

### 3. 手動入力

対話的にURLを1つずつ入力（空行で終了）

### 4. テストデータ

動作確認用のサンプル画像を使用

## 📐 技術仕様

### カード配置計算

- **カードサイズ**: 63mm × 88mm
- **A4用紙**: 210mm × 297mm
- **余白**: 8mm
- **カード間隔**: 1.5mm
- **配置**: 3列 × 3行 = 9枚/ページ

### DPI変換

GitHubリポジトリと同じ計算方式を採用：
```javascript
const dpi = 350
const inch = 2.54
const toPx = (mm) => Math.round(dpi * mm / 10 / inch)
```

### PDF生成フロー

1. **画像ダウンロード**: 並列処理で高速取得
2. **リサイズ処理**: アスペクト比を保持してクロップ
3. **レイアウト配置**: 中央揃えで9枚配置
4. **PDF生成**: ReportLab + 高解像度画像
5. **カット線追加**: 印刷後の切り出し用

## 📁 出力

- **出力先**: `~/Downloads/proxy_cards/`
- **ファイル名**: `proxy_cards_part_01.pdf`, `proxy_cards_part_02.pdf`, ... （12ページ単位で分割）
- **品質**: 高解像度JPEG画像をPDF内に埋め込み
- **分割ルール**: 108枚（12ページ）ごとに自動分割してPDFサイズを管理

## 🎴 使用例

### MTG Cube用プロキシ生成

```bash
# 1. cube_urls.txt に必要なカードURLをリスト
echo "https://cards.scryfall.io/large/front/..." > cube_urls.txt

# 2. バッチ実行
python3 proxy_card_generator.py
# -> "1" を選択
# -> "cube_urls.txt" を入力

# 3. ~/Downloads/proxy_cards/ に分割されたPDFが生成される
# （108枚ごとに分割、大きなキューブでも管理しやすい）
```

### 大量カード処理

540枚のカードURL → 自動的に5個のPDF（108枚×5）に分割（最後のPDFは残りの枚数）

**サイズ管理:**
- 1つのPDFあたり最大12ページ（108枚）で自動分割
- 30MBを超えないよう設計された固定サイズ分割 (PrintSmashの制限が30MBのため)

## 🔧 カスタマイズ

### カードサイズ変更

`ProxyCardPDFGenerator.__init__()` で設定：

```python
self.card_width = 63   # mm (幅)
self.card_height = 88  # mm (高さ)
```

### 余白・間隔調整

```python
self.page_margin = 8   # mm (用紙余白)
self.card_gap = 1.5    # mm (カード間隔)
```

## 🚨 注意事項

- **SSL証明書**: 一部サイトでSSL証明書エラーが発生する場合があります（スクリプト内で自動処理済み）
- **画像品質**: 元画像の解像度に依存します
- **印刷設定**: 必ず「等倍（100%）」または「用紙に合わせる」で印刷してください
- **著作権**: 画像の著作権・利用規約を遵守してください

## 📊 パフォーマンス

- **並列ダウンロード**: 最大5スレッド
- **処理速度**: 約10秒/9枚（ネットワーク速度による）
- **ファイルサイズ**: 約15-25MB/PDF（12ページ、108枚）
- **分割効率**: 30MB制限内で最大12ページの効率的な分割

## 🤝 貢献

このツールは[iMasanari/proxy-card-print](https://github.com/iMasanari/proxy-card-print)の優れた設計思想を参考にして作られました。元プロジェクトに感謝します。

---

**🎴 Happy Proxy Making! 🎴**