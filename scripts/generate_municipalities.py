#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
import xml.etree.ElementTree as ET


ADMIN_SOURCE_URL = "https://nlftp.mlit.go.jp/ksj/gml/codelist/AdminiBoundary_CD.xlsx"
POSTAL_ROMAN_SOURCE_URL = "https://www.post.japanpost.jp/zipcode/dl/roman/KEN_ALL_ROME.zip"
EXCLUDED_CODES = {"01695", "01696", "01697", "01698", "01699", "01700"}

# Stable slugs for ordinance-designated cities.
DESIGNATED_CITY_SLUG = {
    "札幌市": "sapporo",
    "仙台市": "sendai",
    "さいたま市": "saitama",
    "千葉市": "chiba",
    "横浜市": "yokohama",
    "川崎市": "kawasaki",
    "相模原市": "sagamihara",
    "新潟市": "niigata",
    "静岡市": "shizuoka",
    "浜松市": "hamamatsu",
    "名古屋市": "nagoya",
    "京都市": "kyoto",
    "大阪市": "osaka",
    "堺市": "sakai",
    "神戸市": "kobe",
    "岡山市": "okayama",
    "広島市": "hiroshima",
    "北九州市": "kitakyushu",
    "福岡市": "fukuoka",
    "熊本市": "kumamoto",
}

JP_NAME_OR_KANA = re.compile(r"[\u3041-\u3096\u30A1-\u30FA\u30FC\u4E00-\u9FFF\u3005]")
TRAILING_KATAKANA_RE = re.compile(r"^(.+?)[\u30A1-\u30FA\u30FC]+$")


@dataclass(frozen=True)
class AreaRow:
    code: str
    prefecture: str
    name: str
    kana: str


KANA_DIGRAPH_TO_ROMAJI = {
    "キャ": "kya",
    "キュ": "kyu",
    "キョ": "kyo",
    "シャ": "sha",
    "シュ": "shu",
    "ショ": "sho",
    "チャ": "cha",
    "チュ": "chu",
    "チョ": "cho",
    "ニャ": "nya",
    "ニュ": "nyu",
    "ニョ": "nyo",
    "ヒャ": "hya",
    "ヒュ": "hyu",
    "ヒョ": "hyo",
    "ミャ": "mya",
    "ミュ": "myu",
    "ミョ": "myo",
    "リャ": "rya",
    "リュ": "ryu",
    "リョ": "ryo",
    "ギャ": "gya",
    "ギュ": "gyu",
    "ギョ": "gyo",
    "ジャ": "ja",
    "ジュ": "ju",
    "ジョ": "jo",
    "ビャ": "bya",
    "ビュ": "byu",
    "ビョ": "byo",
    "ピャ": "pya",
    "ピュ": "pyu",
    "ピョ": "pyo",
}

KANA_TO_ROMAJI = {
    "ア": "a",
    "イ": "i",
    "ウ": "u",
    "エ": "e",
    "オ": "o",
    "カ": "ka",
    "キ": "ki",
    "ク": "ku",
    "ケ": "ke",
    "コ": "ko",
    "サ": "sa",
    "シ": "shi",
    "ス": "su",
    "セ": "se",
    "ソ": "so",
    "タ": "ta",
    "チ": "chi",
    "ツ": "tsu",
    "テ": "te",
    "ト": "to",
    "ナ": "na",
    "ニ": "ni",
    "ヌ": "nu",
    "ネ": "ne",
    "ノ": "no",
    "ハ": "ha",
    "ヒ": "hi",
    "フ": "fu",
    "ヘ": "he",
    "ホ": "ho",
    "マ": "ma",
    "ミ": "mi",
    "ム": "mu",
    "メ": "me",
    "モ": "mo",
    "ヤ": "ya",
    "ユ": "yu",
    "ヨ": "yo",
    "ラ": "ra",
    "リ": "ri",
    "ル": "ru",
    "レ": "re",
    "ロ": "ro",
    "ワ": "wa",
    "ヲ": "o",
    "ン": "n",
    "ガ": "ga",
    "ギ": "gi",
    "グ": "gu",
    "ゲ": "ge",
    "ゴ": "go",
    "ザ": "za",
    "ジ": "ji",
    "ズ": "zu",
    "ゼ": "ze",
    "ゾ": "zo",
    "ダ": "da",
    "ヂ": "ji",
    "ヅ": "zu",
    "デ": "de",
    "ド": "do",
    "バ": "ba",
    "ビ": "bi",
    "ブ": "bu",
    "ベ": "be",
    "ボ": "bo",
    "パ": "pa",
    "ピ": "pi",
    "プ": "pu",
    "ペ": "pe",
    "ポ": "po",
    "ァ": "a",
    "ィ": "i",
    "ゥ": "u",
    "ェ": "e",
    "ォ": "o",
    "ャ": "ya",
    "ュ": "yu",
    "ョ": "yo",
}


def normalize_name(raw: str) -> str:
    name = raw.replace("\n", "").strip()
    match = TRAILING_KATAKANA_RE.match(name)
    if match:
        head = match.group(1)
        if JP_NAME_OR_KANA.search(head):
            name = head
    return name


def normalize_kana(raw: str) -> str:
    return raw.replace("\n", "").replace(" ", "").replace("　", "").strip()


def normalize_city_text(raw: str) -> str:
    return raw.replace(" ", "").replace("　", "").strip()


def kana_to_romaji(kana: str) -> str:
    s = unicodedata.normalize("NFKC", kana).replace("・", "").replace("　", "").replace(" ", "")
    out: list[str] = []
    i = 0
    geminate = False
    while i < len(s):
        ch = s[i]
        if ch == "ッ":
            geminate = True
            i += 1
            continue
        if ch == "ー":
            if out and out[-1] and out[-1][-1] in "aeiou":
                out[-1] += out[-1][-1]
            i += 1
            continue

        token = ""
        if i + 1 < len(s):
            pair = s[i : i + 2]
            if pair in KANA_DIGRAPH_TO_ROMAJI:
                token = KANA_DIGRAPH_TO_ROMAJI[pair]
                i += 2
        if not token:
            token = KANA_TO_ROMAJI.get(ch, "")
            i += 1
        if not token:
            continue

        if geminate:
            out.append("t" if token.startswith(("ch", "sh", "j")) else token[0])
            geminate = False
        out.append(token)
    return "".join(out)


def strip_admin_suffix_kana(name: str, kana: str) -> str:
    norm_kana = unicodedata.normalize("NFKC", kana)
    suffix_kana = ""
    if name.endswith("市"):
        suffix_kana = "シ"
    elif name.endswith("区"):
        suffix_kana = "ク"
    elif name.endswith("町"):
        if norm_kana.endswith("チョウ"):
            suffix_kana = "チョウ"
        elif norm_kana.endswith("マチ"):
            suffix_kana = "マチ"
    elif name.endswith("村"):
        if norm_kana.endswith("ムラ"):
            suffix_kana = "ムラ"
        elif norm_kana.endswith("ソン"):
            suffix_kana = "ソン"
    if suffix_kana and norm_kana.endswith(suffix_kana):
        return norm_kana[: -len(suffix_kana)]
    return norm_kana


def slug_from_kana(name: str, kana: str) -> str:
    return kana_to_romaji(strip_admin_suffix_kana(name, kana))


def area_type(name: str) -> str:
    if name.endswith("市") or name.endswith("区"):
        return "city"
    if name.endswith("町"):
        return "town"
    if name.endswith("村"):
        return "vill"
    return "city"


def slug_from_postal_roman(raw_city_en: str) -> str:
    cleaned = re.sub(r"[^A-Z ]+", " ", raw_city_en.upper())
    tokens = [t for t in cleaned.split() if t]
    suffix = {"SHI", "KU", "CHO", "MACHI", "SON", "MURA"}
    while tokens and tokens[-1] in suffix:
        tokens.pop()
    if "GUN" in tokens:
        # "ORA GUN OIZUMI MACHI" -> "OIZUMI"
        tokens = tokens[tokens.index("GUN") + 1 :]
    return "".join(tokens).lower()


def read_sheet_rows_from_xlsx(url: str) -> list[AreaRow]:
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    raw = urlopen(url, timeout=30).read()
    zf = zipfile.ZipFile(io.BytesIO(raw))

    shared_strings: list[str] = []
    if "xl/sharedStrings.xml" in zf.namelist():
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", ns):
            shared_strings.append("".join(t.text or "" for t in si.findall(".//m:t", ns)))

    sheet = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
    out: list[AreaRow] = []
    for row in sheet.findall(".//m:sheetData/m:row", ns):
        cols: list[str] = []
        for cell in row.findall("m:c", ns):
            t = cell.attrib.get("t")
            v = cell.find("m:v", ns)
            if v is None:
                cols.append("")
                continue
            value = v.text or ""
            if t == "s":
                value = shared_strings[int(value)]
            cols.append(value)

        if len(cols) < 6 or not cols[0].isdigit() or cols[5].strip():
            continue
        code = cols[0].zfill(5)
        prefecture = normalize_name(cols[1]) if len(cols) > 1 else ""
        name = normalize_name(cols[2]) if len(cols) > 2 else ""
        kana = normalize_kana(cols[4]) if len(cols) > 4 else ""
        if name:
            out.append(AreaRow(code=code, prefecture=prefecture, name=name, kana=kana))
    return out


def read_postal_slug_map(url: str) -> dict[tuple[str, str], str]:
    raw = urlopen(url, timeout=60).read()
    zf = zipfile.ZipFile(io.BytesIO(raw))
    csv_name = next((n for n in zf.namelist() if n.upper().endswith(".CSV")), None)
    if not csv_name:
        raise RuntimeError("Could not find postal CSV in ZIP")

    text = zf.read(csv_name).decode("cp932")
    counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 6:
            continue
        pref_ja = normalize_name(row[1])
        city_ja = normalize_city_text(row[2])
        city_en = row[5].strip()
        if not pref_ja or not city_ja or not city_en:
            continue
        slug = slug_from_postal_roman(city_en)
        if slug:
            counts[(pref_ja, city_ja)][slug] += 1

    out: dict[tuple[str, str], str] = {}
    for key, ctr in counts.items():
        out[key] = ctr.most_common(1)[0][0]
        pref, city = key
        if "郡" in city:
            short_city = city.split("郡", 1)[1]
            if short_city:
                out.setdefault((pref, short_city), out[key])
    return out


def choose_slug(
    row: AreaRow,
    postal_slug_map: dict[tuple[str, str], str],
    designated_city_override: str | None = None,
) -> str:
    if designated_city_override:
        return designated_city_override
    slug = postal_slug_map.get((row.prefecture, row.name))
    if slug:
        return slug
    return slug_from_kana(row.name, row.kana)


def main() -> None:
    rows = read_sheet_rows_from_xlsx(ADMIN_SOURCE_URL)
    postal_slug_map = read_postal_slug_map(POSTAL_ROMAN_SOURCE_URL)
    code_to_row = {row.code: row for row in rows}

    designated_ward_codes: set[str] = set()
    city_to_wards: dict[str, list[AreaRow]] = {}
    for row in rows:
        if not row.name.endswith("市"):
            continue
        prefix = row.code[:3]
        wards = [
            r
            for r in rows
            if r.code != row.code and r.code[:3] == prefix and r.name.startswith(row.name) and r.name.endswith("区")
        ]
        if wards:
            designated_ward_codes.update(r.code for r in wards)
            city_to_wards[row.name] = sorted(wards, key=lambda x: x.code)

    municipalities: list[AreaRow] = []
    for code, row in sorted(code_to_row.items()):
        if code in EXCLUDED_CODES or code in designated_ward_codes:
            continue
        municipalities.append(row)

    municipalities_payload: list[dict[str, object]] = []
    for row in municipalities:
        designated_override = DESIGNATED_CITY_SLUG.get(row.name)
        city_slug = choose_slug(row, postal_slug_map, designated_city_override=designated_override)
        item: dict[str, object] = {
            "code": row.code,
            "name": row.name,
            "kana": row.kana,
            "slug": city_slug,
            "type": area_type(row.name),
        }

        wards = city_to_wards.get(row.name, [])
        if wards:
            ward_entries: list[dict[str, str]] = []
            for ward in wards:
                short_name = ward.name[len(row.name) :] if ward.name.startswith(row.name) else ward.name
                short_kana = ward.kana[len(row.kana) :] if ward.kana.startswith(row.kana) else ward.kana

                full_ward_slug = postal_slug_map.get((ward.prefecture, ward.name))
                if full_ward_slug and full_ward_slug.startswith(city_slug):
                    ward_slug = full_ward_slug[len(city_slug) :]
                    if ward_slug.startswith("shi"):
                        ward_slug = ward_slug[3:]
                    if not ward_slug:
                        ward_slug = slug_from_kana(short_name, short_kana)
                elif full_ward_slug:
                    ward_slug = full_ward_slug
                else:
                    ward_slug = slug_from_kana(short_name, short_kana)

                ward_entries.append(
                    {
                        "code": ward.code,
                        "name": short_name,
                        "kana": short_kana,
                        "slug": ward_slug,
                        "type": area_type(short_name),
                    }
                )
            item["wards"] = ward_entries

        municipalities_payload.append(item)

    out_root = Path("data")
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "municipalities.json").write_text(
        json.dumps(
            {
                "source_url": ADMIN_SOURCE_URL,
                "slug_source_url": POSTAL_ROMAN_SOURCE_URL,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "municipalities": municipalities_payload,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Wrote data/municipalities.json ({len(municipalities_payload)} municipalities)")


if __name__ == "__main__":
    main()
