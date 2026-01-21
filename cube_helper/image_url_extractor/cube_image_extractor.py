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
        """キューブデータを抽出（APIまたはJavaScript変数から）"""
        
        try:
            print(f"ページを取得中: {url}", file=sys.stderr)
            response = self.session.get(url)
            response.raise_for_status()
            
            # URLからキューブIDを抽出
            cube_id = url.split('/')[-1]
            
            # まずAPIエンドポイントを試す（サイレント）
            api_urls = [
                f"https://cubecobra.com/cube/api/cubedata/{cube_id}",
                f"https://cubecobra.com/api/cube/{cube_id}",
                f"https://cubecobra.com/cube/api/cubecardlist/{cube_id}",
                f"https://cubecobra.com/cube/api/cardlist/{cube_id}"
            ]
            
            for api_url in api_urls:
                try:
                    api_response = self.session.get(api_url)
                    if api_response.status_code == 200 and api_response.text.strip():
                        cube_data = api_response.json()
                        if 'cards' in cube_data or 'cardlist' in cube_data or 'mainboard' in cube_data:
                            return cube_data
                except:
                    continue
            
            # APIが失敗した場合、JavaScript変数を探す
            # window.reactPropsのデータを抽出
            pattern = r'window\.reactProps\s*=\s*(\{.*?\});'
            match = re.search(pattern, response.text, re.DOTALL)
            
            if match:
                json_str = match.group(1)
                print("ReactPropsデータを発見しました！", file=sys.stderr)
                
                try:
                    data = json.loads(json_str)
                    
                    # window.cube や他の変数も探してみる
                    cube_pattern = r'window\.cube\s*=\s*(\{.*?\});'
                    cube_match = re.search(cube_pattern, response.text, re.DOTALL)
                    if cube_match:
                        cube_json = cube_match.group(1)
                        cube_data = json.loads(cube_json)
                        return cube_data
                    
                    # window.cubeList も探す
                    cubelist_pattern = r'window\.cubeList\s*=\s*(\{.*?\});'
                    cubelist_match = re.search(cubelist_pattern, response.text, re.DOTALL)
                    if cubelist_match:
                        cubelist_json = cubelist_match.group(1)
                        cubelist_data = json.loads(cubelist_json)
                        return cubelist_data
                    
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
                
                # 検索用の正規化された文字列（末尾のs除去処理を削除）
                search_term = card_type.lower()
                print(f"検索用語: '{search_term}'", file=sys.stderr)
                
                for card in all_cards:
                    # カードのタイプをチェック
                    card_types = []
                    
                    if 'type_line' in card:
                        card_types.append(card['type_line'])
                    if 'details' in card and 'type_line' in card['details']:
                        card_types.append(card['details']['type_line'])
                    if 'details' in card and 'type' in card['details']:
                        card_types.append(card['details']['type'])
                    
                    # 指定されたタイプをチェック（部分一致に戻す）
                    is_target_type = False
                    for ct in card_types:
                        if isinstance(ct, str) and search_term in ct.lower():
                            is_target_type = True
                            break
                    
                    if is_target_type:
                        cards.append(card)
                
                print(f"{card_type}タイプのカード数: {len(cards)}", file=sys.stderr)
                return cards
                
        except Exception as e:
            print(f"カード抽出エラー: {e}", file=sys.stderr)
        
        return cards

    def extract_cards_by_color(self, cube_data: Dict[str, Any], color_category: str) -> List[Dict[str, Any]]:
        """キューブデータから指定された色のカードを抽出"""
        
        cards = []
        
        try:
            if 'cards' in cube_data and 'mainboard' in cube_data['cards']:
                all_cards = cube_data['cards']['mainboard']
                
                for card in all_cards:
                    if self._check_card_color_category_strict(card, color_category):
                        cards.append(card)
                
                return cards
                
        except Exception as e:
            print(f"カード抽出エラー: {e}")
            import traceback
            traceback.print_exc()
        
        return cards

    def _check_card_color_category_strict(self, card: Dict[str, Any], color_category: str) -> bool:
        """厳密にColor Categoryフィールドのみをチェック（推測処理なし）"""
        
        # 全ての可能なColor Categoryフィールドを優先順位付きで探す
        # details.colorcategoryを最優先にする
        possible_fields = [
            card.get('details', {}).get('colorcategory'),      # 最優先
            card.get('colorCategory'),
            card.get('details', {}).get('colorCategory'),
            card.get('color_category'),
            card.get('details', {}).get('color_category'),
        ]
        
        for category_field in possible_fields:
            if category_field is not None:
                if isinstance(category_field, str):
                    return color_category.lower() == category_field.lower()
                elif isinstance(category_field, list):
                    return any(color_category.lower() == str(cat).lower() for cat in category_field)
        
        # Color Categoryフィールドが見つからない場合はFalseを返す
        return False

    def _check_card_color_category(self, card: Dict[str, Any], color_category: str) -> bool:
        """カードが指定された色カテゴリに一致するかチェック（Color Categoryフィールドを使用）"""
        
        # Color Category フィールドを探す（優先順位付き）
        category_field = None
        
        # details.colorcategory を最優先
        if 'details' in card and 'colorcategory' in card['details']:
            category_field = card['details']['colorcategory']
        # 次に colorCategory
        elif 'colorCategory' in card:
            category_field = card['colorCategory']
        # その他の可能性もチェック
        elif 'color_category' in card:
            category_field = card['color_category']
        elif 'details' in card and 'color_category' in card['details']:
            category_field = card['details']['color_category']
        
        # Color Categoryフィールドが見つかった場合のみ判定
        if category_field:
            if isinstance(category_field, str):
                return color_category.lower() == category_field.lower()
            elif isinstance(category_field, list):
                return any(color_category.lower() == str(cat).lower() for cat in category_field)
        
        # Color Categoryフィールドが見つからない場合はFalse
        return False

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

    def get_card_images(self, cube_url: str, card_type: str = None, color_category: str = None) -> List[str]:
        """メイン処理：指定されたカテゴリの画像URLを取得"""
        
        # ReactPropsデータを抽出
        cube_data = self.extract_react_props(cube_url)
        
        if not cube_data:
            print("キューブデータの抽出に失敗しました", file=sys.stderr)
            return []

        cards = []
        
        # タイプまたは色でフィルタ
        if card_type:
            cards = self.extract_cards_by_type(cube_data, card_type)
            filter_desc = f"{card_type}タイプ"
        elif color_category:
            cards = self.extract_cards_by_color(cube_data, color_category)
            filter_desc = f"{color_category}色"
        else:
            # 両方とも指定されていない場合は全カード
            if 'cards' in cube_data and 'mainboard' in cube_data['cards']:
                cards = cube_data['cards']['mainboard']
                filter_desc = "全"
        
        if not cards:
            print(f"{filter_desc}のカードが見つかりませんでした", file=sys.stderr)
            if card_type:
                self._show_available_types(cube_data)
            elif color_category:
                self._show_available_colors(cube_data)
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
                land_types = set()
                
                # 全カードをチェックしてLandタイプを探す
                for card in all_cards:
                    types = []
                    if 'type_line' in card:
                        types.append(card['type_line'])
                    if 'details' in card and 'type_line' in card['details']:
                        types.append(card['details']['type_line'])
                    
                    for t in types:
                        if t:
                            type_examples.add(t)
                            if 'land' in t.lower():
                                land_types.add(t)
                
                # Land系のタイプを優先表示
                if land_types:
                    print("\nLand系のカードタイプ:", file=sys.stderr)
                    for land_type in sorted(land_types):
                        print(f"  - {land_type}", file=sys.stderr)
                
                print("\nその他のカードタイプ（最初の20個）:", file=sys.stderr)
                non_land_types = [t for t in sorted(type_examples) if 'land' not in t.lower()]
                for type_example in non_land_types[:20]:
                    print(f"  - {type_example}", file=sys.stderr)
                    
                print(f"\n総カードタイプ数: {len(type_examples)}", file=sys.stderr)
                print(f"Land系カードタイプ数: {len(land_types)}", file=sys.stderr)
        except Exception as e:
            print(f"タイプ表示エラー: {e}", file=sys.stderr)

    def _show_available_colors(self, cube_data: Dict[str, Any]):
        """利用可能な色カテゴリを表示"""
        try:
            if 'cards' in cube_data and 'mainboard' in cube_data['cards']:
                all_cards = cube_data['cards']['mainboard']
                color_categories = {}
                
                for card in all_cards:
                    # colorCategoryフィールドから実際のカテゴリを取得
                    category = None
                    if 'colorCategory' in card:
                        category = card['colorCategory']
                    elif 'details' in card and 'colorcategory' in card['details']:
                        category = card['details']['colorcategory']
                    
                    if category:
                        if category not in color_categories:
                            color_categories[category] = 0
                        color_categories[category] += 1
                
                print("\n利用可能な色カテゴリ:", file=sys.stderr)
                for category, count in sorted(color_categories.items()):
                    print(f"  - {category}: {count}枚", file=sys.stderr)
                        
                print(f"\n総カウント: {sum(color_categories.values())}枚 / 総カード数: {len(all_cards)}枚", file=sys.stderr)
                print("\nサポートされている色カテゴリ:", file=sys.stderr)
                print("  White, Blue, Black, Red, Green, Colorless, Hybrid, Multicolored, Lands", file=sys.stderr)
        except Exception as e:
            print(f"色情報表示エラー: {e}", file=sys.stderr)


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description='Cube Cobraから指定カテゴリのカード画像URLを取得',
        epilog='例:\n'
               '  %(prog)s "https://www.cubecobra.com/cube/list/48c4bc57-d95c-4226-9c4d-05f140bed38c" -c "Land"\n'
               '  %(prog)s "https://cubecobra.com/cube/list/your-cube-id" -c "Creature" -o creatures.txt\n'
               '  %(prog)s "https://cubecobra.com/cube/list/your-cube-id" --color "red" -o red_cards.txt\n'
               '  %(prog)s "https://cubecobra.com/cube/list/your-cube-id" --color "multicolor" -o multicolor.txt',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('url', help='Cube CobraのキューブリストURL')
    parser.add_argument('-c', '--category', 
                       help='取得するカードタイプ (例: Land, Creature, Instant)')
    parser.add_argument('--color', 
                       help='取得する色カテゴリ (例: white, blue, red, multicolor, colorless)')
    parser.add_argument('-o', '--output', 
                       help='出力ファイル名 (デフォルト: 自動生成)')
    parser.add_argument('--debug', action='store_true',
                       help='デバッグモード（キューブデータをJSONで保存）')
    
    args = parser.parse_args()

    # カテゴリと色の両方が指定されていないかチェック
    if not args.category and not args.color:
        print("エラー: --category (-c) または --color のいずれかを指定してください", file=sys.stderr)
        parser.print_help()
        sys.exit(1)
    
    if args.category and args.color:
        print("エラー: --category (-c) と --color は同時に指定できません", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # 出力ファイル名の設定
    if not args.output:
        if args.category:
            args.output = f"{args.category.lower()}_images.txt"
        elif args.color:
            args.output = f"{args.color.lower()}_images.txt"

    extractor = CubeCobraImageExtractor()
    
    try:
        print(f"URL: {args.url}", file=sys.stderr)
        if args.category:
            print(f"カテゴリ: {args.category}", file=sys.stderr)
        if args.color:
            print(f"色: {args.color}", file=sys.stderr)
        print(f"出力ファイル: {args.output}", file=sys.stderr)
        print("-" * 50, file=sys.stderr)
        
        image_urls = extractor.get_card_images(args.url, 
                                              card_type=args.category, 
                                              color_category=args.color)
        
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