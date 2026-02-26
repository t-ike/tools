"""
Moxfield デッキから Scryfall 経由で日本語カード情報を取得し CSV 出力するスクリプト

Usage:
    python fetch_deck.py <deck_code>
"""

import argparse
import csv
import sys
import time
from typing import Optional

import cloudscraper
import requests

# Moxfield は Cloudflare Bot Protection が有効なため cloudscraper を使用
_mox_scraper = cloudscraper.create_scraper()

# ── 定数 ────────────────────────────────────────────────────────────────
MOXFIELD_DECK_API = "https://api2.moxfield.com/v3/decks/all/{deck_code}"
SCRYFALL_NAMED_API = "https://api.scryfall.com/cards/named"
OUTPUT_FILE = "mtg_cards.csv"
CSV_COLUMNS = [
    "card_name_ja",
    "card_name_en",
    "oracle_id",
    "set_code",
    "is_japanese",
    "image_url",
    "scryfall_uri",
    "all_set_codes",
]
REQUEST_DELAY = 0.1   # Scryfall 推奨: 50-100ms


# ── Moxfield ────────────────────────────────────────────────────────────

def fetch_deck_card_names(deck_code: str) -> list[str]:
    """
    Moxfield の公開デッキから mainboard の英語カード名を取得する。
    重複は除外する。
    """
    url = MOXFIELD_DECK_API.format(deck_code=deck_code)
    print(f"[Moxfield] デッキ取得: {url}")
    resp = _mox_scraper.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # v3 API: boards.mainboard.cards.{key}.card.name
    names: set[str] = set()
    boards = data.get("boards") or {}
    board = boards.get("mainboard") or {}
    for entry in (board.get("cards") or {}).values():
        card_obj = entry.get("card") or {}
        name = card_obj.get("name", "").strip()
        if name:
            names.add(name)

    print(f"[Moxfield] カード {len(names)} 枚（重複除外済み）")
    return sorted(names)


# ── Scryfall ─────────────────────────────────────────────────────────────

def fetch_base_card(card_name: str) -> Optional[dict]:
    """
    /cards/named?exact={card_name} でベースカード情報を取得する。
    """
    resp = requests.get(
        SCRYFALL_NAMED_API,
        params={"exact": card_name},
        timeout=30,
    )
    if resp.status_code == 404:
        print(f"  [WARN] '{card_name}' が Scryfall で見つかりません")
        return None
    resp.raise_for_status()
    return resp.json()


def fetch_all_prints(prints_search_uri: str) -> list[dict]:
    """
    prints_search_uri を使って全再録を取得する（ページング対応）。
    include_multilingual=1 を付けて日本語版も含める。
    """
    # デフォルトは英語のみ返るため、多言語版を含めるパラメータを追加
    sep = "&" if "?" in prints_search_uri else "?"
    base_url = prints_search_uri + sep + "include_multilingual=1"

    all_prints: list[dict] = []
    url: Optional[str] = base_url

    while url:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        page_data = resp.json()
        all_prints.extend(page_data.get("data", []))
        url = page_data.get("next_page")
        if url:
            time.sleep(REQUEST_DELAY)

    return all_prints


def get_image_url_for_face(card: dict, face_index: int = 0) -> str:
    """
    指定した面の PNG 画像 URL を返す。
    - 単面カード: face_index を無視してそのまま返す
    - 両面カード: card_faces[face_index] の image_uris を参照
    """
    if "image_uris" in card:
        # 単面カード（face_index は無視）
        return card["image_uris"].get("png", "")
    faces = card.get("card_faces", [])
    if face_index < len(faces) and "image_uris" in faces[face_index]:
        return faces[face_index]["image_uris"].get("png", "")
    return ""


def pick_best_print(prints: list[dict]) -> dict:
    """
    全 print の中から最適なカードを選ぶ。

    優先度:
      1. 日本語版が存在するセットに絞る
      2. その中で言語バリエーション数が最多のセットを選ぶ
         （大型セットほど多言語対応しており、品質の高い印刷が多い）
      3. 言語数が同数の場合は released_at が最新のセットを選ぶ
      4. 日本語なし → 英語版の中で released_at 最新を返す
    """
    from collections import defaultdict

    # set_code ごとにグループ化
    set_prints: dict[str, list[dict]] = defaultdict(list)
    for p in prints:
        code = p.get("set", "")
        if code:
            set_prints[code].append(p)

    # 日本語版を含むセットだけ残す
    ja_sets = {
        code: ps
        for code, ps in set_prints.items()
        if any(p.get("lang") == "ja" for p in ps)
    }

    if ja_sets:
        def set_score(item: tuple[str, list[dict]]) -> tuple[int, str]:
            _, ps = item
            lang_count = len({p.get("lang") for p in ps})
            ja_card = next(p for p in ps if p.get("lang") == "ja")
            return (lang_count, ja_card.get("released_at", ""))

        _, best_ps = max(ja_sets.items(), key=set_score)
        return next(p for p in best_ps if p.get("lang") == "ja")

    # 日本語なし → 英語版の最新
    en_prints = [p for p in prints if p.get("lang") == "en"]
    if en_prints:
        return max(en_prints, key=lambda p: p.get("released_at", ""))

    return prints[0]


def get_card_name_ja(card: dict, face_index: int = 0) -> str:
    """
    指定した面の日本語印刷名 (printed_name) を返す。
    日本語でない場合は英語名にフォールバックする。
    """
    if card.get("lang") == "ja":
        faces = card.get("card_faces", [])
        if faces:
            face = faces[face_index] if face_index < len(faces) else faces[0]
            return face.get("printed_name") or face.get("name", "")
        if "printed_name" in card:
            return card["printed_name"]
    # 英語フォールバック
    faces = card.get("card_faces", [])
    if faces:
        face = faces[face_index] if face_index < len(faces) else faces[0]
        return face.get("name", "")
    return card.get("name", "")


def build_card_rows(base_card: dict, prints: list[dict]) -> list[dict]:
    """
    CSV 行データを組み立てる。
    両面カードは表面・裏面それぞれ1行ずつ返す。
    """
    best = pick_best_print(prints)
    is_japanese = best.get("lang") == "ja"
    all_set_codes = "|".join(sorted({p.get("set", "") for p in prints} - {""}))

    faces = best.get("card_faces", [])
    is_double_faced = len(faces) >= 2 and "image_uris" not in best

    base = {
        "card_name_en": base_card.get("name", ""),
        "oracle_id": best.get("oracle_id", ""),
        "set_code": best.get("set", ""),
        "is_japanese": is_japanese,
        "scryfall_uri": best.get("scryfall_uri", ""),
        "all_set_codes": all_set_codes,
    }

    if is_double_faced:
        rows = []
        for i in range(len(faces)):
            face_en = faces[i].get("name", "")
            rows.append({
                **base,
                "card_name_ja": get_card_name_ja(best, face_index=i),
                "card_name_en": face_en,
                "image_url": get_image_url_for_face(best, face_index=i),
            })
        return rows

    return [{
        **base,
        "card_name_ja": get_card_name_ja(best),
        "image_url": get_image_url_for_face(best),
    }]


# ── CSV 出力 ─────────────────────────────────────────────────────────────

def write_csv(rows: list[dict], output_path: str) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n[完了] {output_path} に {len(rows)} 件を出力しました")


# ── メイン ───────────────────────────────────────────────────────────────

def main(deck_code: str, output_file: str = OUTPUT_FILE) -> None:
    card_names = fetch_deck_card_names(deck_code)
    rows: list[dict] = []

    for i, name in enumerate(card_names, start=1):
        print(f"[{i}/{len(card_names)}] 処理中: {name}")
        try:
            base_card = fetch_base_card(name)
            if base_card is None:
                continue
            time.sleep(REQUEST_DELAY)

            prints_search_uri = base_card.get("prints_search_uri", "")
            if not prints_search_uri:
                print(f"  [WARN] prints_search_uri が取得できません: {name}")
                continue

            all_prints = fetch_all_prints(prints_search_uri)
            time.sleep(REQUEST_DELAY)

            card_rows = build_card_rows(base_card, all_prints)
            rows.extend(card_rows)
            for row in card_rows:
                print(
                    f"  -> {row['card_name_ja']} / {row['set_code']} "
                    f"/ ja={row['is_japanese']}"
                )

        except requests.HTTPError as e:
            print(f"  [ERROR] HTTP エラー ({name}): {e}")
        except Exception as e:  # noqa: BLE001
            print(f"  [ERROR] 予期しないエラー ({name}): {e}")

    write_csv(rows, output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Moxfield デッキから Scryfall 経由で日本語カード情報を取得し CSV 出力する"
    )
    parser.add_argument("deck_code", help="Moxfield のデッキコード")
    parser.add_argument(
        "-o", "--output",
        default=OUTPUT_FILE,
        metavar="FILE",
        help=f"出力 CSV ファイル名 (デフォルト: {OUTPUT_FILE})",
    )
    args = parser.parse_args()
    main(args.deck_code, args.output)
