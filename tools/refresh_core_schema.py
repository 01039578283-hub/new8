from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
SITE = "https://xn--zj4b74v1taq8c.com"
ORG_ID = f"{SITE}/#organization"
WEBSITE_ID = f"{SITE}/#website"


def thing(name: str) -> dict[str, str]:
    return {"@type": "Thing", "name": name}


def common_graph() -> list[dict]:
    return [
        {
            "@type": "WebSite",
            "@id": WEBSITE_ID,
            "url": f"{SITE}/",
            "name": "코칭센터",
            "inLanguage": "ko-KR",
            "publisher": {"@id": ORG_ID},
        },
        {
            "@type": "EducationalOrganization",
            "@id": ORG_ID,
            "name": "코칭센터",
            "url": f"{SITE}/",
            "telephone": "+82-10-6839-8283",
            "logo": f"{SITE}/assets/favicon.png",
            "image": f"{SITE}/assets/generated/coaching-center-hero-v2.webp",
            "areaServed": {"@type": "Country", "name": "대한민국"},
            "contactPoint": {
                "@type": "ContactPoint",
                "telephone": "+82-10-6839-8283",
                "contactType": "학습 상담",
                "availableLanguage": "ko",
            },
            "knowsAbout": [
                "초등 학습관리",
                "중등 학습관리",
                "고등 학습관리",
                "영어 학습관리",
                "수학 학습관리",
                "국어 학습관리",
                "플래너 관리",
                "오답 재학습",
            ],
            "makesOffer": [
                {"@type": "Offer", "itemOffered": {"@id": f"{SITE}/#diagnosis-service"}},
                {"@type": "Offer", "itemOffered": {"@id": f"{SITE}/#planner-service"}},
                {"@type": "Offer", "itemOffered": {"@id": f"{SITE}/#wrong-answer-service"}},
            ],
        },
        {
            "@type": "Service",
            "@id": f"{SITE}/#diagnosis-service",
            "name": "학생별 학습 진단 상담",
            "serviceType": "학습 진단",
            "provider": {"@id": ORG_ID},
            "audience": {"@type": "EducationalAudience", "educationalRole": "student"},
        },
        {
            "@type": "Service",
            "@id": f"{SITE}/#planner-service",
            "name": "플래너 기반 학습관리",
            "serviceType": "학습관리",
            "provider": {"@id": ORG_ID},
            "audience": {"@type": "EducationalAudience", "educationalRole": "student"},
        },
        {
            "@type": "Service",
            "@id": f"{SITE}/#wrong-answer-service",
            "name": "오답 원인 분석과 재학습 관리",
            "serviceType": "오답 재학습",
            "provider": {"@id": ORG_ID},
            "audience": {"@type": "EducationalAudience", "educationalRole": "student"},
        },
    ]


def breadcrumb(url: str, name: str) -> dict:
    return {
        "@type": "BreadcrumbList",
        "@id": f"{url}#breadcrumb",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "홈", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": name, "item": url},
        ],
    }


def faq_node(url: str, entries: list[tuple[str, str]]) -> dict:
    return {
        "@type": "FAQPage",
        "@id": f"{url}#faq",
        "mainEntity": [
            {
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {"@type": "Answer", "text": answer},
            }
            for question, answer in entries
        ],
    }


HOME_DESCRIPTION = (
    "초·중·고 영어·수학·국어 학습관리 코칭을 안내합니다. 현재 수준 진단부터 "
    "플래너 실행, 오답 재학습, 학부모 피드백까지 한 흐름으로 관리합니다."
)
GUIDE_DESCRIPTION = (
    "초·중·고 학생의 학습 진단, 학년별 관리, 플래너 작성, 시험 대비, "
    "오답 재학습과 학부모 피드백 방법을 단계별로 안내합니다."
)
CONTACT_DESCRIPTION = (
    "초·중·고 영어·수학·국어 학습상담을 안내합니다. 현재 교재, 시험지, "
    "공부 습관과 목표를 바탕으로 필요한 관리 순서를 함께 정리합니다."
)


def home_graph() -> list[dict]:
    url = f"{SITE}/"
    graph = common_graph()
    graph.extend(
        [
            {
                "@type": "WebPage",
                "@id": f"{url}#webpage",
                "url": url,
                "name": "코칭센터 | 영어·수학·국어 학습관리 코칭",
                "description": HOME_DESCRIPTION,
                "inLanguage": "ko-KR",
                "isPartOf": {"@id": WEBSITE_ID},
                "publisher": {"@id": ORG_ID},
                "about": [
                    thing("초등 학습관리"),
                    thing("중등 학습관리"),
                    thing("고등 학습관리"),
                    thing("영어·수학·국어 학습코칭"),
                ],
                "hasPart": [
                    {"@type": "WebPageElement", "name": "학습관리 흐름"},
                    {"@type": "WebPageElement", "name": "학년별 관리 기준"},
                    {"@type": "WebPageElement", "name": "상담 전 체크리스트"},
                    {"@type": "WebPageElement", "name": "자주 묻는 질문"},
                ],
                "dateModified": "2026-07-24",
            },
            {
                "@type": "Service",
                "@id": f"{url}#service",
                "name": "초·중·고 영어·수학·국어 학습관리 코칭",
                "description": HOME_DESCRIPTION,
                "serviceType": "학습관리 코칭",
                "provider": {"@id": ORG_ID},
                "areaServed": {"@type": "Country", "name": "대한민국"},
                "audience": [
                    {"@type": "EducationalAudience", "educationalRole": "student"},
                    {"@type": "Audience", "audienceType": "학부모"},
                ],
                "offers": {"@type": "Offer", "url": f"{SITE}/{quote('상담문의')}/"},
            },
            faq_node(
                url,
                [
                    (
                        "상담 전에 무엇을 준비하면 좋나요?",
                        "최근 시험지, 현재 교재, 숙제 수행 정도, 자주 틀리는 단원, 평소 공부 시간을 알려주시면 진단이 더 구체적입니다.",
                    ),
                    (
                        "초등·중등·고등 모두 상담 가능한가요?",
                        "네. 학년별로 필요한 관리가 다르기 때문에 초등은 습관과 기초, 중등은 내신과 실행력, 고등은 약점 단원과 시험 전략을 중심으로 봅니다.",
                    ),
                    (
                        "오답 관리는 단순 오답노트와 다른가요?",
                        "단순히 답을 고쳐 쓰는 방식이 아니라 왜 틀렸는지 분류하고, 필요한 개념으로 돌아가 유사 문제까지 확인하는 방식입니다.",
                    ),
                ],
            ),
        ]
    )
    return graph


def guide_graph() -> list[dict]:
    path = quote("학습가이드")
    url = f"{SITE}/{path}/"
    graph = common_graph()
    graph.extend(
        [
            breadcrumb(url, "학습가이드"),
            {
                "@type": "WebPage",
                "@id": f"{url}#webpage",
                "url": url,
                "name": "초중고 학습관리 가이드 | 진단·플래너·오답관리 | 코칭센터",
                "description": GUIDE_DESCRIPTION,
                "inLanguage": "ko-KR",
                "isPartOf": {"@id": WEBSITE_ID},
                "publisher": {"@id": ORG_ID},
                "breadcrumb": {"@id": f"{url}#breadcrumb"},
                "about": [
                    thing("학습 진단"),
                    thing("학년별 학습관리"),
                    thing("플래너"),
                    thing("시험 대비"),
                    thing("오답 재학습"),
                ],
                "dateModified": "2026-07-24",
            },
            {
                "@type": "Article",
                "@id": f"{url}#article",
                "headline": "초·중·고 학습관리 가이드: 진단부터 오답 재학습까지",
                "description": GUIDE_DESCRIPTION,
                "inLanguage": "ko-KR",
                "mainEntityOfPage": {"@id": f"{url}#webpage"},
                "author": {"@id": ORG_ID},
                "publisher": {"@id": ORG_ID},
                "dateModified": "2026-07-24",
                "articleSection": [
                    "초기 상담",
                    "학습 진단",
                    "학년별 관리",
                    "플래너",
                    "오답 재학습",
                    "시험 대비",
                    "학부모 피드백",
                ],
                "about": [thing("초중고 학습관리"), thing("플래너"), thing("오답관리")],
            },
            faq_node(
                url,
                [
                    (
                        "학습 진단은 한 번만 하면 되나요?",
                        "처음에는 출발점을 찾고, 이후에는 수업·숙제·오답 기록을 보며 계속 조정합니다. 학생의 수행 흐름이 바뀌면 계획도 함께 바뀌어야 합니다.",
                    ),
                    (
                        "플래너는 왜 필요한가요?",
                        "무엇을 얼마나 했는지, 왜 못 끝냈는지, 다음에는 어디를 줄이거나 늘려야 하는지 확인하기 위한 실행 기록입니다.",
                    ),
                    (
                        "오답 관리는 어떻게 이어지나요?",
                        "틀린 문제를 다시 푸는 데서 멈추지 않고 개념 부족, 계산 실수, 조건 해석, 시간 부족처럼 원인을 나눠 재학습합니다.",
                    ),
                ],
            ),
        ]
    )
    return graph


def contact_graph() -> list[dict]:
    path = quote("상담문의")
    url = f"{SITE}/{path}/"
    graph = common_graph()
    graph.extend(
        [
            breadcrumb(url, "상담문의"),
            {
                "@type": "ContactPage",
                "@id": f"{url}#webpage",
                "url": url,
                "name": "초중고 학습상담 문의 | 영어·수학·국어 | 코칭센터",
                "description": CONTACT_DESCRIPTION,
                "inLanguage": "ko-KR",
                "isPartOf": {"@id": WEBSITE_ID},
                "publisher": {"@id": ORG_ID},
                "breadcrumb": {"@id": f"{url}#breadcrumb"},
                "mainEntity": {"@id": f"{url}#service"},
                "dateModified": "2026-07-24",
            },
            {
                "@type": "Service",
                "@id": f"{url}#service",
                "name": "초·중·고 영어·수학·국어 학습상담",
                "description": CONTACT_DESCRIPTION,
                "serviceType": "학습상담",
                "provider": {"@id": ORG_ID},
                "areaServed": {"@type": "Country", "name": "대한민국"},
                "audience": [
                    {"@type": "EducationalAudience", "educationalRole": "student"},
                    {"@type": "Audience", "audienceType": "학부모"},
                ],
                "offers": {"@type": "Offer", "url": url},
            },
            faq_node(
                url,
                [
                    (
                        "상담문의할 때 어떤 내용을 알려주면 좋나요?",
                        "학년, 현재 교재, 최근 시험지, 숙제 수행 정도, 어려워하는 과목과 목표를 알려주시면 상담이 더 구체적입니다.",
                    ),
                    (
                        "시험지가 없어도 상담이 가능한가요?",
                        "가능합니다. 다만 시험지나 오답 기록이 있으면 반복되는 실수와 취약 단원을 더 빠르게 확인할 수 있습니다.",
                    ),
                    (
                        "상담 후 바로 등록해야 하나요?",
                        "아닙니다. 학생에게 필요한 관리 방향을 먼저 확인하고, 학부모님이 충분히 비교한 뒤 결정하셔도 됩니다.",
                    ),
                ],
            ),
        ]
    )
    return graph


def replace_schema(path: Path, graph: list[dict]) -> None:
    html = path.read_text(encoding="utf-8")
    replacement = (
        '<script type="application/ld+json">'
        + json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":"))
        + "</script>"
    )
    updated, count = re.subn(
        r'<script type="application/ld\+json">.*?</script>',
        replacement,
        html,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise RuntimeError(f"JSON-LD block not found in {path}")
    path.write_text(updated, encoding="utf-8", newline="")


def main() -> None:
    replace_schema(ROOT / "index.html", home_graph())
    replace_schema(ROOT / "학습가이드" / "index.html", guide_graph())
    replace_schema(ROOT / "상담문의" / "index.html", contact_graph())
    print("Core JSON-LD refreshed.")


if __name__ == "__main__":
    main()
