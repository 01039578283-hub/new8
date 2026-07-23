from __future__ import annotations

import csv
import html
import json
import random
import re
import shutil
from pathlib import Path


SITE = Path(__file__).resolve().parents[1]
BASE = SITE.parent
COMMON = BASE / "참고자료" / "공통자료"

SITE_NAME = "코칭센터"
CATEGORY = "고등수학학원"
PHONE_DISPLAY = "010-6839-8283"
PHONE_LINK = "01068398283"


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def slug_ko(name: str) -> str:
    value = re.sub(r"\s+", "", name.strip())
    value = re.sub(r'[\\/:*?"<>|#%&+]', "", value)
    return value


def split_items(value: str) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in re.split(r"[,/·\n]+", value) if x.strip()]


def read_faq(path: Path) -> list[tuple[str, str]]:
    lines = [x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    pairs: list[tuple[str, str]] = []
    q = ""
    for line in lines:
        if line.startswith("질문:"):
            q = line.replace("질문:", "", 1).strip()
        elif line.startswith("답변:") and q:
            pairs.append((q, line.replace("답변:", "", 1).strip()))
            q = ""
    return pairs


def json_script(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def rel_prefix(depth: int) -> str:
    return "../" * depth


def nav_html(depth: int, active: str = "전국학원") -> str:
    p = rel_prefix(depth)
    links = [
        ("홈", f"{p}index.html"),
        ("학습가이드", f"{p}학습가이드/index.html"),
        ("상담문의", f"{p}상담문의/index.html"),
        ("전국학원", f"{p}전국학원/index.html"),
    ]
    items = "\n".join(
        f'        <a{" class=\"active\"" if name == active else ""} href="{href}">{name}</a>'
        for name, href in links
    )
    return f"""  <header class="nav-wrap">
    <nav class="nav" aria-label="주요 메뉴">
      <a class="brand" href="{p}index.html"><span class="brand-mark">C</span><span>{SITE_NAME}</span></a>
      <div class="nav-links">
{items}
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
  <script type="application/ld+json">{json_script(ld)}</script>
</head>"""


def page_shell(
    head: str,
    body: str,
    body_class: str = "core-page academy-page nationwide-page nationwide-detail-page",
) -> str:
    return f"""{head}
<body class="{body_class}">
<div class="site-shell">
{body}
</div>
</body>
</html>
"""


def find_map(row: dict[str, str]) -> str:
    maps = SITE / "assets" / "maps"
    raw = row.get("동 영어", "").strip()
    candidates = [
        raw,
        raw.replace(" ", "-"),
        raw.replace(" ", ""),
        raw.replace("_", "-"),
    ]
    for base in candidates:
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            p = maps / f"{base}{ext}"
            if p.exists():
                return f"assets/maps/{p.name}"
    return "assets/centers/common/local6839.webp"


def choose_rep_images(rows: list[dict[str, str]]) -> list[str]:
    src_dir = COMMON / "대표이미지"
    dst_dir = SITE / "assets" / "representative"
    dst_dir.mkdir(parents=True, exist_ok=True)

    images = [p for p in src_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}]
    images.sort(key=lambda p: p.name)
    rng = random.Random(6839)
    rng.shuffle(images)
    chosen = [images[i % len(images)] for i in range(len(rows))]
    result: list[str] = []
    for i, src in enumerate(chosen, 1):
        ext = src.suffix.lower()
        dst = dst_dir / f"rep-{i:03d}{ext}"
        if not dst.exists() or dst.stat().st_size != src.stat().st_size:
            shutil.copy2(src, dst)
        result.append(f"assets/representative/{dst.name}")
    return result


def make_faqs(local: str, district: str, title: str, base_faq: list[tuple[str, str]], idx: int) -> list[tuple[str, str]]:
    seed_answer = base_faq[idx % len(base_faq)][1] if base_faq else "학생의 현재 학습 상태와 목표를 확인한 뒤 안내합니다."
    return [
        (
            f"{title} 상담은 어떤 순서로 진행되나요?",
            f"먼저 최근 시험지와 현재 교재를 확인하고, {local} 학생의 고등수학 단원별 이해도와 오답 패턴을 나누어 봅니다. 이후 내신 대비, 수능형 문제 접근, 플래너 실행까지 어떤 순서로 관리할지 안내합니다.",
        ),
        (
            f"{local} 고등수학학원에서는 내신 대비를 어떻게 보나요?",
            f"{district} 학교 진도와 시험 범위를 기준으로 개념 확인, 유형 반복, 서술형 풀이, 시간 관리 순서를 잡습니다. 단순히 문제 수를 늘리기보다 학생이 자주 막히는 단원을 먼저 정리합니다.",
        ),
        (
            "고등학생이 수학을 늦게 시작해도 상담이 가능한가요?",
            f"가능합니다. {seed_answer} 다만 고등수학은 단원 간 연결이 강하기 때문에 현재 단원만 보지 않고 이전 개념 결손까지 함께 확인하는 편이 좋습니다.",
        ),
        (
            f"{title} 수업 전 준비하면 좋은 자료가 있나요?",
            "최근 시험지, 학교 프린트, 현재 사용하는 문제집, 오답노트나 풀이 흔적이 있으면 좋습니다. 자료가 부족해도 상담을 통해 현재 수준과 필요한 관리 방향을 먼저 정리할 수 있습니다.",
        ),
        (
            "플래너와 오답 관리는 고등수학에도 필요한가요?",
            f"고등수학은 개념을 아는 것과 시험에서 맞히는 것이 다를 수 있습니다. {local} 학생에게 필요한 문제량, 복습 주기, 다시 풀어야 할 오답을 분리해 관리하면 반복 실수를 줄이는 데 도움이 됩니다.",
        ),
    ]


def make_reviews(local: str, title: str, review_lines: list[str], idx: int) -> list[dict[str, object]]:
    rng = random.Random(1000 + idx)
    pool = review_lines[:]
    rng.shuffle(pool)
    selected = pool[:6] if len(pool) >= 6 else pool
    reviews = []
    for i, text in enumerate(selected):
        if i == 0:
            body = f"{title} 상담을 통해 아이가 고등수학에서 어디서 막히는지 조금 더 선명하게 알 수 있었습니다."
        elif i == 1:
            body = f"{local}에서 고등수학 관리를 알아보던 중 플래너와 오답 재학습까지 함께 설명받아 도움이 되었습니다."
        else:
            body = f"{text} 고등수학 학습관리 과정에서도 아이에게 필요한 부분을 차분히 짚어주셨습니다."
        reviews.append({"body": body, "rating": 4 if i == 5 else 5})
    return reviews


REVIEW_TITLE_BANK = [
    "풀이 과정을 다시 보게 됐어요",
    "오답을 그냥 넘기지 않게 됐어요",
    "시험 준비 흐름이 차분해졌어요",
    "개념을 설명하는 습관이 생겼어요",
    "학습 계획을 지키기 쉬워졌어요",
    "부족한 단원이 분명해졌어요",
]


def review_card_title(idx: int) -> str:
    return REVIEW_TITLE_BANK[idx % len(REVIEW_TITLE_BANK)]


def school_names(row: dict[str, str]) -> list[str]:
    names: list[str] = []
    for key in ("타깃학교\n(고)", "타깃학교\n(중)", "타깃학교\n(초)"):
        names.extend(split_items(row.get(key, "")))
    seen = []
    for name in names:
        if name not in seen:
            seen.append(name)
    return seen


def local_page(row: dict[str, str], idx: int, rep_image: str, all_rows: list[dict[str, str]], faq_base, review_lines) -> str:
    local = row["근처 수업가능 동네"].strip()
    slug = slug_ko(local)
    region = row.get("지역", "").strip()
    district = row.get("시or구", "").strip()
    center = row.get("센터명", "").strip() or f"{local} 학습관리"
    address = row.get("센터 주소", "").strip()
    title = f"{local} 고등수학학원"
    description = f"{region} {district} {local} 고등학생을 위한 고등수학학원 안내입니다. 학교 진도, 내신 대비, 오답 재학습, 플래너 실행 기준을 상담 전 확인할 수 있습니다."
    canonical = f"/전국학원/{CATEGORY}/{slug}/"
    org_id = f"{canonical}#organization"
    webpage_id = f"{canonical}#webpage"
    article_id = f"{canonical}#article"
    service_id = f"{canonical}#service"
    breadcrumb_id = f"{canonical}#breadcrumb"
    faq_id = f"{canonical}#faq"
    rep_root = "/" + rep_image.replace("\\", "/")
    center_img = "assets/centers/common/seoul6839.webp" if region == "서울" else "assets/centers/common/local6839.webp"
    map_img = find_map(row)
    schools = school_names(row)
    high_schools = split_items(row.get("타깃학교\n(고)", ""))
    schools_text = ", ".join(schools[:12]) if schools else "상담 시 현재 학교와 시험 범위를 기준으로 확인합니다."
    high_text = ", ".join(high_schools) if high_schools else "상담 시 고등학교 진도와 시험 범위를 확인합니다."
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
        {"@type": "Thing", "name": "고등수학학원"},
        {"@type": "Thing", "name": "고등수학 내신 대비"},
        {"@type": "Thing", "name": "수학 오답 재학습"},
        {"@type": "Thing", "name": "플래너 관리"},
    ]
    mentions = [
        {"@type": "Place", "name": region},
        {"@type": "Place", "name": district},
        {"@type": "EducationalOrganization", "name": center},
    ] + [{"@type": "School", "name": s} for s in schools]
    has_part = [
        "핵심 요약",
        "답변형 고등수학 안내",
        "지역·학년·추천학생",
        "수업 가능 학교",
        "센터 기준 정보",
        "상담 전 체크리스트",
        "FAQ",
        "학부모 후기",
        "내부링크",
    ]
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
                "alternateName": [SITE_NAME, center, f"{local} 고등수학 학습관리"],
                "url": canonical,
                "telephone": PHONE_DISPLAY,
                "openingHours": "Mo-Sa 12:00-24:00",
                "openingHoursSpecification": [{
                    "@type": "OpeningHoursSpecification",
                    "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
                    "opens": "12:00",
                    "closes": "24:00",
                }],
                "areaServed": {"@type": "Place", "name": local},
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": address,
                    "addressRegion": region,
                    "addressLocality": district,
                    "addressCountry": "KR",
                },
                "knowsAbout": ["고등수학", "수학 내신 대비", "오답 재학습", "플래너 관리", "고등학생 학습 상담"],
                "makesOffer": [
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{local} 고등수학 진단 상담", "serviceType": "TutoringService"}},
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{local} 고등수학 내신 대비", "serviceType": "TutoringService"}},
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{local} 수학 오답 재학습 관리", "serviceType": "TutoringService"}},
                ],
                "aggregateRating": {"@type": "AggregateRating", "ratingValue": "4.8", "bestRating": "5", "ratingCount": "6", "reviewCount": "6"},
                "review": [
                    {"@type": "Review", "author": {"@type": "Person", "name": "학부모"}, "reviewBody": r["body"], "reviewRating": {"@type": "Rating", "ratingValue": str(r["rating"]), "bestRating": "5"}}
                    for r in reviews
                ],
            },
            {
                "@type": "Article",
                "@id": article_id,
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
                "description": f"{local} 고등학생의 수학 개념, 유형 적용, 내신 시험범위, 오답 재학습을 함께 관리합니다.",
                "provider": {"@id": org_id},
                "areaServed": {"@type": "Place", "name": local},
                "audience": {"@type": "EducationalAudience", "educationalRole": "student"},
                "about": about,
                "mentions": mentions,
                "makesOffer": [
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{local} 고등수학 개념 진단"}},
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{local} 수학 내신 대비 플래너"}},
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{local} 수학 오답 원인 분석"}},
                ],
            },
            {
                "@type": "FAQPage",
                "@id": faq_id,
                "mainEntity": [
                    {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                    for q, a in faqs
                ],
            },
            {
                "@type": "ItemList",
                "@id": f"{canonical}#target-schools",
                "name": f"{title} 수업 가능 학교 확인 항목",
                "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": s} for i, s in enumerate(schools)],
            },
            {
                "@type": "ItemList",
                "@id": f"{canonical}#related",
                "name": f"{local} 고등수학학원 관련 내부링크",
                "itemListElement": [
                    {"@type": "ListItem", "position": i + 1, "name": name, "url": url}
                    for i, (name, url, _) in enumerate(related)
                ],
            },
        ],
    }

    rep_rel = "../../../" + rep_image
    center_rel = "../../../" + center_img
    map_rel = "../../../" + map_img
    head = head_html(f"{title} | {SITE_NAME}", description, 3, canonical, "article", rep_root, ld)

    school_cards = ""
    if schools:
        high_card = f"<article class=\"school-card\"><span>HIGH SCHOOL</span><h3>고등 수학 상담 참고 학교</h3><p>{esc(high_text)}</p></article>"
        all_card = f"<article class=\"school-card\"><span>LOCAL SCHOOL</span><h3>지역 학교 흐름 확인</h3><p>{esc(schools_text)}</p></article>"
        school_cards = high_card + all_card
    else:
        school_cards = '<article class="school-card"><span>LOCAL SCHOOL</span><h3>학교별 범위 확인</h3><p>상담 시 현재 학교, 시험 범위, 수행평가 일정을 기준으로 고등수학 관리 방향을 정리합니다.</p></article>'

    related_html = "\n".join(
        f'<a href="{esc(url)}"><strong>{esc(name)} 고등수학학원</strong><small>{esc(area)} 지역 페이지</small></a>'
        for name, url, area in related
    )
    faq_html = "\n".join(
        f'<details class="faq-item"{" open" if i == 0 else ""}><summary>{esc(q)}</summary><p>{esc(a)}</p></details>'
        for i, (q, a) in enumerate(faqs)
    )
    review_html = "\n".join(
        f'<article class="review-card"><span>REVIEW {i + 1:02d}</span><h3>{esc(review_card_title(i))}</h3><p class="star-line">{"★" * int(r["rating"])}{"☆" * (5 - int(r["rating"]))}</p><p>{esc(r["body"])}</p></article>'
        for i, r in enumerate(reviews)
    )
    fee_html = f'<p><a href="{esc(fee_link)}" target="_blank" rel="noopener noreferrer">교습비 안내 확인</a></p>' if fee_link else "<p>교습비는 상담 시 과정과 과목 구성에 따라 안내합니다.</p>"
    body = f"""{nav_html(3)}

  <main>
    <section class="academy-hero">
      <div class="academy-hero-main">
        <nav class="breadcrumb" aria-label="breadcrumb">
          <a href="../../../index.html">홈</a><span>›</span><a href="../../index.html">전국학원</a><span>›</span><a href="../index.html">고등수학학원</a><span>›</span><span>{esc(local)}</span>
        </nav>
        <p class="eyebrow">HIGH SCHOOL MATH COACHING</p>
        <h1>{esc(title)}</h1>
        <p>{esc(description)}</p>
        <div class="academy-badges">
          <span>{esc(region)}</span><span>{esc(district)}</span><span>고등수학</span><span>내신·오답·플래너</span>
        </div>
      </div>
      <aside class="academy-side-card">
        <div>
          <p class="eyebrow">상담 핵심</p>
          <strong>고등수학은 현재 단원보다 “막힌 이유”를 먼저 봅니다.</strong>
          <p>{esc(local)} 학생의 학교 진도, 최근 시험지, 오답 유형을 기준으로 필요한 관리 순서를 정리합니다.</p>
        </div>
        <div class="hero-actions">
          <a class="btn btn-primary" href="tel:{PHONE_DISPLAY}">전화 상담하기</a>
          <a class="btn btn-ghost" href="../../../상담문의/index.html">상담문의</a>
        </div>
      </aside>
    </section>

    <section class="local-media-section">
      <img src="{esc(rep_rel)}" alt="{esc(title + ' ' + SITE_NAME + ' 대표')}" style="display:none;">
      <figure class="local-media-card">
        <img src="{esc(center_rel)}" width="918" height="16116" loading="lazy" decoding="async" alt="{esc(title + ' 본문 ' + SITE_NAME)}">
      </figure>
      <figure class="local-map-card">
        <img src="{esc(map_rel)}" alt="{esc(title + ' 지도 ' + SITE_NAME)}">
        <figcaption>{esc(center)} 기준으로 {esc(local)} 학생의 고등수학 상담 범위를 확인합니다. 실제 방문·상담 전에는 주소와 이동 동선을 함께 확인해 주세요.</figcaption>
      </figure>
    </section>

    <section class="section">
      <div class="section-panel">
        <div class="section-title">
          <p class="eyebrow">핵심 요약</p>
          <h2>{esc(local)} 고등수학학원 선택 전 확인할 기준</h2>
          <p>{esc(local)} 고등학생에게 필요한 수학 관리는 단순 문제풀이보다 현재 단원, 이전 개념 결손, 학교 시험 범위, 오답 반복 이유를 함께 보는 것입니다.</p>
        </div>
        <div class="summary-grid">
          <article class="summary-card"><span>01</span><h3>개념 연결</h3><p>수학Ⅰ·수학Ⅱ·확률과통계·미적분처럼 단원 연결이 강한 과목은 이전 개념까지 확인해야 합니다.</p></article>
          <article class="summary-card"><span>02</span><h3>내신 범위</h3><p>{esc(district)} 학교별 시험 범위와 프린트, 부교재 유형을 상담 시 함께 확인합니다.</p></article>
          <article class="summary-card"><span>03</span><h3>오답 재학습</h3><p>틀린 문제를 다시 푸는 데서 끝내지 않고 계산, 조건 해석, 개념 누락을 분리합니다.</p></article>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-panel">
        <div class="section-title">
          <p class="eyebrow">AEO ANSWER</p>
          <h2>{esc(title)}은 어떤 학생에게 필요할까요?</h2>
        </div>
        <div class="answer-box"><h3>Q. 시험 때 아는 문제도 자주 틀린다면?</h3><p>A. 풀이 속도만 문제가 아닐 수 있습니다. {esc(local)} 고등수학 상담에서는 계산 실수, 조건 누락, 개념 적용 오류를 분리해서 확인합니다.</p></div>
        <div class="answer-box"><h3>Q. 문제집은 많이 푸는데 점수가 잘 오르지 않는다면?</h3><p>A. 문제량보다 오답을 다시 맞히는 구조가 더 중요합니다. 플래너에 복습 주기와 재풀이 기준을 남겨 같은 실수를 줄이는 방향으로 관리합니다.</p></div>
        <div class="answer-box"><h3>Q. 고등수학을 어디서부터 다시 봐야 할지 모르겠다면?</h3><p>A. 현재 학교 진도와 최근 시험 결과를 기준으로, 바로 필요한 단원과 먼저 보완해야 할 기초 개념을 나눠 정리합니다.</p></div>
      </div>
    </section>

    <section class="section">
      <div class="section-panel">
        <div class="section-title">
          <p class="eyebrow">LOCAL & STUDENT FIT</p>
          <h2>지역·학년·추천학생 기준</h2>
        </div>
        <div class="school-grid">
          <article class="school-card"><span>AREA</span><h3>{esc(region)} {esc(district)} {esc(local)}</h3><p>{esc(local)} 생활권 학생의 학교 진도와 시험 일정에 맞춰 고등수학 관리 방향을 상담합니다.</p></article>
          <article class="school-card"><span>GRADE</span><h3>고등학생 중심</h3><p>고1 공통수학부터 고2·고3 선택과목까지, 현재 단원과 목표에 따라 개념·유형·오답 관리를 나눕니다.</p></article>
          <article class="school-card"><span>RECOMMEND</span><h3>이런 학생에게 추천</h3><p>개념은 아는데 시험에서 흔들리는 학생, 오답을 반복하는 학생, 혼자 계획을 지키기 어려운 학생에게 적합합니다.</p></article>
          {school_cards}
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
          <article class="summary-card"><span>센터명</span><h3>{esc(center)}</h3><p>{esc(region)} {esc(district)} {esc(local)} 학생 상담 기준으로 안내합니다.</p></article>
          <article class="summary-card"><span>주소</span><h3>위치 안내</h3><p>{esc(address) if address else "상담 시 위치 정보를 확인해 주세요."}</p></article>
          <article class="summary-card"><span>등록 정보</span><h3>{esc(education_name) if education_name else "교육지원청 등록 정보"}</h3><p>{esc(reg_no) if reg_no else "상담 시 교육지원청 등록 정보를 확인할 수 있습니다."}</p></article>
          <article class="summary-card"><span>교습비</span><h3>수강료 안내</h3>{fee_html}</article>
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
          <article class="checklist-card"><span>1</span><h3>최근 시험지</h3><p>점수보다 어떤 단원에서 왜 틀렸는지를 확인하는 데 필요합니다.</p></article>
          <article class="checklist-card"><span>2</span><h3>현재 교재</h3><p>진도와 난이도를 확인해 바로 시작할 수 있는 위치를 잡습니다.</p></article>
          <article class="checklist-card"><span>3</span><h3>학교 진도</h3><p>{esc(local)} 학생의 학교별 시험 범위와 수행평가 일정을 함께 확인합니다.</p></article>
          <article class="checklist-card"><span>4</span><h3>학습 습관</h3><p>숙제 완료율, 복습 시간, 플래너 실행 여부를 확인해 관리 강도를 정합니다.</p></article>
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
          <h2>{esc(local)} 학부모가 전한 수학 학습 변화</h2>
        </div>
        <div class="review-grid">
          {review_html}
        </div>
        <div class="internal-links">
          <div class="directory-head">
            <h2>{esc(local)} 주변 고등수학학원 페이지</h2>
            <p>같은 카테고리 안에서 가까운 지역 페이지로 이동할 수 있도록 정리했습니다.</p>
          </div>
          <div class="related-grid">
            <a href="../index.html"><strong>고등수학학원 전체</strong><small>카테고리 허브</small></a>
            <a href="../../index.html"><strong>전국학원</strong><small>전체 허브</small></a>
            {related_html}
          </div>
        </div>
      </div>
    </section>
  </main>

{footer_html(3)}
"""
    return page_shell(head, body)


def hub_pages(rows: list[dict[str, str]]) -> None:
    rep = "/assets/generated/coaching-center-hero-v2.webp"
    ld_root = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "CollectionPage", "@id": "/전국학원/#webpage", "url": "/전국학원/", "name": "전국학원", "description": "코칭센터 전국 학원 안내 허브입니다.", "inLanguage": "ko-KR"},
            {"@type": "BreadcrumbList", "@id": "/전국학원/#breadcrumb", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "홈", "item": "/"}, {"@type": "ListItem", "position": 2, "name": "전국학원", "item": "/전국학원/"}]},
            {"@type": "ItemList", "@id": "/전국학원/#categories", "name": "전국학원 카테고리", "itemListElement": [{"@type": "ListItem", "position": 1, "name": CATEGORY, "url": f"/전국학원/{CATEGORY}/"}]},
        ],
    }
    head = head_html("전국학원 | 코칭센터", "코칭센터 전국학원 허브입니다. 고등수학학원 카테고리와 지역별 학습관리 안내 페이지로 이동할 수 있습니다.", 1, "/전국학원/", "website", rep, ld_root)
    body = f"""{nav_html(1)}
  <main>
    <section class="academy-hero">
      <div class="academy-hero-main">
        <nav class="breadcrumb" aria-label="breadcrumb"><a href="../index.html">홈</a><span>›</span><span>전국학원</span></nav>
        <p class="eyebrow">NATIONAL ACADEMY HUB</p>
        <h1>전국학원</h1>
        <p>과목과 학년 카테고리별로 지역 학습관리 페이지를 정리하는 허브입니다. 현재는 고등수학학원 페이지를 먼저 구축했습니다.</p>
      </div>
      <aside class="academy-side-card"><div><p class="eyebrow">구조 안내</p><strong>카테고리에서 지역으로 이동하는 방식</strong><p>예: 전국학원 / 고등수학학원 / 명일동</p></div></aside>
    </section>
    <section class="academy-directory">
      <div class="directory-head"><h2>학원 카테고리</h2><p>추후 영어, 영수, 초등·중등·고등 카테고리를 같은 방식으로 확장할 수 있습니다.</p></div>
      <div class="category-grid">
        <a class="category-card" href="고등수학학원/index.html"><strong>고등수학학원</strong><small>371개 지역 페이지</small></a>
      </div>
    </section>
  </main>
{footer_html(1)}"""
    out = SITE / "전국학원" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        page_shell(head, body, "core-page academy-page nationwide-page nationwide-root-page"),
        encoding="utf-8",
    )

    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(row.get("지역", "기타"), []).append(row)
    blocks = []
    for region, items in groups.items():
        links = "\n".join(
            f'<a href="{slug_ko(r["근처 수업가능 동네"])}/"><strong>{esc(r["근처 수업가능 동네"])}</strong><small>{esc(r.get("시or구", ""))} 고등수학</small></a>'
            for r in items
        )
        blocks.append(f'<div class="region-block"><div class="region-title"><h3>{esc(region)}</h3><span>{len(items)}개 지역</span></div><div class="local-button-grid">{links}</div></div>')
    ld_cat = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "CollectionPage", "@id": f"/전국학원/{CATEGORY}/#webpage", "url": f"/전국학원/{CATEGORY}/", "name": CATEGORY, "description": "고등수학학원 지역별 안내 허브입니다.", "inLanguage": "ko-KR"},
            {"@type": "BreadcrumbList", "@id": f"/전국학원/{CATEGORY}/#breadcrumb", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "홈", "item": "/"}, {"@type": "ListItem", "position": 2, "name": "전국학원", "item": "/전국학원/"}, {"@type": "ListItem", "position": 3, "name": CATEGORY, "item": f"/전국학원/{CATEGORY}/"}]},
            {"@type": "ItemList", "@id": f"/전국학원/{CATEGORY}/#itemlist", "name": "고등수학학원 지역 목록", "numberOfItems": len(rows), "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": f"{r['근처 수업가능 동네']} 고등수학학원", "url": f"/전국학원/{CATEGORY}/{slug_ko(r['근처 수업가능 동네'])}/"} for i, r in enumerate(rows)]},
        ],
    }
    head = head_html(f"{CATEGORY} | {SITE_NAME}", "전국 371개 지역의 고등수학학원 학습관리 페이지를 지역별로 정리한 허브입니다.", 2, f"/전국학원/{CATEGORY}/", "website", rep, ld_cat)
    body = f"""{nav_html(2)}
  <main>
    <section class="academy-hero">
      <div class="academy-hero-main">
        <nav class="breadcrumb" aria-label="breadcrumb"><a href="../../index.html">홈</a><span>›</span><a href="../index.html">전국학원</a><span>›</span><span>{CATEGORY}</span></nav>
        <p class="eyebrow">HIGH SCHOOL MATH DIRECTORY</p>
        <h1>{CATEGORY}</h1>
        <p>지역별 고등수학 상담 기준을 한눈에 찾을 수 있도록 정리했습니다. 각 페이지에는 지역·학년·추천학생, 학교 참고 정보, FAQ, 학부모 후기, 내부링크가 함께 구성됩니다.</p>
      </div>
      <aside class="academy-side-card"><div><p class="eyebrow">총 지역</p><strong>{len(rows)}개</strong><p>서울부터 제주까지 지역명 기준으로 고등수학학원 페이지를 생성했습니다.</p></div></aside>
    </section>
    <section class="academy-directory">
      <div class="directory-head"><h2>지역별 고등수학학원 바로가기</h2><p>광역 지역별로 나누어 보기 쉽게 정리했습니다. 원하는 동네를 선택하면 해당 지역 고등수학학원 안내로 이동합니다.</p></div>
      {"".join(blocks)}
    </section>
  </main>
{footer_html(2)}"""
    out = SITE / "전국학원" / CATEGORY / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        page_shell(
            head,
            body,
            "core-page academy-page directory-page nationwide-page nationwide-category-page",
        ),
        encoding="utf-8",
    )


def main() -> None:
    rows = read_csv(COMMON / "센터정보 정리.csv")
    faq_base = read_faq(COMMON / "FAQ.txt")
    review_lines = [x.strip() for x in (COMMON / "학부모 후기.txt").read_text(encoding="utf-8").splitlines() if x.strip()]
    reps = choose_rep_images(rows)
    hub_pages(rows)
    for idx, row in enumerate(rows):
        slug = slug_ko(row["근처 수업가능 동네"])
        out = SITE / "전국학원" / CATEGORY / slug / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(local_page(row, idx, reps[idx], rows, faq_base, review_lines), encoding="utf-8")
    print(f"generated category={CATEGORY} local_pages={len(rows)}")


if __name__ == "__main__":
    main()
