from __future__ import annotations

import json
import random
import re
import shutil
from pathlib import Path

import generate_highschool_math_pages as shared


SITE = shared.SITE
COMMON = shared.COMMON
SITE_NAME = shared.SITE_NAME
PHONE_DISPLAY = shared.PHONE_DISPLAY
PHONE_LINK = shared.PHONE_LINK
CATEGORY = "고등영어학원"


def esc(value: object) -> str:
    return shared.esc(value)


def slug_ko(name: str) -> str:
    return shared.slug_ko(name)


def split_items(value: str) -> list[str]:
    return shared.split_items(value)


def rel_prefix(depth: int) -> str:
    return "../" * depth


def existing_or_copy_rep_images(rows: list[dict[str, str]]) -> list[str]:
    local_dir = SITE / "assets" / "representative"
    local_dir.mkdir(parents=True, exist_ok=True)
    local_images = sorted(
        [p for p in local_dir.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}],
        key=lambda p: p.name,
    )
    if len(local_images) < len(rows):
        src_dir = COMMON / "대표이미지"
        src_images = sorted(
            [p for p in src_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}],
            key=lambda p: p.name,
        )
        for i, src in enumerate(src_images[: len(rows)], 1):
            dst = local_dir / f"rep-{i:03d}{src.suffix.lower()}"
            if not dst.exists():
                shutil.copy2(src, dst)
        local_images = sorted(
            [p for p in local_dir.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}],
            key=lambda p: p.name,
        )
    rng = random.Random(8283)
    rng.shuffle(local_images)
    return [f"assets/representative/{local_images[i % len(local_images)].name}" for i in range(len(rows))]


def school_names(row: dict[str, str]) -> list[str]:
    names: list[str] = []
    for key in ("타깃학교\n(고)", "타깃학교\n(중)", "타깃학교\n(초)"):
        names.extend(split_items(row.get(key, "")))
    result: list[str] = []
    for name in names:
        if name not in result:
            result.append(name)
    return result


def make_faqs(local: str, district: str, title: str, base_faq: list[tuple[str, str]], idx: int) -> list[tuple[str, str]]:
    base = base_faq[(idx + 3) % len(base_faq)][1] if base_faq else "학생의 현재 학습 상태를 확인한 뒤 안내합니다."
    return [
        (
            f"{title} 상담은 어떤 순서로 진행되나요?",
            f"먼저 현재 학교 진도, 최근 시험지, 사용하는 교재, 어휘 누적 상태를 확인합니다. 이후 {local} 학생의 문법·독해·학교 본문 암기·서술형 약점을 나누어 고등영어 관리 순서를 정리합니다.",
        ),
        (
            f"{local} 고등영어학원에서는 내신 영어를 어떻게 관리하나요?",
            f"{district} 학교 시험 범위에 맞춰 본문 분석, 어휘 암기, 문법 포인트, 변형 문제, 서술형 대비를 순서대로 봅니다. 단순 암기보다 왜 틀렸는지와 다음 시험에서 어떻게 줄일지를 함께 확인합니다.",
        ),
        (
            "고등영어가 갑자기 어려워진 학생도 상담 가능한가요?",
            f"가능합니다. {base} 고등영어는 중등 영어보다 지문 길이, 어휘량, 문장 구조가 빠르게 늘어나기 때문에 현재 막히는 지점을 먼저 찾는 것이 중요합니다.",
        ),
        (
            f"{title} 수업 전 준비하면 좋은 자료가 있나요?",
            "최근 시험지, 학교 프린트, 교과서 본문, 사용하는 문제집, 단어장이나 오답 표시가 있으면 좋습니다. 자료가 부족해도 상담을 통해 현재 수준과 필요한 관리 방향을 먼저 정리할 수 있습니다.",
        ),
        (
            "어휘·문법·독해를 한 번에 관리할 수 있나요?",
            f"네. {local} 학생의 학년과 학교 진도에 맞춰 어휘 누적, 문장 구조 분석, 독해 흐름, 본문 암기, 오답 재확인을 함께 설계합니다.",
        ),
    ]


def make_reviews(local: str, title: str, review_lines: list[str], idx: int) -> list[dict[str, object]]:
    rng = random.Random(2000 + idx)
    pool = review_lines[:]
    rng.shuffle(pool)
    selected = pool[:6] if len(pool) >= 6 else pool
    reviews = []
    for i, text in enumerate(selected):
        if i == 0:
            body = f"{title} 상담 후 아이가 영어 본문과 문법을 어떤 순서로 봐야 하는지 이해하게 되었습니다."
        elif i == 1:
            body = f"{local}에서 고등영어 관리를 알아보며 어휘, 독해, 내신 대비를 함께 점검받아 도움이 되었습니다."
        else:
            body = f"{text} 고등영어 학습관리 과정에서도 아이에게 필요한 부분을 차분히 짚어주셨습니다."
        reviews.append({"body": body, "rating": 4 if i == 5 else 5})
    return reviews


REVIEW_TITLE_BANK = [
    "본문 흐름을 이해하게 됐어요",
    "어휘 복습이 꾸준해졌어요",
    "문법 적용이 편해졌어요",
    "독해 오답을 다시 보게 됐어요",
    "시험 준비가 덜 흔들렸어요",
    "학습 방향이 분명해졌어요",
]


def review_card_title(idx: int) -> str:
    return REVIEW_TITLE_BANK[idx % len(REVIEW_TITLE_BANK)]


def nav_html(depth: int) -> str:
    return shared.nav_html(depth, active="전국학원")


def footer_html(depth: int) -> str:
    return shared.footer_html(depth)


def head_html(title: str, description: str, depth: int, canonical: str, image: str, ld: dict) -> str:
    return shared.head_html(title, description, depth, canonical, "article", image, ld)


def root_hub(rows: list[dict[str, str]]) -> None:
    categories = [
        ("고등수학학원", "고등수학 내신·오답·플래너 지역별 안내"),
        ("고등영어학원", "고등영어 어휘·문법·독해·내신 지역별 안내"),
    ]
    existing = [(name, desc) for name, desc in categories if (SITE / "전국학원" / name).exists()]
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": "/전국학원/#webpage",
                "url": "/전국학원/",
                "name": "전국학원",
                "description": "코칭센터 전국 학원 안내 허브입니다.",
                "inLanguage": "ko-KR",
            },
            {
                "@type": "BreadcrumbList",
                "@id": "/전국학원/#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "홈", "item": "/"},
                    {"@type": "ListItem", "position": 2, "name": "전국학원", "item": "/전국학원/"},
                ],
            },
            {
                "@type": "ItemList",
                "@id": "/전국학원/#categories",
                "name": "전국학원 카테고리",
                "itemListElement": [
                    {"@type": "ListItem", "position": i + 1, "name": name, "url": f"/전국학원/{name}/"}
                    for i, (name, _) in enumerate(existing)
                ],
            },
        ],
    }
    head = shared.head_html(
        "전국학원 | 코칭센터",
        "코칭센터 전국학원 허브입니다. 과목별 카테고리와 지역별 학습관리 안내 페이지로 이동할 수 있습니다.",
        1,
        "/전국학원/",
        "website",
        "/assets/generated/coaching-center-hero-v2.webp",
        ld,
    )
    cards = "\n".join(
        f'<a class="category-card" href="{esc(name)}/index.html"><strong>{esc(name)}</strong><small>{esc(desc)} · 371개 지역</small></a>'
        for name, desc in existing
    )
    body = f"""{nav_html(1)}
  <main>
    <section class="academy-hero">
      <div class="academy-hero-main">
        <nav class="breadcrumb" aria-label="breadcrumb"><a href="../index.html">홈</a><span>›</span><span>전국학원</span></nav>
        <p class="eyebrow">NATIONAL ACADEMY HUB</p>
        <h1>전국학원</h1>
        <p>과목과 학년 카테고리별로 지역 학습관리 페이지를 정리하는 허브입니다. 원하는 카테고리를 선택하면 지역별 상세 안내로 이동할 수 있습니다.</p>
      </div>
      <aside class="academy-side-card"><div><p class="eyebrow">구조 안내</p><strong>카테고리에서 지역으로 이동하는 방식</strong><p>예: 전국학원 / 고등영어학원 / 명일동</p></div></aside>
    </section>
    <section class="academy-directory">
      <div class="directory-head"><h2>학원 카테고리</h2><p>현재 생성된 카테고리입니다. 앞으로 영어수학, 중등, 초등 카테고리도 같은 방식으로 확장할 수 있습니다.</p></div>
      <div class="category-grid">{cards}</div>
    </section>
  </main>
{footer_html(1)}"""
    out = SITE / "전국학원" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(shared.page_shell(head, body), encoding="utf-8")


def category_hub(rows: list[dict[str, str]]) -> None:
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(row.get("지역", "기타"), []).append(row)
    blocks = []
    for region, items in groups.items():
        links = "\n".join(
            f'<a href="{slug_ko(r["근처 수업가능 동네"])}/"><strong>{esc(r["근처 수업가능 동네"])}</strong><small>{esc(r.get("시or구", ""))} 고등영어</small></a>'
            for r in items
        )
        blocks.append(f'<div class="region-block"><div class="region-title"><h3>{esc(region)}</h3><span>{len(items)}개 지역</span></div><div class="local-button-grid">{links}</div></div>')
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": f"/전국학원/{CATEGORY}/#webpage",
                "url": f"/전국학원/{CATEGORY}/",
                "name": CATEGORY,
                "description": "고등영어학원 지역별 안내 허브입니다.",
                "inLanguage": "ko-KR",
            },
            {
                "@type": "BreadcrumbList",
                "@id": f"/전국학원/{CATEGORY}/#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "홈", "item": "/"},
                    {"@type": "ListItem", "position": 2, "name": "전국학원", "item": "/전국학원/"},
                    {"@type": "ListItem", "position": 3, "name": CATEGORY, "item": f"/전국학원/{CATEGORY}/"},
                ],
            },
            {
                "@type": "ItemList",
                "@id": f"/전국학원/{CATEGORY}/#itemlist",
                "name": "고등영어학원 지역 목록",
                "numberOfItems": len(rows),
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": i + 1,
                        "name": f"{r['근처 수업가능 동네']} 고등영어학원",
                        "url": f"/전국학원/{CATEGORY}/{slug_ko(r['근처 수업가능 동네'])}/",
                    }
                    for i, r in enumerate(rows)
                ],
            },
        ],
    }
    head = shared.head_html(
        f"{CATEGORY} | {SITE_NAME}",
        "전국 371개 지역의 고등영어학원 학습관리 페이지를 지역별로 정리한 허브입니다.",
        2,
        f"/전국학원/{CATEGORY}/",
        "website",
        "/assets/generated/coaching-center-hero-v2.webp",
        ld,
    )
    body = f"""{nav_html(2)}
  <main>
    <section class="academy-hero">
      <div class="academy-hero-main">
        <nav class="breadcrumb" aria-label="breadcrumb"><a href="../../index.html">홈</a><span>›</span><a href="../index.html">전국학원</a><span>›</span><span>{CATEGORY}</span></nav>
        <p class="eyebrow">HIGH SCHOOL ENGLISH DIRECTORY</p>
        <h1>{CATEGORY}</h1>
        <p>지역별 고등영어 상담 기준을 한눈에 찾을 수 있도록 정리했습니다. 각 페이지에는 어휘·문법·독해·학교 본문 관리와 FAQ, 학부모 후기, 내부링크가 함께 구성됩니다.</p>
      </div>
      <aside class="academy-side-card"><div><p class="eyebrow">총 지역</p><strong>{len(rows)}개</strong><p>서울부터 제주까지 지역명 기준으로 고등영어학원 페이지를 생성했습니다.</p></div></aside>
    </section>
    <section class="academy-directory">
      <div class="directory-head"><h2>지역별 고등영어학원 바로가기</h2><p>광역 지역별로 나누어 보기 쉽게 정리했습니다. 원하는 동네를 선택하면 해당 지역 고등영어학원 안내로 이동합니다.</p></div>
      {"".join(blocks)}
    </section>
  </main>
{footer_html(2)}"""
    out = SITE / "전국학원" / CATEGORY / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(shared.page_shell(head, body), encoding="utf-8")


def local_page(row: dict[str, str], idx: int, rep_image: str, all_rows: list[dict[str, str]], faq_base, review_lines) -> str:
    local = row["근처 수업가능 동네"].strip()
    slug = slug_ko(local)
    region = row.get("지역", "").strip()
    district = row.get("시or구", "").strip()
    center = row.get("센터명", "").strip() or f"{local} 학습관리"
    address = row.get("센터 주소", "").strip()
    title = f"{local} 고등영어학원"
    description = f"{region} {district} {local} 고등학생을 위한 고등영어학원 안내입니다. 영어 내신, 학교 본문, 어휘, 문법, 독해, 오답 재학습 기준을 상담 전 확인할 수 있습니다."
    canonical = f"/전국학원/{CATEGORY}/{slug}/"
    rep_root = "/" + rep_image.replace("\\", "/")
    center_img = "assets/centers/common/seoul6839.webp" if region == "서울" else "assets/centers/common/local6839.webp"
    map_img = shared.find_map(row)
    schools = school_names(row)
    high_schools = split_items(row.get("타깃학교\n(고)", ""))
    high_text = ", ".join(high_schools) if high_schools else "상담 시 고등학교 영어 진도와 시험 범위를 확인합니다."
    schools_text = ", ".join(schools[:12]) if schools else "상담 시 현재 학교와 시험 범위를 기준으로 확인합니다."
    fee_link = row.get("센터 교습비", "").strip()
    reg_no = row.get("교육지원청 등록번호", "").strip()
    education_name = row.get("교육지원청명칭", "").strip()
    faqs = make_faqs(local, district, title, faq_base, idx)
    reviews = make_reviews(local, title, review_lines, idx)

    related_source = [r for r in all_rows if r.get("시or구") == district and r.get("근처 수업가능 동네") != local]
    if len(related_source) < 7:
        related_source += [r for r in all_rows if r.get("지역") == region and r.get("근처 수업가능 동네") != local]
    related = []
    for r in related_source:
        name = r["근처 수업가능 동네"].strip()
        if name and name not in [x[0] for x in related]:
            related.append((name, f"/전국학원/{CATEGORY}/{slug_ko(name)}/", r.get("시or구", "")))
        if len(related) >= 7:
            break

    about = [
        {"@type": "Thing", "name": title},
        {"@type": "Place", "name": local},
        {"@type": "Thing", "name": "고등영어학원"},
        {"@type": "Thing", "name": "영어 내신 대비"},
        {"@type": "Thing", "name": "학교 본문 관리"},
        {"@type": "Thing", "name": "어휘·문법·독해 관리"},
    ]
    mentions = [
        {"@type": "Place", "name": region},
        {"@type": "Place", "name": district},
        {"@type": "EducationalOrganization", "name": center},
    ] + [{"@type": "School", "name": s} for s in schools]
    has_part = ["핵심 요약", "답변형 고등영어 안내", "지역·학년·추천학생", "수업 가능 학교", "센터 기준 정보", "상담 전 체크리스트", "FAQ", "학부모 후기", "내부링크"]
    org_id = f"{canonical}#organization"
    webpage_id = f"{canonical}#webpage"
    service_id = f"{canonical}#service"
    breadcrumb_id = f"{canonical}#breadcrumb"
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": webpage_id,
                "url": canonical,
                "name": title,
                "description": description,
                "inLanguage": "ko-KR",
                "primaryImageOfPage": {"@id": f"{canonical}#primaryimage"},
                "breadcrumb": {"@id": breadcrumb_id},
                "mainEntity": {"@id": service_id},
                "about": about,
                "mentions": mentions,
                "hasPart": [{"@type": "WebPageElement", "name": x} for x in has_part],
            },
            {"@type": "ImageObject", "@id": f"{canonical}#primaryimage", "url": rep_root, "caption": f"{title} 대표 이미지"},
            {
                "@type": "BreadcrumbList",
                "@id": breadcrumb_id,
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "홈", "item": "/"},
                    {"@type": "ListItem", "position": 2, "name": "전국학원", "item": "/전국학원/"},
                    {"@type": "ListItem", "position": 3, "name": CATEGORY, "item": f"/전국학원/{CATEGORY}/"},
                    {"@type": "ListItem", "position": 4, "name": local, "item": canonical},
                ],
            },
            {
                "@type": ["EducationalOrganization", "LocalBusiness"],
                "@id": org_id,
                "name": title,
                "alternateName": [SITE_NAME, center, f"{local} 고등영어 학습관리"],
                "url": canonical,
                "telephone": PHONE_DISPLAY,
                "openingHours": "Mo-Sa 12:00-24:00",
                "openingHoursSpecification": [{"@type": "OpeningHoursSpecification", "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"], "opens": "12:00", "closes": "24:00"}],
                "areaServed": {"@type": "Place", "name": local},
                "address": {"@type": "PostalAddress", "streetAddress": address, "addressRegion": region, "addressLocality": district, "addressCountry": "KR"},
                "knowsAbout": ["고등영어", "영어 내신 대비", "어휘 관리", "문법 정리", "독해 훈련", "학교 본문 관리"],
                "makesOffer": [
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{local} 고등영어 진단 상담", "serviceType": "TutoringService"}},
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{local} 영어 내신 대비", "serviceType": "TutoringService"}},
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{local} 어휘·문법·독해 관리", "serviceType": "TutoringService"}},
                ],
                "aggregateRating": {"@type": "AggregateRating", "ratingValue": "4.8", "bestRating": "5", "ratingCount": "6", "reviewCount": "6"},
                "review": [{"@type": "Review", "author": {"@type": "Person", "name": "학부모"}, "reviewBody": r["body"], "reviewRating": {"@type": "Rating", "ratingValue": str(r["rating"]), "bestRating": "5"}} for r in reviews],
            },
            {
                "@type": "Article",
                "@id": f"{canonical}#article",
                "headline": title,
                "description": description,
                "image": [rep_root, "/" + center_img, "/" + map_img],
                "inLanguage": "ko-KR",
                "datePublished": "2026-07-02",
                "dateModified": "2026-07-02",
                "author": {"@id": org_id},
                "publisher": {"@type": "Organization", "name": SITE_NAME, "url": "/"},
                "mainEntityOfPage": {"@id": webpage_id},
                "about": about,
                "mentions": mentions,
                "articleSection": has_part,
            },
            {
                "@type": "Service",
                "@id": service_id,
                "name": f"{title} 학습관리",
                "serviceType": "TutoringService",
                "description": f"{local} 고등학생의 영어 내신, 학교 본문, 어휘, 문법, 독해 오답을 함께 관리합니다.",
                "provider": {"@id": org_id},
                "areaServed": {"@type": "Place", "name": local},
                "audience": {"@type": "EducationalAudience", "educationalRole": "student"},
                "about": about,
                "mentions": mentions,
                "makesOffer": [
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{local} 고등영어 본문 분석"}},
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{local} 영어 어휘·문법 관리"}},
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{local} 영어 독해 오답 재학습"}},
                ],
            },
            {"@type": "FAQPage", "@id": f"{canonical}#faq", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]},
            {"@type": "ItemList", "@id": f"{canonical}#target-schools", "name": f"{title} 수업 가능 학교 확인 항목", "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": s} for i, s in enumerate(schools)]},
            {"@type": "ItemList", "@id": f"{canonical}#related", "name": f"{local} 고등영어학원 관련 내부링크", "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": name, "url": url} for i, (name, url, _) in enumerate(related)]},
        ],
    }

    head = head_html(f"{title} | {SITE_NAME}", description, 3, canonical, rep_root, ld)
    rep_rel = "../../../" + rep_image
    center_rel = "../../../" + center_img
    map_rel = "../../../" + map_img
    school_cards = (
        f"<article class=\"school-card\"><span>HIGH SCHOOL</span><h3>고등 영어 상담 참고 학교</h3><p>{esc(high_text)}</p></article>"
        f"<article class=\"school-card\"><span>LOCAL SCHOOL</span><h3>지역 학교 흐름 확인</h3><p>{esc(schools_text)}</p></article>"
        if schools
        else '<article class="school-card"><span>LOCAL SCHOOL</span><h3>학교별 범위 확인</h3><p>상담 시 현재 학교, 시험 범위, 수행평가 일정을 기준으로 고등영어 관리 방향을 정리합니다.</p></article>'
    )
    related_html = "\n".join(f'<a href="{esc(url)}"><strong>{esc(name)} 고등영어학원</strong><small>{esc(area)} 지역 페이지</small></a>' for name, url, area in related)
    faq_html = "\n".join(f'<details class="faq-item"{" open" if i == 0 else ""}><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for i, (q, a) in enumerate(faqs))
    review_html = "\n".join(f'<article class="review-card"><span>REVIEW {i + 1:02d}</span><h3>{esc(review_card_title(i))}</h3><p class="star-line">{"★" * int(r["rating"])}{"☆" * (5 - int(r["rating"]))}</p><p>{esc(r["body"])}</p></article>' for i, r in enumerate(reviews))
    fee_html = f'<p><a href="{esc(fee_link)}" target="_blank" rel="noopener noreferrer">교습비 안내 확인</a></p>' if fee_link else "<p>교습비는 상담 시 과정과 과목 구성에 따라 안내합니다.</p>"

    body = f"""{nav_html(3)}
  <main>
    <section class="academy-hero">
      <div class="academy-hero-main">
        <nav class="breadcrumb" aria-label="breadcrumb">
          <a href="../../../index.html">홈</a><span>›</span><a href="../../index.html">전국학원</a><span>›</span><a href="../index.html">고등영어학원</a><span>›</span><span>{esc(local)}</span>
        </nav>
        <p class="eyebrow">HIGH SCHOOL ENGLISH COACHING</p>
        <h1>{esc(title)}</h1>
        <p>{esc(description)}</p>
        <div class="academy-badges"><span>{esc(region)}</span><span>{esc(district)}</span><span>고등영어</span><span>어휘·문법·독해·내신</span></div>
      </div>
      <aside class="academy-side-card">
        <div><p class="eyebrow">상담 핵심</p><strong>고등영어는 암기량보다 “해석과 적용 흐름”을 먼저 봅니다.</strong><p>{esc(local)} 학생의 학교 본문, 어휘 누적, 문법 포인트, 독해 오답을 기준으로 필요한 관리 순서를 정리합니다.</p></div>
        <div class="hero-actions"><a class="btn btn-primary" href="tel:{PHONE_DISPLAY}">전화 상담하기</a><a class="btn btn-ghost" href="../../../상담문의/index.html">상담문의</a></div>
      </aside>
    </section>

    <section class="local-media-section">
      <img src="{esc(rep_rel)}" alt="{esc(title + ' ' + SITE_NAME + ' 대표')}" style="display:none;">
      <figure class="local-media-card"><img src="{esc(center_rel)}" width="918" height="16116" loading="lazy" decoding="async" alt="{esc(title + ' 본문 ' + SITE_NAME)}"></figure>
      <figure class="local-map-card"><img src="{esc(map_rel)}" alt="{esc(title + ' 지도 ' + SITE_NAME)}"><figcaption>{esc(center)} 기준으로 {esc(local)} 학생의 고등영어 상담 범위를 확인합니다. 실제 방문·상담 전에는 주소와 이동 동선을 함께 확인해 주세요.</figcaption></figure>
    </section>

    <section class="section"><div class="section-panel"><div class="section-title"><p class="eyebrow">핵심 요약</p><h2>{esc(local)} 고등영어학원 선택 전 확인할 기준</h2><p>{esc(local)} 고등학생에게 필요한 영어 관리는 단순 암기보다 학교 본문, 어휘 누적, 문법 적용, 독해 오답, 서술형 대비를 함께 보는 것입니다.</p></div><div class="summary-grid"><article class="summary-card"><span>01</span><h3>본문 흐름</h3><p>교과서와 학교 프린트의 핵심 문장, 변형 포인트, 서술형 가능성을 함께 확인합니다.</p></article><article class="summary-card"><span>02</span><h3>어휘·문법</h3><p>단어 암기 여부뿐 아니라 문장 안에서 문법을 적용하고 해석하는 습관을 봅니다.</p></article><article class="summary-card"><span>03</span><h3>독해 오답</h3><p>지문 해석, 근거 찾기, 선택지 비교 과정에서 반복되는 실수를 분리합니다.</p></article></div></div></section>

    <section class="section"><div class="section-panel"><div class="section-title"><p class="eyebrow">AEO ANSWER</p><h2>{esc(title)}은 어떤 학생에게 필요할까요?</h2></div><div class="answer-box"><h3>Q. 본문은 외웠는데 시험에서 틀린다면?</h3><p>A. 단순 암기보다 변형 문장과 문법 포인트를 적용하는 연습이 필요할 수 있습니다. {esc(local)} 고등영어 상담에서는 본문 암기와 문제 적용 사이의 간격을 확인합니다.</p></div><div class="answer-box"><h3>Q. 단어를 외워도 독해가 느리다면?</h3><p>A. 어휘량뿐 아니라 문장 구조 분석, 접속사 흐름, 핵심 근거 찾기 훈련이 필요합니다. 오답을 유형별로 분리해 다시 읽는 방식을 잡습니다.</p></div><div class="answer-box"><h3>Q. 영어 내신을 어디서부터 준비해야 할까요?</h3><p>A. 현재 학교 시험 범위와 최근 시험 결과를 기준으로 본문, 문법, 어휘, 서술형, 변형 문제 순서를 나눠 준비합니다.</p></div></div></section>

    <section class="section"><div class="section-panel"><div class="section-title"><p class="eyebrow">LOCAL & STUDENT FIT</p><h2>지역·학년·추천학생 기준</h2></div><div class="school-grid"><article class="school-card"><span>AREA</span><h3>{esc(region)} {esc(district)} {esc(local)}</h3><p>{esc(local)} 생활권 학생의 학교 영어 진도와 시험 일정에 맞춰 관리 방향을 상담합니다.</p></article><article class="school-card"><span>GRADE</span><h3>고등학생 중심</h3><p>고1 공통영어부터 고2·고3 내신, 모의고사 독해, 어휘 누적까지 현재 목표에 맞춰 관리합니다.</p></article><article class="school-card"><span>RECOMMEND</span><h3>이런 학생에게 추천</h3><p>본문 암기는 했지만 변형 문제에 약한 학생, 독해 속도가 느린 학생, 어휘와 문법이 따로 노는 학생에게 적합합니다.</p></article>{school_cards}</div></div></section>

    <section class="section"><div class="section-panel"><div class="section-title"><p class="eyebrow">CENTER INFO</p><h2>센터 기준 정보</h2></div><div class="summary-grid"><article class="summary-card"><span>센터명</span><h3>{esc(center)}</h3><p>{esc(region)} {esc(district)} {esc(local)} 학생 상담 기준으로 안내합니다.</p></article><article class="summary-card"><span>주소</span><h3>위치 안내</h3><p>{esc(address) if address else "상담 시 위치 정보를 확인해 주세요."}</p></article><article class="summary-card"><span>등록 정보</span><h3>{esc(education_name) if education_name else "교육지원청 등록 정보"}</h3><p>{esc(reg_no) if reg_no else "상담 시 교육지원청 등록 정보를 확인할 수 있습니다."}</p></article><article class="summary-card"><span>교습비</span><h3>수강료 안내</h3>{fee_html}</article></div></div></section>

    <section class="section"><div class="section-panel"><div class="section-title"><p class="eyebrow">CHECKLIST</p><h2>상담 전 체크리스트</h2></div><div class="checklist-grid"><article class="checklist-card"><span>1</span><h3>최근 시험지</h3><p>점수보다 본문, 문법, 독해 중 어디서 흔들렸는지를 확인합니다.</p></article><article class="checklist-card"><span>2</span><h3>학교 자료</h3><p>교과서 본문, 학교 프린트, 부교재 범위가 있으면 내신 대비 기준을 잡기 쉽습니다.</p></article><article class="checklist-card"><span>3</span><h3>단어장·오답</h3><p>어휘 암기 상태와 반복 오답을 확인해 복습 주기를 정합니다.</p></article><article class="checklist-card"><span>4</span><h3>학습 습관</h3><p>숙제 완료율, 복습 시간, 플래너 실행 여부를 확인해 관리 강도를 정합니다.</p></article></div></div></section>

    <section class="section"><div class="section-panel"><div class="section-title"><p class="eyebrow">FAQ</p><h2>{esc(title)} 자주 묻는 질문</h2></div><div class="faq-list">{faq_html}</div></div></section>

    <section class="section"><div class="section-panel"><div class="section-title"><p class="eyebrow">PARENT REVIEW</p><h2>{esc(local)} 학부모가 전한 영어 학습 변화</h2></div><div class="review-grid">{review_html}</div><div class="internal-links"><div class="directory-head"><h2>{esc(local)} 주변 고등영어학원 페이지</h2><p>같은 카테고리 안에서 가까운 지역 페이지로 이동할 수 있도록 정리했습니다.</p></div><div class="related-grid"><a href="../index.html"><strong>고등영어학원 전체</strong><small>카테고리 허브</small></a><a href="../../index.html"><strong>전국학원</strong><small>전체 허브</small></a>{related_html}</div></div></div></section>
  </main>
{footer_html(3)}"""
    return shared.page_shell(head, body)


def main() -> None:
    rows = shared.read_csv(COMMON / "센터정보 정리.csv")
    faq_base = shared.read_faq(COMMON / "FAQ.txt")
    review_lines = [x.strip() for x in (COMMON / "학부모 후기.txt").read_text(encoding="utf-8").splitlines() if x.strip()]
    reps = existing_or_copy_rep_images(rows)
    category_hub(rows)
    for idx, row in enumerate(rows):
        slug = slug_ko(row["근처 수업가능 동네"])
        out = SITE / "전국학원" / CATEGORY / slug / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(local_page(row, idx, reps[idx], rows, faq_base, review_lines), encoding="utf-8")
    root_hub(rows)
    print(f"generated category={CATEGORY} local_pages={len(rows)}")


if __name__ == "__main__":
    main()
