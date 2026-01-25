#!/usr/bin/env python3
"""
プロキシカード PDF 生成ツール
GitHubリポジトリの仕組みを参考にした独立版
"""

import os
import sys
import json
import requests
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from io import BytesIO
import urllib.request
import time
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed

def mm_to_points(mm):
    """ミリメートルをポイントに変換（1mm = 2.834645669 points）"""
    return mm * 2.834645669

class ProxyCardPDFGenerator:
    def __init__(self):
        # カードサイズ（要求された88mm x 63mm）
        self.card_width = 63   # mm
        self.card_height = 88  # mm
        
        # A4サイズ設定
        self.page_width = 210  # mm
        self.page_height = 297 # mm
        
        # 余白とギャップの最適化（幅のオーバーフローを解決）
        self.page_margin = 0   # mm (10mm → 8mm に縮小)
        self.card_gap = 0    # mm (2mm → 1.5mm に縮小)
        
        # 印刷可能エリア計算
        self.printable_width = self.page_width - (self.page_margin * 2)
        self.printable_height = self.page_height - (self.page_margin * 2)
        
        # 9枚配置計算（3列3行）
        self.cols = 3
        self.rows = 3
        
        # PDFサイズ制限設定
        self.max_pdf_size = 30 * 1024 * 1024  # 30MB
        self.pages_per_split = 12  # 分割単位（ページ数）
        
        # 実際の配置確認
        total_cards_width = (self.card_width * self.cols) + (self.card_gap * (self.cols - 1))
        total_cards_height = (self.card_height * self.rows) + (self.card_gap * (self.rows - 1))
        
        print(f"📏 カードサイズ: {self.card_width}mm x {self.card_height}mm")
        print(f"📄 A4サイズ: {self.page_width}mm x {self.page_height}mm")
        print(f"🎯 印刷エリア: {self.printable_width}mm x {self.printable_height}mm")
        print(f"📐 9枚配置サイズ: {total_cards_width}mm x {total_cards_height}mm")
        
        # 配置可能かチェック
        if total_cards_width > self.printable_width:
            print(f"⚠️  幅が印刷エリアを超過: {total_cards_width}mm > {self.printable_width}mm")
            # 自動調整
            available_width_per_card = (self.printable_width - (self.card_gap * (self.cols - 1))) / self.cols
            if available_width_per_card < self.card_width:
                self.card_width = available_width_per_card
                print(f"🔧 カード幅を自動調整: {self.card_width:.1f}mm")
        if total_cards_height > self.printable_height:
            print(f"⚠️  高さが印刷エリアを超過: {total_cards_height}mm > {self.printable_height}mm")
            # 自動調整
            available_height_per_card = (self.printable_height - (self.card_gap * (self.rows - 1))) / self.rows
            if available_height_per_card < self.card_height:
                self.card_height = available_height_per_card
                print(f"🔧 カード高さを自動調整: {self.card_height:.1f}mm")
        
        # 再計算
        total_cards_width = (self.card_width * self.cols) + (self.card_gap * (self.cols - 1))
        total_cards_height = (self.card_height * self.rows) + (self.card_gap * (self.rows - 1))
        
        # 中央配置のための開始位置計算
        self.start_x = self.page_margin + (self.printable_width - total_cards_width) / 2
        self.start_y = self.page_margin + (self.printable_height - total_cards_height) / 2
        
        print(f"📍 開始位置: ({self.start_x:.1f}mm, {self.start_y:.1f}mm)")
        
    def download_image(self, url, timeout=5, max_retries=2):
        """画像URLから画像をダウンロード（リトライ機能付き）"""
        for attempt in range(max_retries + 1):
            try:
                # SSL証明書の問題を回避
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
                    image_data = response.read()
                    
                # PILで画像を開く
                image = Image.open(BytesIO(image_data))
                
                # RGBに変換（アルファチャンネルがあれば白背景で合成）
                if image.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    if image.mode == 'LA':
                        image = image.convert('RGBA')
                    background.paste(image, mask=image.split()[-1])
                    image = background
                elif image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # 成功した場合
                if attempt > 0:
                    print(f"    ✅ リトライ {attempt}/{max_retries} で成功")
                return image
                
            except Exception as e:
                if attempt < max_retries:
                    print(f"    ⚠️  試行 {attempt + 1}/{max_retries + 1} 失敗: {e}")
                    print(f"    🔄 {timeout}秒後にリトライします...")
                    time.sleep(timeout)  # タイムアウト時間分待機
                else:
                    print(f"❌ 画像ダウンロード完全失敗 {url[:50]}...: {e}")
                    print(f"❌ 最大リトライ回数 ({max_retries}) に達しました")
                    return None
    
    def resize_image_to_card(self, image, force_exact_size=True):
        """画像をカードサイズに正確にリサイズ（枠を完全に埋める）"""
        if not image:
            return None
            
        # 目標サイズ（高解像度で処理）
        target_width = int(self.card_width * 10)  # 1mm = 10 pixels at this resolution
        target_height = int(self.card_height * 10)
        
        print(f"    🖼️  画像リサイズ: {image.width}x{image.height} → {target_width}x{target_height}px")
        
        if force_exact_size:
            # 強制的に正確なサイズにリサイズ（アスペクト比は無視して枠を完全に埋める）
            print(f"    🔧 強制リサイズモード: アスペクト比を無視してカード枠に完全フィット")
            resized = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        else:
            # アスペクト比計算
            img_ratio = image.width / image.height
            target_ratio = target_width / target_height
            
            if img_ratio > target_ratio:
                # 横長画像：高さを基準にリサイズしてから幅をクロップ
                new_height = target_height
                new_width = int(target_height * img_ratio)
                resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 中央でクロップ
                left = (new_width - target_width) // 2
                resized = resized.crop((left, 0, left + target_width, target_height))
            else:
                # 縦長画像：幅を基準にリサイズしてから高さをクロップ
                new_width = target_width
                new_height = int(target_width / img_ratio)
                resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 中央でクロップ
                top = (new_height - target_height) // 2
                resized = resized.crop((0, top, target_width, top + target_height))
        
        # 最終確認：正確なサイズになっているかチェック
        if resized.size != (target_width, target_height):
            print(f"    ⚠️  サイズ不一致を検出、再調整実行")
            # 強制的に正確なサイズにリサイズ（アスペクト比は無視）
            resized = resized.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        print(f"    ✅ 最終サイズ: {resized.width}x{resized.height}px")
        return resized
    
    def download_images_batch(self, urls, force_exact_size=True):
        """複数の画像を順次ダウンロード（レート制限対策で0.3秒間隔、失敗時プログラム終了）"""
        images = []
        
        print(f"🔄 {len(urls)} 枚の画像をダウンロード中（0.3秒間隔、タイムアウト5秒、最大2回リトライ）...")
        
        for i, url in enumerate(urls):
            print(f"  🔄 #{i+1}/{len(urls)}: ダウンロード中...")
            try:
                # 画像をダウンロード（リトライ機能付き）
                image = self.download_image(url)
                
                if image:
                    resized_image = self.resize_image_to_card(image, force_exact_size)
                    images.append(resized_image)
                    print(f"  ✅ #{i+1}: {url[:50]}...")
                else:
                    print(f"  ❌ #{i+1}: ダウンロード完全失敗")
                    print(f"❌ プログラムを終了します")
                    sys.exit(1)
                    
            except Exception as e:
                print(f"  ❌ #{i+1}: 処理エラー - {e}")
                print(f"❌ プログラムを終了します")
                sys.exit(1)
            
            # レート制限対策：0.3秒待機（最後のアイテム以外）
            if i < len(urls) - 1:
                time.sleep(0.3)
                print(f"    ⏱️  0.3秒待機...")
        
        return images
    
    def create_placeholder_image(self):
        """プレースホルダー画像を作成"""
        width = int(self.card_width * 10)
        height = int(self.card_height * 10)
        
        image = Image.new('RGB', (width, height), (240, 240, 240))
        draw = ImageDraw.Draw(image)
        
        # 枠線を描画
        draw.rectangle([(0, 0), (width-1, height-1)], outline=(200, 200, 200), width=3)
        
        # "No Image"テキスト
        try:
            # システムフォントを試す
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", size=24)
        except:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size=24)
            except:
                font = ImageFont.load_default()
        
        text = "No Image"
        
        # テキストサイズ取得
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 中央に配置
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        draw.text((x, y), text, fill=(150, 150, 150), font=font)
        
        return image
    
    def split_batches_by_size(self, all_image_batches):
        """画像バッチを固定ページ数で分割"""
        total_pages = len(all_image_batches)
        
        print(f"\n📊 PDF分割設定:")
        print(f"  総ページ数: {total_pages}")
        print(f"  分割単位: {self.pages_per_split}ページ")
        
        # バッチを分割
        split_batches = []
        for i in range(0, len(all_image_batches), self.pages_per_split):
            chunk = all_image_batches[i:i + self.pages_per_split]
            split_batches.append(chunk)
            print(f"    📋 分割 {len(split_batches)}: {len(chunk)}ページ")
        
        return split_batches
    
    def generate_pdf(self, all_image_batches, output_dir):
        """全ての画像バッチからPDFを生成（固定ページ数で分割）"""
        if not all_image_batches:
            print("❌ 生成する画像がありません")
            return []
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 固定ページ数で分割
        split_batches = self.split_batches_by_size(all_image_batches)
        
        generated_pdfs = []
        
        for batch_index, batch_pages in enumerate(split_batches, 1):
            # PDFファイル名を決定
            if len(split_batches) == 1:
                pdf_filename = f"proxy_cards.pdf"
            else:
                pdf_filename = f"proxy_cards_part{batch_index:02d}.pdf"
            
            pdf_path = os.path.join(output_dir, pdf_filename)
            
            print(f"\n📄 PDF生成中 ({batch_index}/{len(split_batches)}): {pdf_filename}")
            print(f"  ページ数: {len(batch_pages)}")
            
            # 個別PDFを生成
            self.generate_single_pdf(batch_pages, pdf_path, batch_index, len(split_batches))
            generated_pdfs.append(pdf_path)
        
        return generated_pdfs
    
    def generate_single_pdf(self, image_batches, pdf_path, part_num=1, total_parts=1):
        """単一のPDFファイルを生成"""
        # ReportLabでPDF作成
        c = canvas.Canvas(pdf_path, pagesize=A4)
        
        for page_num, images in enumerate(image_batches, 1):
            print(f"  📄 ページ {page_num}/{len(image_batches)} 生成中...")
            
            # 画像を配置
            card_count = 0
            print(f"    🎴 カード配置開始:")
            print(f"      📐 配置エリア: {self.cols}列 × {self.rows}行")
            
            for row in range(self.rows):
                for col in range(self.cols):
                    if card_count < len(images) and images[card_count]:
                        # カード位置計算（画像の左下角）
                        x = self.start_x + col * (self.card_width + self.card_gap)
                        y = self.page_height - (self.start_y + (row + 1) * self.card_height + row * self.card_gap)
                        
                        # 画像を一時ファイルとして保存してから配置
                        temp_image_path = f"/tmp/temp_card_{part_num}_{page_num}_{card_count}.jpg"
                        images[card_count].save(temp_image_path, "JPEG", quality=95)
                        
                        # PDFに画像を配置（完全にカード枠を埋める）
                        print(f"    🎴 カード #{card_count+1} (行{row+1}, 列{col+1}):")
                        print(f"      📍 位置: ({x:.1f}mm, {y:.1f}mm)")
                        print(f"      📐 サイズ: {self.card_width:.1f}mm × {self.card_height:.1f}mm")
                        
                        c.drawImage(
                            temp_image_path,
                            mm_to_points(x),
                            mm_to_points(y),
                            width=mm_to_points(self.card_width),
                            height=mm_to_points(self.card_height)
                        )
                        
                        # 一時ファイル削除
                        try:
                            os.remove(temp_image_path)
                        except:
                            pass
                    
                    card_count += 1
                    if card_count >= 9:  # 9枚まで
                        break
                if card_count >= 9:
                    break
            
            # カット線を追加
            self.add_cut_lines(c)
            
            # 最後のページ以外は新しいページを追加
            if page_num < len(image_batches):
                c.showPage()
                print(f"    ✅ ページ {page_num} 完了、次のページへ")
            else:
                print(f"    ✅ 最終ページ {page_num} 完了")
        
        # PDFを保存
        c.save()
        
        file_size = os.path.getsize(pdf_path)
        actual_size_mb = file_size / 1024 / 1024
        
        print(f"  ✅ PDF保存完了: {os.path.basename(pdf_path)}")
        print(f"    📊 ファイルサイズ: {actual_size_mb:.1f}MB ({file_size:,} bytes)")
        
        return pdf_path
    
    def add_cut_lines(self, canvas_obj):
        """カット線を追加（9枚の画像の外に延長する形で表示）"""
        canvas_obj.setStrokeColorRGB(0, 0, 0)  # 適度なグレー（見やすい）
        canvas_obj.setLineWidth(0.05)  # 適度な太さ
        canvas_obj.setDash([1, 2])  # 破線スタイル（切り取り線らしく）
        
        print(f"  📐 カット線生成中（外側延長モード）...")
        print(f"    📏 カード配置: {self.cols}列 × {self.rows}行")
        print(f"    📍 開始位置: ({self.start_x:.1f}mm, {self.start_y:.1f}mm)")
        print(f"    📐 カードサイズ: {self.card_width:.1f}mm × {self.card_height:.1f}mm")
        print(f"    📏 カード間隔: {self.card_gap:.1f}mm")
        
        # カード配置エリア全体の座標を計算
        cards_left = self.start_x
        cards_right = self.start_x + (self.card_width * self.cols) + (self.card_gap * (self.cols - 1))
        cards_top = self.start_y
        cards_bottom = self.start_y + (self.card_height * self.rows) + (self.card_gap * (self.rows - 1))
        
        # 延長する長さ（5mm延長）
        extension_length = 8.0  # mm
        
        # 縦線（各カードの左右の境界を外に延長）
        for col in range(self.cols + 1):
            if col == 0:
                # 左端の線
                x = cards_left
            elif col == self.cols:
                # 右端の線
                x = cards_right
            else:
                # 中間の線（カード間の境界）
                x = self.start_x + col * (self.card_width + self.card_gap)
            
            # 上方向に延長
            y1_extended = max(0, cards_top - extension_length)
            # 下方向に延長
            y2_extended = min(self.page_height, cards_bottom + extension_length)
            
            print(f"    ┃ 縦線 #{col+1}: x={x:.1f}mm, y={y1_extended:.1f}mm-{y2_extended:.1f}mm (延長)")
            
            canvas_obj.line(
                mm_to_points(x),
                mm_to_points(self.page_height - y1_extended),
                mm_to_points(x),
                mm_to_points(self.page_height - y2_extended)
            )
        
        # 横線（各カードの上下の境界を外に延長）
        for row in range(self.rows + 1):
            if row == 0:
                # 上端の線
                y = cards_top
            elif row == self.rows:
                # 下端の線
                y = cards_bottom
            else:
                # 中間の線（カード間の境界）
                y = self.start_y + row * (self.card_height + self.card_gap)
            
            # 左方向に延長
            x1_extended = max(0, cards_left - extension_length)
            # 右方向に延長
            x2_extended = min(self.page_width, cards_right + extension_length)
            
            print(f"    ━ 横線 #{row+1}: y={y:.1f}mm, x={x1_extended:.1f}mm-{x2_extended:.1f}mm (延長)")
            
            canvas_obj.line(
                mm_to_points(x1_extended),
                mm_to_points(self.page_height - y),
                mm_to_points(x2_extended),
                mm_to_points(self.page_height - y)
            )
        
        print(f"  ✅ カット線生成完了（外側延長: {extension_length}mm）")

def main():
    print("🎴 プロキシカード PDF 生成ツール")
    print("=" * 50)
    
    # 画像フィットモードの選択
    print("\n🖼️ 画像のフィット方法を選択してください：")
    print("1. 完全フィット（推奨）: 枠を完全に埋める（アスペクト比無視）")
    print("2. アスペクト比保持: 画像比率を保ってクロップ")
    
    fit_choice = input("選択 (1-2, デフォルト=1): ").strip()
    force_exact_size = fit_choice != "2"
    
    if force_exact_size:
        print("✅ 完全フィットモード: カードの枠を100%埋めます")
    else:
        print("✅ アスペクト比保持モード: 画像の縦横比を維持します")
    
    # URLリストの取得方法選択
    print("\n📋 URLリストの入力方法を選択してください：")
    print("1. ファイルから読み込み")
    print("2. 手動入力")
    print("3. テストデータを使用")
    
    choice = input("選択 (1-3): ").strip()
    
    urls = []
    
    if choice == "1":
        filename = input("URLリストファイルのパス: ").strip()
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
                urls = [line for line in lines if line.startswith('http')]
            print(f"✅ {len(urls)} 個のURLを読み込みました")
        except Exception as e:
            print(f"❌ ファイル読み込みエラー: {e}")
            return
            
    elif choice == "2":
        print("URLを1行ずつ入力してください（空行で終了）:")
        while True:
            url = input(f"URL {len(urls)+1}: ").strip()
            if not url:
                break
            urls.append(url)
                
    elif choice == "3":
        # テストデータ
        urls = [
            "https://cards.scryfall.io/large/front/3/3/3398df92-8b6f-4966-b97c-528eeabac678.jpg?1645912000",
            "https://cards.scryfall.io/large/front/4/c/4cebd725-a5d1-4dc9-959f-92ff17d11be9.jpg?1730229457",
            "https://cards.scryfall.io/large/front/5/0/502f514f-574e-4868-8103-b9fd673228d9.jpg?1730229373",
            "https://cards.scryfall.io/large/front/a/2/a260c1e2-8fc3-4745-bc17-97fcdf5242c3.jpg?1562933316",
            "https://cards.scryfall.io/large/front/b/8/b8d8f428-9a6d-40a1-aa86-e8d37a048dcf.jpg?1677135450",
            "https://cards.scryfall.io/large/front/b/9/b962ca61-ac60-459d-bbdf-19cc99b66c66.jpg?1730229354",
            "https://cards.scryfall.io/large/front/d/c/dce700d1-67f8-4232-9009-2753d662b1a5.jpg?1562548543",
            "https://cards.scryfall.io/large/front/f/c/fc30e04f-2afa-4e3d-a704-dfda7f393a90.jpg?1730229450",
            "https://cards.scryfall.io/normal/front/4/1/412ceddd-2b9a-4551-a6bf-ae2830a2010a.jpg?1559591578",
        ]
        print(f"✅ テスト用 {len(urls)} 個のURLを使用")
    
    if not urls:
        print("❌ URLが指定されていません")
        return
    
    # 出力ディレクトリ
    output_dir = os.path.expanduser("~/Downloads/proxy_cards")
    print(f"\n📁 PDF出力先: {output_dir}")
    
    # PDF生成器を作成
    generator = ProxyCardPDFGenerator()
    
    # URLを9個ずつのバッチに分割
    batches = [urls[i:i+9] for i in range(0, len(urls), 9)]
    print(f"\n📦 {len(batches)} ページのPDFを作成予定")
    
    # 全ての画像バッチを格納するリスト
    all_image_batches = []
    
    # 各バッチを処理して画像を取得
    for batch_num, batch_urls in enumerate(batches, 1):
        print(f"\n🔄 バッチ {batch_num}/{len(batches)} 処理中... ({len(batch_urls)} 枚)")
        
        # 画像をダウンロードしてリサイズ
        images = generator.download_images_batch(batch_urls, force_exact_size)
        
        # 失敗した画像をプレースホルダーで置換
        for i in range(len(images)):
            if images[i] is None:
                print(f"  🔄 #{i+1} プレースホルダー画像を生成中...")
                images[i] = generator.create_placeholder_image()
        
        all_image_batches.append(images)
        print(f"✅ バッチ {batch_num} 完了")
    
    # 単一のPDFを生成（全バッチを含む）
    print(f"\n📄 PDF生成開始...")
    generated_files = generator.generate_pdf(all_image_batches, output_dir)
    
    print(f"\n🎉 全処理完了!")
    print(f"📄 生成されたPDFファイル: {len(generated_files)} 個")
    
    total_size = 0
    for pdf_file in generated_files:
        file_size = os.path.getsize(pdf_file)
        total_size += file_size
        size_mb = file_size / 1024 / 1024
        print(f"  📄 {os.path.basename(pdf_file)}: {size_mb:.1f}MB ({file_size:,} bytes)")
    
    print(f"\n📊 総計:")
    print(f"  📄 PDFファイル数: {len(generated_files)}")
    print(f"  📄 総ページ数: {len(all_image_batches)}")
    print(f"  📊 総サイズ: {total_size / 1024 / 1024:.1f}MB ({total_size:,} bytes)")
    
    print(f"\n📁 出力ディレクトリ: {output_dir}")
    
    # Finderで開く（macOS）
    try:
        os.system(f"open '{output_dir}'")
        print("📂 Finderでフォルダを開きました")
    except:
        pass

if __name__ == "__main__":
    main()