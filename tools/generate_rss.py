from __future__ import annotations

"""코칭센터.com의 핵심 허브와 최신 상세 페이지로 RSS 2.0 피드를 만든다."""

import html
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "https://xn--zj4b74v1taq8c.com"
FEED_URL = f"{DOMAIN}/rss.xml"
FEED_PATH = ROOT / "rss.xml"
SITEMAP_PATH = ROOT / "sitemap.xml"
KST = timezone(timedelta(hours=9), name="KST")
MAX_ITEMS = 50
ATOM_NS = "http://www.w3.org/2005/Atom"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

FIXED_CORE_PATHS = (
    Path("index.html"),
    Path("학습가이드/index.html"),
    Path("상담문의/index.html"),
    Path("전국학원/index.html"),
    Path("과목별학원/index.html"),
)

REQUIRED_NEW_HUBS = {
    f"{DOMAIN}/%EA%B3%BC%EB%AA%A9%EB%B3%84%ED%95%99%EC%9B%90/"
    f"{category}/"
    for category in (
        "%EC%B4%885%EC%88%98%ED%95%99%ED%95%99%EC%9B%90",
        "%EC%B4%885%EC%98%81%EC%96%B4%ED%95%99%EC%9B%90",
        "%EC%B4%886%EC%88%98%ED%95%99%ED%95%99%EC%9B%90",
        "%EC%B4%886%EC%98%81%EC%96%B4%ED%95%99%EC%9B%90",
    )
}


class PageMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.title_parts: list[str] = []
        self.description = ""
        self.robots = ""
        self.canonical = ""

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            name = values.get("name", "").lower()
            if name == "description":
                self.description = values.get("content", "").strip()
            elif name == "robots":
                self.robots = values.get("content", "").strip()
        elif tag == "link" and "canonical" in values.get("rel", "").lower().split():
            self.canonical = values.get("href", "").strip()

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join("".join(self.title_parts).split())


def sitemap_urls() -> set[str]:
    root = ET.parse(SITEMAP_PATH).getroot()
    return {
        loc.text.strip()
        for loc in root.findall(f"{{{SITEMAP_NS}}}url/{{{SITEMAP_NS}}}loc")
        if loc.text
    }


def page_data(path: Path, now: datetime) -> dict[str, object]:
    parser = PageMetadataParser()
    parser.feed(path.read_text(encoding="utf-8", errors="strict"))
    if not parser.title or not parser.description or not parser.canonical:
        raise ValueError(f"RSS 메타데이터가 비어 있습니다: {path}")
    if "noindex" in parser.robots.lower():
        raise ValueError(f"RSS에 noindex 페이지를 넣을 수 없습니다: {path}")
    if not parser.canonical.startswith(f"{DOMAIN}/"):
        raise ValueError(f"RSS canonical 도메인이 다릅니다: {path}")

    modified = datetime.fromtimestamp(path.stat().st_mtime, KST).replace(microsecond=0)
    if modified > now:
        modified = now
    return {
        "path": path,
        "title": html.unescape(parser.title),
        "description": html.unescape(parser.description),
        "url": parser.canonical,
        "modified": modified,
    }


def core_paths() -> list[Path]:
    category_hubs = sorted((ROOT / "과목별학원").glob("*/index.html"))
    return [ROOT / relative for relative in FIXED_CORE_PATHS] + category_hubs


def select_items(now: datetime) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    used: set[Path] = set()

    for path in core_paths():
        if not path.exists():
            raise FileNotFoundError(f"RSS 핵심 페이지가 없습니다: {path}")
        selected.append(page_data(path, now))
        used.add(path)

    # 한 카테고리의 최근 파일이 피드를 독점하지 않도록 카테고리별 최신 상세를
    # 한 항목씩 순환 선택한다. 21개 카테고리 모두가 RSS에서 발견될 수 있다.
    detail_queues: dict[Path, list[Path]] = {}
    for category_dir in sorted((ROOT / "과목별학원").iterdir()):
        if not category_dir.is_dir():
            continue
        detail_queues[category_dir] = sorted(
            category_dir.glob("*/index.html"),
            key=lambda path: (path.stat().st_mtime_ns, path.as_posix()),
            reverse=True,
        )

    while len(selected) < MAX_ITEMS:
        added_in_round = False
        for category_dir in sorted(detail_queues):
            queue = detail_queues[category_dir]
            while queue:
                path = queue.pop(0)
                if path in used:
                    continue
                try:
                    data = page_data(path, now)
                except ValueError as exc:
                    if "noindex" in str(exc):
                        continue
                    raise
                selected.append(data)
                used.add(path)
                added_in_round = True
                break
            if len(selected) >= MAX_ITEMS:
                break
        if not added_in_round:
            break

    if len(selected) != MAX_ITEMS:
        raise ValueError(f"RSS 항목 수가 {MAX_ITEMS}개가 아닙니다: {len(selected)}")

    links = [str(item["url"]) for item in selected]
    if len(links) != len(set(links)):
        raise ValueError("RSS URL이 중복되었습니다.")
    missing_hubs = REQUIRED_NEW_HUBS - set(links)
    if missing_hubs:
        raise ValueError(f"신규 초5·초6 허브가 RSS에서 누락됐습니다: {missing_hubs}")

    sitemap = sitemap_urls()
    outside_sitemap = set(links) - sitemap
    if outside_sitemap:
        raise ValueError(f"RSS URL이 sitemap에 없습니다: {outside_sitemap}")
    return sorted(
        selected,
        key=lambda item: (item["modified"], item["url"]),
        reverse=True,
    )


def build_feed(items: list[dict[str, object]], now: datetime) -> ET.Element:
    ET.register_namespace("atom", ATOM_NS)
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "코칭센터.com 학습 안내 RSS"
    ET.SubElement(channel, "link").text = f"{DOMAIN}/"
    ET.SubElement(channel, "description").text = (
        "코칭센터.com의 학습가이드와 학년·과목별 지역 학원 안내 최신 항목을 제공합니다."
    )
    ET.SubElement(channel, "language").text = "ko-KR"
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(now)
    ET.SubElement(channel, "generator").text = "코칭센터 정적 RSS 생성기"
    ET.SubElement(channel, "ttl").text = "60"
    ET.SubElement(
        channel,
        f"{{{ATOM_NS}}}link",
        {"href": FEED_URL, "rel": "self", "type": "application/rss+xml"},
    )

    for data in items:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = str(data["title"])
        ET.SubElement(item, "link").text = str(data["url"])
        ET.SubElement(item, "guid", {"isPermaLink": "true"}).text = str(data["url"])
        ET.SubElement(item, "pubDate").text = format_datetime(data["modified"])
        ET.SubElement(item, "description").text = str(data["description"])
    return rss


def validate_written_feed(expected_links: set[str]) -> None:
    root = ET.parse(FEED_PATH).getroot()
    if root.tag != "rss" or root.attrib.get("version") != "2.0":
        raise ValueError("RSS 2.0 루트가 올바르지 않습니다.")
    channel = root.find("channel")
    if channel is None:
        raise ValueError("RSS channel이 없습니다.")
    items = channel.findall("item")
    links = [item.findtext("link", "").strip() for item in items]
    guids = [item.findtext("guid", "").strip() for item in items]
    if len(items) != MAX_ITEMS or set(links) != expected_links:
        raise ValueError("작성된 RSS 항목 집합이 선택 결과와 다릅니다.")
    if links != guids or len(links) != len(set(links)):
        raise ValueError("RSS link/guid가 일치하지 않거나 중복되었습니다.")
    required_fields = ("title", "link", "guid", "pubDate", "description")
    for item in items:
        if any(not item.findtext(field, "").strip() for field in required_fields):
            raise ValueError("RSS item 필수 필드가 비어 있습니다.")
        guid = item.find("guid")
        if guid is None or guid.attrib.get("isPermaLink") != "true":
            raise ValueError("RSS guid 설정이 올바르지 않습니다.")


def main() -> None:
    now = datetime.now(KST).replace(microsecond=0)
    items = select_items(now)
    root = build_feed(items, now)
    ET.indent(root, space="  ")
    xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    FEED_PATH.write_bytes(xml + b"\n")
    validate_written_feed({str(item["url"]) for item in items})
    print(f"rss_items={len(items)}")
    print(f"target={FEED_PATH}")


if __name__ == "__main__":
    main()
