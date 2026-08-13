from __future__ import annotations

"""Strict content-quality audit for the six middle-grade subject directories.

This complements ``audit_high_grade_subject_pages.py``.  It deliberately checks
the weaknesses that broad SEO/schema audits do not catch: sentence reuse inside
a page, a repeated availability statement, overly uniform article lengths,
similarity headroom, and natural three-tier keyword coverage.

The keyword checks validate on-page semantic coverage only.  Monthly search
volume and competition are external research inputs and cannot be proved from
the generated HTML itself.
"""

import html
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

import generate_high_grade_subject_pages as build


SITE = Path(__file__).resolve().parents[1]
PARENT = build.shared.PARENT
MIDDLE_CONFIGS = tuple(
    config for config in build.CONFIGS if config.school_level == "중등"
)

# A 3,000-character article whose category-wide range is around 100 characters
# still reads as mechanically length-normalized.  All three distribution gates
# must pass so that a few artificial outliers cannot create a false positive.
MIN_ARTICLE_LENGTH_RANGE = 300
MIN_UNIQUE_LENGTH_RATIO = 0.50
MIN_ARTICLE_LENGTH_STDDEV = 70.0

# The general duplicate-content rejection line is 0.75.  The category that was
# closest to it (중2영어학원) must retain at least six points of headroom.
MAX_MIDDLE2_ENGLISH_MASKED_SIMILARITY = 0.69
MIN_SENTENCE_LENGTH = 12

LONG_TAIL_INTENTS = (
    "상담",
    "내신",
    "수업 가능",
    "가능 여부",
    "진단",
    "시험",
    "시험지",
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
    return re.sub(
        r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", source))
    ).strip()


def text_blocks(fragment: str) -> list[str]:
    """Return paragraph-like blocks without joining headings to sentences."""

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
            normalized = re.sub(r"\s+", " ", sentence).strip(" \t\r\n\"'“”‘’")
            if len(normalized) >= MIN_SENTENCE_LENGTH:
                result.append(normalized)
    return result


def page_content(source: str) -> dict[str, object]:
    quick = extract(
        r'<div class="subject-quick-answer"[^>]*>(.*?)</div>', source
    )
    article = extract(
        r'<article class="manuscript-article"[^>]*>(.*?)</article>', source
    )
    faq_fragments = re.findall(
        r'<details class="faq-item"[^>]*>.*?<summary>.*?</summary>\s*'
        r"<p>(.*?)</p>\s*</details>",
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
        "sentences": [
            sentence
            for fragment in zones.values()
            for sentence in sentences(fragment)
        ],
        "article_text": visible_text(article),
        "headings": headings,
        "faq_questions": faq_questions,
    }


def masked_shingles(
    source: str, row: dict[str, str], config: build.CategoryConfig
) -> set[str]:
    article = extract(
        r'<article class="manuscript-article"[^>]*>(.*?)</article>', source
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
    config: build.CategoryConfig,
    local: str,
) -> dict[str, object]:
    title = extract(r"<title>(.*?)</title>", source)
    h1 = visible_text(extract(r"<h1\b[^>]*>(.*?)</h1>", source))
    meta = extract(r'<meta name="description" content="([^"]*)"', source)
    zones = content["zones"]
    assert isinstance(zones, dict)
    headings = content["headings"]
    faq_questions = content["faq_questions"]
    assert isinstance(headings, list)
    assert isinstance(faq_questions, list)

    primary = f"{local} {config.category}"
    primary_zones = {
        "title": title,
        "h1": h1,
        "meta": meta,
        "quick": visible_text(str(zones["quick"])),
        "headings": " ".join(headings),
        "faq_questions": " ".join(faq_questions),
    }
    primary_hits = [name for name, value in primary_zones.items() if primary in value]
    primary_ok = (
        all(primary in primary_zones[name] for name in ("title", "h1", "meta"))
        and any(
            primary in primary_zones[name]
            for name in ("quick", "headings", "faq_questions")
        )
    )

    signal_labels = [item["label"] for item in build.signals_for(config)]
    secondary_zones = {
        "meta": meta,
        "quick": visible_text(str(zones["quick"])),
        "headings": " ".join(headings),
        "faq": " ".join(faq_questions)
        + " "
        + visible_text(str(zones["faq"])),
    }
    secondary_labels = sorted(
        {
            label
            for value in secondary_zones.values()
            for label in signal_labels
            if label in value
        }
    )
    secondary_zone_hits = {
        name: sorted({label for label in signal_labels if label in value})
        for name, value in secondary_zones.items()
    }
    secondary_ok = (
        len(secondary_labels) >= 2
        and len(secondary_zone_hits["meta"]) >= 2
        and sum(bool(labels) for labels in secondary_zone_hits.values()) >= 3
    )

    query_candidates = list(dict.fromkeys(headings + faq_questions))
    long_tail_queries = [
        query
        for query in query_candidates
        if local in query
        and config.grade in query
        and config.subject in query
        and any(intent in query for intent in LONG_TAIL_INTENTS)
    ]
    long_tail_ok = len(long_tail_queries) >= 3

    return {
        "primary_ok": primary_ok,
        "primary_hits": primary_hits,
        "secondary_ok": secondary_ok,
        "secondary_labels": secondary_labels,
        "secondary_zone_hits": secondary_zone_hits,
        "long_tail_ok": long_tail_ok,
        "long_tail_queries": long_tail_queries,
    }


def main() -> None:
    build.shared.CATEGORY_CATALOG.update(build.category_profiles())
    rows = build.shared.read_csv(build.shared.COMMON / "센터정보 정리.csv")
    build.shared.enrich_center_rows(rows)
    row_by_slug = {
        build.shared.slug_ko(row["근처 수업가능 동네"]): row for row in rows
    }

    errors: list[str] = []
    reports: list[dict[str, object]] = []

    for config in MIDDLE_CONFIGS:
        target = SITE / PARENT / config.category
        pages = sorted(target.glob("*/index.html"), key=lambda page: page.parent.name)
        duplicate_pages = 0
        duplicate_excess = 0
        availability_repeat_pages = 0
        availability_occurrences: list[int] = []
        article_lengths: list[int] = []
        keyword_primary_pass = 0
        keyword_secondary_pass = 0
        keyword_long_tail_pass = 0
        keyword_all_pass = 0
        shingles: list[set[str]] = []
        slugs: list[str] = []

        for page in pages:
            slug = page.parent.name
            row = row_by_slug.get(slug)
            if row is None:
                errors.append(f"{config.category}/{slug}: missing center row")
                continue
            source = page.read_text(encoding="utf-8")
            content = page_content(source)
            page_sentences = content["sentences"]
            assert isinstance(page_sentences, list)
            counts = Counter(page_sentences)
            duplicates = {
                sentence: count for sentence, count in counts.items() if count > 1
            }
            if duplicates:
                duplicate_pages += 1
                duplicate_excess += sum(count - 1 for count in duplicates.values())
                errors.append(
                    f"{config.category}/{slug}: exact sentence repeats="
                    f"{list(duplicates.items())[:3]}"
                )

            availability_count = sum(
                count
                for sentence, count in counts.items()
                if "확인된 센터 정보상" in sentence
                or "확인된 센터 정보만으로는" in sentence
            )
            availability_occurrences.append(availability_count)
            if availability_count > 1:
                availability_repeat_pages += 1
                errors.append(
                    f"{config.category}/{slug}: canonical availability statement "
                    f"count={availability_count} (expected at most 1)"
                )

            article_text = content["article_text"]
            assert isinstance(article_text, str)
            article_lengths.append(len(article_text))

            local = row["근처 수업가능 동네"].strip()
            tiers = keyword_tiers(source, content, config, local)
            keyword_primary_pass += bool(tiers["primary_ok"])
            keyword_secondary_pass += bool(tiers["secondary_ok"])
            keyword_long_tail_pass += bool(tiers["long_tail_ok"])
            all_tiers = all(
                tiers[name]
                for name in ("primary_ok", "secondary_ok", "long_tail_ok")
            )
            keyword_all_pass += all_tiers
            if not all_tiers:
                errors.append(
                    f"{config.category}/{slug}: keyword tiers "
                    f"primary={tiers['primary_ok']} secondary={tiers['secondary_ok']} "
                    f"long_tail={tiers['long_tail_ok']} "
                    f"labels={tiers['secondary_labels']} "
                    f"long_tail_count={len(tiers['long_tail_queries'])}"
                )

            shingles.append(masked_shingles(source, row, config))
            slugs.append(slug)

        page_count = len(pages)
        length_range = (
            max(article_lengths) - min(article_lengths) if article_lengths else 0
        )
        unique_lengths = len(set(article_lengths))
        unique_length_ratio = unique_lengths / page_count if page_count else 0.0
        length_stddev = (
            statistics.pstdev(article_lengths) if len(article_lengths) > 1 else 0.0
        )
        if length_range < MIN_ARTICLE_LENGTH_RANGE:
            errors.append(
                f"{config.category}: article length range={length_range} "
                f"(<{MIN_ARTICLE_LENGTH_RANGE})"
            )
        if unique_length_ratio < MIN_UNIQUE_LENGTH_RATIO:
            errors.append(
                f"{config.category}: unique article length ratio="
                f"{unique_length_ratio:.3f} (<{MIN_UNIQUE_LENGTH_RATIO:.2f})"
            )
        if length_stddev < MIN_ARTICLE_LENGTH_STDDEV:
            errors.append(
                f"{config.category}: article length stddev={length_stddev:.1f} "
                f"(<{MIN_ARTICLE_LENGTH_STDDEV:.1f})"
            )

        max_similarity = 0.0
        max_pair = ("", "")
        if config.category == "중2영어학원":
            for left in range(len(shingles)):
                for right in range(left + 1, len(shingles)):
                    score = jaccard(shingles[left], shingles[right])
                    if score > max_similarity:
                        max_similarity = score
                        max_pair = (slugs[left], slugs[right])
            if max_similarity >= MAX_MIDDLE2_ENGLISH_MASKED_SIMILARITY:
                errors.append(
                    f"{config.category}: masked similarity={max_similarity:.4f} "
                    f"pair={max_pair} "
                    f"(must be <{MAX_MIDDLE2_ENGLISH_MASKED_SIMILARITY:.2f})"
                )

        reports.append(
            {
                "category": config.category,
                "detail_pages": page_count,
                "exact_sentence_duplicate_pages": duplicate_pages,
                "exact_sentence_duplicate_excess": duplicate_excess,
                "repeated_canonical_availability_pages": availability_repeat_pages,
                "canonical_availability_occurrences": {
                    "min": min(availability_occurrences, default=0),
                    "max": max(availability_occurrences, default=0),
                },
                "article_length": {
                    "min": min(article_lengths, default=0),
                    "max": max(article_lengths, default=0),
                    "range": length_range,
                    "unique_lengths": unique_lengths,
                    "unique_ratio": round(unique_length_ratio, 3),
                    "stddev": round(length_stddev, 1),
                    "gates": {
                        "min_range": MIN_ARTICLE_LENGTH_RANGE,
                        "min_unique_ratio": MIN_UNIQUE_LENGTH_RATIO,
                        "min_stddev": MIN_ARTICLE_LENGTH_STDDEV,
                    },
                },
                "keyword_tiers": {
                    "primary_pass": keyword_primary_pass,
                    "secondary_pass": keyword_secondary_pass,
                    "long_tail_pass": keyword_long_tail_pass,
                    "all_tiers_pass": keyword_all_pass,
                    "expected": page_count,
                },
                "masked_5_shingle_max": (
                    round(max_similarity, 6)
                    if config.category == "중2영어학원"
                    else None
                ),
                "masked_max_pair": (
                    max_pair if config.category == "중2영어학원" else None
                ),
            }
        )

    report = {
        "scope": "six middle-grade subject categories",
        "categories": reports,
        "errors": len(errors),
        "error_samples": errors[:80],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
