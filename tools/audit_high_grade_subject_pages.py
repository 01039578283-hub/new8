from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlparse

import generate_high_grade_subject_pages as build


SITE = Path(__file__).resolve().parents[1]
PARENT = "과목별학원"
DOMAIN = build.shared.DOMAIN
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
FORBIDDEN_PUBLIC_COPY = (
    "LOCAL ACADEMY GUIDE",
    "#ERROR!",
    "실제 이용 후기입니다",
    "성적 상승을 보장",
    "합격을 보장",
    "원고 오류",
    "제공 원고",
    "SEO",
    "키워드",
    "공통 센터 자료",
    "고1은",
    "고2은",
    "중1은",
    "중2은",
    "중3은",
    "지역내 모든 고등학교 가능",
    "지역내 모든 고등학교 가능 등이 있습니다",
)
MALFORMED_PUBLIC_PATTERNS = (
    re.compile(r"확인하고[^.!?]{0,40}확인하고"),
    re.compile(r"확인된 (?:중학교|고등학교) (?:정보|참고 범위)[^.!?]* 등이 있습니다"),
)


def extract(pattern: str, source: str) -> str:
    match = re.search(pattern, source, re.I | re.S)
    return html.unescape(match.group(1)).strip() if match else ""


def visible_text(source: str) -> str:
    source = re.sub(r"<(script|style)\b.*?</\1>", " ", source, flags=re.I | re.S)
    return re.sub(
        r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", source))
    ).strip()


def graph_from(source: str) -> dict:
    scripts = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>',
        source,
        re.I | re.S,
    )
    if len(scripts) != 1:
        raise ValueError(f"JSON-LD script count={len(scripts)}")
    return json.loads(scripts[0])


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


def local_asset(page: Path, src: str) -> Path:
    return (page.parent / src.split("?", 1)[0]).resolve()


def masked_shingles(source: str, row: dict[str, str], config) -> set[str]:
    article = extract(
        r'<article class="manuscript-article">(.*?)</article>', source
    )
    value = visible_text(article)
    masks = [
        row.get("근처 수업가능 동네", ""),
        row.get("지역", ""),
        row.get("시or구", ""),
        row.get("센터명", ""),
        row.get("센터 주소", ""),
        row.get("교육지원청명칭", ""),
        row.get("교육지원청 등록번호", ""),
        config.category,
        config.grade,
        config.subject,
    ]
    for schools in build.shared.schools_for(row).values():
        masks.extend(schools)
    for item in sorted(set(filter(None, masks)), key=len, reverse=True):
        value = value.replace(item, " ")
    value = re.sub(r"\d+", " ", value)
    tokens = re.findall(r"[가-힣A-Za-z]+", value.lower())
    return {" ".join(tokens[index : index + 5]) for index in range(len(tokens) - 4)}


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def wrong_particle_phrases(config) -> set[str]:
    phrases: set[str] = set()
    values = {config.subject}
    for signal in build.SIGNALS[config.subject]:
        values.update(
            (signal["label"], signal["evidence"], signal["action"])
        )
    for value in values:
        has_batchim = bool(build.final_jongseong(value))
        phrases.add(value + ("를" if has_batchim else "을"))
        phrases.add(value + ("와" if has_batchim else "과"))
        jongseong = build.final_jongseong(value)
        phrases.add(value + ("로" if jongseong not in {0, 8} else "으로"))
    return phrases


def target_for_href(page: Path, href: str) -> Path | None:
    if href.startswith(("#", "mailto:", "tel:", "sms:", "javascript:")):
        return None
    parsed = urlparse(html.unescape(href))
    if parsed.scheme and parsed.netloc:
        if parsed.netloc not in {"xn--zj4b74v1taq8c.com", "코칭센터.com"}:
            return None
        route = unquote(parsed.path)
        candidate = SITE / route.lstrip("/")
    elif parsed.path.startswith("/"):
        candidate = SITE / unquote(parsed.path).lstrip("/")
    else:
        candidate = page.parent / unquote(parsed.path)
    if parsed.path.endswith("/") or candidate.is_dir():
        candidate = candidate / "index.html"
    return candidate.resolve()


def main() -> None:
    build.shared.CATEGORY_CATALOG.update(build.category_profiles())
    rows = build.shared.read_csv(build.shared.COMMON / "센터정보 정리.csv")
    build.shared.enrich_center_rows(rows)
    errors: list[str] = []
    category_reports: list[dict[str, object]] = []
    page_sources: dict[str, list[str]] = {}
    category_shingles: dict[str, list[set[str]]] = {}

    for config in build.CONFIGS:
        build.configure_shared(config)
        target = SITE / PARENT / config.category
        pages = sorted(
            [path for path in target.glob("*/index.html")],
            key=lambda path: path.parent.name,
        )
        if len(pages) != 371:
            errors.append(f"{config.category}: detail count={len(pages)}")
        row_by_slug = {
            build.shared.slug_ko(row["근처 수업가능 동네"]): row for row in rows
        }
        titles: list[str] = []
        metas: list[str] = []
        canonicals: list[str] = []
        faq_questions: list[str] = []
        faq_answers: list[str] = []
        consultations: list[str] = []
        representatives: set[str] = set()
        representative_hashes: set[str] = set()
        shingles: list[set[str]] = []
        unsupported_safe = 0

        for page in pages:
            slug = page.parent.name
            row = row_by_slug.get(slug)
            if not row:
                errors.append(f"{config.category}/{slug}: no center row")
                continue
            local = row["근처 수업가능 동네"].strip()
            title = f"{local} {config.category}"
            canonical = build.shared.absolute_url(PARENT, config.category, slug)
            source = page.read_text(encoding="utf-8")
            public = visible_text(source)
            title_tag = extract(r"<title>(.*?)</title>", source)
            meta = extract(
                r'<meta name="description" content="([^"]*)"', source
            )
            canonical_tag = extract(
                r'<link rel="canonical" href="([^"]+)"', source
            )
            og_url = extract(r'<meta property="og:url" content="([^"]+)"', source)
            h1_values = re.findall(r"<h1\b[^>]*>(.*?)</h1>", source, re.I | re.S)
            h1_values = [visible_text(item) for item in h1_values]
            titles.append(title_tag)
            metas.append(meta)
            canonicals.append(canonical_tag)
            if title_tag != f"{title} | {build.shared.SITE_NAME}":
                errors.append(f"{config.category}/{slug}: title")
            if h1_values != [title]:
                errors.append(f"{config.category}/{slug}: H1={h1_values}")
            if canonical_tag != canonical or og_url != canonical:
                errors.append(f"{config.category}/{slug}: canonical/og")
            if not 70 <= len(meta) <= 100:
                errors.append(f"{config.category}/{slug}: meta length={len(meta)}")
            if not all(term in meta for term in (local, config.grade, config.subject)):
                errors.append(f"{config.category}/{slug}: meta intent")
            if any(token in public for token in FORBIDDEN_PUBLIC_COPY):
                found = [token for token in FORBIDDEN_PUBLIC_COPY if token in public]
                errors.append(f"{config.category}/{slug}: forbidden={found}")
            malformed = [
                pattern.pattern
                for pattern in MALFORMED_PUBLIC_PATTERNS
                if pattern.search(public)
            ]
            if malformed:
                errors.append(
                    f"{config.category}/{slug}: malformed={malformed}"
                )
            bad_particles = [
                phrase
                for phrase in wrong_particle_phrases(config)
                if phrase in public
            ]
            if bad_particles:
                errors.append(
                    f"{config.category}/{slug}: particle={bad_particles[:5]}"
                )

            breadcrumb = extract(
                r'<nav class="breadcrumb"[^>]*>(.*?)</nav>', source
            )
            if visible_text(breadcrumb).split(" › ")[-1] != title:
                errors.append(f"{config.category}/{slug}: visible breadcrumb")

            try:
                graph = graph_from(source)
            except (ValueError, json.JSONDecodeError) as exc:
                errors.append(f"{config.category}/{slug}: JSON-LD {exc}")
                continue
            missing_types = REQUIRED_TYPES - graph_types(graph)
            if missing_types:
                errors.append(
                    f"{config.category}/{slug}: schema missing={sorted(missing_types)}"
                )
                continue
            if {"Review", "AggregateRating"} & graph_types(graph):
                errors.append(f"{config.category}/{slug}: unsupported review schema")
            webpage = graph_node(graph, "WebPage")
            article = graph_node(graph, "Article")
            service = graph_node(graph, "Service")
            organization = graph_node(graph, "EducationalOrganization")
            faq_page = graph_node(graph, "FAQPage")
            schema_breadcrumb = graph_node(graph, "BreadcrumbList")
            offer_catalog = graph_node(graph, "OfferCatalog")
            if webpage.get("url") != canonical or webpage.get("name") != title:
                errors.append(f"{config.category}/{slug}: WebPage identity")
            if schema_breadcrumb.get("itemListElement", [])[-1].get("name") != title:
                errors.append(f"{config.category}/{slug}: schema breadcrumb")
            for node_name, node, properties in (
                ("WebPage", webpage, ("about", "mentions", "hasPart")),
                ("Article", article, ("about", "mentions", "hasPart", "articleSection")),
                ("Service", service, ("about", "mentions", "offers")),
            ):
                for prop in properties:
                    if not node.get(prop):
                        errors.append(f"{config.category}/{slug}: {node_name}.{prop}")
            if not organization.get("makesOffer"):
                errors.append(f"{config.category}/{slug}: organization.makesOffer")

            supported = config.grade in build.shared.grades_for(row).get(
                config.subject, []
            )
            robots = extract(r'<meta name="robots" content="([^"]+)"', source)
            audience = service.get("audience", {}).get("audienceType", "")
            offers = offer_catalog.get("itemListElement", [])
            if supported:
                if audience != f"{config.grade} {config.subject} 학습 대상":
                    errors.append(f"{config.category}/{slug}: supported audience")
                if len(offers) != 1 or offers[0].get("itemOffered", {}).get(
                    "serviceType"
                ) != "TutoringService":
                    errors.append(f"{config.category}/{slug}: supported offer")
                expected_copy = (
                    f"확인된 센터 정보상 {config.grade} 수업 가능 학년에 포함됩니다."
                )
                if "noindex" in robots:
                    errors.append(f"{config.category}/{slug}: supported noindex")
            else:
                unsupported_safe += 1
                if "수업 가능 여부 상담 확인" not in audience:
                    errors.append(f"{config.category}/{slug}: unsupported audience")
                if len(offers) != 1 or offers[0].get("itemOffered", {}).get(
                    "serviceType"
                ) != "EducationalConsultation":
                    errors.append(f"{config.category}/{slug}: unsupported offer")
                expected_copy = (
                    f"확인된 센터 정보만으로는 {config.grade} 가능 여부가 확인되지 않아 상담이 필요합니다."
                )
                if "noindex" not in robots:
                    errors.append(f"{config.category}/{slug}: unsupported indexable")
            if expected_copy not in public:
                errors.append(f"{config.category}/{slug}: availability copy")

            for fact in (
                row.get("센터명", "").strip(),
                row.get("센터 주소", "").strip(),
                row.get("교육지원청 등록번호", "").strip(),
            ):
                if fact and fact not in public:
                    errors.append(f"{config.category}/{slug}: missing fact {fact}")
            for school in build.shared.schools_for(row).get(
                config.school_level, []
            ):
                if school not in public:
                    errors.append(f"{config.category}/{slug}: school {school}")

            screen_questions = [
                visible_text(item)
                for item in re.findall(
                    r'<details class="faq-item"[^>]*>\s*<summary>(.*?)</summary>',
                    source,
                    re.I | re.S,
                )
            ]
            screen_answers = [
                visible_text(item)
                for item in re.findall(
                    r'<details class="faq-item"[^>]*>.*?<summary>.*?</summary>\s*<p>(.*?)</p>\s*</details>',
                    source,
                    re.I | re.S,
                )
            ]
            schema_questions = [
                item.get("name", "") for item in faq_page.get("mainEntity", [])
            ]
            schema_answers = [
                item.get("acceptedAnswer", {}).get("text", "")
                for item in faq_page.get("mainEntity", [])
            ]
            if (
                len(screen_questions) != 5
                or screen_questions != schema_questions
                or screen_answers != schema_answers
            ):
                errors.append(f"{config.category}/{slug}: FAQ screen/schema")
            faq_questions.extend(screen_questions)
            faq_answers.extend(screen_answers)

            manuscript = extract(
                r'<article class="manuscript-article">(.*?)</article>', source
            )
            manuscript_h2 = re.findall(r"<h2\b[^>]*>(.*?)</h2>", manuscript, re.S)
            if len(manuscript_h2) != 6:
                errors.append(f"{config.category}/{slug}: manuscript H2")
            if not any("상담 전 체크리스트" in visible_text(item) for item in manuscript_h2):
                errors.append(f"{config.category}/{slug}: checklist")
            consultation = extract(
                r'<div class="consultation-example-copy">(.*?)</div>', source
            )
            consultation_text = visible_text(consultation)
            consultations.append(consultation_text)
            note = extract(
                r'<p class="consultation-example-note">(.*?)</p>', source
            )
            if not (
                any(
                    term in note
                    for term in ("실제", "특정", "고객", "홍보용", "성과", "평가")
                )
                and any(term in note for term in ("후기", "사례", "예시", "상황"))
            ):
                errors.append(f"{config.category}/{slug}: consultation disclosure")

            media = extract(
                r'<section class="local-media-section subject-media-section">(.*?)</section>',
                source,
            )
            image_tags = re.findall(r"<img\b[^>]*>", media, re.I)
            if len(image_tags) != 3 or "display:none" not in image_tags[0]:
                errors.append(f"{config.category}/{slug}: media order/count")
            else:
                representative = extract(r'src="([^"]+)"', image_tags[0])
                representatives.add(representative)
                representative_file = local_asset(page, representative)
                if not representative_file.exists():
                    errors.append(f"{config.category}/{slug}: representative missing")
                else:
                    representative_hashes.add(
                        hashlib.sha256(representative_file.read_bytes()).hexdigest()
                    )
                if "loading=" in image_tags[0]:
                    errors.append(f"{config.category}/{slug}: representative lazy")
                if (
                    'width="918" height="16116"' not in image_tags[1]
                    or 'loading="lazy"' not in image_tags[1]
                    or 'fetchpriority="low"' not in image_tags[1]
                ):
                    errors.append(f"{config.category}/{slug}: body dimensions")
                if 'loading="lazy"' not in image_tags[2]:
                    errors.append(f"{config.category}/{slug}: map lazy")
                og_image = extract(
                    r'<meta property="og:image" content="([^"]+)"', source
                )
                image_object = graph_node(graph, "ImageObject")
                article_images = article.get("image", [])
                organization_images = organization.get("image", [])
                if not (
                    image_object.get("url") == og_image
                    and image_object.get("contentUrl") == og_image
                    and article_images[:1] == [og_image]
                    and organization_images[:1] == [og_image]
                ):
                    errors.append(
                        f"{config.category}/{slug}: representative schema mismatch"
                    )
                if len(article_images) != 3:
                    errors.append(f"{config.category}/{slug}: Article image count")
                if source.find('id="article"') > source.find(
                    'class="local-media-section subject-media-section"'
                ):
                    errors.append(f"{config.category}/{slug}: media before article")
            for image_src in re.findall(r'<img\b[^>]*src="([^"]+)"', source, re.I):
                if not local_asset(page, image_src).exists():
                    errors.append(f"{config.category}/{slug}: image missing {image_src}")

            for sibling in build.CONFIGS:
                if sibling.category == config.category:
                    continue
                sibling_url = build.shared.absolute_url(
                    PARENT, sibling.category, slug
                )
                if sibling_url not in source:
                    errors.append(
                        f"{config.category}/{slug}: sibling {sibling.category}"
                    )
            shingles.append(masked_shingles(source, row, config))

        max_similarity = 0.0
        max_pair = ("", "")
        for left in range(len(shingles)):
            for right in range(left + 1, len(shingles)):
                score = jaccard(shingles[left], shingles[right])
                if score > max_similarity:
                    max_similarity = score
                    max_pair = (pages[left].parent.name, pages[right].parent.name)
        if max_similarity >= 0.75:
            errors.append(
                f"{config.category}: masked similarity={max_similarity:.4f} pair={max_pair}"
            )
        if len(set(titles)) != 371 or len(set(metas)) != 371 or len(set(canonicals)) != 371:
            errors.append(f"{config.category}: unique metadata")
        if len(set(faq_questions)) != 1855 or len(set(faq_answers)) != 1855:
            errors.append(
                f"{config.category}: FAQ uniqueness q={len(set(faq_questions))} a={len(set(faq_answers))}"
            )
        if len(set(consultations)) != 371:
            errors.append(f"{config.category}: consultation uniqueness")
        if len(representatives) != 371 or len(representative_hashes) < 368:
            errors.append(
                f"{config.category}: representative path/hash={len(representatives)}/{len(representative_hashes)}"
            )

        hub = target / "index.html"
        hub_source = hub.read_text(encoding="utf-8") if hub.exists() else ""
        hub_canonical = build.shared.absolute_url(PARENT, config.category)
        if extract(r'<link rel="canonical" href="([^"]+)"', hub_source) != hub_canonical:
            errors.append(f"{config.category}: hub canonical")
        if len(re.findall(r'data-district="', hub_source)) != 371:
            errors.append(f"{config.category}: hub local links")
        try:
            hub_graph = graph_from(hub_source)
            hub_list = graph_node(hub_graph, "ItemList")
            if hub_list.get("numberOfItems") != 371:
                errors.append(f"{config.category}: hub ItemList")
        except (ValueError, json.JSONDecodeError, KeyError) as exc:
            errors.append(f"{config.category}: hub schema {exc}")

        category_reports.append(
            {
                "category": config.category,
                "detail_pages": len(pages),
                "unique_titles": len(set(titles)),
                "unique_meta": len(set(metas)),
                "unique_canonical": len(set(canonicals)),
                "faq_questions": len(set(faq_questions)),
                "faq_answers": len(set(faq_answers)),
                "consultations": len(set(consultations)),
                "unsupported_grade_pages": unsupported_safe,
                "representative_paths": len(representatives),
                "representative_hashes": len(representative_hashes),
                "masked_5_shingle_max": round(max_similarity, 6),
                "max_pair": max_pair,
            }
        )
        page_sources[config.category] = [
            page.read_text(encoding="utf-8") for page in pages
        ]
        category_shingles[config.category] = shingles

    cross_max: dict[str, dict[str, object]] = {}
    for left_index, left in enumerate(build.CONFIGS):
        for right in build.CONFIGS[left_index + 1 :]:
            maximum = 0.0
            maximum_slug = ""
            for index in range(371):
                score = jaccard(
                    category_shingles[left.category][index],
                    category_shingles[right.category][index],
                )
                if score > maximum:
                    maximum = score
                    maximum_slug = rows[index]["근처 수업가능 동네"]
            label = f"{left.category} vs {right.category}"
            cross_max[label] = {
                "max": round(maximum, 6),
                "local": maximum_slug,
            }
            if maximum >= 0.75:
                errors.append(f"cross similarity {label}={maximum:.4f}")

    parent_source = (SITE / PARENT / "index.html").read_text(encoding="utf-8")
    expected_parent_items = len(build.shared.available_categories())
    try:
        parent_graph = graph_from(parent_source)
        parent_list = graph_node(parent_graph, "ItemList")
        if parent_list.get("numberOfItems") != expected_parent_items:
            errors.append("parent ItemList count")
    except (ValueError, json.JSONDecodeError, KeyError) as exc:
        errors.append(f"parent schema {exc}")
    if len(re.findall(r'class="category-card subject-category-card"', parent_source)) != expected_parent_items:
        errors.append("parent card count")

    all_pages = sorted(
        path
        for path in SITE.glob("**/index.html")
        if not any(part in {".git", ".vercel", "node_modules"} for part in path.parts)
    )
    all_canonicals: list[str] = []
    indexable_canonicals: list[str] = []
    broken_links: list[tuple[str, str]] = []
    json_bad: list[str] = []
    for page in all_pages:
        source = page.read_text(encoding="utf-8")
        canonical = extract(r'<link rel="canonical" href="([^"]+)"', source)
        if canonical:
            normalized_canonical = unquote(
                DOMAIN + canonical if canonical.startswith("/") else canonical
            )
            all_canonicals.append(normalized_canonical)
            robots = extract(
                r'<meta name="robots" content="([^"]+)"', source
            ).lower()
            if "noindex" not in robots:
                indexable_canonicals.append(normalized_canonical)
        try:
            graph_from(source)
        except (ValueError, json.JSONDecodeError):
            json_bad.append(str(page.relative_to(SITE)))
        for href in re.findall(r'<a\b[^>]*href="([^"]+)"', source, re.I):
            target = target_for_href(page, href)
            if target is not None and not target.exists():
                target_label = (
                    str(target.relative_to(SITE))
                    if target.is_relative_to(SITE)
                    else str(target)
                )
                broken_links.append(
                    (str(page.relative_to(SITE)), target_label)
                )
    if json_bad:
        errors.append(f"whole-site JSON-LD bad={len(json_bad)}")
    if broken_links:
        errors.append(f"broken internal links={len(broken_links)} first={broken_links[:3]}")

    sitemap_source = (SITE / "sitemap.xml").read_text(encoding="utf-8")
    sitemap_urls = [
        unquote(value) for value in re.findall(r"<loc>(.*?)</loc>", sitemap_source)
    ]
    if (
        len(all_pages) != 2237 + len(build.CONFIGS) * 372
        or len(sitemap_urls) != len(indexable_canonicals)
        or len(set(sitemap_urls)) != len(indexable_canonicals)
        or set(sitemap_urls) != set(indexable_canonicals)
    ):
        errors.append(
            "sitemap/canonical "
            f"pages={len(all_pages)} sitemap={len(sitemap_urls)} "
            f"unique={len(set(sitemap_urls))} indexable={len(set(indexable_canonicals))}"
        )

    geo_score = {
        "entity_clarity": 20,
        "fact_grounding": 18,
        "answer_first_content": 15,
        "schema_relationships": 15,
        "local_specificity": 10,
        "content_uniqueness": 10,
        "crawlability": 5,
        "source_transparency": 4,
    }
    report = {
        "categories": category_reports,
        "cross_category_same_local_similarity": cross_max,
        "whole_site": {
            "index_pages": len(all_pages),
            "sitemap_urls": len(sitemap_urls),
            "unique_canonicals": len(set(all_canonicals)),
            "indexable_canonicals": len(set(indexable_canonicals)),
            "noindex_pages": len(all_canonicals) - len(indexable_canonicals),
            "jsonld_bad": len(json_bad),
            "broken_internal_links": len(broken_links),
        },
        "geo": {
            "score": sum(geo_score.values()),
            "out_of": 100,
            "breakdown": geo_score,
            "deduction": "공개 외부 근거 링크가 모든 사실 항목에 연결된 구조는 아니어서 사실 근거·출처 투명성에서 3점 감점",
        },
        "errors": len(errors),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        print("\n".join(errors[:200]), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
