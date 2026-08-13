from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class KeywordPlan:
    """Three search-intent layers used in separate page elements.

    The representative phrase belongs in title/H1, the secondary phrase in the
    description, and the detailed phrase in one answer-oriented heading. Keeping
    those jobs separate avoids repeating every phrase in every element.
    """

    representative: str
    secondary: str
    detailed: str
    issue: str
    subject: str


ISSUE_QUERIES = {
    "개념 연결": "개념 연결 진단",
    "조건 해석": "문제 조건 해석 연습",
    "계산 정확도": "계산 실수 점검",
    "함수·그래프": "함수와 그래프 연결",
    "서술형 풀이": "서술형 풀이 과정 점검",
    "시간 배분": "수학 시험 시간 배분",
    "오답 재풀이": "수학 오답 재풀이",
    "어휘 누적": "영어 어휘 누적 복습",
    "문장 구조": "긴 문장 구조 분석",
    "독해 근거": "영어 독해 근거 찾기",
    "학교 본문": "교과서 본문 변형 대비",
    "서술형 교정": "영어 서술형 교정",
    "읽기 속도": "영어 시험 시간 관리",
    "오답 분류": "영어 오답 유형 분석",
    "연산 원리": "연산 원리 설명",
    "문장제 해석": "수학 문장제 조건 찾기",
    "분수·소수 개념": "분수와 소수 개념 이해",
    "도형·측정": "도형과 측정 단원 점검",
    "단원 복습": "수학 단원 복습",
    "소리·철자 연결": "영어 소리와 철자 연결",
    "기초 어휘": "영어 기초 어휘 복습",
    "기본 문장": "영어 기본 문장 연습",
    "듣기·말하기": "영어 듣기와 말하기",
    "읽기 이해": "영어 읽기 이해",
    "쓰기·철자": "영어 쓰기와 철자 점검",
    "짧은 반복 복습": "영어 반복 복습 습관",
}


SECONDARY_PHRASES = {
    "수학": (
        "{grade} 수학 내신 대비",
        "{grade} 수학 학습 진단",
        "{grade} 수학 시험 준비",
    ),
    "영어": (
        "{grade} 영어 내신 대비",
        "{grade} 영어 학습 진단",
        "{grade} 영어 시험 준비",
    ),
}


ELEMENTARY_SECONDARY_PHRASES = {
    "수학": (
        "{grade} 수학 단원 학습",
        "{grade} 수학 기초 진단",
        "{grade} 수학 학교 진도",
    ),
    "영어": (
        "{grade} 영어 단원 학습",
        "{grade} 영어 기초 진단",
        "{grade} 영어 학교 진도",
    ),
}


DETAIL_HEADING_ENDINGS = (
    "최근 시험지와 학생 설명을 함께 보는 순서",
    "정답보다 막힌 단계를 먼저 나누는 기준",
    "상담 전에 확인할 자료와 첫 질문",
    "첫 주 보완 목표를 작게 정하는 방법",
    "다시 해낸 결과까지 비교하는 진단법",
    "학교 자료와 오답 기록을 대조하는 방법",
    "현재 실력과 다음 행동을 잇는 점검 순서",
    "학생이 혼자 설명한 범위를 확인하는 법",
    "시험 범위와 복습 날짜를 함께 잡는 방법",
)


ELEMENTARY_DETAIL_HEADING_ENDINGS = (
    "최근 학습지와 학생 설명을 함께 보는 순서",
    "정답보다 혼자 해낸 단계를 먼저 나누는 기준",
    "상담 전에 확인할 학습 자료와 첫 질문",
    "첫 주 복습 목표를 작게 정하는 방법",
    "다시 설명하고 적용한 결과를 비교하는 진단법",
    "학교 단원과 오답 기록을 대조하는 방법",
    "현재 학습 상태와 다음 행동을 잇는 점검 순서",
    "학생이 혼자 설명한 범위를 확인하는 법",
    "교과서 단원과 복습 날짜를 함께 잡는 방법",
)


MIDDLE2_ENGLISH_DIAGNOSTIC_HEADINGS = (
    "정답을 고른 이유와 근거 문장을 나란히 확인하는 진단",
    "외운 본문과 변형 문장 적용 사이의 간격을 찾는 진단",
    "어휘 뜻·문장 뼈대·선택지 근거를 차례로 나누는 진단",
    "최근 시험지의 표시 흔적으로 읽기 과정을 되짚는 진단",
    "틀린 답보다 처음 해석이 어긋난 문장을 찾는 진단",
    "학생 설명과 실제 답안 기록을 같은 기준으로 비교하는 진단",
    "학교 본문 암기와 낯선 지문 독해를 따로 확인하는 진단",
    "문장을 읽은 시간과 답의 근거를 찾은 시간을 나누는 진단",
    "서술형 답안의 내용·구조·철자를 차례로 확인하는 진단",
    "단어를 아는 수준과 문맥에서 뜻을 고르는 수준을 나누는 진단",
    "교과서·프린트·시험지에서 반복된 막힘을 찾는 진단",
    "힌트를 받은 풀이와 혼자 다시 해낸 결과를 구분하는 진단",
)


MIDDLE2_ENGLISH_PRACTICE_HEADINGS = (
    "한 문장을 구조 표시·해석·근거 확인으로 다시 읽는 복습",
    "학교 본문의 핵심 문장을 변형 문장으로 넓히는 복습",
    "오답 선택지가 틀린 이유까지 한 줄로 남기는 복습",
    "어휘를 예문과 본문 위치에 묶어 다시 만나는 복습",
    "긴 문장을 절 단위로 끊고 수식 관계를 되짚는 복습",
    "서술형 문장을 쓴 뒤 구조와 철자를 따로 고치는 복습",
    "읽기 시간을 재되 근거 표시의 정확도를 함께 보는 복습",
    "시험 범위표에 본문·문법·서술형 날짜를 나누는 복습",
    "틀린 원인을 어휘·구조·근거 세 칸으로 분류하는 복습",
    "힌트 없이 다시 읽은 날짜와 성공 여부를 남기는 복습",
    "학교 프린트의 표현을 교과서 문장과 대조하는 복습",
    "새 지문 학습과 이전 오답 재확인을 번갈아 배치하는 복습",
)


MIDDLE2_ENGLISH_PARENT_HEADINGS = (
    "진도량보다 학생이 다시 설명한 문장을 확인하는 피드백",
    "숙제 완료와 독립적으로 고친 오답을 구분하는 피드백",
    "본문 암기 여부와 변형 문장 적용을 따로 묻는 피드백",
    "단어 시험 점수와 지문 속 의미 판단을 비교하는 피드백",
    "정답률·읽기 시간·근거 정확도를 함께 보는 피드백",
    "서술형 교정 전후 문장을 나란히 받는 피드백",
    "학교 일정에 맞춘 다음 점검 날짜가 보이는 피드백",
    "도움을 받은 단계와 혼자 해낸 단계를 나누는 피드백",
    "이번 주 보완 행동을 한 가지로 좁혀 주는 피드백",
    "오답 유형별 재확인 결과가 이어지는 피드백",
    "막힌 문장과 교정 행동을 짝지어 보여 주는 피드백",
    "다음 시험까지 유지할 복습 기준을 알려 주는 피드백",
)


FAQ_START_BANKS = {
    "수학": (
        "최근 시험지와 풀이 노트를 같은 자리에 놓고 시작합니다.",
        "현재 교재보다 최근 시험에서 멈춘 풀이 단계를 먼저 고릅니다.",
        "학교 범위표, 풀이 흔적, 오답 기록의 겹치는 지점부터 봅니다.",
        "학생이 가장 오래 멈춘 문항과 식을 세우지 못한 조건부터 확인합니다.",
        "맞힌 대표 문항 한 개와 조건이 바뀐 문항 한 개를 비교해 봅니다.",
        "틀린 문항을 개념·조건·계산으로 나누어 표시하는 데서 출발합니다.",
        "최근 서술형 답안과 풀이를 고치기 전 기록을 함께 준비하면 좋습니다.",
        "시험 범위표에 단원별 복습 날짜를 적은 뒤 우선순위를 정합니다.",
        "정답만 고친 오답과 힌트 없이 다시 푼 오답을 구분합니다.",
        "계산 실수 기록과 식을 세운 근거가 남은 문항을 대조합니다.",
        "문항별 풀이 시간과 건너뛴 지점이 남은 자료부터 봅니다.",
        "학생이 풀이 이유를 직접 설명할 수 있는 문항을 기준점으로 잡습니다.",
    ),
    "영어": (
        "최근 시험지와 학교 범위표를 같은 자리에 놓고 시작합니다.",
        "현재 교재보다 최근 시험에서 멈춘 문장을 먼저 고릅니다.",
        "교과서 본문, 학교 프린트, 오답 기록의 겹치는 지점부터 봅니다.",
        "학생이 가장 오래 읽은 지문과 근거를 놓친 문항부터 확인합니다.",
        "암기한 본문 한 문장과 처음 보는 문장 한 개를 비교해 봅니다.",
        "틀린 문항을 어휘·구조·근거로 나누어 표시하는 데서 출발합니다.",
        "최근 서술형 답안과 교정 전 문장을 함께 준비하면 좋습니다.",
        "시험 범위표에 자료별 복습 날짜를 적은 뒤 우선순위를 정합니다.",
        "정답만 고친 오답과 힌트 없이 다시 푼 오답을 구분합니다.",
        "단어 시험 기록과 실제 지문에서 뜻을 놓친 문장을 대조합니다.",
        "문장을 읽은 시간과 근거를 찾은 위치가 남은 자료부터 봅니다.",
        "학생이 직접 설명할 수 있는 문장 한 개를 기준점으로 잡습니다.",
    ),
}


ELEMENTARY_FAQ_START_BANKS = {
    "수학": (
        "최근 단원평가와 풀이 노트를 같은 자리에 놓고 시작합니다.",
        "현재 교재보다 가장 오래 멈춘 풀이 단계를 먼저 고릅니다.",
        "교과서 단원, 학습지, 오답 기록의 겹치는 지점부터 봅니다.",
        "학생이 식의 이유를 직접 설명할 수 있는 대표 문항을 준비합니다.",
        "맞힌 문항 한 개와 조건이 바뀐 문항 한 개를 비교해 봅니다.",
        "틀린 문항을 개념·조건·계산으로 나누어 표시합니다.",
        "최근 단원평가와 고치기 전 풀이를 함께 준비하면 좋습니다.",
        "학교 단원 안내에 복습 날짜를 적은 뒤 우선순위를 정합니다.",
        "답만 고친 오답과 힌트 없이 다시 푼 오답을 구분합니다.",
        "계산 실수 기록과 식의 이유가 남은 문항을 대조합니다.",
        "풀이 시간과 멈춘 단계가 남은 학습지부터 봅니다.",
        "학생이 계산 이유를 말할 수 있는 문항을 기준점으로 잡습니다.",
    ),
    "영어": (
        "최근 학교 학습지와 사용 중인 교재를 같은 자리에 놓고 시작합니다.",
        "현재 교재보다 혼자 읽기 어려운 낱말과 문장을 먼저 고릅니다.",
        "학교 단원, 낱말 카드, 복습 기록의 겹치는 지점부터 봅니다.",
        "학생이 소리 내어 읽고 뜻을 말할 수 있는 문장부터 확인합니다.",
        "익힌 낱말 한 개와 그 낱말이 들어간 문장 한 개를 비교해 봅니다.",
        "어려운 항목을 소리·철자·뜻·문장으로 나누어 표시합니다.",
        "최근 듣고 쓴 낱말과 고치기 전 문장을 함께 준비하면 좋습니다.",
        "학교 단원 안내에 듣기·읽기·쓰기 복습 날짜를 나누어 적습니다.",
        "따라 읽은 문장과 혼자 읽은 문장을 구분해 기록합니다.",
        "낱말 복습 기록과 문장에서 뜻을 놓친 표현을 대조합니다.",
        "문장을 읽은 날짜와 혼자 말한 표현이 남은 자료부터 봅니다.",
        "학생이 직접 읽고 설명할 수 있는 짧은 문장을 기준점으로 잡습니다.",
    ),
}


def _choice(key: str, slot: str, values: tuple[str, ...]) -> str:
    digest = hashlib.sha256(f"{key}|{slot}".encode("utf-8")).hexdigest()
    return values[int(digest[:12], 16) % len(values)]


def make_plan(
    *,
    category: str,
    grade: str,
    subject: str,
    local: str,
    primary_label: str,
    key: str,
    school_level: str = "",
) -> KeywordPlan:
    issue = ISSUE_QUERIES.get(primary_label, f"{subject} 학습 진단")
    secondary_banks = (
        ELEMENTARY_SECONDARY_PHRASES
        if school_level == "초등"
        else SECONDARY_PHRASES
    )
    secondary_template = _choice(
        key,
        "keyword-secondary",
        secondary_banks[subject],
    )
    secondary = secondary_template.format(grade=grade)
    detail_issue = issue.removeprefix(f"{subject} ")
    return KeywordPlan(
        representative=category,
        secondary=secondary,
        detailed=f"{local} {grade} {subject} {detail_issue}",
        issue=issue,
        subject=subject,
    )


def meta_candidates(
    plan: KeywordPlan,
    *,
    local: str,
    primary_label: str,
    secondary_label: str,
    key: str,
    school_level: str = "",
) -> tuple[str, ...]:
    if school_level == "초등":
        options = (
            f"{local} {plan.representative} 선택 기준입니다. {plan.secondary}에 필요한 "
            f"{primary_label}·{secondary_label} 진단, 학교 학습지와 오답 기록, 상담 준비 항목을 정리했습니다.",
            f"{local} {plan.representative} 상담 전에 {plan.secondary} 기준과 "
            f"{primary_label}·{secondary_label} 복습 순서, 교과서 단원과 센터 정보를 확인해 보세요.",
            f"{local} {plan.representative} 안내입니다. 최근 학습 자료를 바탕으로 "
            f"{primary_label}·{secondary_label} 항목을 진단하고 {plan.secondary}와 상담 체크리스트를 살펴봅니다.",
        )
    else:
        options = (
        f"{local} {plan.representative} 선택 기준입니다. {plan.secondary}에 필요한 "
        f"{primary_label}·{secondary_label} 진단, 학교 자료와 오답 기록, 상담 준비 항목을 정리했습니다.",
        f"{local} {plan.representative} 상담 전에 {plan.secondary} 기준과 "
        f"{primary_label}·{secondary_label} 보완 순서, 학교 시험 자료와 센터 정보를 확인해 보세요.",
        f"{local} {plan.representative} 안내입니다. 최근 시험지를 바탕으로 "
        f"{primary_label}·{secondary_label} 항목을 진단하고 {plan.secondary}와 상담 체크리스트를 살펴봅니다.",
        )
    first = _choice(key, "keyword-meta", options)
    return (first,) + tuple(item for item in options if item != first)


def apply_heading_plan(
    headings: tuple[str, ...],
    plan: KeywordPlan,
    *,
    category: str,
    primary_label: str,
    secondary_label: str,
    tertiary_label: str,
    key: str,
    school_level: str = "",
) -> tuple[str, ...]:
    result = list(headings)
    heading_endings = (
        ELEMENTARY_DETAIL_HEADING_ENDINGS
        if school_level == "초등"
        else DETAIL_HEADING_ENDINGS
    )
    ending = _choice(key, "keyword-detail-heading", heading_endings)
    result[0] = f"{plan.detailed}: {ending}"

    if category == "중2영어학원":
        diagnostic = _choice(
            key,
            "middle2-english-diagnostic-heading",
            MIDDLE2_ENGLISH_DIAGNOSTIC_HEADINGS,
        )
        practice = _choice(
            key,
            "middle2-english-practice-heading",
            MIDDLE2_ENGLISH_PRACTICE_HEADINGS,
        )
        parent = _choice(
            key,
            "middle2-english-parent-heading",
            MIDDLE2_ENGLISH_PARENT_HEADINGS,
        )
        result[1] = f"{primary_label} 신호를 읽는 법: {diagnostic}"
        result[2] = f"{secondary_label}에서 {tertiary_label}까지: {practice}"
        result[4] = f"{parent}: 다음 확인일을 정하는 기준"

    return tuple(result)


def answer_faq(
    plan: KeywordPlan,
    *,
    local: str,
    grade: str,
    subject: str,
    primary_evidence: str,
    secondary_label: str,
    tertiary_label: str,
    key: str,
    school_level: str = "",
) -> tuple[str, str]:
    question = (
        f"{local} {grade} {subject} 상담에서 {plan.issue}에는 어떤 자료가 필요한가요?"
    )
    opening_banks = (
        ELEMENTARY_FAQ_START_BANKS
        if school_level == "초등"
        else FAQ_START_BANKS
    )
    opening = _choice(key, "keyword-faq-opening", opening_banks[plan.subject])
    answer = (
        f"{local}의 {grade} {subject} 자료를 준비할 때는 다음 순서를 참고하세요. "
        f"{opening} 확인 항목은 {primary_evidence}, {secondary_label} 기록, "
        f"{tertiary_label} 재확인 결과입니다. 세 자료를 비교한 뒤 첫 주에 바꿀 행동 "
        "한 가지와 다시 점검할 날짜를 정합니다."
    )
    return question, answer


def validate_plan(plan: KeywordPlan, *, local: str, category: str) -> None:
    if plan.representative != category:
        raise ValueError("representative keyword must match the category")
    if not plan.detailed.startswith(f"{local} "):
        raise ValueError("detailed keyword must start with the local intent")
    values = (
        plan.representative,
        plan.secondary,
        plan.detailed,
        plan.issue,
        plan.subject,
    )
    if any(not value.strip() for value in values):
        raise ValueError("keyword plan contains a blank phrase")
