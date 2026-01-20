#!/usr/bin/env python3
"""
Cube Cobraキューブリストから指定カテゴリのカード画像URLを取得する最終版スクリプト

使用例:
  python cube_image_extractor.py "https://www.cubecobra.com/cube/list/48c4bc57-d95c-4226-9c4d-05f140bed38c" -c "Land" -o lands.txt
  python cube_image_extractor.py "https://www.cubecobra.com/cube/list/48c4bc57-d95c-4226-9c4d-05f140bed38c" -c "Creature" -o creatures.txt
"""

import requests
import json
import sys
import re
import argparse
from typing import List, Dict, Any


class CubeCobraImageExtractor:
    """Cube CobraからカードイメージURLを抽出するクラス"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def extract_react_props(self, url: str) -> Dict[str, Any]:
        """window.reactPropsからデータを抽出"""
        
        try:
            print(f"ページを取得中: {url}", file=sys.stderr)
            response = self.session.get(url)
            response.raise_for_status()
            
            # window.reactPropsのデータを抽出
            pattern = r'window\.reactProps\s*=\s*(\{.*?\});'
            match = re.search(pattern, response.text, re.DOTALL)
            
            if match:
                json_str = match.group(1)
                print("ReactPropsデータを発見しました！", file=sys.stderr)
                
                try:
                    data = json.loads(json_str)
                    return data
                except json.JSONDecodeError as e:
                    print(f"JSON解析エラー: {e}", file=sys.stderr)
                    return {}
            else:
                print("ReactPropsデータが見つかりませんでした", file=sys.stderr)
                return {}
                
        except Exception as e:
            print(f"エラー: {e}", file=sys.stderr)
            return {}

    def extract_cards_by_type(self, cube_data: Dict[str, Any], card_type: str) -> List[Dict[str, Any]]:
        """キューブデータから指定されたタイプのカードを抽出"""
        
        cards = []
        
        try:
            if 'cards' in cube_data and 'mainboard' in cube_data['cards']:
                all_cards = cube_data['cards']['mainboard']
                print(f"総カード数: {len(all_cards)}", file=sys.stderr)
                
                for card in all_cards:
                    # カードのタイプをチェック
                    card_types = []
                    
                    if 'type_line' in card:
                        card_types.append(card['type_line'])
                    if 'details' in card and 'type_line' in card['details']:
                        card_types.append(card['details']['type_line'])
                    if 'details' in card and 'type' in card['details']:
                        card_types.append(card['details']['type'])
                    
                    # 指定されたタイプをチェック
                    is_target_type = False
                    for ct in card_types:
                        if isinstance(ct, str) and card_type.lower() in ct.lower():
                            is_target_type = True
                            break
                    
                    if is_target_type:
                        cards.append(card)
                
                print(f"{card_type}タイプのカード数: {len(cards)}", file=sys.stderr)
                return cards
                
        except Exception as e:
            print(f"カード抽出エラー: {e}", file=sys.stderr)
        
        return cards

    def extract_image_urls(self, cards: List[Dict[str, Any]]) -> List[str]:
        """カードリストから画像URLを抽出"""
        
        image_urls = []
        
        for card in cards:
            image_url = None
            
            # 様々な場所から画像URLを探す（空文字列チェックを追加）
            if 'imgUrl' in card and card['imgUrl'].strip():
                image_url = card['imgUrl']
            elif 'details' in card:
                details = card['details']
                if 'image_normal' in details:
                    image_url = details['image_normal']
                elif 'image_small' in details:
                    image_url = details['image_small']
                elif 'art_crop' in details:
                    image_url = details['art_crop']
                elif 'image_uris' in details:
                    image_uris = details['image_uris']
                    if isinstance(image_uris, dict):
                        image_url = image_uris.get('normal', image_uris.get('large', image_uris.get('small')))
                    elif isinstance(image_uris, str):
                        image_url = image_uris
                elif 'card_faces' in details:
                    # 両面カードの場合
                    faces = details['card_faces']
                    if faces and len(faces) > 0 and 'image_uris' in faces[0]:
                        face_images = faces[0]['image_uris']
                        if isinstance(face_images, dict):
                            image_url = face_images.get('normal', face_images.get('large'))
            
            if image_url:
                image_urls.append(image_url)
        
        return image_urls

    def get_card_images(self, cube_url: str, card_type: str) -> List[str]:
        """メイン処理：指定されたカテゴリの画像URLを取得"""
        
        # ReactPropsデータを抽出
        cube_data = self.extract_react_props(cube_url)
        
        if not cube_data:
            print("キューブデータの抽出に失敗しました", file=sys.stderr)
            return []
        
        # 指定されたタイプのカードを抽出
        cards = self.extract_cards_by_type(cube_data, card_type)
        
        if not cards:
            print(f"{card_type}タイプのカードが見つかりませんでした", file=sys.stderr)
            self._show_available_types(cube_data)
            return []
        
        # 画像URLを抽出
        image_urls = self.extract_image_urls(cards)
        
        return list(set(image_urls))  # 重複を除去

    def _show_available_types(self, cube_data: Dict[str, Any]):
        """利用可能なカードタイプを表示"""
        try:
            if 'cards' in cube_data and 'mainboard' in cube_data['cards']:
                all_cards = cube_data['cards']['mainboard']
                print("\n利用可能なカードタイプの例:", file=sys.stderr)
                type_examples = set()
                for card in all_cards[:50]:  # 最初の50枚をチェック
                    if 'type_line' in card:
                        type_examples.add(card['type_line'])
                    if 'details' in card and 'type_line' in card['details']:
                        type_examples.add(card['details']['type_line'])
                
                for type_example in sorted(type_examples):
                    print(f"  - {type_example}", file=sys.stderr)
        except Exception:
            pass


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description='Cube Cobraから指定カテゴリのカード画像URLを取得',
        epilog='例:\n'
               '  %(prog)s "https://www.cubecobra.com/cube/list/48c4bc57-d95c-4226-9c4d-05f140bed38c" -c "Land"\n'
               '  %(prog)s "https://cubecobra.com/cube/list/your-cube-id" -c "Creature" -o creatures.txt',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('url', help='Cube CobraのキューブリストURL')
    parser.add_argument('-c', '--category', default='Land', 
                       help='取得するカテゴリ名 (デフォルト: Land)')
    parser.add_argument('-o', '--output', 
                       help='出力ファイル名 (デフォルト: <category>_images.txt)')
    parser.add_argument('--debug', action='store_true',
                       help='デバッグモード（キューブデータをJSONで保存）')
    
    args = parser.parse_args()

    # 出力ファイル名の設定
    if not args.output:
        args.output = f"{args.category.lower()}_images.txt"

    extractor = CubeCobraImageExtractor()
    
    try:
        print(f"URL: {args.url}", file=sys.stderr)
        print(f"カテゴリ: {args.category}", file=sys.stderr)
        print(f"出力ファイル: {args.output}", file=sys.stderr)
        print("-" * 50, file=sys.stderr)
        
        image_urls = extractor.get_card_images(args.url, args.category)
        
        if image_urls:
            # ファイルに保存
            with open(args.output, 'w', encoding='utf-8') as f:
                for url in sorted(image_urls):
                    f.write(url + '\n')
            
            print(f"\n✅ {len(image_urls)}個の画像URLを {args.output} に保存しました", file=sys.stderr)
            
            # 最初の数個を表示
            print("\n取得した画像URL（最初の5個）:", file=sys.stderr)
            for i, url in enumerate(sorted(image_urls)[:5], 1):
                print(f"  {i}: {url}", file=sys.stderr)
            
            if len(image_urls) > 5:
                print(f"  ...他 {len(image_urls) - 5} 個", file=sys.stderr)
        else:
            print("❌ 画像URLを取得できませんでした", file=sys.stderr)
            
    except KeyboardInterrupt:
        print("\n処理が中断されました", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()