#!/usr/bin/env python3
"""Add page-specific anchor TOCs to subject academy detail pages.

The top-level ``과목별학원`` hub and its category hubs are intentionally left
untouched. Every detail page uses the H2 text already rendered in the page, so
the TOC stays consistent with page-specific copy when a generator is rerun.
"""

from __future__ import annotations

import argparse
import html
import re
import struct
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
SUBJECT_ROOT = ROOT / "과목별학원"
MAP_ROOT = ROOT / "assets" / "maps"

SUBJECT_CATEGORIES = (
    "고1수학학원",
    "고1영어학원",
    "고2수학학원",
    "고2영어학원",
    "국영수학원",
    "보습학원",
    "소수정예학원",
    "중1수학학원",
    "중1영어학원",
    "중2수학학원",
    "중2영어학원",
    "중3수학학원",
    "중3영어학원",
    "초3수학학원",
    "초3영어학원",
    "초4수학학원",
    "초4영어학원",
    "초5수학학원",
    "초5영어학원",
    "초6수학학원",
    "초6영어학원",
)
EXPECTED_PER_CATEGORY = 371
DETAIL_STYLESHEET_VERSION = "20260829-1"
TARGET_IDS = (
    "quick-summary",
    "center-information",
    "article",
    "section-01",
    "section-02",
    "section-03",
    "section-04",
    "section-05",
    "section-06",
    "faq",
    "consultation-example",
    "related-pages",
)

TOC_START = "<!-- subject-page-anchor-toc:start -->"
TOC_END = "<!-- subject-page-anchor-toc:end -->"
TOC_BLOCK_RE = re.compile(
    rf"{re.escape(TOC_START)}.*?{re.escape(TOC_END)}",
    re.IGNORECASE | re.DOTALL,
)
TOC_REMOVE_RE = re.compile(
    rf"^[ \t]*{re.escape(TOC_START)}[ \t]*\n.*?"
    rf"^[ \t]*{re.escape(TOC_END)}[ \t]*(?:\n\s*\n)?",
    re.IGNORECASE | re.DOTALL | re.MULTILINE,
)
OPEN_TAG_RE = re.compile(
    r"<(?P<tag>section|article)\b(?P<attrs>[^>]*)>", re.IGNORECASE
)
ID_RE = re.compile(r"\bid\s*=\s*([\"'])(?P<id>[^\"']+)\1", re.IGNORECASE)
ANY_ID_RE = re.compile(r"\bid\s*=\s*([\"'])(?P<id>[^\"']+)\1", re.IGNORECASE)
H2_RE = re.compile(r"<h2\b[^>]*>(?P<body>.*?)</h2>", re.IGNORECASE | re.DOTALL)
MAP_IMG_RE = re.compile(
    r"<img\b(?P<attrs>[^>]*\bsrc\s*=\s*(?P<quote>[\"'])"
    r"(?P<src>[^\"']*assets/maps/[^\"']+)(?P=quote)[^>]*)>",
    re.IGNORECASE,
)
TOC_LINK_RE = re.compile(
    r"<li>\s*<a\s+href=[\"']#(?P<id>[^\"']+)[\"']>.*?"
    r"<span>(?P<label>.*?)</span>\s*</a>\s*</li>",
    re.IGNORECASE | re.DOTALL,
)
SITE_CSS_HREF_RE = re.compile(
    r"(?P<before><link\b[^>]*\bhref\s*=\s*[\"']"
    r"(?P<path>[^\"']*assets/site\.css))"
    r"(?:\?v=[^\"']*)?(?P<after>[\"'][^>]*>)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PageEnhancement:
    source: str
    link_count: int
    map_dimensions_added: int


def visible_text(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(html.unescape(text).split())


def detail_pages() -> tuple[list[Path], dict[str, int]]:
    pages: list[Path] = []
    counts: dict[str, int] = {}
    for category in SUBJECT_CATEGORIES:
        category_pages = sorted(
            (SUBJECT_ROOT / category).glob("*/index.html"),
            key=lambda path: path.as_posix(),
        )
        counts[category] = len(category_pages)
        pages.extend(category_pages)
    return pages, counts


def target_headings(source: str) -> list[tuple[str, str]]:
    openings: dict[str, re.Match[str]] = {}
    for opening in OPEN_TAG_RE.finditer(source):
        id_match = ID_RE.search(opening.group("attrs"))
        if id_match and id_match.group("id") in TARGET_IDS:
            target_id = id_match.group("id")
            if target_id in openings:
                raise ValueError(f"Duplicate target id {target_id!r}")
            openings[target_id] = opening

    missing = [target_id for target_id in TARGET_IDS if target_id not in openings]
    if missing:
        raise ValueError("Missing target ids: " + ", ".join(missing))

    ordered_openings = [openings[target_id] for target_id in TARGET_IDS]
    positions = [opening.start() for opening in ordered_openings]
    if positions != sorted(positions):
        raise ValueError("Target ids are not in the expected document order")

    headings: list[tuple[str, str]] = []
    for index, (target_id, opening) in enumerate(zip(TARGET_IDS, ordered_openings)):
        boundary = (
            ordered_openings[index + 1].start()
            if index + 1 < len(ordered_openings)
            else len(source)
        )
        heading = H2_RE.search(source, opening.end(), boundary)
        if not heading:
            raise ValueError(f"No H2 found for target {target_id!r}")
        label = visible_text(heading.group("body"))
        if not label:
            raise ValueError(f"Empty H2 found for target {target_id!r}")
        headings.append((target_id, label))
    return headings


def toc_markup(headings: list[tuple[str, str]]) -> str:
    items = []
    for number, (target_id, label) in enumerate(headings, start=1):
        items.append(
            "          <li>"
            f'<a href="#{html.escape(target_id, quote=True)}">'
            f'<span class="subject-page-toc-number" aria-hidden="true">{number:02d}</span>'
            f"<span>{html.escape(label)}</span>"
            "</a></li>"
        )
    return (
        f"    {TOC_START}\n"
        '    <nav class="section subject-page-toc" aria-labelledby="subject-page-toc-title">\n'
        '      <div class="subject-page-toc-panel">\n'
        '        <div class="subject-page-toc-heading">\n'
        '          <p class="eyebrow">PAGE CONTENTS</p>\n'
        '          <strong id="subject-page-toc-title">이 페이지에서 확인할 내용</strong>\n'
        '          <p>원하는 항목을 누르면 해당 내용으로 바로 이동합니다.</p>\n'
        "        </div>\n"
        '        <ol class="subject-page-toc-list">\n'
        + "\n".join(items)
        + "\n        </ol>\n"
        + "      </div>\n"
        + "    </nav>\n"
        + f"    {TOC_END}\n\n"
    )


@lru_cache(maxsize=None)
def image_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if data.startswith(b"\xff\xd8"):
        index = 2
        sof_markers = {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }
        while index < len(data):
            while index < len(data) and data[index] != 0xFF:
                index += 1
            while index < len(data) and data[index] == 0xFF:
                index += 1
            if index >= len(data):
                break
            marker = data[index]
            index += 1
            if marker in {0x01, 0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
                continue
            if index + 2 > len(data):
                break
            segment_length = struct.unpack(">H", data[index : index + 2])[0]
            if segment_length < 2 or index + segment_length > len(data):
                break
            if marker in sof_markers and segment_length >= 7:
                height, width = struct.unpack(">HH", data[index + 3 : index + 7])
                return width, height
            index += segment_length
    raise ValueError(f"Unsupported or invalid map image: {path}")


def map_path(src: str) -> Path:
    filename = Path(unquote(src.split("?", 1)[0])).name
    path = MAP_ROOT / filename
    if not path.is_file():
        raise FileNotFoundError(f"Map asset not found: {filename}")
    return path


def add_map_dimensions(source: str) -> tuple[str, int]:
    matches = list(MAP_IMG_RE.finditer(source))
    if len(matches) != 1:
        raise ValueError(f"Expected one visible map image, found {len(matches)}")
    match = matches[0]
    attrs = match.group("attrs")
    has_width = bool(re.search(r"\bwidth\s*=", attrs, re.IGNORECASE))
    has_height = bool(re.search(r"\bheight\s*=", attrs, re.IGNORECASE))
    if has_width != has_height:
        raise ValueError("Map image has only one intrinsic dimension")
    if has_width:
        return source, 0

    width, height = image_dimensions(map_path(match.group("src")))
    tag = match.group(0)
    src_attr = re.search(
        r"\bsrc\s*=\s*([\"'])[^\"']+\1", tag, re.IGNORECASE
    )
    if not src_attr:
        raise ValueError("Map image src attribute not found")
    replacement = (
        tag[: src_attr.end()]
        + f' width="{width}" height="{height}"'
        + tag[src_attr.end() :]
    )
    return source[: match.start()] + replacement + source[match.end() :], 1


def update_stylesheet_version(source: str) -> str:
    matches = list(SITE_CSS_HREF_RE.finditer(source))
    if len(matches) != 1:
        raise ValueError(f"Expected one site stylesheet link, found {len(matches)}")
    return SITE_CSS_HREF_RE.sub(
        rf"\g<before>?v={DETAIL_STYLESHEET_VERSION}\g<after>", source, count=1
    )


def enhance_detail_html_with_stats(original: str) -> PageEnhancement:
    source = original.replace("\r\n", "\n").replace("\r", "\n")
    source = TOC_REMOVE_RE.sub("", source, count=1)
    source = update_stylesheet_version(source)
    headings = target_headings(source)

    quick_summary = next(
        opening
        for opening in OPEN_TAG_RE.finditer(source)
        if (id_match := ID_RE.search(opening.group("attrs")))
        and id_match.group("id") == "quick-summary"
    )
    insertion_point = source.rfind("\n", 0, quick_summary.start()) + 1
    source = source[:insertion_point] + toc_markup(headings) + source[insertion_point:]
    source, map_dimensions_added = add_map_dimensions(source)
    return PageEnhancement(source, len(headings), map_dimensions_added)


def enhance_detail_html(original: str) -> str:
    """Return one generated detail page with its TOC and map dimensions."""
    return enhance_detail_html_with_stats(original).source


def validate_page(source: str) -> list[str]:
    errors: list[str] = []
    if source.count(TOC_START) != 1 or source.count(TOC_END) != 1:
        errors.append("TOC marker count is not exactly one")
        return errors

    toc_match = TOC_BLOCK_RE.search(source)
    if not toc_match:
        errors.append("TOC block missing")
        return errors

    try:
        headings = target_headings(source)
    except Exception as exc:
        errors.append(str(exc))
        return errors

    toc_links = [
        (match.group("id"), visible_text(match.group("label")))
        for match in TOC_LINK_RE.finditer(toc_match.group(0))
    ]
    if toc_links != headings:
        errors.append("TOC link order or label does not match page H2 headings")

    stylesheet_matches = list(SITE_CSS_HREF_RE.finditer(source))
    if len(stylesheet_matches) != 1:
        errors.append(
            f"Expected one site stylesheet link, found {len(stylesheet_matches)}"
        )
    elif (
        stylesheet_matches[0].group(0).count(
            f"site.css?v={DETAIL_STYLESHEET_VERSION}"
        )
        != 1
    ):
        errors.append("Detail stylesheet version is not current")

    all_ids = [match.group("id") for match in ANY_ID_RE.finditer(source)]
    if len(all_ids) != len(set(all_ids)):
        errors.append("Duplicate id found")
    for target_id, _label in headings:
        if all_ids.count(target_id) != 1:
            errors.append(
                f"Anchor target count for {target_id!r} is {all_ids.count(target_id)}"
            )

    quick_position = source.find('id="quick-summary"')
    if quick_position < 0 or toc_match.start() > quick_position:
        errors.append("TOC is not before the quick summary")

    map_matches = list(MAP_IMG_RE.finditer(source))
    if len(map_matches) != 1:
        errors.append(f"Expected one map image, found {len(map_matches)}")
    else:
        attrs = map_matches[0].group("attrs")
        width_match = re.search(r'\bwidth\s*=\s*["\'](\d+)["\']', attrs)
        height_match = re.search(r'\bheight\s*=\s*["\'](\d+)["\']', attrs)
        if not width_match or not height_match:
            errors.append("Map image intrinsic dimensions missing")
        else:
            expected = image_dimensions(map_path(map_matches[0].group("src")))
            actual = (int(width_match.group(1)), int(height_match.group(1)))
            if actual != expected:
                errors.append(
                    f"Map dimensions {actual} do not match intrinsic dimensions {expected}"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Write changes to disk")
    parser.add_argument(
        "--check", action="store_true", help="Fail when detail pages are not current"
    )
    args = parser.parse_args()

    pages, category_counts = detail_pages()
    failures: list[str] = []
    for category, count in category_counts.items():
        if count != EXPECTED_PER_CATEGORY:
            failures.append(
                f"{category}: expected {EXPECTED_PER_CATEGORY} details, found {count}"
            )

    expected_total = len(SUBJECT_CATEGORIES) * EXPECTED_PER_CATEGORY
    if len(pages) != expected_total:
        failures.append(f"Expected {expected_total} detail pages, found {len(pages)}")

    for hub in [SUBJECT_ROOT / "index.html"] + [
        SUBJECT_ROOT / category / "index.html" for category in SUBJECT_CATEGORIES
    ]:
        if not hub.is_file():
            failures.append(f"Hub missing: {hub.relative_to(ROOT)}")
        elif TOC_START in hub.read_text(encoding="utf-8"):
            failures.append(f"Hub unexpectedly contains a TOC: {hub.relative_to(ROOT)}")

    changed = 0
    map_dimensions_added = 0
    link_counts: dict[int, int] = {}
    for path in pages:
        original = path.read_bytes().decode("utf-8")
        newline = "\r\n" if "\r\n" in original else "\n"
        try:
            enhancement = enhance_detail_html_with_stats(original)
            validation_errors = validate_page(enhancement.source)
        except Exception as exc:
            failures.append(f"{path.relative_to(ROOT)}: {exc}")
            continue

        if validation_errors:
            failures.append(
                f"{path.relative_to(ROOT)}: " + "; ".join(validation_errors)
            )
            continue

        link_counts[enhancement.link_count] = (
            link_counts.get(enhancement.link_count, 0) + 1
        )
        map_dimensions_added += enhancement.map_dimensions_added
        serialized = enhancement.source.replace("\n", newline)
        if serialized != original:
            changed += 1
            if args.write:
                path.write_bytes(serialized.encode("utf-8"))

    distribution = ",".join(
        f"{count}:{pages_with_count}"
        for count, pages_with_count in sorted(link_counts.items())
    )
    total_links = sum(count * total for count, total in link_counts.items())
    print(
        f"pages={len(pages)} categories={len(SUBJECT_CATEGORIES)} "
        f"per_category={EXPECTED_PER_CATEGORY}"
    )
    print(f"toc_link_distribution={distribution} total_links={total_links}")
    print(f"map_dimensions_added={map_dimensions_added}")
    print(f"changed={changed} mode={'write' if args.write else 'check' if args.check else 'dry-run'}")

    if failures:
        print(f"failures={len(failures)}", file=sys.stderr)
        for failure in failures[:50]:
            print(failure, file=sys.stderr)
        return 1
    if args.check and changed:
        print("Target pages are not up to date. Run with --write.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
