from __future__ import annotations

"""이번에 추가한 초5·초6 수학·영어 URL을 바탕화면 TXT로 내보낸다."""

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SITEMAP = ROOT / "sitemap.xml"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
DISPLAY_DOMAIN = "https://코칭센터.com"
CATEGORIES = (
    "초5수학학원",
    "초5영어학원",
    "초6수학학원",
    "초6영어학원",
)
EXPECTED_PER_CATEGORY = 372
EXPECTED_TOTAL = len(CATEGORIES) * EXPECTED_PER_CATEGORY
DEFAULT_OUTPUT = (
    Path.home() / "Desktop" / "코칭센터.com_초5·초6_신규_URL_1488개.txt"
)


def sitemap_urls() -> list[str]:
    root = ET.parse(SITEMAP).getroot()
    return [
        loc.text.strip()
        for loc in root.findall(f"{{{SITEMAP_NS}}}url/{{{SITEMAP_NS}}}loc")
        if loc.text
    ]


def local_file(decoded_path: str) -> Path:
    parts = [part for part in decoded_path.strip("/").split("/") if part]
    return ROOT.joinpath(*parts, "index.html")


def collect_urls() -> list[str]:
    selected: list[tuple[str, str]] = []
    counts = {category: 0 for category in CATEGORIES}

    for encoded_url in sitemap_urls():
        parsed = urlsplit(encoded_url)
        decoded_path = unquote(parsed.path)
        parts = [part for part in decoded_path.strip("/").split("/") if part]
        if len(parts) not in {2, 3} or parts[0] != "과목별학원":
            continue
        category = parts[1]
        if category not in counts:
            continue

        source_path = local_file(decoded_path)
        if not source_path.exists():
            raise FileNotFoundError(f"URL에 해당하는 HTML이 없습니다: {source_path}")
        source = source_path.read_text(encoding="utf-8", errors="strict")
        if re.search(
            r'<meta\s+name=["\']robots["\']\s+content=["\'][^"\']*noindex',
            source,
            flags=re.I,
        ):
            raise ValueError(f"noindex URL이 신규 목록에 포함됐습니다: {encoded_url}")
        canonical_match = re.search(
            r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)',
            source,
            flags=re.I,
        )
        if not canonical_match or canonical_match.group(1) != encoded_url:
            raise ValueError(f"canonical과 sitemap URL이 다릅니다: {source_path}")

        display_url = f"{DISPLAY_DOMAIN}{decoded_path}"
        selected.append((category, display_url))
        counts[category] += 1

    if any(count != EXPECTED_PER_CATEGORY for count in counts.values()):
        raise ValueError(f"카테고리별 URL 수가 예상과 다릅니다: {counts}")
    if len(selected) != EXPECTED_TOTAL:
        raise ValueError(f"신규 URL 수가 {EXPECTED_TOTAL}개가 아닙니다: {len(selected)}")

    order = {category: index for index, category in enumerate(CATEGORIES)}
    selected.sort(
        key=lambda item: (
            order[item[0]],
            item[1].count("/"),
            len(item[1]),
            item[1],
        )
    )
    urls = [url for _, url in selected]
    if len(urls) != len(set(urls)):
        raise ValueError("신규 URL 목록에 중복이 있습니다.")
    return urls


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    urls = collect_urls()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = "\r\n".join(urls) + "\r\n"
    args.output.write_bytes(b"\xef\xbb\xbf" + payload.encode("utf-8"))
    print(f"exported_urls={len(urls)}")
    print(f"target={args.output}")


if __name__ == "__main__":
    main()
