from __future__ import annotations

import csv
import hashlib
import html
import json
import random
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape


SITE = Path(__file__).resolve().parents[1]
BASE = SITE.parent
COMMON = BASE / "참고자료" / "공통자료"

DOMAIN = "https://xn--zj4b74v1taq8c.com"
SITE_NAME = "코칭센터"
CATEGORY = "고등영수학원"
PHONE_DISPLAY = "010-6839-8283"
PHONE_LINK = "01068398283"
LASTMOD = "2026-07-19"


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def slug_ko(value: str) -> str:
    value = re.sub(r"\s+", "", (value or "").strip())
    value = re.sub(r'[\\/:*?"<>|#%&+]', "", value)
    return value


def split_items(value: str) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in re.split(r"[,/·\n]+", value) if x.strip()]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_faq(path: Path) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    q = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("질문:"):
            q = line.replace("질문:", "", 1).strip()
        elif line.startswith("답변:") and q:
            pairs.append((q, line.replace("답변:", "", 1).strip()))
            q = ""
    return pairs


def read_reviews(path: Path) -> list[str]:
    return [x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def rel_prefix(depth: int) -> str:
    return "../" * depth


def canonical_for(*parts: str) -> str:
    raw = "/" + "/".join(part.strip("/") for part in parts if part) + "/"
    return DOMAIN + quote(raw, safe="/")


def asset_url(rel: str) -> str:
    return DOMAIN + "/" + quote(rel.lstrip("/"), safe="/")


def seeded(seed: str) -> int:
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12], 16)


def choose_variant(seed: str, items: list[str]) -> str:
    return items[seeded(seed) % len(items)]


def nav_html(depth: int) -> str:
    p = rel_prefix(depth)
    return f"""  <header class="nav-wrap">
    <nav class="nav" aria-label="주요 메뉴">
      <a class="brand" href="{p}index.html"><span class="brand-mark">C</span><span>{SITE_NAME}</span></a>
      <div class="nav-links">
        <a href="{p}index.html">홈</a>
        <a href="{p}학습가이드/index.html">학습가이드</a>
        <a href="{p}상담문의/index.html">상담문의</a>
        <a class="active" href="{p}전국학원/index.html">전국학원</a>
      </div>
    </nav>
  </header>"""


def footer_html(depth: int) -> str:
    p = rel_prefix(depth)
    return f"""  <footer class="footer">
    <p><strong>{SITE_NAME}</strong> · 영어·수학·국어 학습관리 코칭 · 상담은 전화·문자로 편하게 문의하실 수 있습니다.</p>
  </footer>

  <div class="floating-cta" aria-label="빠른 상담 버튼">
    <a href="tel:{PHONE_DISPLAY}">전화문의</a>
    <a href="sms:{PHONE_LINK}">문자문의</a>
    <a href="{p}상담문의/index.html">상담문의</a>
  </div>"""


def head_html(title: str, description: str, depth: int, canonical: str, og_type: str, image: str, ld: dict) -> str:
    p = rel_prefix(depth)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <link rel="canonical" href="{esc(canonical)}">
  <meta property="og:type" content="{esc(og_type)}">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{esc(canonical)}">
  <meta property="og:image" content="{esc(image)}">
  <link rel="icon" type="image/png" href="{p}assets/favicon.png">
  <link rel="apple-touch-icon" href="{p}assets/favicon.png">
  <link rel="stylesheet" href="{p}assets/site.css">
  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False, separators=(",", ":"))}</script>
</head>"""


def page_shell(head: str, body: str) -> str:
    return f"""{head}
<body>
<div class="site-shell">
{body}
</div>
</body>
</html>
"""


def get_school_lookup() -> dict[tuple[str, str, str], dict[str, str]]:
    rows = read_csv(COMMON / "타깃학교.csv")
    lookup: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        key = (row.get("근처 수업가능 동네", ""), row.get("지역", ""), row.get("시or구", ""))
        lookup[key] = row
    return lookup


def merged_school_row(row: dict[str, str], lookup: dict[tuple[str, str, str], dict[str, str]]) -> dict[str, str]:
    key = (row.get("근처 수업가능 동네", ""), row.get("지역", ""), row.get("시or구", ""))
    return lookup.get(key, row)


def high_schools(row: dict[str, str]) -> list[str]:
    return split_items(row.get("타깃학교\n(고)", ""))


def local_schools(row: dict[str, str]) -> list[str]:
    names: list[str] = []
    for key in ("타깃학교\n(고)", "타깃학교\n(중)", "타깃학교\n(초)"):
        for name in split_items(row.get(key, "")):
            if name not in names:
                names.append(name)
    return names


def representative_images(count: int) -> list[str]:
    reps = sorted(
        [
            p
            for p in (SITE / "assets" / "representative").iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        ],
        key=lambda p: p.name,
    )
    if not reps:
        src = sorted(
            [
                p
                for p in (COMMON / "대표이미지").iterdir()
                if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}
            ],
            key=lambda p: p.name,
        )
        dst = SITE / "assets" / "representative"
        dst.mkdir(parents=True, exist_ok=True)
        for i, p in enumerate(src, 1):
            target = dst / f"rep-{i:03d}{p.suffix.lower()}"
            if not target.exists():
                target.write_bytes(p.read_bytes())
        reps = sorted(dst.iterdir(), key=lambda p: p.name)

    rng = random.Random(68398283)
    pool = reps[:]
    rng.shuffle(pool)
    return [f"assets/representative/{pool[i % len(pool)].name}" for i in range(count)]


def find_map(row: dict[str, str]) -> str:
    maps = SITE / "assets" / "maps"
    raw = (row.get("동 영어") or "").strip()
    candidates = [
        raw,
        raw.replace(" ", "-"),
        raw.replace(" ", ""),
        raw.replace("_", "-"),
        (row.get("근처 수업가능 동네") or "").strip(),
    ]
    for base in candidates:
        if not base:
            continue
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            p = maps / f"{base}{ext}"
            if p.exists():
                return f"assets/maps/{p.name}"
    return "assets/centers/common/local6839.jpg"


def center_image(row: dict[str, str]) -> str:
    return "assets/centers/common/seoul6839.jpg" if row.get("지역") == "서울" else "assets/centers/common/local6839.jpg"


def make_faqs(local: str, district: str, title: str, base_faq: list[tuple[str, str]], idx: int) -> list[tuple[str, str]]:
    base_answers = [answer for _, answer in base_faq] or ["학생의 현재 학습 상태와 목표를 먼저 확인한 뒤 필요한 관리 방향을 안내합니다."]
    base = base_answers[idx % len(base_answers)]
    return [
        (
            f"{title} 상담은 어떤 순서로 진행되나요?",
            f"먼저 최근 시험지와 현재 교재를 확인하고, {local} 학생의 영어·수학 단원별 이해도와 반복 오답을 나누어 봅니다. 이후 내신 대비, 수능형 문제 접근, 플래너 실행까지 어떤 순서로 관리할지 안내합니다.",
        ),
        (
            f"{local} 고등영수학원에서는 영어와 수학을 어떻게 함께 관리하나요?",
            f"{district} 학교 진도와 시험 범위를 기준으로 영어는 어휘·문법·독해·학교 본문을, 수학은 개념·유형·오답 원인을 분리해 확인합니다. 두 과목 모두 공부량보다 실행과 재학습 흐름을 더 중요하게 봅니다.",
        ),
        (
            f"{title}은 내신 대비에도 도움이 될까요?",
            f"도움이 될 수 있습니다. {local} 고등학생의 학교별 시험 범위, 프린트, 부교재, 수행평가 흐름을 상담 때 함께 확인하고 시험 전 주차별 계획을 세우는 방식으로 관리합니다.",
        ),
        (
            f"{title} 상담 전 준비하면 좋은 자료가 있나요?",
            "최근 영어·수학 시험지, 학교 프린트, 현재 사용하는 문제집, 오답노트나 풀이 흔적이 있으면 좋습니다. 자료가 부족해도 상담을 통해 현재 수준과 필요한 관리 방향을 먼저 정리할 수 있습니다.",
        ),
        (
            "고등학생도 플래너와 오답 관리가 꼭 필요한가요?",
            f"네. {base} 특히 고등 과정은 영어와 수학 모두 누적 결손이 점수에 직접 영향을 주기 때문에, {local} 학생에게 필요한 복습 주기와 다시 풀어야 할 오답을 분리해 관리하는 편이 좋습니다.",
        ),
    ]


def make_reviews(local: str, title: str, review_lines: list[str], idx: int) -> list[dict[str, object]]:
    rng = random.Random(5000 + idx)
    pool = review_lines[:]
    rng.shuffle(pool)
    selected = pool[:6] if len(pool) >= 6 else pool
    templates = [
        f"{title} 상담을 통해 아이가 영어와 수학에서 각각 어디가 막히는지 조금 더 선명하게 알 수 있었습니다.",
        f"{local}에서 고등 영수 관리를 알아보던 중 플래너와 오답 재학습까지 함께 설명받아 도움이 되었습니다.",
        f"영어는 본문과 어휘, 수학은 오답 원인을 나누어 봐 주셔서 {local} 고등학생에게 필요한 관리가 무엇인지 정리됐습니다.",
    ]
    reviews: list[dict[str, object]] = []
    for i in range(6):
        if i < len(templates):
            body = templates[i]
        else:
            seed_text = selected[i % len(selected)] if selected else "아이에게 필요한 부분을 차분히 짚어주셨습니다."
            body = f"{seed_text} {title} 학습관리 과정에서도 아이에게 필요한 부분을 차분히 짚어주셨습니다."
        reviews.append({"body": body, "rating": 4 if i == 5 else 5})
    return reviews


def star_line(rating: int) -> str:
    return "★★★★★" if rating >= 5 else "★★★★☆"


def mentions_for(row: dict[str, str], school_row: dict[str, str]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = [
        {"@type": "Place", "name": row.get("지역", "")},
        {"@type": "Place", "name": row.get("시or구", "")},
        {"@type": "EducationalOrganization", "name": row.get("센터명", "")},
    ]
    for school in local_schools(school_row):
        items.append({"@type": "School", "name": school})
    return [x for x in items if x.get("name")]


def make_ld(
    row: dict[str, str],
    school_row: dict[str, str],
    slug: str,
    title: str,
    description: str,
    canonical: str,
    rep: str,
    body_img: str,
    map_img: str,
    faqs: list[tuple[str, str]],
    reviews: list[dict[str, object]],
    related: list[dict[str, str]],
) -> dict:
    local = row["근처 수업가능 동네"]
    district = row["시or구"]
    region = row["지역"]
    org_id = canonical + "#organization"
    webpage_id = canonical + "#webpage"
    breadcrumb_id = canonical + "#breadcrumb"
    service_id = canonical + "#service"
    article_id = canonical + "#article"
    image_id = canonical + "#primaryimage"
    image_urls = [asset_url(rep), asset_url(body_img), asset_url(map_img)]
    high_school_text = ", ".join(high_schools(school_row))

    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": webpage_id,
                "url": canonical,
                "name": title,
                "description": description,
                "inLanguage": "ko-KR",
                "primaryImageOfPage": {"@id": image_id},
                "breadcrumb": {"@id": breadcrumb_id},
                "mainEntity": {"@id": service_id},
                "about": [
                    {"@type": "Thing", "name": title},
                    {"@type": "Place", "name": local},
                    {"@type": "Thing", "name": "고등영수학원"},
                    {"@type": "Thing", "name": "고등 영어 내신"},
                    {"@type": "Thing", "name": "고등 수학 내신"},
                    {"@type": "Thing", "name": "플래너 관리"},
                    {"@type": "Thing", "name": "오답 재학습"},
                ],
                "mentions": mentions_for(row, school_row),
                "hasPart": [
                    {"@type": "WebPageElement", "name": "핵심 요약", "description": "영어·수학 상담 기준을 요약합니다."},
                    {"@type": "WebPageElement", "name": "지역·학년·추천학생", "description": "지역과 고등학생 상황에 맞는 추천 기준을 정리합니다."},
                    {"@type": "WebPageElement", "name": "상담 전 체크리스트", "description": "상담 전 준비하면 좋은 자료를 안내합니다."},
                    {"@type": "WebPageElement", "name": "FAQ", "description": "자주 묻는 질문을 답변형으로 정리합니다."},
                ],
            },
            {"@type": "ImageObject", "@id": image_id, "url": asset_url(rep), "caption": f"{title} 대표 이미지"},
            {
                "@type": "BreadcrumbList",
                "@id": breadcrumb_id,
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "홈", "item": DOMAIN + "/"},
                    {"@type": "ListItem", "position": 2, "name": "전국학원", "item": canonical_for("전국학원")},
                    {"@type": "ListItem", "position": 3, "name": CATEGORY, "item": canonical_for("전국학원", CATEGORY)},
                    {"@type": "ListItem", "position": 4, "name": local, "item": canonical},
                ],
            },
            {
                "@type": ["EducationalOrganization", "LocalBusiness"],
                "@id": org_id,
                "name": title,
                "alternateName": [SITE_NAME, row.get("센터명", ""), f"{local} 고등 영수 학습관리"],
                "url": canonical,
                "telephone": PHONE_DISPLAY,
                "openingHours": "Mo-Sa 12:00-24:00",
                "openingHoursSpecification": [
                    {
                        "@type": "OpeningHoursSpecification",
                        "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
                        "opens": "12:00",
                        "closes": "24:00",
                    }
                ],
                "areaServed": {"@type": "Place", "name": local},
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": row.get("센터 주소", ""),
                    "addressRegion": region,
                    "addressLocality": district,
                    "addressCountry": "KR",
                },
                "knowsAbout": ["고등영수", "고등 영어 내신", "고등 수학 내신", "플래너 관리", "오답 재학습", "학부모 피드백"],
                "makesOffer": [
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{local} 고등영수 진단 상담", "serviceType": "TutoringService"}},
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{local} 영어·수학 내신 대비", "serviceType": "TutoringService"}},
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{local} 오답 재학습 관리", "serviceType": "TutoringService"}},
                ],
                "aggregateRating": {"@type": "AggregateRating", "ratingValue": "4.8", "bestRating": "5", "ratingCount": "6", "reviewCount": "6"},
                "review": [
                    {
                        "@type": "Review",
                        "author": {"@type": "Person", "name": f"학부모 {i + 1}"},
                        "reviewRating": {"@type": "Rating", "ratingValue": str(review["rating"]), "bestRating": "5"},
                        "reviewBody": review["body"],
                    }
                    for i, review in enumerate(reviews)
                ],
            },
            {
                "@type": "Article",
                "@id": article_id,
                "headline": title,
                "description": description,
                "image": image_urls,
                "inLanguage": "ko-KR",
                "datePublished": LASTMOD,
                "dateModified": LASTMOD,
                "author": {"@id": org_id},
                "publisher": {"@type": "Organization", "name": SITE_NAME, "url": DOMAIN + "/"},
                "mainEntityOfPage": {"@id": webpage_id},
                "about": [
                    {"@type": "Thing", "name": title},
                    {"@type": "Place", "name": local},
                    {"@type": "Thing", "name": CATEGORY},
                    {"@type": "Thing", "name": "고등 영어 내신 대비"},
                    {"@type": "Thing", "name": "고등 수학 오답 관리"},
                    {"@type": "Thing", "name": "플래너 실행 점검"},
                ],
                "mentions": mentions_for(row, school_row),
                "hasPart": [
                    {"@type": "WebPageElement", "name": "영어·수학 진단"},
                    {"@type": "WebPageElement", "name": "내신 대비 흐름"},
                    {"@type": "WebPageElement", "name": "오답 재학습"},
                    {"@type": "WebPageElement", "name": "학부모 상담 체크리스트"},
                ],
                "articleSection": ["핵심 요약", "답변형 학습 안내", "지역·학년·추천학생", "상담 전 체크리스트", "FAQ", "학부모 후기", "내부링크"],
            },
            {
                "@type": "Service",
                "@id": service_id,
                "name": f"{title} 학습관리",
                "serviceType": "TutoringService / 고등영수 학습코칭",
                "description": f"{local} 고등학생의 영어·수학 내신, 오답 재학습, 플래너 실행을 함께 관리합니다.",
                "provider": {"@id": org_id},
                "areaServed": {"@type": "Place", "name": local},
                "audience": {"@type": "EducationalAudience", "educationalRole": "student"},
                "about": [
                    {"@type": "Thing", "name": title},
                    {"@type": "Thing", "name": "고등영수학원"},
                    {"@type": "Thing", "name": "영어·수학 내신 대비"},
                    {"@type": "Thing", "name": "오답 재학습"},
                ],
                "mentions": mentions_for(row, school_row),
                "makesOffer": [
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{local} 고등영수 진단"}},
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{local} 내신 대비 플래너"}},
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{local} 영어·수학 오답 재학습"}},
                ],
            },
            {
                "@type": "FAQPage",
                "@id": canonical + "#faq",
                "mainEntity": [
                    {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                    for q, a in faqs
                ],
            },
            {
                "@type": "ItemList",
                "@id": canonical + "#related-pages",
                "name": f"{local} 관련 고등 학습 페이지",
                "itemListElement": [
                    {"@type": "ListItem", "position": i + 1, "name": item["name"], "url": item["url"]}
                    for i, item in enumerate(related)
                ],
            },
            {
                "@type": "ItemList",
                "@id": canonical + "#schools",
                "name": f"{local} 고등영수 상담 참고 학교",
                "itemListElement": [
                    {"@type": "ListItem", "position": i + 1, "name": school}
                    for i, school in enumerate(high_schools(school_row))
                ],
            },
        ],
    }


def related_locations(rows: list[dict[str, str]], idx: int, current_slug: str, current_city: str) -> list[dict[str, str]]:
    same_city = [r for r in rows if r.get("시or구") == current_city and slug_ko(r.get("근처 수업가능 동네", "")) != current_slug]
    if len(same_city) < 5:
        same_city.extend(rows[max(0, idx - 3) : idx] + rows[idx + 1 : idx + 6])
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in same_city:
        local = row.get("근처 수업가능 동네", "")
        slug = slug_ko(local)
        if not slug or slug in seen or slug == current_slug:
            continue
        seen.add(slug)
        result.append({"name": f"{local} {CATEGORY}", "url": canonical_for("전국학원", CATEGORY, slug), "city": row.get("시or구", "")})
        if len(result) >= 6:
            break
    return result


def page_html(row: dict[str, str], school_row: dict[str, str], rows: list[dict[str, str]], rep: str, base_faq: list[tuple[str, str]], review_lines: list[str], idx: int) -> str:
    local = row["근처 수업가능 동네"]
    slug = slug_ko(local)
    region = row["지역"]
    district = row["시or구"]
    center = row.get("센터명", "")
    title = f"{local} {CATEGORY}"
    description = f"{region} {district} {local} 고등학생을 위한 고등영수학원 안내입니다. 영어·수학 내신, 오답 재학습, 플래너 실행, 상담 전 확인사항을 함께 정리했습니다."
    canonical = canonical_for("전국학원", CATEGORY, slug)
    body_img = center_image(row)
    map_img = find_map(row)
    faqs = make_faqs(local, district, title, base_faq, idx)
    reviews = make_reviews(local, title, review_lines, idx)
    nearby = related_locations(rows, idx, slug, district)
    related = [
        {"name": f"{local} 고등수학학원", "url": canonical_for("전국학원", "고등수학학원", slug)},
        {"name": f"{local} 고등영어학원", "url": canonical_for("전국학원", "고등영어학원", slug)},
        {"name": f"{CATEGORY} 전체", "url": canonical_for("전국학원", CATEGORY)},
        {"name": "전국학원", "url": canonical_for("전국학원")},
    ] + [{"name": item["name"], "url": item["url"]} for item in nearby[:4]]
    ld = make_ld(row, school_row, slug, title, description, canonical, rep, body_img, map_img, faqs, reviews, related)
    head = head_html(f"{title} | {SITE_NAME}", description, 3, canonical, "article", asset_url(rep), ld)
    high = high_schools(school_row)
    local_all = local_schools(school_row)
    high_text = ", ".join(high) if high else "상담 시 현재 학교 진도와 시험 범위를 기준으로 확인합니다."
    local_text = ", ".join(local_all[:8]) if local_all else "학교별 자료는 상담 시 확인합니다."
    tuition = row.get("센터 교습비", "").replace("view?usp=shari", "view?usp=sharing")
    if tuition and "usp=sharing" not in tuition and "drive.google.com" in tuition:
        tuition = tuition.rstrip("/") + "?usp=sharing"

    faq_html = "\n".join(
        f'<details class="faq-item"{" open" if i == 0 else ""}><summary>{esc(q)}</summary><p>{esc(a)}</p></details>'
        for i, (q, a) in enumerate(faqs)
    )
    review_html = "\n".join(
        f'<article class="review-card"><span>PARENT REVIEW</span><h3>{esc(local)} 고등영수 상담 후기</h3><p class="star-line">{star_line(int(review["rating"]))}</p><p>{esc(review["body"])}</p></article>'
        for review in reviews
    )
    nearby_links = "\n".join(
        f'<a href="/전국학원/{CATEGORY}/{slug_ko(item["name"].replace(" " + CATEGORY, ""))}/"><strong>{esc(item["name"])}</strong><small>{esc(item["city"])} 지역 페이지</small></a>'
        for item in nearby
    )
    tuition_html = (
        f'<p><a href="{esc(tuition)}" target="_blank" rel="noopener noreferrer">교습비 안내 확인</a></p>'
        if tuition
        else "<p>교습비 안내는 상담 시 확인할 수 있습니다.</p>"
    )
    school_card = (
        f'<article class="school-card"><span>HIGH SCHOOL</span><h3>고등 영수 상담 참고 학교</h3><p>{esc(high_text)}</p></article>'
        if high
        else '<article class="school-card"><span>HIGH SCHOOL</span><h3>고등 영수 상담 참고 학교</h3><p>학교별 시험 범위와 현재 교재를 상담 시 함께 확인합니다.</p></article>'
    )
    local_school_card = f'<article class="school-card"><span>LOCAL SCHOOL</span><h3>지역 학교 흐름 확인</h3><p>{esc(local_text)}</p></article>'

    body = f"""{nav_html(3)}
  <main>
    <section class="academy-hero">
      <div class="academy-hero-main">
        <nav class="breadcrumb" aria-label="breadcrumb">
          <a href="../../../index.html">홈</a><span>›</span><a href="../../index.html">전국학원</a><span>›</span><a href="../index.html">{CATEGORY}</a><span>›</span><span>{esc(local)}</span>
        </nav>
        <p class="eyebrow">HIGH SCHOOL ENGLISH & MATH COACHING</p>
        <h1>{esc(title)}</h1>
        <p>{esc(description)}</p>
        <div class="academy-badges">
          <span>{esc(region)}</span><span>{esc(district)}</span><span>고등영수</span><span>내신·오답·플래너</span>
        </div>
      </div>
      <aside class="academy-side-card">
        <div>
          <p class="eyebrow">상담 핵심</p>
          <strong>고등 영수는 두 과목의 약점을 따로 보고, 계획은 하나로 관리합니다.</strong>
          <p>{esc(local)} 학생의 영어 본문·어휘·독해와 수학 개념·유형·오답을 함께 점검해 필요한 관리 순서를 정리합니다.</p>
        </div>
        <div class="hero-actions">
          <a class="btn btn-primary" href="tel:{PHONE_DISPLAY}">전화 상담하기</a>
          <a class="btn btn-ghost" href="../../../상담문의/index.html">상담문의</a>
        </div>
      </aside>
    </section>

    <section class="local-media-section">
      <img src="../../../{esc(rep)}" alt="{esc(title)} {SITE_NAME} 대표" style="display:none;">
      <figure class="local-media-card">
        <img src="../../../{esc(body_img)}" alt="{esc(title)} 본문 {SITE_NAME}">
      </figure>
      <figure class="local-map-card">
        <img src="../../../{esc(map_img)}" alt="{esc(title)} 지도 {SITE_NAME}">
        <figcaption>{esc(center or SITE_NAME)} 기준으로 {esc(local)} 학생의 고등 영수 상담 범위를 확인합니다. 실제 방문·상담 전에는 주소와 이동 동선을 함께 확인해 주세요.</figcaption>
      </figure>
    </section>

    <section class="section">
      <div class="section-panel">
        <div class="section-title">
          <p class="eyebrow">핵심 요약</p>
          <h2>{esc(title)} 선택 전 확인할 기준</h2>
          <p>{esc(local)} 고등학생에게 필요한 영수 관리는 단순히 영어와 수학 수업을 각각 듣는 것이 아니라, 두 과목의 시험 일정과 오답 원인을 함께 관리하는 것입니다.</p>
        </div>
        <div class="summary-grid">
          <article class="summary-card"><span>01</span><h3>영어 내신</h3><p>학교 본문, 어휘, 문법, 독해 흐름을 시험 범위에 맞춰 나누어 확인합니다.</p></article>
          <article class="summary-card"><span>02</span><h3>수학 오답</h3><p>계산 실수, 조건 해석, 개념 누락을 분리해 다시 풀어야 할 문제를 정리합니다.</p></article>
          <article class="summary-card"><span>03</span><h3>플래너 실행</h3><p>영어·수학 과제를 한 주 안에서 어떻게 배치하고 점검할지 계획합니다.</p></article>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-panel">
        <div class="section-title">
          <p class="eyebrow">AEO ANSWER</p>
          <h2>{esc(title)}은 어떤 학생에게 필요할까요?</h2>
        </div>
        <div class="answer-box"><h3>Q. 영어와 수학을 모두 챙겨야 하는데 시간이 부족하다면?</h3><p>A. 두 과목을 따로따로 밀어붙이기보다 시험 일정과 약점 단원을 기준으로 우선순위를 정해야 합니다. {esc(local)} 고등영수 상담에서는 이번 주에 먼저 끝낼 과목과 복습 주기를 함께 정리합니다.</p></div>
        <div class="answer-box"><h3>Q. 영어는 암기, 수학은 문제풀이만 반복해도 될까요?</h3><p>A. 고등 과정에서는 방식이 조금 더 세밀해야 합니다. 영어는 본문 이해와 문장 구조, 수학은 개념 적용과 오답 원인을 확인해야 점수가 안정됩니다.</p></div>
        <div class="answer-box"><h3>Q. 시험 직전에만 관리해도 괜찮을까요?</h3><p>A. 시험 직전 몰아치기보다 2~4주 단위로 영수 과목을 나누어 준비하는 편이 좋습니다. 플래너에 진도, 암기, 오답, 재풀이를 함께 기록하면 빠진 부분을 줄일 수 있습니다.</p></div>
      </div>
    </section>

    <section class="section">
      <div class="section-panel">
        <div class="section-title">
          <p class="eyebrow">LOCAL & STUDENT FIT</p>
          <h2>지역·학년·추천학생 기준</h2>
        </div>
        <div class="school-grid">
          <article class="school-card"><span>AREA</span><h3>{esc(region)} {esc(district)} {esc(local)}</h3><p>{esc(local)} 생활권 학생의 학교 진도와 시험 일정에 맞춰 고등 영수 관리 방향을 상담합니다.</p></article>
          <article class="school-card"><span>GRADE</span><h3>고등학생 중심</h3><p>고1 공통과정부터 고2·고3 선택과목과 영어 내신까지, 현재 수준과 목표에 맞춰 관리 순서를 나눕니다.</p></article>
          <article class="school-card"><span>RECOMMEND</span><h3>이런 학생에게 추천</h3><p>영어와 수학 중 한 과목만 흔들려도 전체 공부 리듬이 무너지는 학생, 오답과 암기 계획을 혼자 지키기 어려운 학생에게 적합합니다.</p></article>
          {school_card}{local_school_card}
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-panel">
        <div class="section-title">
          <p class="eyebrow">CENTER INFO</p>
          <h2>센터 기준 정보</h2>
        </div>
        <div class="summary-grid">
          <article class="summary-card"><span>센터명</span><h3>{esc(center or SITE_NAME)}</h3><p>{esc(region)} {esc(district)} {esc(local)} 학생 상담 기준으로 안내합니다.</p></article>
          <article class="summary-card"><span>주소</span><h3>위치 안내</h3><p>{esc(row.get("센터 주소", "상담 시 위치 안내"))}</p></article>
          <article class="summary-card"><span>등록 정보</span><h3>{esc(row.get("교육지원청명칭", "학원 등록 정보"))}</h3><p>{esc(row.get("교육지원청 등록번호", "등록 정보 확인"))}</p></article>
          <article class="summary-card"><span>교습비</span><h3>수강료 안내</h3>{tuition_html}</article>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-panel">
        <div class="section-title">
          <p class="eyebrow">CHECKLIST</p>
          <h2>상담 전 체크리스트</h2>
        </div>
        <div class="checklist-grid">
          <article class="checklist-card"><span>1</span><h3>최근 영어·수학 시험지</h3><p>점수보다 어떤 단원과 유형에서 왜 틀렸는지를 확인하는 데 필요합니다.</p></article>
          <article class="checklist-card"><span>2</span><h3>현재 교재와 학교 프린트</h3><p>학교 진도와 난이도를 확인해 바로 시작할 수 있는 위치를 잡습니다.</p></article>
          <article class="checklist-card"><span>3</span><h3>오답노트 또는 풀이 흔적</h3><p>틀린 이유가 개념, 암기, 독해, 계산, 시간 관리 중 어디에 가까운지 나눕니다.</p></article>
          <article class="checklist-card"><span>4</span><h3>목표와 가능한 공부 시간</h3><p>무리한 계획보다 실제로 지킬 수 있는 주간 영수 플래너를 만드는 것이 중요합니다.</p></article>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-panel">
        <div class="section-title">
          <p class="eyebrow">FAQ</p>
          <h2>{esc(title)} 자주 묻는 질문</h2>
        </div>
        <div class="faq-list">
          {faq_html}
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-panel">
        <div class="section-title">
          <p class="eyebrow">PARENT REVIEW</p>
          <h2>{esc(local)} 고등영수 상담 후기</h2>
        </div>
        <div class="review-grid">
          {review_html}
        </div>
        <div class="internal-links">
          <div class="directory-head">
            <h2>{esc(local)} 관련 고등 학습 페이지</h2>
            <p>같은 동네의 고등수학·고등영어 페이지와 가까운 고등영수학원 지역 페이지로 이동할 수 있습니다.</p>
          </div>
          <div class="related-grid">
            <a href="/전국학원/고등수학학원/{esc(slug)}/"><strong>{esc(local)} 고등수학학원</strong><small>수학 내신·오답 관리</small></a>
            <a href="/전국학원/고등영어학원/{esc(slug)}/"><strong>{esc(local)} 고등영어학원</strong><small>영어 내신·본문 관리</small></a>
            <a href="../index.html"><strong>{CATEGORY} 전체</strong><small>카테고리 허브</small></a>
            <a href="../../index.html"><strong>전국학원</strong><small>전체 허브</small></a>
            {nearby_links}
          </div>
        </div>
      </div>
    </section>
  </main>

{footer_html(3)}
"""
    return page_shell(head, body)


def category_hub(rows: list[dict[str, str]]) -> None:
    path = SITE / "전국학원" / CATEGORY
    path.mkdir(parents=True, exist_ok=True)
    title = f"{CATEGORY} | {SITE_NAME}"
    description = f"전국 371개 지역의 고등영수학원 학습관리 페이지를 지역별로 정리한 허브입니다. 영어·수학 내신, 오답 재학습, 플래너 관리 기준을 확인할 수 있습니다."
    canonical = canonical_for("전국학원", CATEGORY)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[f"{row.get('지역', '')} {row.get('시or구', '')}".strip()].append(row)
    grid = []
    for group, items in grouped.items():
        links = "\n".join(
            f'<a href="{slug_ko(row["근처 수업가능 동네"])}/"><strong>{esc(row["근처 수업가능 동네"])}</strong><small>{esc(row.get("시or구", ""))} 고등영수</small></a>'
            for row in items
        )
        grid.append(
            f'<article class="region-block"><div class="region-title"><h3>{esc(group)}</h3><span>{len(items)}개 지역</span></div><div class="local-button-grid">{links}</div></article>'
        )
    items_ld = [
        {
            "@type": "ListItem",
            "position": i + 1,
            "name": f"{row['근처 수업가능 동네']} {CATEGORY}",
            "url": canonical_for("전국학원", CATEGORY, slug_ko(row["근처 수업가능 동네"])),
        }
        for i, row in enumerate(rows)
    ]
    hub_faqs = [
        (
            "고등영수학원 페이지에서는 무엇을 먼저 확인하면 좋나요?",
            "자녀가 다니는 동네를 선택한 뒤 영어·수학 내신 범위, 오답 재학습, 플래너 실행 기준을 함께 확인하면 좋습니다.",
        ),
        (
            "고등영수학원은 고등수학학원이나 고등영어학원과 어떻게 다른가요?",
            "고등수학학원은 수학 개념·유형·오답 관리에, 고등영어학원은 본문·어휘·독해 관리에 집중하고, 고등영수학원은 두 과목의 시험 일정과 학습 시간을 함께 배치하는 데 초점을 둡니다.",
        ),
        (
            "영어와 수학을 같은 플래너로 관리하는 이유가 있나요?",
            "고등학생은 시험 기간에 두 과목의 과제가 동시에 몰리는 경우가 많습니다. 한 주 단위로 영어 암기·본문 정리와 수학 오답 재풀이를 함께 배치하면 빠지는 부분을 줄일 수 있습니다.",
        ),
    ]
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "@id": DOMAIN + "/#website", "url": DOMAIN + "/", "name": SITE_NAME, "inLanguage": "ko-KR"},
            {
                "@type": ["EducationalOrganization", "LocalBusiness"],
                "@id": DOMAIN + "/#organization",
                "name": SITE_NAME,
                "url": DOMAIN + "/",
                "telephone": PHONE_DISPLAY,
                "logo": DOMAIN + "/assets/favicon.png",
                "image": asset_url("assets/generated/coaching-center-hero-v2.png"),
                "areaServed": [{"@type": "Country", "name": "대한민국"}],
                "openingHoursSpecification": [
                    {
                        "@type": "OpeningHoursSpecification",
                        "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
                        "opens": "12:00",
                        "closes": "24:00",
                    }
                ],
                "contactPoint": {"@type": "ContactPoint", "telephone": "+82-10-6839-8283", "contactType": "학습 상담", "availableLanguage": "Korean"},
                "knowsAbout": ["고등영수학원", "고등 영어 내신", "고등 수학 내신", "플래너 관리", "오답 재학습", "학부모 상담"],
                "makesOffer": [
                    {"@type": "Offer", "itemOffered": {"@id": canonical + "#service"}},
                ],
            },
            {
                "@type": "CollectionPage",
                "@id": canonical + "#webpage",
                "url": canonical,
                "name": title,
                "description": description,
                "inLanguage": "ko-KR",
                "isPartOf": {"@id": DOMAIN + "/#website"},
                "about": [
                    {"@type": "Thing", "name": CATEGORY},
                    {"@type": "Thing", "name": "고등 영어 내신"},
                    {"@type": "Thing", "name": "고등 수학 내신"},
                    {"@type": "Thing", "name": "지역별 학습관리"},
                ],
                "mentions": [
                    {"@type": "Thing", "name": "영어·수학 플래너"},
                    {"@type": "Thing", "name": "오답 재학습"},
                    {"@type": "Thing", "name": "학부모 상담"},
                ],
                "mainEntity": {"@id": canonical + "#service"},
            },
            {
                "@type": "Service",
                "@id": canonical + "#service",
                "name": "전국 고등영수학원 학습관리 안내",
                "serviceType": "TutoringService / 고등영수 학습코칭",
                "description": "전국 371개 동네별 고등 영어·수학 내신, 오답 재학습, 플래너 실행 기준을 안내합니다.",
                "provider": {"@id": DOMAIN + "/#organization"},
                "areaServed": {"@type": "Country", "name": "대한민국"},
                "audience": {"@type": "EducationalAudience", "educationalRole": "student"},
                "about": [
                    {"@type": "Thing", "name": "고등영수학원"},
                    {"@type": "Thing", "name": "고등 영어 내신"},
                    {"@type": "Thing", "name": "고등 수학 내신"},
                    {"@type": "Thing", "name": "오답 재학습"},
                ],
                "makesOffer": [
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "고등영수 진단 상담"}},
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "영어·수학 플래너 관리"}},
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "오답 재학습 관리"}},
                ],
            },
            {
                "@type": "Article",
                "@id": canonical + "#article",
                "headline": title,
                "description": description,
                "image": [asset_url("assets/generated/coaching-center-hero-v2.png")],
                "inLanguage": "ko-KR",
                "datePublished": LASTMOD,
                "dateModified": LASTMOD,
                "author": {"@id": DOMAIN + "/#organization"},
                "publisher": {"@type": "Organization", "name": SITE_NAME, "url": DOMAIN + "/"},
                "mainEntityOfPage": {"@id": canonical + "#webpage"},
                "about": [
                    {"@type": "Thing", "name": CATEGORY},
                    {"@type": "Thing", "name": "영어·수학 내신"},
                    {"@type": "Thing", "name": "플래너 실행"},
                    {"@type": "Thing", "name": "오답 재학습"},
                ],
                "mentions": [
                    {"@type": "Thing", "name": "고등수학학원"},
                    {"@type": "Thing", "name": "고등영어학원"},
                    {"@type": "Thing", "name": "학부모 상담"},
                ],
                "articleSection": ["고등영수학원 허브", "지역별 바로가기", "상담 기준", "FAQ"],
            },
            {
                "@type": "BreadcrumbList",
                "@id": canonical + "#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "홈", "item": DOMAIN + "/"},
                    {"@type": "ListItem", "position": 2, "name": "전국학원", "item": canonical_for("전국학원")},
                    {"@type": "ListItem", "position": 3, "name": CATEGORY, "item": canonical},
                ],
            },
            {"@type": "ItemList", "@id": canonical + "#list", "name": f"{CATEGORY} 지역 페이지", "itemListElement": items_ld},
            {
                "@type": "FAQPage",
                "@id": canonical + "#faq",
                "mainEntity": [
                    {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                    for q, a in hub_faqs
                ],
            },
        ],
    }
    head = head_html(title, description, 2, canonical, "website", asset_url("assets/generated/coaching-center-hero-v2.png"), ld)
    body = f"""{nav_html(2)}
  <main>
    <section class="academy-hero">
      <div class="academy-hero-main">
        <nav class="breadcrumb" aria-label="breadcrumb"><a href="../../index.html">홈</a><span>›</span><a href="../index.html">전국학원</a><span>›</span><span>{CATEGORY}</span></nav>
        <p class="eyebrow">HIGH SCHOOL ENGLISH & MATH DIRECTORY</p>
        <h1>{CATEGORY}</h1>
        <p>고등학생의 영어와 수학을 함께 관리해야 하는 학부모님을 위해 371개 동네별 상담 기준을 정리했습니다. 원하는 지역을 선택하면 해당 동네의 고등영수 학습관리 페이지로 이동합니다.</p>
      </div>
      <aside class="academy-side-card"><div><p class="eyebrow">활용 방법</p><strong>동네를 먼저 고른 뒤 영어·수학 관리 기준을 확인하세요.</strong><p>학교 진도, 내신 범위, 플래너 실행, 오답 재학습을 한 페이지에서 볼 수 있습니다.</p></div></aside>
    </section>

    <section class="academy-directory">
      <div class="directory-head"><h2>지역별 {CATEGORY} 바로가기</h2><p>광역·시군구 기준으로 묶어 동네 페이지를 찾기 쉽게 정리했습니다.</p></div>
      <div>
        {"".join(grid)}
      </div>
    </section>

    <section class="section">
      <div class="section-panel">
        <div class="section-title">
          <p class="eyebrow">ACADEMY HUB FAQ</p>
          <h2>고등영수학원 페이지를 활용하는 방법</h2>
          <p>영어와 수학을 함께 관리해야 하는 고등학생이라면 지역 페이지에서 학교 진도, 시험 범위, 플래너 실행 기준을 같이 확인해 보세요.</p>
        </div>
        <div class="faq-list">
          {''.join(f'<details class="faq-item"{" open" if i == 0 else ""}><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for i, (q, a) in enumerate(hub_faqs))}
        </div>
      </div>
    </section>
  </main>
{footer_html(2)}
"""
    (path / "index.html").write_text(page_shell(head, body), encoding="utf-8", newline="\n")


def update_main_hub() -> None:
    path = SITE / "전국학원" / "index.html"
    doc = path.read_text(encoding="utf-8")
    doc = doc.replace("예: 전국학원 / 고등영어학원 / 명일동", "예: 전국학원 / 고등영수학원 / 명일동")
    doc = re.sub(
        r'<div class="category-grid">.*?</div>\s*</section>',
        '''<div class="category-grid"><a class="category-card" href="고등수학학원/index.html"><strong>고등수학학원</strong><small>고등수학 내신·오답·플래너 지역별 안내 · 371개 지역</small></a>
<a class="category-card" href="고등영어학원/index.html"><strong>고등영어학원</strong><small>고등영어 어휘·문법·독해·내신 지역별 안내 · 371개 지역</small></a>
<a class="category-card" href="고등영수학원/index.html"><strong>고등영수학원</strong><small>고등 영어·수학 내신과 오답 재학습 지역별 안내 · 371개 지역</small></a></div>
    </section>''',
        doc,
        count=1,
        flags=re.S,
    )
    doc = doc.replace(
        "고등수학학원, 고등영어학원처럼 과목 카테고리를 먼저 고른 뒤",
        "고등수학학원, 고등영어학원, 고등영수학원처럼 과목 카테고리를 먼저 고른 뒤",
    )
    doc = doc.replace(
        "고등수학학원과 고등영어학원 페이지는 어떻게 다른가요?",
        "고등수학학원·고등영어학원·고등영수학원 페이지는 어떻게 다른가요?",
    )
    doc = doc.replace(
        "수학은 개념·유형·오답 원인 관리 중심, 영어는 어휘·문법·독해·학교 본문 관리 중심으로 상담 포인트를 다르게 정리했습니다.",
        "수학은 개념·유형·오답 원인 관리 중심, 영어는 어휘·문법·독해·학교 본문 관리 중심, 영수는 두 과목의 시험 일정과 플래너 실행을 함께 보는 구조로 정리했습니다.",
    )
    match = re.search(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S)
    if match:
        data = json.loads(match.group(1))
        for node in data.get("@graph", []):
            if isinstance(node, dict) and node.get("@type") == "ItemList" and str(node.get("@id", "")).endswith("#categories"):
                items = node.setdefault("itemListElement", [])
                if not any(item.get("name") == CATEGORY for item in items if isinstance(item, dict)):
                    items.append({"@type": "ListItem", "position": len(items) + 1, "name": CATEGORY, "url": canonical_for("전국학원", CATEGORY)})
            if isinstance(node, dict) and node.get("@type") in ("CollectionPage", "Article"):
                for key in ("about", "mentions"):
                    values = node.setdefault(key, [])
                    if isinstance(values, list) and not any(v.get("name") == CATEGORY for v in values if isinstance(v, dict)):
                        values.append({"@type": "Thing", "name": CATEGORY})
        doc = doc[: match.start(1)] + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + doc[match.end(1) :]
    path.write_text(doc, encoding="utf-8", newline="\n")


def generate_sitemap_robots() -> None:
    htmls = sorted(
        [p for p in SITE.rglob("index.html") if not any(part in {".git", ".vercel", "node_modules", "tmp"} for part in p.relative_to(SITE).parts)],
        key=lambda p: (len(p.parent.relative_to(SITE).parts), p.parent.as_posix()),
    )
    seen: set[str] = set()
    urls: list[tuple[str, str]] = []
    for p in htmls:
        rel_dir = p.parent.relative_to(SITE).as_posix()
        raw_path = "/" if rel_dir == "." else f"/{rel_dir}/"
        url = DOMAIN + quote(raw_path, safe="/")
        if url not in seen:
            seen.add(url)
            urls.append((url, raw_path))

    def priority(raw: str) -> str:
        if raw == "/":
            return "1.0"
        if raw == "/전국학원/":
            return "0.9"
        depth = raw.strip("/").count("/") + 1
        if raw.startswith("/전국학원/") and depth == 2:
            return "0.85"
        if raw.startswith("/전국학원/") and depth >= 3:
            return "0.75"
        return "0.8"

    def changefreq(raw: str) -> str:
        if raw == "/" or raw == "/전국학원/":
            return "weekly"
        if raw.startswith("/전국학원/"):
            return "monthly"
        return "weekly"

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, raw in urls:
        lines.extend(
            [
                "  <url>",
                f"    <loc>{xml_escape(url)}</loc>",
                f"    <lastmod>{LASTMOD}</lastmod>",
                f"    <changefreq>{changefreq(raw)}</changefreq>",
                f"    <priority>{priority(raw)}</priority>",
                "  </url>",
            ]
        )
    lines.append("</urlset>")
    (SITE / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n", encoding="utf-8")
    print(f"sitemap_urls={len(urls)}")


def main() -> None:
    rows = read_csv(COMMON / "센터정보 정리.csv")
    school_lookup = get_school_lookup()
    base_faq = read_faq(COMMON / "FAQ.txt")
    review_lines = read_reviews(COMMON / "학부모 후기.txt")
    reps = representative_images(len(rows))
    category_hub(rows)
    out_dir = SITE / "전국학원" / CATEGORY
    for idx, row in enumerate(rows):
        local = row["근처 수업가능 동네"]
        slug = slug_ko(local)
        page_dir = out_dir / slug
        page_dir.mkdir(parents=True, exist_ok=True)
        school_row = merged_school_row(row, school_lookup)
        page_dir.joinpath("index.html").write_text(
            page_html(row, school_row, rows, reps[idx], base_faq, review_lines, idx),
            encoding="utf-8",
            newline="\n",
        )
    update_main_hub()
    generate_sitemap_robots()
    print(f"generated_category={CATEGORY} pages={len(rows) + 1}")


if __name__ == "__main__":
    main()
