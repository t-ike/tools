#!/usr/bin/env python3
"""
Cube Cobra APIからキューブリストの画像URLを取得するスクリプト

使用例:
  python cube_image_extractor_api.py "https://www.cubecobra.com/cube/list/48c4bc57-d95c-4226-9c4d-05f140bed38c" --color "White" -o white_cards.txt
  python cube_image_extractor_api.py "https://www.cubecobra.com/cube/list/48c4bc57-d95c-4226-9c4d-05f140bed38c" --color "Lands" -o lands.txt
"""

import requests
import json
import sys
import argparse
import re
import os
from pathlib import Path
from typing import List, Dict, Any, Optional


class CubeCobraAPIExtractor:
    """Cube Cobra APIからカードイメージURLを抽出するクラス"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def extract_cube_id_from_url(self, cube_url: str) -> str:
        """URLからキューブIDを抽出"""
        # URL例: https://www.cubecobra.com/cube/list/48c4bc57-d95c-4226-9c4d-05f140bed38c
        match = re.search(r'/cube/list/([a-f0-9-]+)', cube_url)
        if match:
            return match.group(1)
        else:
            raise ValueError(f"無効なCube CobraのURL: {cube_url}")

    def get_cube_data_via_api(self, cube_id: str) -> Dict[str, Any]:
        """Cube Cobra APIを使ってキューブデータを取得"""
        
        api_url = f"https://cubecobra.com/cube/api/cubeJSON/{cube_id}"
        
        try:
            print(f"APIからデータを取得中: {api_url}")
            response = self.session.get(api_url, timeout=30)
            response.raise_for_status()
            
            cube_data = response.json()
            return cube_data
            
        except requests.exceptions.RequestException as e:
            print(f"APIリクエストエラー: {e}", file=sys.stderr)
            return {}
        except json.JSONDecodeError as e:
            print(f"JSONデコードエラー: {e}", file=sys.stderr)
            return {}

    def get_card_color_category(self, card: Dict[str, Any]) -> Optional[str]:
        """カードの色カテゴリを取得（新しい優先順位付き）"""
        
        # 1. colorCategory があればそちらを採用（nullでない場合）
        if card.get('colorCategory') and card.get('colorCategory') != 'null':
            return card.get('colorCategory')
        
        # 2. type_line に Land を含むものは Lands に分類
        type_line = card.get('type_line', '')
        if 'Land' in type_line:
            return 'Lands'
        
        # 3. colors があり、1色だけであればそちらを採用
        colors = card.get('colors')
        if colors and isinstance(colors, list) and len(colors) == 1:
            color_mapping = {
                'W': 'White',
                'U': 'Blue', 
                'B': 'Black',
                'R': 'Red',
                'G': 'Green'
            }
            single_color = colors[0]
            if single_color in color_mapping:
                return color_mapping[single_color]
        
        # 4. colors が null または 2色以上ある場合は、details.colorcategory を採用
        if colors is None or (isinstance(colors, list) and len(colors) != 1):
            if 'details' in card and card['details'].get('colorcategory'):
                return card['details'].get('colorcategory')
        
        # どれも該当しない場合はNone
        return None

    def check_card_color_category(self, card: Dict[str, Any], target_color: str) -> bool:
        """カードが指定された色カテゴリに一致するかチェック"""
        
        card_color_category = self.get_card_color_category(card)
        
        if card_color_category:
            return target_color.lower() == card_color_category.lower()
        
        return False

    def extract_cards_by_color(self, cube_data: Dict[str, Any], target_colors: List[str]) -> List[Dict[str, Any]]:
        """指定された色カテゴリ（複数可）のカードを抽出"""
        
        if 'cards' not in cube_data or 'mainboard' not in cube_data['cards']:
            print("カードデータが見つかりません", file=sys.stderr)
            return []
        
        all_cards = cube_data['cards']['mainboard']
        matched_cards = []
        unclassified_cards = []
        
        # 全カード指定の場合
        if 'all' in [color.lower() for color in target_colors]:
            print(f"\n✅ 全カードを抽出: {len(all_cards)}枚")
            return all_cards
        
        # カテゴリ別の統計
        category_counts = {}
        
        for card in all_cards:
            card_color_category = self.get_card_color_category(card)
            
            if card_color_category is None:
                # 分類できないカードをリストアップ
                card_name = card.get('name', 'Unknown')
                if 'details' in card:
                    card_name = card['details'].get('name', card_name)
                unclassified_cards.append(card_name)
            else:
                # 統計更新
                category_counts[card_color_category] = category_counts.get(card_color_category, 0) + 1
                
                # 指定されたカテゴリのいずれかに一致するかチェック
                for target_color in target_colors:
                    if self.check_card_color_category(card, target_color):
                        matched_cards.append(card)
                        break
        
        # 分類できないカードがあれば出力
        if unclassified_cards:
            print(f"\n⚠️  色カテゴリが特定できないカード ({len(unclassified_cards)}枚):")
            for i, name in enumerate(unclassified_cards, 1):
                print(f"  {i}: {name}")
        
        # 統計情報を表示
        if len(target_colors) == 1:
            print(f"\n✅ {target_colors[0]}カテゴリのカード: {len(matched_cards)}枚")
        else:
            print(f"\n✅ 指定カテゴリ ({', '.join(target_colors)}) のカード: {len(matched_cards)}枚")
            print("\n📊 各カテゴリの内訳:")
            for category, count in sorted(category_counts.items()):
                if any(self.check_card_color_category({'colorCategory': category}, target_color) for target_color in target_colors):
                    print(f"  {category}: {count}枚")
        
        return matched_cards

    def extract_image_urls(self, cards: List[Dict[str, Any]]) -> List[str]:
        """カードリストから画像URLを抽出"""
        
        image_urls = []
        
        for card in cards:
            image_url = None
            
            # 複数の画像URLフィールドをチェック（優先順位付き）
            if 'imgUrl' in card and card['imgUrl']:
                image_url = card['imgUrl']
            elif 'details' in card:
                details = card['details']
                if 'image_normal' in details and details['image_normal']:
                    image_url = details['image_normal']
                elif 'image_small' in details and details['image_small']:
                    image_url = details['image_small']
                elif 'art_crop' in details and details['art_crop']:
                    image_url = details['art_crop']
                elif 'image_uris' in details:
                    image_uris = details['image_uris']
                    if isinstance(image_uris, dict):
                        image_url = image_uris.get('normal', image_uris.get('large', image_uris.get('small')))
                    elif isinstance(image_uris, str):
                        image_url = image_uris
            
            if image_url:
                image_urls.append(image_url)
        
        return image_urls

    def save_image_urls_to_file(self, image_urls: List[str], output_file: str):
        """画像URLをファイルに保存"""
        
        try:
            # outputディレクトリを作成
            output_dir = Path('output')
            output_dir.mkdir(exist_ok=True)
            
            # 出力ファイルのパスを調整
            output_path = output_dir / output_file
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for url in image_urls:
                    f.write(url + '\n')
            
            print(f"\n✅ {len(image_urls)}個の画像URLを {output_path} に保存しました")
            
            if image_urls:
                print(f"\n取得した画像URL（最初の5個）:")
                for i, url in enumerate(image_urls[:5], 1):
                    print(f"  {i}: {url}")
                if len(image_urls) > 5:
                    print(f"  ...他 {len(image_urls) - 5} 個")
                    
        except Exception as e:
            print(f"ファイル保存エラー: {e}", file=sys.stderr)

    def get_card_images(self, cube_url: str, target_colors: List[str], output_file: str = None):
        """メイン処理：指定された色カテゴリ（複数可）の画像URLを取得"""
        
        try:
            # URLからキューブIDを抽出
            cube_id = self.extract_cube_id_from_url(cube_url)
            print(f"キューブID: {cube_id}")
            
            # APIからデータを取得
            cube_data = self.get_cube_data_via_api(cube_id)
            
            if not cube_data:
                print("キューブデータの取得に失敗しました", file=sys.stderr)
                return []
            
            # キューブの基本情報を表示
            cube_name = cube_data.get('name', 'Unknown')
            total_cards = len(cube_data.get('cards', {}).get('mainboard', []))
            print(f"キューブ名: {cube_name}")
            print(f"総カード数: {total_cards}")
            
            # 指定色のカードを抽出
            cards = self.extract_cards_by_color(cube_data, target_colors)
            
            if not cards:
                colors_str = ', '.join(target_colors)
                print(f"{colors_str}カテゴリのカードが見つかりませんでした", file=sys.stderr)
                return []
            
            # 画像URLを抽出
            image_urls = self.extract_image_urls(cards)
            
            # ファイルに保存
            if output_file:
                self.save_image_urls_to_file(image_urls, output_file)
            
            return image_urls
            
        except Exception as e:
            print(f"処理エラー: {e}", file=sys.stderr)
            return []


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description='Cube Cobra APIから指定色カテゴリのカード画像URLを取得',
        epilog='例:\n'
               '  %(prog)s "https://www.cubecobra.com/cube/list/48c4bc57-d95c-4226-9c4d-05f140bed38c" --color "White" -o white_cards.txt\n'
               '  %(prog)s "https://cubecobra.com/cube/list/your-cube-id" --color "White,Blue" -o white_blue_cards.txt\n'
               '  %(prog)s "https://cubecobra.com/cube/list/your-cube-id" --color "all" -o all_cards.txt',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('url', help='Cube CobraのキューブリストURL')
    parser.add_argument('--color', required=True,
                       help='取得する色カテゴリ (例: White, Blue, Black, Red, Green, Colorless, Multicolored, Lands, "White,Blue", "all")')
    parser.add_argument('-o', '--output',
                       help='出力ファイル名 (デフォルト: 自動生成)')

    args = parser.parse_args()

    # 色カテゴリを解析（カンマ区切りで複数指定可能）
    target_colors = [color.strip() for color in args.color.split(',')]

    # 出力ファイル名の自動生成
    if not args.output:
        if len(target_colors) == 1:
            if target_colors[0].lower() == 'all':
                args.output = "all_cards_images.txt"
            else:
                color_safe = target_colors[0].lower().replace(' ', '_')
                args.output = f"{color_safe}_images.txt"
        else:
            # 複数色の場合は色名を結合
            colors_safe = '_'.join([color.lower().replace(' ', '_') for color in target_colors])
            args.output = f"{colors_safe}_images.txt"

    print("=== Cube Cobra API 画像URL抽出 ===")
    print(f"URL: {args.url}")
    print(f"色: {', '.join(target_colors)}")
    print(f"出力ファイル: output/{args.output}")
    print("--------------------------------------------------")

    # 抽出処理を実行
    extractor = CubeCobraAPIExtractor()
    image_urls = extractor.get_card_images(args.url, target_colors, args.output)

    if image_urls:
        print(f"\n🎉 処理完了！{len(image_urls)}個の画像URLを取得しました。")
    else:
        print("\n❌ 画像URLの取得に失敗しました。")
        sys.exit(1)


if __name__ == "__main__":
    main()