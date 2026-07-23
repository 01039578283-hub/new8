from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote
from zipfile import ZipFile

import generate_korean_english_math_pages as generator


SITE = Path(__file__).resolve().parents[1]
COMMON = SITE.parent / "참고자료" / "공통자료"
ZIP_PATH = Path.home() / "Desktop" / "코칭센터.com 추가 원고" / "국영수학원.zip"
PARENT = "과목별학원"
CATEGORY = "국영수학원"
DOMAIN = "https://xn--zj4b74v1taq8c.com"
TARGET = SITE / PARENT / CATEGORY
REQUIRED_TYPES = {
    "EducationalOrganization",
    "LocalBusiness",
    "WebPage",
    "ImageObject",
    "BreadcrumbList",
    "Article",
    "Service",
    "OfferCatalog",
    "FAQPage",
    "ItemList",
}


def sections(text: str) -> dict[str, str]:
    marker = re.compile(r"^\[([^\]]+)\]\s*$", re.MULTILINE)
    matches = list(marker.finditer(text))
    return {
        match.group(1).strip(): text[
            match.end() : (
                matches[index + 1].start()
                if index + 1 < len(matches)
                else len(text)
            )
        ].strip()
        for index, match in enumerate(matches)
    }


def slug_for(title: str) -> str:
    local = title[: -len(f" {CATEGORY}")].strip()
    return re.sub(r"\s+", "", local)


def canonical_for(slug: str = "") -> str:
    parts = [PARENT, CATEGORY] + ([slug] if slug else [])
    path = "/" + "/".join(parts) + "/"
    return DOMAIN + quote(path, safe="/")


def graph_types(graph: dict) -> set[str]:
    result: set[str] = set()
    for node in graph.get("@graph", []):
        node_type = node.get("@type")
        if isinstance(node_type, list):
            result.update(node_type)
        elif node_type:
            result.add(node_type)
    return result


def graph_node(graph: dict, node_type: str) -> dict:
    for node in graph.get("@graph", []):
        value = node.get("@type")
        if value == node_type or isinstance(value, list) and node_type in value:
            return node
    raise KeyError(node_type)


def asset_path(src: str, page: Path) -> Path:
    clean = src.split("?", 1)[0]
    return (page.parent / clean).resolve()


def main() -> None:
    errors: list[str] = []
    with ZipFile(ZIP_PATH) as archive:
        manuscripts = [
            sections(archive.read(name).decode("utf-8-sig"))
            for name in archive.namelist()
            if name.lower().endswith(".txt")
        ]
    manuscript_by_slug = {
        slug_for(item["페이지타이틀"].strip()): item for item in manuscripts
    }
    with (COMMON / "센터정보 정리.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    generator.enrich_center_rows(rows)
    row_by_slug = {
        re.sub(r"\s+", "", row["근처 수업가능 동네"].strip()): row
        for row in rows
    }

    pages = sorted(
        path
        for path in TARGET.glob("*/index.html")
        if path.parent.name != CATEGORY
    )
    if len(pages) != 371:
        errors.append(f"detail page count={len(pages)}")
    if set(path.parent.name for path in pages) != set(manuscript_by_slug):
        errors.append("detail/manuscript slug set mismatch")

    meta_values: set[str] = set()
    title_values: set[str] = set()
    representative_sources: set[str] = set()
    representative_hashes: set[str] = set()
    organization_ids: set[str] = set()
    total_faq = 0
    for page in pages:
        slug = page.parent.name
        source = page.read_text(encoding="utf-8")
        manuscript = manuscript_by_slug.get(slug)
        row = row_by_slug.get(slug)
        if not manuscript or not row:
            errors.append(f"{slug}: missing source data")
            continue
        title = manuscript["페이지타이틀"].strip()
        canonical = canonical_for(slug)
        title_values.add(title)
        (
            prepared_manuscript,
            _,
            prepared_blocks,
            _,
            _,
            _,
        ) = generator.prepare_detail_copy(manuscript, row)

        if len(re.findall(r"<h1\b", source, re.I)) != 1:
            errors.append(f"{slug}: H1 count")
        h1 = re.search(r"<h1>(.*?)</h1>", source, re.S)
        if not h1 or html.unescape(h1.group(1)).strip() != title:
            errors.append(f"{slug}: H1 mismatch")

        canonical_matches = re.findall(
            r'<link rel="canonical" href="([^"]+)">', source, re.I
        )
        og_matches = re.findall(
            r'<meta property="og:url" content="([^"]+)">', source, re.I
        )
        if canonical_matches != [canonical]:
            errors.append(f"{slug}: canonical")
        if og_matches != [canonical]:
            errors.append(f"{slug}: og:url")

        meta_match = re.search(
            r'<meta name="description" content="([^"]*)">', source, re.I
        )
        expected_meta = prepared_manuscript["메타설명"]
        if not meta_match or html.unescape(meta_match.group(1)) != expected_meta:
            errors.append(f"{slug}: meta mismatch")
        else:
            meta_values.add(expected_meta)
            if CATEGORY in {"보습학원", "소수정예학원"} and not (
                70 <= len(expected_meta) <= 100
            ):
                errors.append(f"{slug}: meta length={len(expected_meta)}")

        json_matches = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            source,
            re.S,
        )
        if len(json_matches) != 1:
            errors.append(f"{slug}: JSON-LD count")
            continue
        try:
            graph = json.loads(json_matches[0].replace("<\\/", "</"))
        except json.JSONDecodeError as exc:
            errors.append(f"{slug}: JSON parse {exc}")
            continue
        missing_types = REQUIRED_TYPES - graph_types(graph)
        if missing_types:
            errors.append(f"{slug}: missing types {sorted(missing_types)}")
        if "Review" in graph_types(graph) or "AggregateRating" in graph_types(graph):
            errors.append(f"{slug}: reconstructed review marked as Review")

        webpage = graph_node(graph, "WebPage")
        article = graph_node(graph, "Article")
        service = graph_node(graph, "Service")
        offer_catalog = graph_node(graph, "OfferCatalog")
        organization = graph_node(graph, "EducationalOrganization")
        local_business = graph_node(graph, "LocalBusiness")
        faq_page = graph_node(graph, "FAQPage")
        if organization is not local_business:
            errors.append(f"{slug}: organization/local business split")
        expected_org_id = generator.stable_id(
            "academy",
            row.get("센터명", ""),
            row.get("센터 주소", ""),
            row.get("교육지원청 등록번호", ""),
        )
        if organization.get("@id") != expected_org_id:
            errors.append(f"{slug}: unstable organization id")
        organization_ids.add(organization.get("@id", ""))
        if organization.get("telephone"):
            errors.append(f"{slug}: site phone assigned to local center")
        address_schema = organization.get("address", {})
        if address_schema.get("streetAddress") != generator.compact_text(
            row.get("센터 주소", "")
        ):
            errors.append(f"{slug}: organization street address")
        if "addressRegion" in address_schema or "addressLocality" in address_schema:
            errors.append(f"{slug}: inferred postal region/locality")
        if any(
            key in organization
            for key in ("alternateName", "parentOrganization", "teaches", "educationalLevel")
        ):
            errors.append(f"{slug}: invalid organization semantics")
        if organization.get("openingHours") != "Mo-Sa 12:00-23:59":
            errors.append(f"{slug}: opening hours")
        expected_area_count = len(row.get("_서비스 지역") or [])
        if len(organization.get("areaServed", [])) != expected_area_count:
            errors.append(f"{slug}: organization service areas")
        if not organization.get("hasMap") or not organization.get("mainEntityOfPage"):
            errors.append(f"{slug}: organization evidence links")
        if len(organization.get("subjectOf", [])) != 2:
            errors.append(f"{slug}: organization subjectOf")
        for node_name, node in (
            ("WebPage", webpage),
            ("Article", article),
            ("Service", service),
        ):
            for key in ("about", "mentions"):
                if not node.get(key):
                    errors.append(f"{slug}: {node_name}.{key}")
        if not webpage.get("hasPart"):
            errors.append(f"{slug}: WebPage.hasPart")
        if not article.get("articleSection") or not article.get("hasPart"):
            errors.append(f"{slug}: Article sections")
        if service.get("makesOffer"):
            errors.append(f"{slug}: Service.makesOffer")
        if not service.get("offers") or not organization.get("makesOffer"):
            errors.append(f"{slug}: offers/makesOffer")
        if not service.get("hasOfferCatalog") or not organization.get("hasOfferCatalog"):
            errors.append(f"{slug}: offer catalog links")
        grade_map = generator.grades_for(row)
        expected_offer_count = max(
            1,
            sum(1 for levels in grade_map.values() if levels),
        )
        if (
            len(offer_catalog.get("itemListElement", [])) != expected_offer_count
            or len(organization.get("makesOffer", [])) != expected_offer_count
        ):
            errors.append(f"{slug}: documented offer count")
        expected_topics = {
            str(value)
            for value in generator.category_profile().get("topic_names", ())
        }
        if not expected_topics.issubset(set(organization.get("knowsAbout", []))):
            errors.append(f"{slug}: category knowsAbout")
        if CATEGORY not in service.get("audience", {}).get("audienceType", ""):
            errors.append(f"{slug}: category audience")
        if article.get("datePublished") != generator.PUBLISHED_DATE:
            errors.append(f"{slug}: published date")
        if article.get("dateModified") != generator.UPDATED_AT:
            errors.append(f"{slug}: modified date")
        expected_parts = {
            canonical + "#article",
            canonical + "#faq",
            canonical + "#related-pages",
            canonical + "#quick-summary",
            canonical + "#center-information",
            canonical + "#consultation-example",
        }
        actual_parts = {
            item.get("@id")
            for item in webpage.get("hasPart", [])
            if isinstance(item, dict) and item.get("@id")
        }
        if not expected_parts.issubset(actual_parts):
            errors.append(f"{slug}: WebPage linked parts")
        if f'<time datetime="{generator.UPDATED_AT}">' not in source:
            errors.append(f"{slug}: visible modified date")
        opening_hours = generator.compact_text(row.get("_운영 시간")) or "12시-24시"
        if html.escape(opening_hours, quote=True) not in source:
            errors.append(f"{slug}: visible operating hours")
        location_guide = generator.compact_text(row.get("위치안내"))
        if location_guide and html.escape(location_guide, quote=True) not in source:
            errors.append(f"{slug}: visible location guide")

        screen_questions = [
            html.unescape(value).strip()
            for value in re.findall(
                r'<details class="faq-item"[^>]*>\s*<summary>(.*?)</summary>',
                source,
                re.S,
            )
        ]
        schema_questions = [
            item.get("name", "") for item in faq_page.get("mainEntity", [])
        ]
        expected_faq_count = int(
            generator.category_profile().get("faq_count", 5)
        )
        if (
            screen_questions != schema_questions
            or len(screen_questions) != expected_faq_count
        ):
            errors.append(f"{slug}: FAQ screen/schema mismatch")
        total_faq += len(screen_questions)

        if len(re.findall(r'class="manuscript-section"', source)) != 6:
            errors.append(f"{slug}: manuscript section count")
        for body_heading, _ in prepared_blocks:
            if esc := html.escape(body_heading, quote=True):
                if esc not in source:
                    errors.append(f"{slug}: missing heading {body_heading}")

        media_match = re.search(
            r'<section class="local-media-section subject-media-section">\s*'
            r'<img src="([^"]+)" alt="([^"]+)" style="display:none;">',
            source,
            re.S,
        )
        if not media_match:
            errors.append(f"{slug}: hidden representative position")
        else:
            representative_sources.add(media_match.group(1))
            representative_file = asset_path(media_match.group(1), page)
            if not representative_file.exists():
                errors.append(f"{slug}: representative missing")
            else:
                representative_hashes.add(
                    hashlib.sha256(representative_file.read_bytes()).hexdigest()
                )
            if "loading=" in media_match.group(0):
                errors.append(f"{slug}: representative lazy loading")
            expected_alt = f"{title} 코칭센터 대표"
            if html.unescape(media_match.group(2)) != expected_alt:
                errors.append(f"{slug}: representative alt")

        expected_body = (
            "seoul6839.webp" if row.get("지역", "").strip() == "서울"
            else "local6839.webp"
        )
        if f"assets/centers/common/{expected_body}" not in source:
            errors.append(f"{slug}: center image")
        image_object = graph_node(graph, "ImageObject")
        if not image_object.get("url", "").endswith(expected_body):
            errors.append(f"{slug}: primary image is not visible body image")
        for src in re.findall(r'<img[^>]+src="([^"]+)"', source):
            if not asset_path(src, page).exists():
                errors.append(f"{slug}: missing image {src}")

        for target_name, _, _ in generator.related_for(row, rows):
            target_local = target_name[: -len(f" {CATEGORY}")].strip()
            target_row = row_by_slug.get(generator.slug_ko(target_local))
            if (
                not target_row
                or target_row.get("지역", "").strip()
                != row.get("지역", "").strip()
            ):
                errors.append(f"{slug}: cross-region nearby link {target_local}")
        for sibling_name, sibling_url, _ in generator.sibling_category_links(
            row["근처 수업가능 동네"].strip()
        ):
            if sibling_name == CATEGORY or html.escape(sibling_url, quote=True) not in source:
                errors.append(f"{slug}: sibling category link {sibling_name}")

    all_html = [
        path
        for path in SITE.glob("**/index.html")
        if not any(part in {".git", ".vercel", "node_modules"} for part in path.parts)
    ]
    bad_nav = []
    for path in all_html:
        source = path.read_text(encoding="utf-8")
        nav_match = re.search(
            r'<div class="nav-links">(.*?)</div>', source, re.DOTALL
        )
        if (
            not nav_match
            or nav_match.group(1).count(">과목별학원</a>") != 1
        ):
            bad_nav.append(path)
    bad_css = [
        path
        for path in all_html
        if f"site.css?v={generator.ASSET_VERSION}" not in path.read_text(encoding="utf-8")
    ]
    if bad_nav:
        errors.append(f"navigation pages={len(bad_nav)}")
    if bad_css:
        errors.append(f"CSS version pages={len(bad_css)}")
    if len(organization_ids) != 188:
        errors.append(f"stable organization entities={len(organization_ids)}")

    category_source = (TARGET / "index.html").read_text(encoding="utf-8")
    if len(re.findall(r'data-district="', category_source)) != 371:
        errors.append("category local link count")
    sitemap = (SITE / "sitemap.xml").read_text(encoding="utf-8")
    sitemap_urls = re.findall(r"<loc>(.*?)</loc>", sitemap)
    expected_total = len(all_html)
    if len(sitemap_urls) != expected_total or len(set(sitemap_urls)) != expected_total:
        errors.append(
            f"sitemap count={len(sitemap_urls)} unique={len(set(sitemap_urls))}"
        )
    expected_sitemap = {canonical_for(), *[canonical_for(p.parent.name) for p in pages]}
    if not expected_sitemap.issubset(set(sitemap_urls)):
        errors.append("sitemap subject URLs missing")

    report = {
        "detail_pages": len(pages),
        "all_index_pages": len(all_html),
        "unique_titles": len(title_values),
        "unique_meta_descriptions": len(meta_values),
        "screen_faq_entries": total_faq,
        "representative_paths": len(representative_sources),
        "representative_content_hashes": len(representative_hashes),
        "sitemap_urls": len(sitemap_urls),
        "errors": len(errors),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        print("\n".join(errors[:100]), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
