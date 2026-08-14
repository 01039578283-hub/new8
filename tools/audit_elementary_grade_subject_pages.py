from __future__ import annotations

"""Strict audit for the eight elementary grade/subject directories.

This audit is intentionally independent from the generator's active category
selection.  It can therefore report missing elementary output before all eight
categories are added to ``generate_high_grade_subject_pages.py``.  Search-volume
and competition data are external inputs; the keyword checks below validate
only the three-tier on-page structure.
"""

import hashlib
import html
import json
import re
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

import generate_high_grade_subject_pages as build


SITE = Path(__file__).resolve().parents[1]
PARENT = build.shared.PARENT
EXPECTED_DETAILS = 371
EXPECTED_FAQ_PER_PAGE = 5
MAX_MASKED_SIMILARITY = 0.75
MIN_ARTICLE_LENGTH_RANGE = 300
MIN_UNIQUE_LENGTH_RATIO = 0.50
MIN_ARTICLE_LENGTH_STDDEV = 70.0
MIN_SENTENCE_LENGTH = 12


@dataclass(frozen=True)
class ElementarySpec:
    category: str
    grade: str
    subject: str
    school_level: str = "초등"


SPECS = (
    ElementarySpec("초3수학학원", "초3", "수학"),
    ElementarySpec("초3영어학원", "초3", "영어"),
    ElementarySpec("초4수학학원", "초4", "수학"),
    ElementarySpec("초4영어학원", "초4", "영어"),
    ElementarySpec("초5수학학원", "초5", "수학"),
    ElementarySpec("초5영어학원", "초5", "영어"),
    ElementarySpec("초6수학학원", "초6", "수학"),
    ElementarySpec("초6영어학원", "초6", "영어"),
)

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
FORBIDDEN_AUTHORING_COPY = (
    "LOCAL ACADEMY GUIDE",
    "#ERROR!",
    "실제 이용 후기입니다",
    "성적 상승을 보장",
    "합격을 보장",
    "제공 원고",
    "원고 오류",
    "공통 센터 자료",
    "SEO",
    "AEO",
    "GEO",
    "키워드",
    "생성기",
    "템플릿",
    "ChatGPT",
    "AI가 작성",
    "초3은",
    "초4은",
    "초5은",
    "초6은",
)
MALFORMED_PUBLIC_PATTERNS = (
    re.compile(r"\ufffd"),
    re.compile(r"확인하고[^.!?]{0,40}확인하고"),
    re.compile(r"확인된 (?:초등학교|중학교|고등학교) (?:정보|참고 범위)[^.!?]* 등이 있습니다"),
    re.compile(r"(?:초3|초4|초5|초6) (?:수학|영어)[은는]은"),
)
LONG_TAIL_INTENTS = (
    "상담",
    "학습",
    "수업 가능",
    "가능 여부",
    "진단",
    "평가",
    "오답",
    "준비",
    "피드백",
    "체크리스트",
    "보완",
)


def extract(pattern: str, source: str) -> str:
    match = re.search(pattern, source, re.I | re.S)
    return html.unescape(match.group(1)).strip() if match else ""


def visible_text(source: str) -> str:
    source = re.sub(r"<(script|style)\b.*?</\1>", " ", source, flags=re.I | re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", source))).strip()


def text_blocks(fragment: str) -> list[str]:
    blocks = re.findall(
        r"<(?:p|li|blockquote)\b[^>]*>(.*?)</(?:p|li|blockquote)>",
        fragment,
        re.I | re.S,
    )
    if not blocks and visible_text(fragment):
        blocks = [fragment]
    return [visible_text(block) for block in blocks if visible_text(block)]


def sentences(fragment: str) -> list[str]:
    result: list[str] = []
    for block in text_blocks(fragment):
        for sentence in re.findall(r"[^.!?]+(?:[.!?]+|$)", block):
            value = re.sub(r"\s+", " ", sentence).strip(" \t\r\n\"'“”‘’")
            if len(value) >= MIN_SENTENCE_LENGTH:
                result.append(value)
    return result


def page_content(source: str) -> dict[str, object]:
    quick = extract(r'<div class="subject-quick-answer"[^>]*>(.*?)</div>', source)
    article = extract(r'<article class="manuscript-article"[^>]*>(.*?)</article>', source)
    faq_fragments = re.findall(
        r'<details class="faq-item"[^>]*>.*?<summary>.*?</summary>\s*<p>(.*?)</p>\s*</details>',
        source,
        re.I | re.S,
    )
    consultation = extract(
        r'<div class="consultation-example-copy"[^>]*>(.*?)</div>', source
    )
    headings = [
        visible_text(item)
        for item in re.findall(r"<h2\b[^>]*>(.*?)</h2>", article, re.I | re.S)
    ]
    faq_questions = [
        visible_text(item)
        for item in re.findall(
            r'<details class="faq-item"[^>]*>\s*<summary>(.*?)</summary>',
            source,
            re.I | re.S,
        )
    ]
    zones = {
        "quick": quick,
        "article": article,
        "faq": " ".join(faq_fragments),
        "consultation": consultation,
    }
    return {
        "zones": zones,
        "sentences": [sentence for zone in zones.values() for sentence in sentences(zone)],
        "article": article,
        "article_text": visible_text(article),
        "headings": headings,
        "faq_questions": faq_questions,
    }


def graph_from(source: str) -> dict:
    scripts = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', source, re.I | re.S
    )
    if len(scripts) != 1:
        raise ValueError(f"JSON-LD script count={len(scripts)}")
    graph = json.loads(scripts[0])
    if not isinstance(graph.get("@graph"), list):
        raise ValueError("JSON-LD @graph missing")
    return graph


def node_types(node: dict) -> set[str]:
    value = node.get("@type")
    if isinstance(value, list):
        return set(value)
    return {value} if isinstance(value, str) else set()


def graph_types(graph: dict) -> set[str]:
    return {
        node_type
        for node in graph.get("@graph", [])
        if isinstance(node, dict)
        for node_type in node_types(node)
    }


def graph_node(graph: dict, node_type: str) -> dict:
    for node in graph.get("@graph", []):
        if isinstance(node, dict) and node_type in node_types(node):
            return node
    raise KeyError(node_type)


def graph_nodes(graph: dict, node_type: str) -> list[dict]:
    return [
        node
        for node in graph.get("@graph", [])
        if isinstance(node, dict) and node_type in node_types(node)
    ]


def local_asset(page: Path, src: str) -> Path | None:
    parsed = urlparse(html.unescape(src))
    if parsed.scheme or parsed.netloc:
        path = unquote(parsed.path).lstrip("/")
        return (SITE / path).resolve() if path else None
    return (page.parent / unquote(parsed.path)).resolve()


def target_for_href(page: Path, href: str) -> Path | None:
    if href.startswith(("#", "mailto:", "tel:", "sms:", "javascript:")):
        return None
    parsed = urlparse(html.unescape(href))
    internal_hosts = {
        urlparse(build.shared.DOMAIN).netloc,
        "xn--zj4b74v1taq8c.com",
        "코칭센터.com",
    }
    if parsed.scheme and parsed.netloc:
        if parsed.netloc not in internal_hosts:
            return None
        candidate = SITE / unquote(parsed.path).lstrip("/")
    elif parsed.path.startswith("/"):
        candidate = SITE / unquote(parsed.path).lstrip("/")
    else:
        candidate = page.parent / unquote(parsed.path)
    if parsed.path.endswith("/") or candidate.is_dir():
        candidate /= "index.html"
    return candidate.resolve()


def signals_for_spec(spec: ElementarySpec) -> tuple[dict, ...]:
    """Return the elementary signal bank used to author this category.

    Specs are independent from ``build.CONFIGS`` so the audit can report a
    missing category before its generator config is registered.  Prefer the
    generator's selector when the config exists and otherwise use the same
    elementary subject bank directly.
    """

    config = next(
        (item for item in build.CONFIGS if item.category == spec.category),
        None,
    )
    if config is not None:
        return tuple(build.signals_for(config))
    return tuple(build.ELEMENTARY_SIGNALS[spec.subject])


def wrong_particle_phrases(spec: ElementarySpec) -> set[str]:
    phrases: set[str] = set()
    values = {spec.subject}
    for signal in signals_for_spec(spec):
        values.update((signal["label"], signal["evidence"], signal["action"]))
    for value in values:
        has_batchim = bool(build.final_jongseong(value))
        phrases.add(value + ("를" if has_batchim else "을"))
        phrases.add(value + ("와" if has_batchim else "과"))
        jongseong = build.final_jongseong(value)
        phrases.add(value + ("로" if jongseong not in {0, 8} else "으로"))
    return phrases


def masked_shingles(source: str, row: dict[str, str], spec: ElementarySpec) -> set[str]:
    value = visible_text(
        extract(r'<article class="manuscript-article"[^>]*>(.*?)</article>', source)
    )
    masks = [
        row.get("근처 수업가능 동네", ""),
        row.get("지역", ""),
        row.get("시or구", ""),
        row.get("센터명", ""),
        row.get("센터 주소", ""),
        row.get("교육지원청명칭", ""),
        row.get("교육지원청 등록번호", ""),
        spec.category,
        spec.grade,
        spec.subject,
    ]
    for schools in build.shared.schools_for(row).values():
        masks.extend(schools)
    for item in sorted(set(filter(None, masks)), key=len, reverse=True):
        value = value.replace(item, " ")
    value = re.sub(r"\d+", " ", value)
    tokens = re.findall(r"[가-힣A-Za-z]+", value.lower())
    return {
        " ".join(tokens[index : index + 5])
        for index in range(max(0, len(tokens) - 4))
    }


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def keyword_tiers(
    source: str,
    content: dict[str, object],
    spec: ElementarySpec,
    local: str,
) -> dict[str, object]:
    title = extract(r"<title>(.*?)</title>", source)
    h1 = visible_text(extract(r"<h1\b[^>]*>(.*?)</h1>", source))
    meta = extract(r'<meta name="description" content="([^"]*)"', source)
    zones = content["zones"]
    headings = content["headings"]
    faq_questions = content["faq_questions"]
    assert isinstance(zones, dict)
    assert isinstance(headings, list)
    assert isinstance(faq_questions, list)

    primary = f"{local} {spec.category}"
    primary_zones = {
        "title": title,
        "h1": h1,
        "meta": meta,
        "quick": visible_text(str(zones["quick"])),
        "headings": " ".join(headings),
        "faq_questions": " ".join(faq_questions),
    }
    primary_ok = (
        all(primary in primary_zones[name] for name in ("title", "h1", "meta"))
        and any(
            primary in primary_zones[name]
            for name in ("quick", "headings", "faq_questions")
        )
    )

    signal_labels = [item["label"] for item in signals_for_spec(spec)]
    secondary_zones = {
        "meta": meta,
        "quick": visible_text(str(zones["quick"])),
        "headings": " ".join(headings),
        "faq": " ".join(faq_questions) + " " + visible_text(str(zones["faq"])),
    }
    secondary_hits = {
        name: sorted({label for label in signal_labels if label in value})
        for name, value in secondary_zones.items()
    }
    secondary_labels = sorted({label for labels in secondary_hits.values() for label in labels})
    secondary_ok = (
        len(secondary_labels) >= 2
        and len(secondary_hits["meta"]) >= 2
        and sum(bool(labels) for labels in secondary_hits.values()) >= 3
    )

    queries = list(dict.fromkeys(headings + faq_questions))
    long_tail_queries = [
        query
        for query in queries
        if local in query
        and spec.grade in query
        and spec.subject in query
        and any(intent in query for intent in LONG_TAIL_INTENTS)
    ]
    return {
        "primary": primary_ok,
        "secondary": secondary_ok,
        "long_tail": len(long_tail_queries) >= 3,
        "secondary_labels": secondary_labels,
        "long_tail_count": len(long_tail_queries),
    }


def relation_id(value: object) -> str:
    return value.get("@id", "") if isinstance(value, dict) else ""


def main() -> None:
    rows = build.shared.read_csv(build.shared.COMMON / "센터정보 정리.csv")
    build.shared.enrich_center_rows(rows)
    config_by_category = {
        config.category: config for config in build.CONFIGS
    }
    row_by_slug = {
        build.shared.slug_ko(row["근처 수업가능 동네"]): row for row in rows
    }
    expected_slugs = set(row_by_slug)
    generated_categories = {
        spec.category
        for spec in SPECS
        if len(list((SITE / PARENT / spec.category).glob("*/index.html")))
        == EXPECTED_DETAILS
    }
    errors: list[str] = []
    reports: list[dict[str, object]] = []
    category_shingles: dict[str, dict[str, set[str]]] = {}

    for spec in SPECS:
        target = SITE / PARENT / spec.category
        pages = sorted(target.glob("*/index.html"), key=lambda page: page.parent.name)
        actual_slugs = {page.parent.name for page in pages}
        if len(pages) != EXPECTED_DETAILS:
            errors.append(f"{spec.category}: detail count={len(pages)} expected={EXPECTED_DETAILS}")
        if actual_slugs != expected_slugs:
            errors.append(
                f"{spec.category}: slug set missing={sorted(expected_slugs - actual_slugs)[:5]} "
                f"extra={sorted(actual_slugs - expected_slugs)[:5]}"
            )

        titles: list[str] = []
        metas: list[str] = []
        canonicals: list[str] = []
        faq_questions_all: list[str] = []
        faq_answers_all: list[str] = []
        consultations: list[str] = []
        representative_paths: set[str] = set()
        representative_hashes: set[str] = set()
        article_lengths: list[int] = []
        duplicate_pages = 0
        unsupported_pages = 0
        keyword_pass = Counter()
        shingles_by_slug: dict[str, set[str]] = {}

        for page in pages:
            slug = page.parent.name
            row = row_by_slug.get(slug)
            if row is None:
                errors.append(f"{spec.category}/{slug}: missing center row")
                continue
            local = row["근처 수업가능 동네"].strip()
            page_label = f"{spec.category}/{slug}"
            title = f"{local} {spec.category}"
            canonical = build.shared.absolute_url(PARENT, spec.category, slug)
            source = page.read_text(encoding="utf-8")
            public = visible_text(source)
            content = page_content(source)

            title_tag = extract(r"<title>(.*?)</title>", source)
            meta = extract(r'<meta name="description" content="([^"]*)"', source)
            canonical_tag = extract(r'<link rel="canonical" href="([^"]+)"', source)
            og_title = extract(r'<meta property="og:title" content="([^"]+)"', source)
            og_description = extract(
                r'<meta property="og:description" content="([^"]*)"', source
            )
            og_url = extract(r'<meta property="og:url" content="([^"]+)"', source)
            h1_values = [
                visible_text(item)
                for item in re.findall(r"<h1\b[^>]*>(.*?)</h1>", source, re.I | re.S)
            ]
            titles.append(title_tag)
            metas.append(meta)
            canonicals.append(canonical_tag)
            if title_tag != f"{title} | {build.shared.SITE_NAME}":
                errors.append(f"{page_label}: title={title_tag!r}")
            if h1_values != [title]:
                errors.append(f"{page_label}: H1={h1_values}")
            if canonical_tag != canonical or og_url != canonical:
                errors.append(f"{page_label}: canonical/og:url")
            if og_title != title_tag or og_description != meta:
                errors.append(f"{page_label}: Open Graph title/description")
            if not 70 <= len(meta) <= 100:
                errors.append(f"{page_label}: meta length={len(meta)}")
            if not all(term in meta for term in (local, spec.grade, spec.subject)):
                errors.append(f"{page_label}: meta search intent")

            forbidden = [token for token in FORBIDDEN_AUTHORING_COPY if token in public]
            if forbidden:
                errors.append(f"{page_label}: authoring/forbidden copy={forbidden}")
            malformed = [
                pattern.pattern for pattern in MALFORMED_PUBLIC_PATTERNS if pattern.search(public)
            ]
            bad_particles = [
                phrase for phrase in wrong_particle_phrases(spec) if phrase in public
            ]
            if malformed or bad_particles:
                errors.append(
                    f"{page_label}: malformed={malformed} particles={bad_particles[:5]}"
                )

            breadcrumb = extract(r'<nav class="breadcrumb"[^>]*>(.*?)</nav>', source)
            breadcrumb_labels = [
                visible_text(item)
                for item in re.findall(
                    r"<(?:a|span)\b[^>]*>(.*?)</(?:a|span)>", breadcrumb, re.I | re.S
                )
            ]
            breadcrumb_labels = [label for label in breadcrumb_labels if label != "›"]
            if breadcrumb_labels != ["홈", PARENT, spec.category, title]:
                errors.append(f"{page_label}: visible breadcrumb={breadcrumb_labels}")

            try:
                graph = graph_from(source)
                missing_types = REQUIRED_TYPES - graph_types(graph)
                if missing_types:
                    raise ValueError(f"schema missing={sorted(missing_types)}")
                if {"Review", "AggregateRating"} & graph_types(graph):
                    errors.append(f"{page_label}: unsupported review schema")
                webpage = graph_node(graph, "WebPage")
                article = graph_node(graph, "Article")
                service = graph_node(graph, "Service")
                organization = graph_node(graph, "EducationalOrganization")
                faq_page = graph_node(graph, "FAQPage")
                schema_breadcrumb = graph_node(graph, "BreadcrumbList")
                offer_catalog = graph_node(graph, "OfferCatalog")
                image_object = graph_node(graph, "ImageObject")
            except (ValueError, json.JSONDecodeError, KeyError) as exc:
                errors.append(f"{page_label}: JSON-LD {exc}")
                continue

            if webpage.get("url") != canonical or webpage.get("name") != title:
                errors.append(f"{page_label}: WebPage identity")
            if article.get("headline") != title or relation_id(article.get("mainEntityOfPage")) != webpage.get("@id"):
                errors.append(f"{page_label}: Article identity/relationship")
            if spec.grade not in article.get("educationalLevel", []):
                errors.append(f"{page_label}: Article.educationalLevel")
            schema_crumbs = schema_breadcrumb.get("itemListElement", [])
            expected_crumb_names = ["홈", PARENT, spec.category, title]
            if (
                [item.get("name") for item in schema_crumbs] != expected_crumb_names
                or [item.get("position") for item in schema_crumbs] != [1, 2, 3, 4]
                or not schema_crumbs
                or schema_crumbs[-1].get("item") != canonical
            ):
                errors.append(f"{page_label}: schema breadcrumb")
            for node_name, node, properties in (
                ("WebPage", webpage, ("about", "mentions", "hasPart")),
                ("Article", article, ("about", "mentions", "hasPart", "articleSection")),
                ("Service", service, ("about", "mentions", "offers")),
            ):
                for prop in properties:
                    if not node.get(prop):
                        errors.append(f"{page_label}: {node_name}.{prop}")
            if not organization.get("makesOffer"):
                errors.append(f"{page_label}: EducationalOrganization.makesOffer")
            if relation_id(service.get("provider")) != organization.get("@id"):
                errors.append(f"{page_label}: Service.provider")

            supported = build.is_supported(
                config_by_category[spec.category], row
            )
            robots = extract(r'<meta name="robots" content="([^"]+)"', source).lower()
            audience = service.get("audience", {}).get("audienceType", "")
            offers = offer_catalog.get("itemListElement", [])
            offered_type = (
                offers[0].get("itemOffered", {}).get("serviceType", "")
                if len(offers) == 1
                else ""
            )
            if supported:
                expected_copy = f"확인된 센터 정보상 {spec.grade} 수업 가능 학년에 포함됩니다."
                if audience != f"{spec.grade} {spec.subject} 학습 대상":
                    errors.append(f"{page_label}: supported audience")
                if offered_type != "TutoringService" or "noindex" in robots:
                    errors.append(f"{page_label}: supported offer/robots")
            else:
                unsupported_pages += 1
                expected_copy = (
                    f"확인된 센터 정보만으로는 {spec.grade} 가능 여부가 확인되지 않아 상담이 필요합니다."
                )
                if "수업 가능 여부 상담 확인" not in audience:
                    errors.append(f"{page_label}: unsupported audience")
                if offered_type != "EducationalConsultation" or "noindex" not in robots:
                    errors.append(f"{page_label}: unsupported offer/robots")
            if expected_copy not in public:
                errors.append(f"{page_label}: availability fact copy")

            facts = (
                row.get("센터명", "").strip(),
                row.get("센터 주소", "").strip(),
                row.get("교육지원청 등록번호", "").strip(),
            )
            for fact in facts:
                if fact and fact not in public:
                    errors.append(f"{page_label}: missing visible fact={fact}")
            if facts[0] and organization.get("name") != facts[0]:
                errors.append(f"{page_label}: organization name fact")
            if facts[1] and organization.get("address", {}).get("streetAddress") != facts[1]:
                errors.append(f"{page_label}: organization address fact")
            if facts[2] and organization.get("identifier", {}).get("value") != facts[2]:
                errors.append(f"{page_label}: organization registration fact")
            for school in build.shared.schools_for(row).get(spec.school_level, []):
                if school not in public:
                    errors.append(f"{page_label}: missing elementary school={school}")

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
            schema_questions = [item.get("name", "") for item in faq_page.get("mainEntity", [])]
            schema_answers = [
                item.get("acceptedAnswer", {}).get("text", "")
                for item in faq_page.get("mainEntity", [])
            ]
            if (
                len(screen_questions) != EXPECTED_FAQ_PER_PAGE
                or screen_questions != schema_questions
                or screen_answers != schema_answers
            ):
                errors.append(f"{page_label}: FAQ screen/schema mismatch")
            faq_questions_all.extend(screen_questions)
            faq_answers_all.extend(screen_answers)

            article_fragment = content["article"]
            headings = content["headings"]
            article_text = content["article_text"]
            assert isinstance(article_fragment, str)
            assert isinstance(headings, list)
            assert isinstance(article_text, str)
            if len(headings) != 6:
                errors.append(f"{page_label}: manuscript H2 count={len(headings)}")
            if not any("상담 전 체크리스트" in heading for heading in headings):
                errors.append(f"{page_label}: consultation checklist section")
            zones = content["zones"]
            assert isinstance(zones, dict)
            if len(visible_text(str(zones["quick"]))) < 60:
                errors.append(f"{page_label}: answer-first summary")
            article_lengths.append(len(article_text))

            page_sentences = content["sentences"]
            assert isinstance(page_sentences, list)
            duplicates = {
                sentence: count
                for sentence, count in Counter(page_sentences).items()
                if count > 1
            }
            if duplicates:
                duplicate_pages += 1
                errors.append(f"{page_label}: exact sentence repeats={list(duplicates.items())[:3]}")

            consultation = visible_text(
                extract(r'<div class="consultation-example-copy"[^>]*>(.*?)</div>', source)
            )
            consultations.append(consultation)
            disclosure = visible_text(
                extract(r'<p class="consultation-example-note"[^>]*>(.*?)</p>', source)
            )
            if not (
                any(term in disclosure for term in ("실제", "특정", "고객", "홍보용", "성과", "평가"))
                and any(term in disclosure for term in ("후기", "사례", "예시", "상황"))
            ):
                errors.append(f"{page_label}: consultation example disclosure")

            media = extract(
                r'<section class="local-media-section subject-media-section"[^>]*>(.*?)</section>',
                source,
            )
            image_tags = re.findall(r"<img\b[^>]*>", media, re.I)
            if len(image_tags) != 3 or "display:none" not in image_tags[0]:
                errors.append(f"{page_label}: media order/count")
            else:
                srcs = [extract(r'src="([^"]+)"', tag) for tag in image_tags]
                alts = [extract(r'alt="([^"]*)"', tag) for tag in image_tags]
                if not all(srcs) or not all(alts):
                    errors.append(f"{page_label}: image src/alt")
                representative_paths.add(srcs[0])
                representative_file = local_asset(page, srcs[0])
                if representative_file is None or not representative_file.exists():
                    errors.append(f"{page_label}: representative missing")
                else:
                    representative_hashes.add(hashlib.sha256(representative_file.read_bytes()).hexdigest())
                if "loading=" in image_tags[0]:
                    errors.append(f"{page_label}: representative lazy-loaded")
                if (
                    'width="918" height="16116"' not in image_tags[1]
                    or 'loading="lazy"' not in image_tags[1]
                    or 'fetchpriority="low"' not in image_tags[1]
                ):
                    errors.append(f"{page_label}: body image dimensions/loading")
                if 'loading="lazy"' not in image_tags[2]:
                    errors.append(f"{page_label}: map image loading")
                og_image = extract(r'<meta property="og:image" content="([^"]+)"', source)
                article_images = article.get("image", [])
                organization_images = organization.get("image", [])
                if not (
                    image_object.get("url") == og_image
                    and image_object.get("contentUrl") == og_image
                    and article_images[:1] == [og_image]
                    and organization_images[:1] == [og_image]
                    and len(article_images) == 3
                ):
                    errors.append(f"{page_label}: image schema relationship")
                if source.find('id="article"') > source.find(
                    'class="local-media-section subject-media-section"'
                ):
                    errors.append(f"{page_label}: media appears before article")
            for image_src in re.findall(r'<img\b[^>]*src="([^"]+)"', source, re.I):
                asset = local_asset(page, image_src)
                if asset is None or not asset.exists():
                    errors.append(f"{page_label}: image target missing={image_src}")

            for sibling in SPECS:
                if (
                    sibling.category == spec.category
                    or sibling.category not in generated_categories
                ):
                    continue
                sibling_url = build.shared.absolute_url(PARENT, sibling.category, slug)
                if sibling_url not in source:
                    errors.append(f"{page_label}: sibling link={sibling.category}")
            for href in re.findall(r'<a\b[^>]*href="([^"]*)"', source, re.I):
                if not href:
                    errors.append(f"{page_label}: empty href")
                    continue
                link_target = target_for_href(page, href)
                if link_target is not None and not link_target.exists():
                    errors.append(f"{page_label}: broken internal link={href}")

            tiers = keyword_tiers(source, content, spec, local)
            for tier in ("primary", "secondary", "long_tail"):
                keyword_pass[tier] += bool(tiers[tier])
            if not all(tiers[tier] for tier in ("primary", "secondary", "long_tail")):
                errors.append(
                    f"{page_label}: keyword tiers primary={tiers['primary']} "
                    f"secondary={tiers['secondary']} long_tail={tiers['long_tail']} "
                    f"labels={tiers['secondary_labels']} long_tail_count={tiers['long_tail_count']}"
                )

            shingles_by_slug[slug] = masked_shingles(source, row, spec)

        max_similarity = 0.0
        max_pair = ("", "")
        shingle_items = sorted(shingles_by_slug.items())
        for left in range(len(shingle_items)):
            for right in range(left + 1, len(shingle_items)):
                score = jaccard(shingle_items[left][1], shingle_items[right][1])
                if score > max_similarity:
                    max_similarity = score
                    max_pair = (shingle_items[left][0], shingle_items[right][0])
        if max_similarity >= MAX_MASKED_SIMILARITY:
            errors.append(
                f"{spec.category}: masked similarity={max_similarity:.4f} pair={max_pair}"
            )

        page_count = len(pages)
        expected_faq_total = EXPECTED_DETAILS * EXPECTED_FAQ_PER_PAGE
        if not (
            len(set(titles)) == EXPECTED_DETAILS
            and len(set(metas)) == EXPECTED_DETAILS
            and len(set(canonicals)) == EXPECTED_DETAILS
        ):
            errors.append(
                f"{spec.category}: metadata uniqueness title/meta/canonical="
                f"{len(set(titles))}/{len(set(metas))}/{len(set(canonicals))}"
            )
        if (
            len(set(faq_questions_all)) != expected_faq_total
            or len(set(faq_answers_all)) != expected_faq_total
        ):
            errors.append(
                f"{spec.category}: FAQ uniqueness q/a="
                f"{len(set(faq_questions_all))}/{len(set(faq_answers_all))}"
            )
        if len(set(consultations)) != EXPECTED_DETAILS:
            errors.append(f"{spec.category}: consultation uniqueness={len(set(consultations))}")
        if len(representative_paths) != EXPECTED_DETAILS or len(representative_hashes) < 368:
            errors.append(
                f"{spec.category}: representative path/hash="
                f"{len(representative_paths)}/{len(representative_hashes)}"
            )

        length_range = max(article_lengths, default=0) - min(article_lengths, default=0)
        unique_length_ratio = len(set(article_lengths)) / page_count if page_count else 0.0
        length_stddev = statistics.pstdev(article_lengths) if len(article_lengths) > 1 else 0.0
        if page_count and (
            length_range < MIN_ARTICLE_LENGTH_RANGE
            or unique_length_ratio < MIN_UNIQUE_LENGTH_RATIO
            or length_stddev < MIN_ARTICLE_LENGTH_STDDEV
        ):
            errors.append(
                f"{spec.category}: article-length distribution range={length_range} "
                f"unique_ratio={unique_length_ratio:.3f} stddev={length_stddev:.1f}"
            )

        hub = target / "index.html"
        hub_source = hub.read_text(encoding="utf-8") if hub.exists() else ""
        hub_canonical = build.shared.absolute_url(PARENT, spec.category)
        if extract(r'<link rel="canonical" href="([^"]+)"', hub_source) != hub_canonical:
            errors.append(f"{spec.category}: hub canonical")
        if len(re.findall(r'data-district="', hub_source)) != EXPECTED_DETAILS:
            errors.append(f"{spec.category}: hub local-link count")
        try:
            hub_graph = graph_from(hub_source)
            hub_list = graph_node(hub_graph, "ItemList")
            if hub_list.get("numberOfItems") != EXPECTED_DETAILS:
                errors.append(f"{spec.category}: hub ItemList count")
        except (ValueError, json.JSONDecodeError, KeyError) as exc:
            errors.append(f"{spec.category}: hub JSON-LD {exc}")

        reports.append(
            {
                "category": spec.category,
                "detail_pages": page_count,
                "unique_title_meta_canonical": [
                    len(set(titles)),
                    len(set(metas)),
                    len(set(canonicals)),
                ],
                "faq_unique_questions_answers": [
                    len(set(faq_questions_all)),
                    len(set(faq_answers_all)),
                ],
                "unsupported_grade_pages": unsupported_pages,
                "exact_sentence_duplicate_pages": duplicate_pages,
                "keyword_tiers_pass": dict(keyword_pass),
                "article_length": {
                    "min": min(article_lengths, default=0),
                    "max": max(article_lengths, default=0),
                    "range": length_range,
                    "unique_ratio": round(unique_length_ratio, 3),
                    "stddev": round(length_stddev, 1),
                },
                "representative_paths_hashes": [
                    len(representative_paths),
                    len(representative_hashes),
                ],
                "masked_5_shingle_max": round(max_similarity, 6),
                "masked_max_pair": max_pair,
            }
        )
        category_shingles[spec.category] = shingles_by_slug

    cross_similarity: dict[str, dict[str, object]] = {}
    for left_index, left in enumerate(SPECS):
        for right in SPECS[left_index + 1 :]:
            maximum = 0.0
            maximum_slug = ""
            common_slugs = sorted(
                set(category_shingles.get(left.category, {}))
                & set(category_shingles.get(right.category, {}))
            )
            for slug in common_slugs:
                score = jaccard(
                    category_shingles[left.category][slug],
                    category_shingles[right.category][slug],
                )
                if score > maximum:
                    maximum = score
                    maximum_slug = slug
            label = f"{left.category} vs {right.category}"
            cross_similarity[label] = {"max": round(maximum, 6), "slug": maximum_slug}
            if maximum >= MAX_MASKED_SIMILARITY:
                errors.append(f"cross similarity {label}={maximum:.4f} slug={maximum_slug}")

    report = {
        "scope": "eight elementary grade/subject categories (grades 3-6)",
        "expected_details_per_category": EXPECTED_DETAILS,
        "categories": reports,
        "cross_category_same_local_similarity": cross_similarity,
        "errors": len(errors),
        "error_samples": errors[:100],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        print("\n".join(errors[:200]), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
