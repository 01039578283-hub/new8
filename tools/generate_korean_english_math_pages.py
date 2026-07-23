from __future__ import annotations

import csv
import hashlib
import html
import json
import random
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import quote
from zipfile import ZipFile


SITE = Path(__file__).resolve().parents[1]
COMMON = SITE.parent / "참고자료" / "공통자료"
ZIP_PATH = Path.home() / "Desktop" / "코칭센터.com 추가 원고" / "국영수학원.zip"

SITE_NAME = "코칭센터"
DOMAIN = "https://xn--zj4b74v1taq8c.com"
PARENT = "과목별학원"
CATEGORY = "국영수학원"
PHONE_DISPLAY = "010-6839-8283"
PHONE_LINK = "01068398283"
TODAY = date.today().isoformat()
PUBLISHED_DATE = "2026-07-24T00:00:00+09:00"
UPDATED_AT = f"{TODAY}T00:00:00+09:00"
ASSET_VERSION = "20260724-6"

REQUIRED_SECTIONS = {
    "페이지타이틀",
    "메타설명",
    "본문",
    "FAQ",
    "학부모후기",
    "JSON-LD 요약",
}


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def json_script(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )


def slug_ko(name: str) -> str:
    value = re.sub(r"\s+", "", name.strip())
    return re.sub(r'[\\/:*?"<>|#%&+]', "", value)


def compact_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def split_items(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[,/·\n]+", value) if item.strip()]


def unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def stable_pick(key: str, slot: str, options: list[str]) -> str:
    """Choose copy deterministically so repeated builds produce identical pages."""
    digest = hashlib.sha256(f"{key}|{slot}".encode("utf-8")).digest()
    return options[int.from_bytes(digest[:8], "big") % len(options)]


def stable_percent(key: str, slot: str) -> int:
    digest = hashlib.sha256(f"{key}|{slot}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % 100


def stable_id(prefix: str, *values: str) -> str:
    """Create an entity identifier that stays the same on every rebuild."""
    normalized = "|".join(compact_text(value) for value in values)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:18]
    return f"{DOMAIN}/#entity-{prefix}-{digest}"


def place_id_for(region: str, district: str = "", local: str = "") -> str:
    if local:
        return stable_id("locality", region, district, local)
    if district:
        return stable_id("district", region, district)
    return stable_id("region", region)


def polish_reader_terms(value: str, key: str) -> str:
    """Replace production-oriented wording with reader-facing language."""
    replacements = [
        (
            "원고에는 지정된 학교명이 제공되지 않았으므로 실제 상담에서 재학 학교와 평가 자료를 먼저 확인해야 합니다.",
            [
                "상담에서는 재학 학교와 최근 평가 자료를 먼저 확인한 뒤 과목별 준비 범위를 정해야 합니다.",
                "상담할 때는 학생의 재학 학교와 최근 시험지를 확인하고 필요한 학습 순서를 정해야 합니다.",
                "학교별 계획은 교과서와 최근 범위표를 확인한 뒤 학생의 현재 진도에 맞추어야 합니다.",
                "내신 준비는 재학 학교의 일정과 최근 평가 결과를 확인하는 단계부터 시작해야 합니다.",
            ],
        ),
        (
            "에서 제공되지 않은 학교명을 새로 만들어 쓰지 않는 대신 재학 학교 확인 후 계획을 수정하는 시점을 구체적으로 정해야 합니다.",
            [
                "에서는 재학 학교와 최근 평가 자료를 확인하고 계획을 조정할 시점을 구체적으로 정해야 합니다.",
                "에서는 학생의 교과서와 시험 범위를 먼저 살핀 뒤 과제와 복습 일정을 조정해야 합니다.",
                "에서는 재학 학교의 일정과 현재 진도를 확인해 필요한 단원부터 계획에 반영해야 합니다.",
                "에서는 최근 시험지와 수행평가 일정을 확인한 뒤 다음 학습량을 결정해야 합니다.",
            ],
        ),
        (
            "특정 학교명이 제공되지 않아 학교를 임의로 생성하지 않고 상담에서 재학 학교와 시험 자료를 확인하는 절차를 안내합니다.",
            [
                "재학 학교별 준비는 상담에서 최근 시험 범위와 학생의 학습 자료를 확인한 뒤 구체화합니다.",
                "학교별 수업 범위는 학생이 가져온 교과서와 최근 평가 자료를 살핀 뒤 결정합니다.",
                "내신 준비는 상담 시 재학 학교의 일정과 최근 시험지를 확인한 뒤 필요한 단원부터 설계합니다.",
                "학교별 계획은 학생의 현재 진도와 최근 범위표를 대조한 뒤 과제와 복습 일정으로 연결합니다.",
            ],
        ),
        (
            "자료에 제공되지 않은 학교명을 임의로 넣지 않는 안내가 정확합니다.",
            [
                "학교별 범위는 추측하지 않고 재학 학교와 최근 시험 자료를 확인해 정하는 것이 정확합니다.",
                "재학 학교의 교과서와 최근 범위표를 확인한 뒤 수업 계획을 세워야 정확합니다.",
                "학교 이름보다 학생이 가져온 시험지와 수행평가 일정을 먼저 확인하는 편이 정확합니다.",
                "상담에서는 재학 학교와 최근 평가 자료를 확인한 뒤 필요한 준비 범위를 정해야 합니다.",
            ],
        ),
        (
            "의 원자료는 고등학교 범위를 특정 학교명으로 모두 적지 않았으므로 제공되지 않은 고등학교명을 이 페이지에 임의로 추가하지 않습니다.",
            [
                "의 고등학교별 범위는 상담 때 최근 범위표와 시험 자료를 확인해 정합니다.",
                "의 고등학교 과정은 학생이 가져온 교과서와 최근 평가 자료를 살핀 뒤 수업 범위를 조정합니다.",
                "의 고등학교 수업 범위는 재학 학교의 최근 시험 일정과 학생의 현재 진도를 함께 확인해 결정합니다.",
                "의 고등학교 내신 준비는 상담 시 범위표와 시험지를 확인한 뒤 필요한 단원부터 설계합니다.",
            ],
        ),
        (
            "자료의 수업 학교 목록에는",
            [
                "학습 상담에서 참고할 학교에는",
                "학교별 내신 자료를 확인할 대상에는",
                "수업 범위를 살펴볼 학교에는",
                "센터 상담 시 참고할 학교에는",
                "학교 일정 확인이 필요한 대상에는",
                "학생별 자료를 비교할 학교에는",
            ],
        ),
        (
            "정보성 원고입니다.",
            [
                "상담 전에 확인할 학습 안내입니다.",
                "학생의 현재 상태를 점검하는 학습 안내입니다.",
                "수업 선택 기준을 정리한 안내입니다.",
                "세 과목 관리 기준을 살펴보는 안내입니다.",
                "학부모 상담에 필요한 내용을 정리한 안내입니다.",
                "학습 진단과 관리 방식을 설명하는 안내입니다.",
            ],
        ),
        (
            "정보성 원고",
            [
                "학습관리 안내",
                "상담 전 학습 안내",
                "수업 선택 안내",
                "세 과목 관리 안내",
                "학생 맞춤 학습 안내",
                "진단·관리 안내",
            ],
        ),
        (
            "구조화 요약",
            [
                "학습관리 요약",
                "상담 기준 요약",
                "세 과목 관리 요약",
                "수업 선택 요약",
                "학생 진단 요약",
                "학습 설계 요약",
            ],
        ),
        (
            "제공된 학교 목록과",
            [
                "학교별 참고 정보와",
                "확인 가능한 학교 정보와",
                "학교별 내신 자료와",
                "학생의 학교 자료와",
            ],
        ),
        (
            "제공 학교 목록과",
            [
                "학교별 참고 정보와",
                "확인 가능한 학교 정보와",
                "학교별 내신 자료와",
                "학생의 학교 자료와",
            ],
        ),
        (
            "제공된 학교 목록을",
            [
                "학교별 참고 정보를",
                "확인 가능한 학교 정보를",
                "학교별 내신 자료를",
                "학생의 학교 자료를",
            ],
        ),
        (
            "제공 학교 목록을",
            [
                "학교별 참고 정보를",
                "확인 가능한 학교 정보를",
                "학교별 내신 자료를",
                "학생의 학교 자료를",
            ],
        ),
        (
            "제공된 학교 목록은",
            [
                "학교별 참고 정보는",
                "확인 가능한 학교 정보는",
                "학교별 내신 자료는",
                "학생의 학교 자료는",
            ],
        ),
        (
            "제공 학교 목록은",
            [
                "학교별 참고 정보는",
                "확인 가능한 학교 정보는",
                "학교별 내신 자료는",
                "학생의 학교 자료는",
            ],
        ),
        (
            "제공된 학교 목록",
            [
                "센터별 학교 참고 정보",
                "상담 시 확인할 학교 정보",
                "학교별 학습 범위 자료",
                "확인 가능한 학교 정보",
                "학교별 내신 참고 자료",
                "학생별 학교 자료",
            ],
        ),
        (
            "제공 학교 목록",
            [
                "학교별 참고 정보",
                "상담 대상 학교 정보",
                "학교별 시험 범위 자료",
                "센터별 학교 정보",
                "학교별 내신 자료",
                "학생의 학교 자료",
            ],
        ),
        (
            "제공된 학교 자료",
            [
                "확인 가능한 학교 자료",
                "학교별 학습 자료",
                "상담 시 준비한 학교 자료",
                "센터별 학교 참고 정보",
                "최근 학교 평가 자료",
                "학생의 학교 자료",
            ],
        ),
        (
            "제공 학교별",
            [
                "학교별",
                "재학 학교별",
                "학생의 학교별",
                "학교 자료별",
            ],
        ),
        (
            "제공된 자료",
            [
                "확인 가능한 자료",
                "상담 기준 자료",
                "센터별 확인 자료",
                "현재 확인된 정보",
            ],
        ),
        (
            "제공 위치",
            [
                "상담 기준 위치",
                "센터 위치",
                "방문 안내 위치",
                "확인된 센터 위치",
            ],
        ),
        (
            "이번 페이지의",
            [
                "상담 대상",
                "현재 살펴볼",
                "이 안내에서 다루는",
                "학습 점검이 필요한",
            ],
        ),
        (
            "페이지에 학교명이 없을 때",
            [
                "학교별 자료가 아직 준비되지 않았을 때",
                "상담 전에 학교 정보가 확인되지 않았을 때",
                "학교별 시험 자료가 없는 상태에서",
                "재학 학교 자료를 아직 준비하지 못했을 때",
            ],
        ),
    ]
    result = value
    for index, (needle, options) in enumerate(replacements):
        if needle in result:
            result = result.replace(
                needle,
                stable_pick(key, f"reader-term-{index}", options),
            )
    return result


HEADING_BANKS: dict[str, list[str]] = {
    "{TITLE}, 어떤 학생에게 맞는가": [
        "{LOCAL} 학생에게 맞는 세 과목 관리",
        "수업 적합성을 판단하는 학생의 학습 신호",
        "현재 학습 상태와 수업 선택 기준",
        "세 과목 관리가 필요한 학생 유형",
        "학습 습관으로 살펴보는 수업 적합성",
        "진단 결과로 확인하는 추천 학생",
    ],
    "국어·영어·수학을 한 주 계획으로 연결하기": [
        "세 과목을 한 주 계획에 배치하는 순서",
        "국어·영어·수학 계획을 하나로 잇는 방법",
        "과목별 우선순위와 주간 시간표",
        "세 과목의 학습량을 조정하는 기준",
        "학교 일정에 맞춘 국영수 계획",
        "과목별 목표를 주간 실행으로 바꾸기",
    ],
    "과제·오답·복습이 이어지는 관리 구조": [
        "과제에서 재풀이까지 이어지는 점검",
        "미완 과제와 오답을 다음 계획에 반영하기",
        "복습이 끊기지 않는 학습관리 순서",
        "채점 이후 다시 풀기까지의 관리 기준",
        "과제 기록을 다음 주 계획으로 연결하기",
        "오답 원인과 복습 날짜를 관리하는 법",
    ],
    "상담에서 비교할 여섯 가지 질문": [
        "상담 전에 준비할 여섯 가지 확인 질문",
        "학원 비교를 구체화하는 여섯 가지 기준",
        "등록 결정 전에 답을 들어야 할 질문",
        "수업과 관리 방식을 비교하는 체크리스트",
        "상담 내용을 판단하는 여섯 가지 항목",
        "학생에게 맞는지 확인할 상담 질문",
    ],
    "{TITLE} 선택에 대한 바로 답": [
        "{LOCAL}에서 먼저 확인할 학원 선택 기준",
        "세 과목 학원을 고를 때의 핵심 답변",
        "상담 전 우선 확인할 선택 조건",
        "국영수 수업 비교의 첫 번째 기준",
        "학생 상황에 맞춘 학원 선택 순서",
        "수업 횟수보다 먼저 볼 판단 근거",
    ],
    "국어·영어·수학의 공부 단위 구분": [
        "세 과목을 서로 다른 방식으로 점검하기",
        "국어·영어·수학별 학습 단위",
        "과목마다 달라야 하는 공부 기준",
        "세 과목의 약점을 나누어 보는 법",
        "과목별 진단과 복습 단위 정리",
        "국영수 학습을 같은 방식으로 보지 않기",
    ],
    "개념·응용·오답 중 어디부터 시작할까": [
        "개념과 응용, 오답의 시작 순서",
        "현재 공백에 맞춘 학습 우선순위",
        "먼저 보완할 학습 단계 찾기",
        "정답률보다 먼저 확인할 막힘 지점",
        "개념 이해와 문제 적용을 구분하는 진단",
        "학생 자료로 정하는 첫 학습 과제",
    ],
    "학교별 평가와 {LOCAL} 생활 리듬 반영": [
        "학교 평가 일정과 일상 시간표 맞추기",
        "{LOCAL} 등원 동선과 시험 준비 계획",
        "학교별 범위와 학생 생활 리듬",
        "내신 일정에 맞춘 수업·복습 배치",
        "학교 자료와 실제 등원 시간을 함께 보기",
        "시험 주차와 귀가 후 복습 시간 점검",
    ],
    "점수 대신 먼저 추적할 학습 지표": [
        "점수 변화 전에 확인할 실행 기록",
        "학습 과정에서 먼저 볼 변화 신호",
        "과제·질문·오답으로 확인하는 진전",
        "성적표보다 앞서 살펴볼 학습 지표",
        "한 주 계획이 작동하는지 확인하는 기록",
        "학생의 실행 변화를 측정하는 기준",
    ],
    "현재 점수보다 먼저 볼 학습 신호": [
        "현재 점수 뒤에 있는 학습 원인",
        "학생의 공부 흐름을 보여 주는 신호",
        "맞힌 문제에서도 확인할 이해 수준",
        "점수만으로 보이지 않는 학습 상태",
        "진단에서 먼저 살펴볼 행동 기록",
        "학생 설명으로 확인하는 실제 이해",
    ],
    "제공된 학교 자료로 내신 범위를 읽는 법": [
        "학교별 자료로 내신 범위를 확인하는 법",
        "최근 범위표와 평가지를 읽는 순서",
        "학교 자료를 수업 계획에 반영하기",
        "교과서·프린트·시험 주차 점검",
        "학교별 평가 자료와 과제 계획",
        "내신 자료를 다음 학습으로 연결하기",
    ],
    "등록 전 확인할 약속과 기록": [
        "등록 전에 정할 점검 날짜와 기록",
        "첫 한 달의 약속을 구체화하는 법",
        "상담 내용을 실행 기준으로 바꾸기",
        "수업 시작 전에 확인할 관리 약속",
        "첫 점검일까지 남겨야 할 기록",
        "등록 판단을 돕는 확인 항목",
    ],
    "한 주 학습 루틴을 만드는 방법": [
        "학생이 지킬 수 있는 주간 루틴",
        "수업과 가정 복습을 잇는 시간표",
        "한 주 계획을 실제 행동으로 바꾸기",
        "학교 일정에 맞춘 반복 학습",
        "당일 회상과 이틀 뒤 재풀이",
        "지속 가능한 학습 습관 설계",
    ],
    "{LOCAL}에서 실제로 생기는 일정 문제": [
        "{LOCAL} 등원과 학교 일정 함께 보기",
        "수업 전후 시간을 현실적으로 계산하기",
        "학교 종료부터 귀가까지의 학습 동선",
        "과제 시간을 지키기 위한 일정 점검",
        "평일과 주말의 다른 공부 흐름",
        "가까운 위치가 실제 편의가 되는 조건",
    ],
    "이번 페이지의 학생 유형과 우선순위": [
        "상담 대상 학생의 학습 습관과 우선순위",
        "현재 학생에게 먼저 필요한 변화",
        "시험지와 과제 기록으로 찾는 약점",
        "학생 상황에서 출발하는 첫 달 계획",
        "학습 행동을 기준으로 정하는 순서",
        "새 교재보다 먼저 살펴볼 학생 자료",
    ],
    "첫 4주 과제와 피드백 설계": [
        "첫 한 달 과제량과 피드백 조정",
        "미완 이유를 반영하는 주간 계획",
        "초기 4주의 실행 기록과 보완",
        "학생이 지킬 수 있는 최소 과제 설정",
        "과제 완료 기준과 점검 주기",
        "첫 달 학습 흐름을 안정시키는 방법",
    ],
    "세 과목의 약점을 같은 방식으로 보지 않기": [
        "국어·영어·수학의 병목을 따로 찾기",
        "과목별로 달라야 하는 진단과 과제",
        "세 과목의 집중 과제와 유지 과제",
        "학생 에너지에 맞춘 과목별 배분",
        "통합 관리와 동일 진도의 차이",
        "과목별 약점을 한 계획에서 조정하기",
    ],
    "학부모와 학생이 함께 정할 선택 기준": [
        "보호자와 학생이 함께 확인할 기준",
        "상담 답변을 비교하는 체크리스트",
        "수업 선택 전에 합의할 항목",
        "학생과 보호자가 나누어 볼 조건",
        "광고 문구보다 먼저 확인할 절차",
        "지속 가능한 수업을 고르는 질문",
    ],
    "수업 후 48시간을 관리하는 복습 구조": [
        "수업 뒤 이틀 안에 확인할 복습",
        "48시간 안에 이해를 기억으로 바꾸기",
        "당일 회상과 재풀이 날짜 정하기",
        "수업 내용을 다시 꺼내는 복습 간격",
        "이틀 안에 점검하는 대표 문항",
        "다음 수업 전 기억을 확인하는 방법",
    ],
    "과목별로 다른 진단 기준": [
        "국어·영어·수학별 진단 자료",
        "세 과목의 막힘을 구분하는 기준",
        "과목마다 다른 약점 확인 순서",
        "시험지로 나누어 보는 국영수 공백",
        "과목별 이해·적용·회상 점검",
        "같은 점수도 다르게 해석하는 진단",
    ],
}


REPEATED_SENTENCE_BANKS: dict[str, list[str]] = {
    "{TITLE}에서 들은 내용을 보호자와 학생이 각각 한 문장으로 정리하면 서로 다르게 이해한 부분도 찾기 쉽습니다.": [
        "{TITLE} 상담을 마친 뒤 보호자와 학생이 핵심을 따로 요약하면 이해가 엇갈린 조건을 확인하기 쉽습니다.",
        "상담에서 들은 반 배정·과제·피드백 기준을 학생과 보호자가 각자 적어 비교하는 편이 좋습니다.",
        "학생과 보호자가 수업 설명을 자신의 말로 다시 정리하면 놓친 조건과 다르게 이해한 부분이 드러납니다.",
        "상담 내용을 함께 들었더라도 보호자와 학생이 따로 요약해 보면 추가로 물어볼 항목을 찾을 수 있습니다.",
        "수업과 관리에 관한 설명을 학생과 보호자가 각자 한 문장으로 남기면 선택 기준이 더 분명해집니다.",
        "보호자와 학생이 상담 핵심을 별도로 기록한 뒤 대조하면 서로 다르게 받아들인 내용을 바로잡기 쉽습니다.",
        "상담 직후 학생은 자신의 과제를, 보호자는 점검 기준을 설명해 보면 이해 여부를 확인할 수 있습니다.",
        "들은 내용을 그대로 기억하려 하기보다 학생과 보호자가 각자의 표현으로 정리해 비교하는 과정이 필요합니다.",
        "학생이 이해한 수업 방식과 보호자가 확인한 관리 방식을 나란히 적어 보면 빠진 질문을 찾기 좋습니다.",
        "상담 뒤 각자가 생각한 첫 목표와 점검 날짜를 말해 보면 설명이 충분했는지 판단할 수 있습니다.",
        "설명받은 내용을 보호자와 학생이 따로 정리한 다음 공통점과 차이를 확인해 보세요.",
        "학생과 보호자가 상담 내용을 각자의 언어로 다시 말할 수 있어야 실제 실행 계획도 같은 방향으로 맞출 수 있습니다.",
    ],
    "{LOCAL}의 학교 대응은 학교명을 반복하는 데 의미가 있는 것이 아니라 범위표와 시험지 분석이 다음 과제와 오답 계획으로 이어지는지 확인하는 데 의미가 있습니다.": [
        "{LOCAL}의 학교 대응은 학교명 자체보다 최근 범위표와 시험지가 다음 과제·오답 계획에 어떻게 반영되는지를 보는 과정입니다.",
        "학교 이름을 많이 언급하는 것보다 {LOCAL} 학생의 범위표와 평가 결과가 다음 학습량으로 이어지는지가 중요합니다.",
        "{LOCAL} 내신 준비에서는 학교명 나열보다 시험 자료 분석 뒤 무엇을 복습할지 정하는 절차를 확인해야 합니다.",
        "학교별 대응의 핵심은 {LOCAL} 학생의 최근 평가 자료가 다음 주 과제와 재풀이 날짜로 연결되는가에 있습니다.",
        "{LOCAL}에서는 학교를 안다는 설명보다 실제 범위표·시험지를 분석해 오답 계획을 바꾸는지를 살펴보아야 합니다.",
        "학교 정보는 출발점일 뿐이며, {LOCAL} 학생의 시험 결과를 다음 과제와 복습 순서에 반영해야 의미가 있습니다.",
        "{LOCAL}의 학교별 준비는 이름을 반복하는 방식이 아니라 최근 자료를 읽고 다음 학습 행동을 정하는 방식이어야 합니다.",
        "내신 대응이 구체적인지는 {LOCAL} 학생의 범위와 시험지를 분석한 결과가 과제 조정으로 이어지는지 보면 알 수 있습니다.",
        "{LOCAL} 학교 자료는 안내용 목록에 머물지 않고 시험 분석·오답 분류·다음 과제로 이어져야 합니다.",
        "학교명보다 중요한 것은 {LOCAL} 학생의 실제 평가 자료를 바탕으로 복습 범위와 다음 과제를 결정하는 일입니다.",
        "{LOCAL} 내신 관리는 범위표 확인에서 끝나지 않고 시험지 분석과 재학습 계획까지 이어져야 합니다.",
        "학교별 준비를 판단할 때는 {LOCAL} 학생의 평가 자료가 과제량과 오답 일정에 실제로 반영되는지 확인하세요.",
    ],
    "{TITLE}에서는 학교 수가 많은 만큼 공통 개념 진도와 학교별 시험 자료를 나누고, 학년·교과서·프린트·수행평가 일정을 학생별로 다시 확인해야 합니다.": [
        "{TITLE} 상담에서는 공통 개념과 학교별 시험 자료를 구분하고 학생마다 학년·교과서·프린트·수행평가 일정을 다시 확인해야 합니다.",
        "참고 학교가 여러 곳이라면 공통 진도와 개별 시험 자료를 나눈 뒤 학생별 교재와 평가 일정을 점검하는 과정이 필요합니다.",
        "학교 수가 많을수록 같은 계획을 적용하기보다 학생의 학년, 교과서, 프린트와 수행평가 날짜를 따로 맞추어야 합니다.",
        "공통 개념 학습은 함께 설계할 수 있지만 시험 자료와 수행평가 일정은 학생별로 분리해 확인하는 편이 좋습니다.",
        "여러 학교를 참고할 때는 공통 진도와 학교별 범위를 나누고 각 학생의 실제 자료를 기준으로 계획을 조정해야 합니다.",
        "학생마다 교과서와 프린트, 평가 주차가 다르므로 공통 수업과 학교별 보완 항목을 구분해 살펴보아야 합니다.",
        "학교별 준비는 공통 개념을 유지하면서도 학년과 교재, 수행평가 일정을 학생 단위로 다시 확인해야 구체화됩니다.",
        "같은 지역 학생이라도 학교 자료가 다를 수 있어 공통 진도와 개별 시험 대비를 나누어 계획하는 것이 필요합니다.",
    ],
    "{LOCAL}에서 이 학교 목록을 준비할 때는 같은 학년이라도 교과서와 시험 주차가 다를 수 있으므로 최근 범위표와 평가지를 실제 수업 계획에 대조해야 합니다.": [
        "{LOCAL}에서 학교별 준비를 할 때는 같은 학년이라도 교과서와 시험 주차가 다를 수 있어 최근 범위표와 평가지를 수업 계획에 대조해야 합니다.",
        "같은 학년 학생도 교재와 평가 일정이 다를 수 있으므로 {LOCAL}에서는 최근 학교 자료를 실제 학습 계획과 맞추어 보아야 합니다.",
        "{LOCAL} 내신 상담에서는 학교명이 아니라 학생의 최신 범위표와 평가지를 확인해 교재·시험 주차 차이를 반영해야 합니다.",
        "학교별 시험 준비는 {LOCAL} 학생이 가져온 최근 범위표와 평가 자료를 기준으로 수업 순서를 조정하는 데서 시작합니다.",
        "{LOCAL}에서는 같은 학년이라는 이유만으로 계획을 통일하지 말고 교과서와 시험 주차를 실제 자료로 확인해야 합니다.",
        "최근 범위표와 평가지를 수업 계획에 대조하면 {LOCAL} 학생마다 다른 교재와 시험 일정을 놓치지 않을 수 있습니다.",
        "{LOCAL}의 학교 자료는 학년명만으로 판단하지 않고 교과서·프린트·평가 주차까지 확인해 계획에 반영해야 합니다.",
        "같은 지역과 학년이어도 시험 범위가 달라질 수 있으므로 {LOCAL} 학생의 최신 자료를 우선 살펴보는 편이 정확합니다.",
    ],
    "{TITLE}의 주간 피드백은 잘함이나 노력 필요 같은 표현보다 완료율, 반복 오답, 질문 수, 다음 주 조정 내용을 포함해야 합니다.": [
        "주간 피드백에는 막연한 평가보다 과제 완료율, 반복 오답, 질문 기록과 다음 주 조정 항목이 담겨야 합니다.",
        "{TITLE}의 피드백은 잘했다는 말에 그치지 않고 완료 범위와 오답 유형, 질문, 다음 계획을 보여 주어야 합니다.",
        "한 주 점검에서는 노력 정도보다 무엇을 마쳤고 어떤 오답이 반복됐으며 다음 주에 무엇을 바꿀지 확인해야 합니다.",
        "완료율·반복 오답·질문 수·계획 변경이 함께 기록되어야 주간 피드백을 다음 행동으로 연결할 수 있습니다.",
        "학생에게 필요한 피드백은 추상적인 칭찬보다 완료한 범위와 남은 질문, 재풀이할 항목을 구체적으로 알려 주는 것입니다.",
        "주간 기록이 유용하려면 과제 결과와 반복 실수, 질문 내용, 다음 학습량 조정이 한눈에 보여야 합니다.",
        "잘함과 부족함만 표시하기보다 실행률과 오답 원인, 질문, 다음 주 보완 계획을 함께 남기는 편이 좋습니다.",
        "다음 계획을 바꾸려면 주간 피드백에 완료 여부와 반복된 실수, 학생 질문이 구체적으로 기록되어야 합니다.",
    ],
    "{TITLE}의 진단 결과는 상·중·하 같은 등급보다 이번 주에 바꿀 행동과 다음 점검 날짜로 이어져야 실제 실행 계획이 됩니다.": [
        "진단은 상·중·하 등급에서 끝나지 않고 이번 주에 바꿀 행동과 다음 확인 날짜를 정해야 실행 계획이 됩니다.",
        "{TITLE}의 진단 결과는 수준 표시보다 학생이 바로 실천할 과제와 재점검 시점을 알려 주어야 합니다.",
        "학생 수준을 분류하는 것만으로는 부족하며 진단 뒤 첫 행동과 다음 점검 날짜가 구체적으로 정해져야 합니다.",
        "진단 결과가 실제 도움이 되려면 이번 주 학습량과 바꿀 습관, 다시 확인할 시점으로 연결되어야 합니다.",
        "등급을 붙이는 것보다 학생이 무엇부터 시작하고 언제 결과를 확인할지 정하는 일이 중요합니다.",
        "현재 상태를 설명한 뒤 첫 과제와 점검 날짜까지 제시해야 진단이 실행 가능한 계획으로 바뀝니다.",
        "진단표에는 수준명보다 이번 주 행동 목표와 다음 상담에서 확인할 자료가 분명하게 남아야 합니다.",
        "진단은 학생을 분류하는 절차가 아니라 다음 행동과 점검 시점을 결정하는 출발점이어야 합니다.",
    ],
}


FAQ_QUESTION_BANKS: list[tuple[str, list[str]]] = [
    (
        "상담에서 가장 먼저 확인할 것은 무엇인가요?",
        [
            "{TITLE} 상담은 어떤 자료부터 확인하면 좋을까요?",
            "세 과목 상담에서 첫 번째로 살펴볼 기준은 무엇인가요?",
            "{LOCAL} 학생의 학습 상태를 확인할 때 무엇부터 준비해야 하나요?",
            "국영수 학습 진단은 어떤 기록에서 시작해야 하나요?",
            "{TITLE}을 비교할 때 가장 먼저 물어볼 내용은 무엇인가요?",
            "상담 첫 단계에서 학생의 어떤 자료를 확인해야 하나요?",
        ],
    ),
    (
        "국어·영어·수학 과제량은 많을수록 좋은가요?",
        [
            "{LOCAL} 학생의 세 과목 과제는 어느 정도가 적당한가요?",
            "국어·영어·수학 숙제는 양이 많으면 더 효과적인가요?",
            "세 과목 과제량은 어떤 기준으로 조정해야 하나요?",
            "학생이 끝내지 못하는 과제가 많다면 무엇부터 바꿔야 하나요?",
            "{TITLE}의 과제는 분량과 완료 기준 중 무엇이 더 중요한가요?",
            "국영수 과제를 학생 일정에 맞추려면 무엇을 확인해야 하나요?",
        ],
    ),
    (
        "수업 진도가 빠르면 학습 효과도 큰가요?",
        [
            "{LOCAL}에서 진도가 빠른 수업이 항상 유리한가요?",
            "수업 속도와 실제 학습 효과는 어떻게 구분하나요?",
            "선행 진도보다 복습을 우선해야 하는 시점은 언제인가요?",
            "진도가 빨라도 오답이 남는다면 계획을 어떻게 바꿔야 하나요?",
            "{TITLE}의 진도 속도는 어떤 자료로 판단해야 하나요?",
            "새 단원으로 넘어갈 준비가 됐는지는 어떻게 확인하나요?",
        ],
    ),
    (
        "이번 학생 유형에게 맞는지 어떻게 판단하나요?",
        [
            "{TITLE}이 학생에게 맞는지는 어떤 변화로 판단하나요?",
            "현재 학습 습관과 수업 방식이 맞는지 어떻게 확인할까요?",
            "{LOCAL} 학생에게 이 관리 방식이 적합한지 보는 기준은 무엇인가요?",
            "첫 2~4주 동안 어떤 기록을 보면 수업 적합성을 알 수 있나요?",
            "학생 유형에 맞는 수업인지 상담에서 무엇을 물어봐야 하나요?",
            "{TITLE} 선택 후 첫 달에 확인할 변화는 무엇인가요?",
        ],
    ),
    (
        "과제를 학부모가 매일 확인해야 하나요?",
        [
            "보호자는 학생 과제를 어느 범위까지 확인하면 좋을까요?",
            "{TITLE}의 과제 관리는 학부모가 매일 점검해야 하나요?",
            "학생 자율성과 보호자 확인은 어떻게 나누는 편이 좋나요?",
            "{LOCAL} 학부모는 과제 시작과 오답 중 무엇을 확인해야 하나요?",
            "과제 점검에서 보호자와 수업 담당자의 역할은 어떻게 다른가요?",
            "학생이 스스로 과제를 관리하도록 확인 범위를 줄일 수 있나요?",
        ],
    ),
    (
        "위치를 볼 때 주차나 교통만 확인하면 되나요?",
        [
            "{TITLE}의 위치는 이동 거리 외에 무엇을 확인해야 하나요?",
            "센터 위치를 볼 때 귀가와 복습 시간도 계산해야 하나요?",
            "{LOCAL}에서 등원 동선을 정할 때 어떤 조건을 함께 봐야 하나요?",
            "가까운 학원이라도 실제 시간표와 맞지 않을 수 있나요?",
            "주차·교통 외에 학생의 수업 전후 일정을 어떻게 확인하나요?",
            "센터까지의 거리가 실제 학습 리듬에 맞는지 어떻게 판단하나요?",
        ],
    ),
    (
        "안내 주소와 상담·수업 시간을 같은 날 확인해야 하나요?",
        [
            "센터 위치는 실제 등원 요일과 비슷한 시간에 확인해야 하나요?",
            "{TITLE} 방문 전에 주소와 수업 시간을 함께 확인할까요?",
            "{LOCAL}의 평일 이동 시간은 어떤 방식으로 계산하면 좋나요?",
            "상담 시간과 실제 수업 시간의 이동 조건이 다를 수 있나요?",
            "학교 종료 뒤 센터까지의 동선은 언제 확인하는 편이 정확한가요?",
            "주소를 확인할 때 결석·시험 기간 시간표도 함께 물어봐야 하나요?",
        ],
    ),
    (
        "등록 전 진단에서 무엇을 관찰해야 하나요?",
        [
            "{TITLE} 등록 전 진단에서는 학생의 어떤 행동을 봐야 하나요?",
            "진단 시간에 정답률 외에 무엇을 관찰하면 좋을까요?",
            "{LOCAL} 학생의 실제 이해 수준은 어떻게 확인하나요?",
            "수업 전 진단이 구체적인지 판단할 기준은 무엇인가요?",
            "학생이 직접 설명하고 질문하는 과정도 진단에 포함되나요?",
            "진단 결과가 다음 과제로 이어지는지 어떻게 확인할까요?",
        ],
    ),
    (
        "오답 노트는 모든 문제를 다시 써야 하나요?",
        [
            "{LOCAL} 학생의 오답 노트에는 무엇을 남겨야 하나요?",
            "틀린 문제를 모두 옮겨 적는 방식이 효과적인가요?",
            "오답 기록에서 풀이보다 먼저 적을 내용은 무엇인가요?",
            "재풀이 날짜는 오답 노트에 어떻게 표시하면 좋을까요?",
            "{TITLE}의 오답 관리는 어떤 항목을 확인해야 하나요?",
            "오답을 실제 재학습으로 연결하는 기록 방식은 무엇인가요?",
        ],
    ),
    (
        "안내 주소가 가까우면 바로 등록해도 될까요?",
        [
            "{LOCAL}에서 센터가 가깝다는 이유만으로 결정해도 될까요?",
            "이동 거리가 짧으면 학생에게 맞는 수업이라고 볼 수 있나요?",
            "{TITLE} 선택에서 위치와 수업 적합성은 어떻게 비교하나요?",
            "가까운 학원이라도 상담에서 추가로 확인할 조건은 무엇인가요?",
            "센터 접근성과 과제·복습 시간을 함께 판단하려면 어떻게 해야 하나요?",
            "주소가 편리한 것 외에 첫 달 계획도 확인해야 하나요?",
        ],
    ),
    (
        "제공 학교 목록은 같은 교재로 준비해도 되나요?",
        [
            "{LOCAL}의 학교별 내신을 같은 교재로 준비해도 되나요?",
            "학교가 다르면 교과서와 시험 자료도 나누어 준비해야 하나요?",
            "{TITLE} 상담에서 학교별 범위를 어떻게 확인하나요?",
            "같은 학년 학생도 학교에 따라 학습 계획이 달라질 수 있나요?",
            "{LOCAL} 학교별 시험 대비는 어떤 자료부터 비교해야 하나요?",
            "공통 개념 교재와 학교별 내신 자료를 어떻게 구분할까요?",
        ],
    ),
    (
        "페이지에 학교명이 없을 때 내신 상담은 어떻게 해야 하나요?",
        [
            "{LOCAL} 학교 자료가 아직 없다면 상담에서 무엇부터 확인할까요?",
            "학교별 시험 자료를 준비하지 못했다면 어떤 자료를 가져가면 좋나요?",
            "재학 학교 정보가 없는 상태에서도 내신 상담이 가능한가요?",
            "{TITLE} 상담 전에 최근 시험지와 범위표를 준비하면 도움이 되나요?",
            "학교명이 안내에 없을 때 학년·교과서를 어떻게 확인해야 하나요?",
            "학교별 정보가 부족하다면 학생 자료로 무엇을 확인할 수 있나요?",
        ],
    ),
]


SCHOOL_FAQ_ANSWER_BANK = [
    "{TITLE}에서는 학교명만으로 계획을 통일하지 않고 학년·교과서·프린트·시험 주차를 최근 범위표와 함께 확인합니다. 공통 개념과 학교별 자료를 나누어 준비하는지가 핵심입니다.",
    "같은 학교나 학년이라도 교과서와 평가 일정은 달라질 수 있습니다. {LOCAL} 학생의 최근 시험지와 범위표를 보고 공통 학습과 학교별 보완 항목을 구분해야 합니다.",
    "학교별 내신 준비는 하나의 교재로 끝내기 어렵습니다. {TITLE} 상담에서는 공통 개념을 유지하되 실제 프린트와 시험 주차에 맞춘 자료가 별도로 필요한지 확인하세요.",
    "{LOCAL}의 학교 자료는 학년명만으로 판단하지 말고 교과서, 프린트, 수행평가와 시험 범위를 함께 보아야 합니다. 그 결과를 과제와 오답 계획에 반영하는지가 중요합니다.",
    "공통 개념은 함께 공부할 수 있지만 내신 범위는 학교와 학년별로 달라질 수 있습니다. 최근 평가 자료를 기준으로 학생별 준비 순서를 다시 정하는 편이 좋습니다.",
    "{TITLE}에서 학교별 준비를 확인할 때는 학교명보다 최근 범위표와 시험지를 먼저 보아야 합니다. 같은 교재를 쓰더라도 보완할 프린트와 서술형 범위가 달라질 수 있습니다.",
    "학생의 학교가 같아도 학년과 담당 교과, 평가 주차에 따라 대비 자료가 달라집니다. {LOCAL} 내신은 공통 학습과 학교별 자료를 구분해 계획하는 것이 안전합니다.",
    "한 권의 교재를 모든 학교에 그대로 적용하기보다 최근 시험 자료를 대조해 공통 개념과 개별 범위를 나누어야 합니다. 상담에서는 이 구분이 과제로 이어지는지 확인하세요.",
    "{LOCAL} 학생의 내신 자료는 교과서·프린트·범위표를 실제로 확인한 뒤 정해야 합니다. 학교 이름만 같다는 이유로 준비 범위를 동일하게 잡지 않는 편이 좋습니다.",
    "학교별 시험은 범위와 출제 자료가 달라질 수 있으므로 최근 자료를 먼저 준비하세요. {TITLE} 상담에서는 공통 진도와 학생별 시험 계획이 어떻게 나뉘는지 물어볼 수 있습니다.",
    "학교 정보는 출발점이고 실제 계획은 학생의 최신 범위표와 평가지를 기준으로 정해야 합니다. 공통 개념 수업 뒤 학교별 보완 과제가 이어지는지 확인하는 것이 좋습니다.",
    "{LOCAL} 내신 준비에서는 학교명 반복보다 최근 시험지를 분석해 다음 과제와 오답 일정으로 연결하는 과정이 중요합니다. 같은 교재라도 학생별 보완 범위는 달라질 수 있습니다.",
]


REVIEW_NOTE_BANK = [
    "아래 내용은 실제 이용 후기가 아니라, {LOCAL} 학부모가 상담에서 점검할 수 있는 상황을 설명한 예시입니다.",
    "다음 내용은 특정 고객의 체험담이 아닌, {LOCAL} 보호자가 학원 선택 과정에서 마주칠 수 있는 상담 사례입니다.",
    "실제 성과를 보장하는 후기가 아니라, {LOCAL} 학생의 상황을 기준으로 구성한 상담 장면 예시입니다.",
    "아래 사례는 실제 고객 평가가 아니며, {LOCAL} 학부모가 비교 과정에서 확인할 질문을 보여 줍니다.",
    "특정 학생의 결과를 소개하는 내용이 아니라, {LOCAL} 상담에서 생길 수 있는 판단 상황을 재구성했습니다.",
    "다음 예시는 실제 수강 후기가 아닌, {LOCAL} 보호자가 수업과 관리 기준을 비교하는 과정을 설명합니다.",
    "실제 이용자의 발언을 옮긴 것이 아니라, {LOCAL} 학부모 상담에서 자주 검토할 상황을 사례로 정리했습니다.",
    "아래 내용은 홍보용 성공 사례가 아니라, {LOCAL}에서 학원을 알아볼 때 적용할 수 있는 상담 예시입니다.",
    "특정 고객 경험으로 오해하지 않도록, {LOCAL} 학생의 일반적인 학습 상황을 가정해 구성한 사례입니다.",
    "다음 상담 장면은 실제 후기가 아니며, {LOCAL} 보호자가 학생 일정과 학습 기준을 비교하도록 만든 예시입니다.",
    "아래 사례는 성적 향상을 주장하는 고객 후기가 아니라, {LOCAL} 상담 질문을 구체화하기 위한 상황 설명입니다.",
    "실제 등록 경험을 재현한 내용은 아니며, {LOCAL} 학부모가 확인할 선택 기준을 보여 주는 가상 상담 사례입니다.",
]


def rewrite_heading(heading: str, title: str, local: str, key: str) -> str:
    normalized = heading.replace(title, "{TITLE}").replace(local, "{LOCAL}")
    options = HEADING_BANKS.get(normalized)
    if options:
        return stable_pick(key, f"heading-{normalized}", options).format(
            TITLE=title,
            LOCAL=local,
        )
    return polish_reader_terms(heading, key + "|heading")


def rewrite_repeated_sentences(
    value: str,
    title: str,
    local: str,
    key: str,
) -> str:
    parts = re.split(r"(?<=[.!?])(\s+)", value)
    output: list[str] = []
    sentence_index = 0
    for part in parts:
        if not part or part.isspace():
            output.append(part)
            continue
        normalized = part.replace(title, "{TITLE}").replace(local, "{LOCAL}")
        options = REPEATED_SENTENCE_BANKS.get(normalized)
        if options:
            part = stable_pick(
                key,
                f"sentence-{sentence_index}-{normalized}",
                options,
            ).format(TITLE=title, LOCAL=local)
        output.append(part)
        sentence_index += 1
    return "".join(output)


def varied_replace(
    value: str,
    needle: str,
    options: list[str],
    key: str,
    slot: str,
    replace_percent: int,
) -> str:
    occurrence = 0

    def replacement(match: re.Match[str]) -> str:
        nonlocal occurrence
        current = occurrence
        occurrence += 1
        if stable_percent(key, f"{slot}-use-{current}") >= replace_percent:
            return match.group(0)
        return stable_pick(key, f"{slot}-choice-{current}", options)

    return re.sub(re.escape(needle), replacement, value)


def thin_entity_mentions(
    value: str,
    title: str,
    local: str,
    address: str,
    key: str,
    *,
    place_phrase: str = "",
    title_percent: int = 40,
    local_percent: int = 28,
) -> str:
    """Reduce exact-match repetition while keeping factual addresses untouched."""
    address_token = "\uFFF0ADDRESS\uFFF1"
    result = value.replace(address, address_token) if address else value
    place_token = "\uFFF0PLACE\uFFF1"
    if place_phrase:
        result = result.replace(place_phrase, place_token)
    title_forms = [
        (title + "에서는", ["세 과목 학습관리에서는", "해당 수업에서는", "이 지역 국영수 과정에서는"]),
        (title + "에서", ["세 과목 상담에서", "해당 학원에서", "이 지역 국영수 수업에서"]),
        (title + "의", ["해당 학습관리의", "이 지역 국영수 과정의", "세 과목 수업의"]),
        (title + "을", ["해당 학원을", "이 지역 국영수 과정을", "세 과목 수업을"]),
        (title + "를", ["해당 학원을", "이 지역 국영수 과정을", "세 과목 수업을"]),
        (title + "은", ["해당 학원은", "이 지역 국영수 과정은", "세 과목 학습관리는"]),
        (title + "는", ["해당 학원은", "이 지역 국영수 과정은", "세 과목 학습관리는"]),
        (title + "이", ["해당 학원이", "이 지역 국영수 과정이", "세 과목 학습관리가"]),
        (title + "가", ["해당 학원이", "이 지역 국영수 과정이", "세 과목 학습관리가"]),
    ]
    for index, (needle, options) in enumerate(title_forms):
        result = varied_replace(
            result,
            needle,
            options,
            key,
            f"title-form-{index}",
            title_percent,
        )
    result = varied_replace(
        result,
        title,
        ["해당 학원", "이 지역 국영수학원", "세 과목 학습관리"],
        key,
        "title-plain",
        title_percent,
    )

    # Preserve exact title phrases that intentionally remained before thinning locality.
    title_token = "\uFFF0TITLE\uFFF1"
    result = result.replace(title, title_token)
    local_forms = [
        (local + "에서는", ["이 지역에서는", "해당 생활권에서는", "지역 내에서는"]),
        (local + "에서", ["이 지역에서", "해당 생활권에서", "지역 내에서"]),
        (local + "의", ["이 지역의", "해당 생활권의", "지역 내"]),
        (local + " 학생", ["지역 학생", "이 지역 학생", "해당 생활권 학생"]),
        (local + " 학부모", ["지역 학부모", "이 지역 보호자", "해당 생활권 학부모"]),
        (local + " 기준", ["지역 기준", "상담 기준", "해당 생활권 기준"]),
        (local + " 생활", ["지역 생활", "이 지역의 일상", "해당 생활권의 일상"]),
    ]
    for index, (needle, options) in enumerate(local_forms):
        result = varied_replace(
            result,
            needle,
            options,
            key,
            f"local-form-{index}",
            local_percent,
        )
    result = varied_replace(
        result,
        local,
        ["이 지역", "해당 생활권", "지역 내"],
        key,
        "local-plain",
        local_percent,
    )
    result = result.replace(title_token, title)
    result = result.replace(place_token, place_phrase)
    return result.replace(address_token, address)


def rewrite_faq_entry(
    question: str,
    answer: str,
    title: str,
    local: str,
    address: str,
    place_phrase: str,
    key: str,
    index: int,
) -> tuple[str, str]:
    normalized_question = question.replace(title, "{TITLE}").replace(local, "{LOCAL}")
    for marker, options in FAQ_QUESTION_BANKS:
        if marker in normalized_question:
            question = stable_pick(
                key,
                f"faq-question-{index}-{marker}",
                options,
            ).format(TITLE=title, LOCAL=local)
            break

    normalized_answer = answer.replace(title, "{TITLE}").replace(local, "{LOCAL}")
    if (
        "학교명이 같아도 학년, 교과서, 프린트, 시험 주차가 다를 수 있다고 보고"
        in normalized_answer
    ):
        answer = stable_pick(
            key,
            f"faq-school-answer-{index}",
            SCHOOL_FAQ_ANSWER_BANK,
        ).format(TITLE=title, LOCAL=local)
    else:
        answer = rewrite_repeated_sentences(
            answer,
            title,
            local,
            key + f"|faq-answer-{index}",
        )

    question = polish_reader_terms(question, key + f"|faq-question-{index}")
    answer = polish_reader_terms(answer, key + f"|faq-answer-{index}")
    question = thin_entity_mentions(
        question,
        title,
        local,
        address,
        key + f"|faq-q-entity-{index}",
        place_phrase=place_phrase,
        title_percent=30 if index == 0 else 55,
        local_percent=38,
    )
    answer = thin_entity_mentions(
        answer,
        title,
        local,
        address,
        key + f"|faq-a-entity-{index}",
        place_phrase=place_phrase,
        title_percent=55,
        local_percent=42,
    )
    return question, answer


def prepare_detail_copy(
    sections: dict[str, str],
    row: dict[str, str],
) -> tuple[
    dict[str, str],
    str,
    list[tuple[str, list[str]]],
    list[tuple[str, str]],
    str,
    list[str],
]:
    title = sections["페이지타이틀"].strip()
    local = locality_from_title(title)
    address = compact_text(row.get("센터 주소"))
    place_phrase = " ".join(
        value
        for value in (
            compact_text(row.get("지역")),
            compact_text(row.get("시or구")),
            local,
        )
        if value
    )
    key = title
    prepared = dict(sections)
    prepared["메타설명"] = polish_reader_terms(
        re.sub(r"\s+", " ", sections["메타설명"]).strip(),
        key + "|meta",
    )
    prepared["JSON-LD 요약"] = polish_reader_terms(
        re.sub(r"\s+", " ", sections["JSON-LD 요약"]).strip(),
        key + "|json-summary",
    )

    intro, blocks = parse_body(sections["본문"])
    intro = rewrite_repeated_sentences(intro, title, local, key + "|intro")
    intro = polish_reader_terms(intro, key + "|intro")
    intro = thin_entity_mentions(
        intro,
        title,
        local,
        address,
        key + "|intro-entity",
        place_phrase=place_phrase,
        title_percent=20,
        local_percent=22,
    )

    rewritten_blocks: list[tuple[str, list[str]]] = []
    for block_index, (heading, paragraphs) in enumerate(blocks):
        rewritten_heading = rewrite_heading(
            heading,
            title,
            local,
            key + f"|block-{block_index}",
        )
        rewritten_paragraphs = []
        for paragraph_index, paragraph in enumerate(paragraphs):
            paragraph_key = key + f"|block-{block_index}|paragraph-{paragraph_index}"
            value = rewrite_repeated_sentences(
                paragraph,
                title,
                local,
                paragraph_key,
            )
            value = polish_reader_terms(value, paragraph_key)
            value = thin_entity_mentions(
                value,
                title,
                local,
                address,
                paragraph_key + "|entity",
                place_phrase=place_phrase,
            )
            rewritten_paragraphs.append(value)
        rewritten_blocks.append((rewritten_heading, rewritten_paragraphs))

    permutations = [
        (0, 1, 2, 3, 4, 5),
        (0, 2, 1, 3, 5, 4),
        (0, 3, 1, 2, 4, 5),
        (0, 1, 3, 2, 5, 4),
        (0, 2, 3, 1, 4, 5),
        (0, 3, 2, 1, 5, 4),
    ]
    order = stable_pick(
        key,
        "section-order",
        [",".join(map(str, order)) for order in permutations],
    )
    rewritten_blocks = [rewritten_blocks[int(index)] for index in order.split(",")]

    source_faqs = parse_faq(sections["FAQ"])
    faqs = [
        rewrite_faq_entry(
            question,
            answer,
            title,
            local,
            address,
            place_phrase,
            key,
            index,
        )
        for index, (question, answer) in enumerate(source_faqs)
    ]
    faq_orders = [
        (0, 1, 2, 3, 4),
        (0, 2, 4, 1, 3),
        (1, 3, 0, 4, 2),
        (2, 0, 3, 1, 4),
        (3, 1, 4, 0, 2),
        (4, 2, 0, 3, 1),
    ]
    faq_order = stable_pick(
        key,
        "faq-order",
        [",".join(map(str, order)) for order in faq_orders],
    )
    faqs = [faqs[int(index)] for index in faq_order.split(",")]

    _, review_items = parse_review(sections["학부모후기"])
    review_note = stable_pick(key, "review-note", REVIEW_NOTE_BANK).format(LOCAL=local)
    rewritten_reviews = []
    for index, review in enumerate(review_items):
        review_key = key + f"|review-{index}"
        value = rewrite_repeated_sentences(review, title, local, review_key)
        value = polish_reader_terms(value, review_key)
        value = thin_entity_mentions(
            value,
            title,
            local,
            address,
            review_key + "|entity",
            place_phrase=place_phrase,
            title_percent=55,
            local_percent=48,
        )
        rewritten_reviews.append(value)

    return (
        prepared,
        intro,
        rewritten_blocks,
        faqs,
        review_note,
        rewritten_reviews,
    )


def rel_prefix(depth: int) -> str:
    return "../" * depth


def absolute_url(*parts: str) -> str:
    path = "/" + "/".join(part.strip("/") for part in parts if part) + "/"
    return DOMAIN + quote(path, safe="/")


def asset_absolute(path: str) -> str:
    return DOMAIN + "/" + quote(path.lstrip("/"), safe="/")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def enrich_center_rows(rows: list[dict[str, str]]) -> None:
    """Join only verified, non-conflicting operational facts to center rows."""
    education_rows = read_csv(COMMON / "EducationalOrganization.csv")
    education_by_local = {
        compact_text(item.get("서비스 제공 지역")): item
        for item in education_rows
    }
    locals_in_rows = {
        compact_text(row.get("근처 수업가능 동네")) for row in rows
    }
    if len(education_rows) != 371 or set(education_by_local) != locals_in_rows:
        raise ValueError("EducationalOrganization/center locality mismatch")

    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        local = compact_text(row.get("근처 수업가능 동네"))
        education = education_by_local[local]
        center = compact_text(row.get("센터명"))
        address = compact_text(row.get("센터 주소"))
        if compact_text(education.get("실제 센터명")) != center:
            raise ValueError(f"{local}: center name mismatch")
        if compact_text(education.get("도로명 주소")) != address:
            raise ValueError(f"{local}: center address mismatch")
        # The source file contains an old shared phone number and another site's
        # URL. Those fields are deliberately not imported.
        row["_운영 시간"] = compact_text(education.get("운영 시간"))
        center_key = compact_text(row.get("교육지원청 등록번호")) or f"{center}|{address}"
        groups[center_key].append(row)

    for group_rows in groups.values():
        service_areas = [
            {
                "region": compact_text(item.get("지역")),
                "district": compact_text(item.get("시or구")),
                "local": compact_text(item.get("근처 수업가능 동네")),
            }
            for item in group_rows
        ]
        for row in group_rows:
            row["_서비스 지역"] = service_areas


def write_preserving_newline(path: Path, source: str) -> None:
    existing = path.read_bytes() if path.exists() else b""
    newline = "\r\n" if b"\r\n" in existing else "\n"
    normalized = source.replace("\r\n", "\n")
    path.write_text(
        normalized.replace("\n", newline),
        encoding="utf-8",
        newline="",
    )


def parse_sections(text: str) -> dict[str, str]:
    marker = re.compile(r"^\[([^\]]+)\]\s*$", re.MULTILINE)
    matches = list(marker.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip()] = text[match.end() : end].strip()
    return sections


def parse_body(body: str) -> tuple[str, list[tuple[str, list[str]]]]:
    heading = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
    matches = list(heading.finditer(body))
    intro = body[: matches[0].start()].strip() if matches else body.strip()
    sections: list[tuple[str, list[str]]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        content = body[match.end() : end].strip()
        paragraphs = [
            re.sub(r"\s*\n\s*", " ", part.strip())
            for part in re.split(r"\n\s*\n", content)
            if part.strip()
        ]
        sections.append((match.group(1).strip(), paragraphs))
    return re.sub(r"\s*\n\s*", " ", intro), sections


def parse_faq(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(
        r"^Q(?:\d+)?\.\s*(.+?)\s*\n"
        r"(?:A(?:\d+)?\.\s*)?(.+?)"
        r"(?=\n\s*Q(?:\d+)?\.|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    return [
        (
            re.sub(r"\s+", " ", question).strip(),
            re.sub(r"\s+", " ", answer).strip(),
        )
        for question, answer in pattern.findall(text)
    ]


def parse_review(text: str) -> tuple[str, list[str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "", []
    note = lines[0] if lines[0].startswith("※") else ""
    source = lines[1:] if note else lines
    reviews = [
        line.lstrip("-• ").strip().replace("“", "").replace("”", "").strip('" ')
        for line in source
    ]
    return note, [review for review in reviews if review]


def load_manuscripts() -> list[dict[str, str]]:
    if not ZIP_PATH.exists():
        raise FileNotFoundError(ZIP_PATH)
    manuscripts: list[dict[str, str]] = []
    with ZipFile(ZIP_PATH) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise ValueError(f"ZIP CRC error: {bad_member}")
        for info in archive.infolist():
            if not info.filename.lower().endswith(".txt"):
                continue
            sections = parse_sections(archive.read(info).decode("utf-8-sig"))
            missing = REQUIRED_SECTIONS - sections.keys()
            empty = {name for name in REQUIRED_SECTIONS if not sections.get(name, "").strip()}
            if missing or empty:
                raise ValueError(
                    f"{info.filename}: missing={sorted(missing)} empty={sorted(empty)}"
                )
            if Path(info.filename).stem != sections["페이지타이틀"].strip():
                raise ValueError(f"Filename/title mismatch: {info.filename}")
            manuscripts.append(sections)
    manuscripts.sort(key=lambda item: item["페이지타이틀"])
    if len(manuscripts) != 371:
        raise ValueError(f"Expected 371 manuscripts, found {len(manuscripts)}")
    return manuscripts


def locality_from_title(title: str) -> str:
    suffix = f" {CATEGORY}"
    if not title.endswith(suffix):
        raise ValueError(f"Unexpected title: {title}")
    return title[: -len(suffix)].strip()


def find_map(row: dict[str, str]) -> str:
    maps = SITE / "assets" / "maps"
    bases = unique(
        [
            row.get("동 영어", "").strip(),
            row.get("동 영어", "").strip().replace(" ", "-"),
            row.get("동 영어", "").strip().replace(" ", ""),
            row.get("동 영어", "").strip().replace("_", "-"),
        ]
    )
    for base in bases:
        for extension in (".jpg", ".jpeg", ".png", ".webp"):
            candidate = maps / f"{base}{extension}"
            if candidate.exists():
                return f"assets/maps/{candidate.name}"
    raise FileNotFoundError(f"Map not found: {row.get('근처 수업가능 동네')}")


def representative_paths(count: int) -> list[str]:
    directory = SITE / "assets" / "representative"
    candidates = sorted(
        [
            path
            for path in directory.iterdir()
            if path.is_file()
            and path.suffix.lower() in {".gif", ".jpg", ".jpeg", ".png", ".webp"}
        ],
        key=lambda path: path.name,
    )
    deduplicated: list[Path] = []
    digests: set[str] = set()
    for path in candidates:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in digests:
            continue
        digests.add(digest)
        deduplicated.append(path)
    # 공통 이미지 폴더에는 파일명은 다르지만 내용이 같은 이미지가 소수 있습니다.
    # 371개 페이지에 서로 다른 파일 경로를 배정하는 것을 우선하고, 내용이 고유한
    # 파일이 충분할 때만 해시 중복 제거 목록을 사용합니다.
    source = deduplicated if len(deduplicated) >= count else candidates
    if len(source) < count:
        raise ValueError(f"Representative images: {len(source)} < required {count}")
    random.Random("coaching-center-korean-english-math-2026").shuffle(source)
    return [
        f"assets/representative/{path.name}" for path in source[:count]
    ]


def schools_for(row: dict[str, str]) -> dict[str, list[str]]:
    return {
        "초등": split_items(row.get("타깃학교\n(초)", "")),
        "중등": split_items(row.get("타깃학교\n(중)", "")),
        "고등": split_items(row.get("타깃학교\n(고)", "")),
    }


def grades_for(row: dict[str, str]) -> dict[str, list[str]]:
    return {
        "국어": split_items(row.get("가능학년\n(국어)", "")),
        "영어": split_items(row.get("가능학년\n(영어)", "")),
        "수학": split_items(row.get("가능학년\n(수학)", "")),
    }


def nav_html(depth: int, active: str) -> str:
    prefix = rel_prefix(depth)
    links = [
        ("홈", f"{prefix}index.html"),
        ("학습가이드", f"{prefix}학습가이드/index.html"),
        ("상담문의", f"{prefix}상담문의/index.html"),
        ("전국학원", f"{prefix}전국학원/index.html"),
        ("과목별학원", f"{prefix}과목별학원/index.html"),
    ]
    items = "\n".join(
        f'        <a{" class=\"active\"" if name == active else ""} '
        f'href="{href}">{name}</a>'
        for name, href in links
    )
    return f"""  <header class="nav-wrap">
    <nav class="nav" aria-label="주요 메뉴">
      <a class="brand" href="{prefix}index.html"><span class="brand-mark">C</span><span>{SITE_NAME}</span></a>
      <div class="nav-links">
{items}
      </div>
    </nav>
  </header>"""


def footer_html(depth: int) -> str:
    prefix = rel_prefix(depth)
    return f"""  <footer class="footer">
    <p><strong>{SITE_NAME}</strong> · 국어·영어·수학 학습관리 코칭 · 센터별 실제 수업 과목과 학년은 상담 시 확인해 주세요.</p>
  </footer>

  <div class="floating-cta" aria-label="빠른 상담 버튼">
    <a href="tel:{PHONE_DISPLAY}">전화문의</a>
    <a href="sms:{PHONE_LINK}">문자문의</a>
    <a href="{prefix}상담문의/index.html">상담문의</a>
  </div>"""


def head_html(
    title: str,
    description: str,
    depth: int,
    canonical: str,
    image: str,
    graph: dict,
    *,
    og_type: str = "article",
    directory: bool = False,
) -> str:
    prefix = rel_prefix(depth)
    directory_script = (
        f'\n  <script defer src="{prefix}assets/directory.js?v={ASSET_VERSION}"></script>'
        if directory
        else ""
    )
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
  <link rel="icon" type="image/png" href="{prefix}assets/favicon.png">
  <link rel="apple-touch-icon" href="{prefix}assets/favicon.png">
  <link rel="stylesheet" href="{prefix}assets/site.css?v={ASSET_VERSION}">{directory_script}
  <script type="application/ld+json">{json_script(graph)}</script>
</head>"""


def page_shell(head: str, body: str, body_class: str) -> str:
    return f"""{head}
<body class="{body_class}">
<div class="site-shell">
{body}
</div>
</body>
</html>
"""


def offers_for(
    row: dict[str, str],
    local: str,
    canonical: str,
    org_id: str,
    place_id: str,
) -> list[dict]:
    fee_url = row.get("센터 교습비", "").strip()
    grade_map = grades_for(row)
    offers: list[dict] = []
    for subject in ("국어", "영어", "수학"):
        subject_grades = grade_map.get(subject, [])
        audience_type = (
            " · ".join(subject_grades) + f" {subject} 학습 대상"
            if subject_grades
            else f"{subject} 수업 가능 학년 상담 확인"
        )
        offer = {
            "@type": "Offer",
            "@id": canonical + f"#offer-{quote(subject)}",
            "name": f"{local} {subject} 학습관리 상담",
            "url": canonical,
            "itemOffered": {
                "@type": "Service",
                "@id": canonical + f"#service-{quote(subject)}",
                "name": f"{local} {subject} 학습관리",
                "serviceType": "TutoringService",
                "provider": {"@id": org_id},
                "areaServed": {"@id": place_id},
                "audience": {
                    "@type": "EducationalAudience",
                    "educationalRole": "student",
                    "audienceType": audience_type,
                },
            },
        }
        if fee_url:
            offer["subjectOf"] = {
                "@type": "DigitalDocument",
                "name": "센터 교습비 안내",
                "url": fee_url,
            }
        offers.append(offer)
    return offers


def build_graph(
    sections: dict[str, str],
    row: dict[str, str],
    representative: str,
    center_image: str,
    map_image: str,
    faqs: list[tuple[str, str]],
    headings: list[str],
    related: list[tuple[str, str]],
) -> dict:
    title = sections["페이지타이틀"].strip()
    local = locality_from_title(title)
    slug = slug_ko(local)
    canonical = absolute_url(PARENT, CATEGORY, slug)
    parent_url = absolute_url(PARENT)
    category_url = absolute_url(PARENT, CATEGORY)
    region = compact_text(row.get("지역"))
    district = compact_text(row.get("시or구"))
    center = compact_text(row.get("센터명")) or f"{local} 학습센터"
    address = compact_text(row.get("센터 주소"))
    identifier = compact_text(row.get("교육지원청 등록번호"))
    education_name = compact_text(row.get("교육지원청명칭"))
    opening_hours = compact_text(row.get("_운영 시간")) or "12시-24시"
    org_id = stable_id("academy", center, address, identifier)
    region_id = place_id_for(region)
    district_id = place_id_for(region, district)
    place_id = place_id_for(region, district, local)
    publisher_id = DOMAIN + "/#organization"
    website_id = DOMAIN + "/#website"
    webpage_id = canonical + "#webpage"
    article_id = canonical + "#article"
    service_id = canonical + "#service"
    catalog_id = canonical + "#offer-catalog"
    breadcrumb_id = canonical + "#breadcrumb"
    image_id = canonical + "#primaryimage"
    faq_id = canonical + "#faq"
    school_list_id = canonical + "#school-reference"
    related_list_id = canonical + "#related-pages"
    schools = schools_for(row)
    school_names = unique([school for items in schools.values() for school in items])
    grades = grades_for(row)
    educational_levels = unique(
        [grade for items in grades.values() for grade in items]
    )
    json_summary = re.sub(r"\s+", " ", sections["JSON-LD 요약"]).strip()
    description = re.sub(r"\s+", " ", sections["메타설명"]).strip()
    center_image_url = asset_absolute(center_image)
    map_image_url = asset_absolute(map_image)
    offers = offers_for(row, local, canonical, org_id, place_id)
    offer_refs = [{"@id": offer["@id"]} for offer in offers]

    topic_about = [
        {"@type": "Thing", "name": title},
        {"@type": "Thing", "name": "국영수학원"},
        {"@type": "Thing", "name": "국어 학습관리"},
        {"@type": "Thing", "name": "영어 학습관리"},
        {"@type": "Thing", "name": "수학 학습관리"},
        {"@type": "Thing", "name": "학교 시험 대비"},
        {"@type": "Thing", "name": "오답 재학습"},
    ]
    mentions = [
        {"@id": region_id},
        {"@id": district_id},
        {"@id": place_id},
    ] + [{"@type": "School", "name": school} for school in school_names]

    address_data = {
        "@type": "PostalAddress",
        "streetAddress": address,
        "addressRegion": region,
        "addressLocality": district,
        "addressCountry": "KR",
    }
    service_areas = row.get("_서비스 지역") or [
        {"region": region, "district": district, "local": local}
    ]
    area_refs = [
        {
            "@id": place_id_for(
                compact_text(area.get("region")),
                compact_text(area.get("district")),
                compact_text(area.get("local")),
            )
        }
        for area in service_areas
    ]
    organization = {
        "@type": ["EducationalOrganization", "LocalBusiness"],
        "@id": org_id,
        "name": center,
        "telephone": PHONE_DISPLAY,
        "description": json_summary,
        "address": address_data,
        "areaServed": area_refs,
        "openingHours": "Mo-Sa 12:00-23:59",
        "openingHoursSpecification": [
            {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": [
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                ],
                "opens": "12:00",
                "closes": "23:59",
            }
        ],
        "image": [center_image_url, map_image_url],
        "hasMap": map_image_url,
        "knowsAbout": [
            "국어 교과서·문법·독서 학습",
            "영어 어휘·문법·독해 학습",
            "수학 개념·유형·서술형 학습",
            "학습 플래너",
            "오답 재학습",
        ],
        "makesOffer": offer_refs,
        "hasOfferCatalog": {"@id": catalog_id},
        "mainEntityOfPage": {"@id": webpage_id},
        "subjectOf": [{"@id": webpage_id}, {"@id": article_id}],
    }
    if identifier:
        organization["identifier"] = {
            "@type": "PropertyValue",
            "propertyID": "교육지원청 등록번호",
            "value": identifier,
        }
    if education_name:
        organization["additionalProperty"] = {
            "@type": "PropertyValue",
            "propertyID": "교육지원청 등록 명칭",
            "value": education_name,
        }

    webpage = {
        "@type": "WebPage",
        "@id": webpage_id,
        "url": canonical,
        "name": title,
        "description": description,
        "abstract": json_summary,
        "inLanguage": "ko-KR",
        "isPartOf": [
            {"@id": website_id},
            {"@id": category_url + "#collection"},
        ],
        "breadcrumb": {"@id": breadcrumb_id},
        "primaryImageOfPage": {"@id": image_id},
        "mainEntity": [{"@id": org_id}, {"@id": service_id}],
        "about": [{"@id": service_id}, {"@id": org_id}, *topic_about],
        "mentions": mentions,
        "hasPart": [
            {"@id": article_id},
            {"@id": faq_id},
            {"@id": related_list_id},
            {"@id": canonical + "#quick-summary"},
            {"@id": canonical + "#center-information"},
            {"@id": canonical + "#consultation-example"},
        ]
        + [
            {"@id": canonical + f"#section-{index:02d}"}
            for index, _ in enumerate(headings, 1)
        ]
        + ([{"@id": school_list_id}] if school_names else []),
    }

    breadcrumb = {
        "@type": "BreadcrumbList",
        "@id": breadcrumb_id,
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "홈",
                "item": DOMAIN + "/",
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": PARENT,
                "item": parent_url,
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": CATEGORY,
                "item": category_url,
            },
            {
                "@type": "ListItem",
                "position": 4,
                "name": local,
                "item": canonical,
            },
        ],
    }

    article = {
        "@type": "Article",
        "@id": article_id,
        "mainEntityOfPage": {"@id": webpage_id},
        "headline": title,
        "description": description,
        "abstract": json_summary,
        "inLanguage": "ko-KR",
        "articleSection": [CATEGORY, region, district, local, *headings],
        "about": [{"@id": service_id}, {"@id": place_id}, *topic_about],
        "mentions": mentions,
        "hasPart": [
            {"@id": canonical + f"#section-{index:02d}"}
            for index, _ in enumerate(headings, 1)
        ],
        "publisher": {"@id": publisher_id},
        "author": {"@id": publisher_id},
        "datePublished": PUBLISHED_DATE,
        "dateModified": UPDATED_AT,
        "image": [center_image_url, map_image_url],
        "educationalLevel": educational_levels,
    }

    service = {
        "@type": "Service",
        "@id": service_id,
        "name": f"{title} 학습관리",
        "serviceType": "TutoringService",
        "provider": {"@id": org_id},
        "areaServed": {"@id": place_id},
        "description": description,
        "audience": {
            "@type": "EducationalAudience",
            "educationalRole": "student",
            "audienceType": (
                " · ".join(educational_levels) + " 국어·영어·수학 학습 대상"
                if educational_levels
                else "초등·중등·고등 국어·영어·수학 학습 대상"
            ),
        },
        "about": topic_about,
        "mentions": mentions,
        "offers": offer_refs,
        "hasOfferCatalog": {"@id": catalog_id},
        "subjectOf": [{"@id": webpage_id}, {"@id": article_id}],
    }

    faq_page = {
        "@type": "FAQPage",
        "@id": faq_id,
        "isPartOf": {"@id": webpage_id},
        "mainEntity": [
            {
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {"@type": "Answer", "text": answer},
            }
            for question, answer in faqs
        ],
    }

    item_lists = []
    if school_names:
        item_lists.append(
            {
            "@type": "ItemList",
            "@id": school_list_id,
            "name": f"{title} 제공 학교 참고",
            "isPartOf": {"@id": webpage_id},
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": index,
                    "name": school,
                }
                for index, school in enumerate(school_names, 1)
            ],
            }
        )
    item_lists.append(
        {
            "@type": "ItemList",
            "@id": related_list_id,
            "name": f"{title} 관련 내부링크",
            "isPartOf": {"@id": webpage_id},
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": index,
                    "name": name,
                    "url": url,
                }
                for index, (name, url) in enumerate(related, 1)
            ],
        }
    )

    places_by_id: dict[str, dict] = {}
    for area in service_areas:
        area_region = compact_text(area.get("region"))
        area_district = compact_text(area.get("district"))
        area_local = compact_text(area.get("local"))
        area_region_id = place_id_for(area_region)
        area_district_id = place_id_for(area_region, area_district)
        area_local_id = place_id_for(area_region, area_district, area_local)
        places_by_id[area_region_id] = {
            "@type": "AdministrativeArea",
            "@id": area_region_id,
            "name": area_region,
        }
        places_by_id[area_district_id] = {
            "@type": "AdministrativeArea",
            "@id": area_district_id,
            "name": area_district,
            "containedInPlace": {"@id": area_region_id},
        }
        places_by_id[area_local_id] = {
            "@type": "Place",
            "@id": area_local_id,
            "name": area_local,
            "containedInPlace": {"@id": area_district_id},
        }
    places = list(places_by_id.values())
    web_elements = [
        {
            "@type": "WebPageElement",
            "@id": canonical + f"#section-{index:02d}",
            "name": heading,
            "position": index,
            "isPartOf": {"@id": article_id},
        }
        for index, heading in enumerate(headings, 1)
    ] + [
        {
            "@type": "WebPageElement",
            "@id": canonical + "#quick-summary",
            "name": f"{title} 30초 핵심 안내",
            "isPartOf": {"@id": webpage_id},
        },
        {
            "@type": "WebPageElement",
            "@id": canonical + "#center-information",
            "name": f"{center} 센터 기준 정보",
            "isPartOf": {"@id": webpage_id},
        },
        {
            "@type": "WebPageElement",
            "@id": canonical + "#consultation-example",
            "name": f"{local} 학부모 상담 상황 예시",
            "isPartOf": {"@id": webpage_id},
        },
    ]
    offer_catalog = {
        "@type": "OfferCatalog",
        "@id": catalog_id,
        "name": f"{local} 국어·영어·수학 학습관리",
        "itemListElement": offers,
    }
    publisher = {
        "@type": "Organization",
        "@id": publisher_id,
        "name": SITE_NAME,
        "url": DOMAIN + "/",
        "telephone": "+82-10-6839-8283",
    }
    website = {
        "@type": "WebSite",
        "@id": website_id,
        "url": DOMAIN + "/",
        "name": SITE_NAME,
        "inLanguage": "ko-KR",
        "publisher": {"@id": publisher_id},
    }

    return {
        "@context": "https://schema.org",
        "@graph": [
            organization,
            publisher,
            website,
            webpage,
            {
                "@type": "ImageObject",
                "@id": image_id,
                "url": center_image_url,
                "contentUrl": center_image_url,
                "caption": f"{title} {SITE_NAME} 본문 학습 안내",
            },
            breadcrumb,
            article,
            service,
            offer_catalog,
            faq_page,
            *places,
            *web_elements,
            *item_lists,
        ],
    }


def paragraph_html(value: str) -> str:
    return f"<p>{esc(re.sub(r'\\s*\\n\\s*', ' ', value.strip()))}</p>"


def grade_cards(row: dict[str, str]) -> str:
    cards = []
    for subject, grades in grades_for(row).items():
        value = " · ".join(grades) if grades else "상담 시 가능 학년 확인"
        cards.append(
            '<article class="subject-info-card">'
            f"<span>{esc(subject)}</span><h3>{esc(subject)} 수업 가능 학년</h3>"
            f"<p>{esc(value)}</p></article>"
        )
    return "".join(cards)


def school_cards(row: dict[str, str]) -> str:
    cards = []
    for level, schools in schools_for(row).items():
        if not schools:
            continue
        cards.append(
            '<article class="school-card">'
            f"<span>{esc(level)}</span><h3>{esc(level)} 학교 참고</h3>"
            f"<p>{esc(' · '.join(schools))}</p></article>"
        )
    if cards:
        return "".join(cards)
    return (
        '<article class="school-card"><span>학교별 내신</span>'
        "<h3>상담 시 학습 범위 확인</h3>"
        "<p>학교별 교재와 시험 범위는 최근 범위표·평가 자료를 준비해 학생의 현재 학년과 함께 확인하는 것이 좋습니다.</p></article>"
    )


def related_for(
    row: dict[str, str], rows: list[dict[str, str]]
) -> list[tuple[str, str, str]]:
    local = row["근처 수업가능 동네"].strip()
    district = row.get("시or구", "").strip()
    region = row.get("지역", "").strip()
    source = [
        item
        for item in rows
        if item.get("시or구", "").strip() == district
        and item["근처 수업가능 동네"].strip() != local
    ]
    if len(source) < 6:
        source.extend(
            item
            for item in rows
            if item.get("지역", "").strip() == region
            and item["근처 수업가능 동네"].strip() != local
        )
    result: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for item in source:
        name = item["근처 수업가능 동네"].strip()
        if not name or name in seen:
            continue
        seen.add(name)
        result.append(
            (
                f"{name} {CATEGORY}",
                absolute_url(PARENT, CATEGORY, slug_ko(name)),
                compact_text(item.get("시or구"))
                or compact_text(item.get("지역"))
                or "다른 지역",
            )
        )
        if len(result) == 6:
            break
    return result


def render_detail(
    sections: dict[str, str],
    row: dict[str, str],
    representative: str,
    rows: list[dict[str, str]],
) -> str:
    title = sections["페이지타이틀"].strip()
    local = locality_from_title(title)
    slug = slug_ko(local)
    region = compact_text(row.get("지역"))
    district = compact_text(row.get("시or구"))
    center = compact_text(row.get("센터명")) or f"{local} 학습센터"
    address = compact_text(row.get("센터 주소"))
    registration = compact_text(row.get("교육지원청 등록번호"))
    education_name = compact_text(row.get("교육지원청명칭"))
    fee_url = row.get("센터 교습비", "").strip()
    opening_hours = compact_text(row.get("_운영 시간")) or "12시-24시"
    location_guide = compact_text(row.get("위치안내"))
    (
        prepared_sections,
        intro,
        manuscript_sections,
        faqs,
        review_note,
        review_items,
    ) = prepare_detail_copy(sections, row)
    meta = prepared_sections["메타설명"]
    if len(manuscript_sections) != 6:
        raise ValueError(f"{title}: expected 6 H2 sections")
    if len(faqs) != 5:
        raise ValueError(f"{title}: expected 5 FAQ entries")
    if not review_items:
        raise ValueError(f"{title}: consultation example missing")

    center_image = (
        "assets/centers/common/seoul6839.webp"
        if region == "서울"
        else "assets/centers/common/local6839.webp"
    )
    map_image = find_map(row)
    canonical = absolute_url(PARENT, CATEGORY, slug)
    related_local = related_for(row, rows)
    related = [
        (f"{CATEGORY} 전체 지역", absolute_url(PARENT, CATEGORY)),
        (PARENT, absolute_url(PARENT)),
        (
            f"{local} 고등수학학원",
            absolute_url("전국학원", "고등수학학원", slug),
        ),
        (
            f"{local} 고등영어학원",
            absolute_url("전국학원", "고등영어학원", slug),
        ),
        (
            f"{local} 고등영수학원",
            absolute_url("전국학원", "고등영수학원", slug),
        ),
        *[(name, url) for name, url, _ in related_local],
    ]
    graph = build_graph(
        prepared_sections,
        row,
        representative,
        center_image,
        map_image,
        faqs,
        [heading for heading, _ in manuscript_sections],
        related,
    )
    head = head_html(
        f"{title} | {SITE_NAME}",
        meta,
        3,
        canonical,
        asset_absolute(representative),
        graph,
    )
    representative_rel = "../../../" + representative
    center_rel = "../../../" + center_image
    map_rel = "../../../" + map_image

    prose = "".join(
        f'<section class="manuscript-section" id="section-{index:02d}">'
        f'<div class="manuscript-heading"><span>{index:02d}</span>'
        f"<h2>{esc(heading)}</h2></div>"
        + "".join(paragraph_html(paragraph) for paragraph in paragraphs)
        + "</section>"
        for index, (heading, paragraphs) in enumerate(manuscript_sections, 1)
    )
    faq_html = "".join(
        f'<details class="faq-item"{" open" if index == 0 else ""}>'
        f"<summary>{esc(question)}</summary><p>{esc(answer)}</p></details>"
        for index, (question, answer) in enumerate(faqs)
    )
    review_html = "".join(
        f"<blockquote>{esc(review)}</blockquote>" for review in review_items
    )
    nearby_links = "".join(
        f'<a href="{esc(url)}"><strong>{esc(name)}</strong>'
        f"<small>{esc(target_area)} 학습 안내</small></a>"
        for name, url, target_area in related_local
    )
    grade_html = grade_cards(row)
    school_html = school_cards(row)
    fee_html = (
        f'<a class="center-fee-link" href="{esc(fee_url)}" target="_blank" '
        'rel="noopener noreferrer">센터 교습비 안내 확인 <span>↗</span></a>'
        if fee_url
        else "<p>교습비는 상담 시 과목과 학년 구성에 따라 확인합니다.</p>"
    )
    route_html = (
        '<div class="map-route-note"><strong>찾아오는 기준</strong>'
        f"<p>{esc(location_guide)}</p></div>"
        if location_guide
        else ""
    )
    updated_label = TODAY.replace("-", ".")

    body = f"""{nav_html(3, PARENT)}
  <main>
    <section class="academy-hero">
      <div class="academy-hero-main">
        <nav class="breadcrumb" aria-label="breadcrumb">
          <a href="../../../index.html">홈</a><span>›</span>
          <a href="../../index.html">{PARENT}</a><span>›</span>
          <a href="../index.html">{CATEGORY}</a><span>›</span><span>{esc(local)}</span>
        </nav>
        <p class="eyebrow">KOREAN · ENGLISH · MATH LOCAL GUIDE</p>
        <h1>{esc(title)}</h1>
        <p>{esc(meta)}</p>
        <div class="academy-badges">
          <span>{esc(region)}</span><span>{esc(district)}</span>
          <span>국어</span><span>영어</span><span>수학</span>
        </div>
      </div>
      <aside class="academy-side-card">
        <div>
          <p class="eyebrow">상담 핵심</p>
          <strong>세 과목의 약점은 따로 진단하고, 실행 계획은 하나로 연결합니다.</strong>
          <p>{esc(local)} 학생의 최근 시험지·교재·학교 일정·학습 습관을 함께 확인해 과목별 우선순위를 정리합니다.</p>
        </div>
        <div class="hero-actions">
          <a class="btn btn-primary" href="tel:{PHONE_DISPLAY}">전화 상담하기</a>
          <a class="btn btn-ghost" href="../../../상담문의/index.html">상담문의</a>
        </div>
      </aside>
    </section>

    <section class="section subject-quick-section" id="quick-summary">
      <div class="section-panel subject-quick-panel">
        <div class="section-title">
          <p class="eyebrow">30초 핵심 안내</p>
          <h2>{esc(title)} 상담 전 먼저 확인할 내용</h2>
        </div>
        <div class="subject-quick-answer"><p>{esc(intro)}</p></div>
        <p class="service-area-clarifier"><strong>{esc(local)}은 수업 가능 생활권 기준입니다.</strong> 실제 방문 센터는 {esc(center)}이며, 주소와 등록 정보는 아래 센터 기준 정보에서 확인할 수 있습니다.</p>
        <div class="subject-info-grid">{grade_html}</div>
      </div>
    </section>

    <section class="local-media-section subject-media-section">
      <img src="{esc(representative_rel)}" alt="{esc(title + ' ' + SITE_NAME + ' 대표')}" style="display:none;">
      <figure class="local-media-card">
        <img src="{esc(center_rel)}" width="918" height="16116" decoding="async" alt="{esc(title + ' 본문 ' + SITE_NAME)}">
      </figure>
      <figure class="local-map-card">
        <img src="{esc(map_rel)}" loading="lazy" decoding="async" alt="{esc(title + ' 지도 ' + SITE_NAME)}">
        <figcaption>{esc(region)} {esc(district)} {esc(local)}에서 국어·영어·수학 상담을 준비할 때 센터 위치와 실제 이동 동선을 함께 확인해 주세요.</figcaption>
        {route_html}
      </figure>
    </section>

    <section class="section" id="center-information">
      <div class="section-panel center-facts-panel">
        <div class="section-title">
          <p class="eyebrow">센터 기준 정보</p>
          <h2>{esc(center)} 안내</h2>
          <p>센터명·주소·등록 정보와 교습비 확인 경로를 상담 전에 살펴볼 수 있도록 정리했습니다.</p>
        </div>
        <div class="center-facts-grid">
          <article><span>센터명</span><strong>{esc(center)}</strong><p>{esc(region)} {esc(district)} {esc(local)} 상담 기준</p></article>
          <article><span>주소</span><strong>센터 위치</strong><p>{esc(address) if address else "상담 시 위치 확인"}</p></article>
          <article><span>등록 정보</span><strong>{esc(education_name) if education_name else "교육지원청 등록 정보"}</strong><p>{esc(registration) if registration else "상담 시 등록 정보 확인"}</p></article>
          <article><span>교습비</span><strong>센터별 수강료 자료</strong>{fee_html}</article>
          <article><span>운영 시간</span><strong>{esc(opening_hours)}</strong><p>실제 수업 가능 시간은 학년·과목별 일정에 따라 상담에서 확인합니다.</p></article>
          <article><span>안내 생활권</span><strong>{esc(region)} {esc(district)} {esc(local)}</strong><p>동네명은 수업 가능 지역을 찾기 위한 안내 기준입니다.</p></article>
        </div>
        <div class="school-grid subject-school-grid" id="school-reference">{school_html}</div>
        <div class="information-basis">
          <div><span>정보 정리</span><strong>{SITE_NAME}</strong></div>
          <div><span>페이지 최초 작성</span><time datetime="{PUBLISHED_DATE}">2026.07.24</time></div>
          <div><span>최근 내용 정리</span><time datetime="{UPDATED_AT}">{updated_label}</time></div>
          <p>센터명·주소·등록번호·가능 학년·학교 참고 정보는 제공된 센터 자료를 기준으로 정리했으며, 실제 수업 범위와 일정은 상담에서 다시 확인합니다.</p>
        </div>
      </div>
    </section>

    <section class="section" id="article">
      <div class="section-panel manuscript-panel">
        <div class="section-title manuscript-title">
          <p class="eyebrow">지역별 학습 안내</p>
          <h2>{esc(title)} 선택과 학습관리 기준</h2>
          <p>학생의 과목별 학습 상황과 상담 전에 확인할 기준을 여섯 가지 주제로 나누어 정리했습니다.</p>
        </div>
        <article class="manuscript-article">
          {prose}
        </article>
      </div>
    </section>

    <section class="section" id="faq">
      <div class="section-panel">
        <div class="section-title">
          <p class="eyebrow">FAQ</p>
          <h2>{esc(title)} 자주 묻는 질문</h2>
        </div>
        <div class="faq-list">{faq_html}</div>
      </div>
    </section>

    <section class="section" id="consultation-example">
      <div class="section-panel consultation-example-panel">
        <div class="section-title">
          <p class="eyebrow">상담 상황 예시</p>
          <h2>{esc(local)} 학부모가 확인한 학원 선택 기준</h2>
        </div>
        <p class="consultation-example-note">{esc(review_note)}</p>
        <div class="consultation-example-copy">{review_html}</div>
      </div>
    </section>

    <section class="section" id="related-pages">
      <div class="section-panel">
        <div class="internal-links">
          <div class="directory-head">
            <h2>{esc(local)} 관련 학습 페이지</h2>
            <p>과목별 허브와 같은 동네의 기존 학습 페이지, 같은 시군구와 광역권의 국영수학원 안내를 함께 정리했습니다.</p>
          </div>
          <div class="subject-switch-grid">
            <a href="../index.html"><strong>{CATEGORY} 전체</strong><small>371개 지역 허브</small></a>
            <a href="../../index.html"><strong>{PARENT}</strong><small>과목별 전체 허브</small></a>
            <a href="/전국학원/고등수학학원/{esc(slug)}/"><strong>{esc(local)} 고등수학학원</strong><small>수학 학습관리</small></a>
            <a href="/전국학원/고등영어학원/{esc(slug)}/"><strong>{esc(local)} 고등영어학원</strong><small>영어 학습관리</small></a>
            <a href="/전국학원/고등영수학원/{esc(slug)}/"><strong>{esc(local)} 고등영수학원</strong><small>영어·수학 학습관리</small></a>
          </div>
          <div class="related-grid subject-nearby-grid">{nearby_links}</div>
        </div>
      </div>
    </section>
  </main>
{footer_html(3)}"""
    return page_shell(
        head,
        body,
        "core-page academy-page nationwide-page nationwide-detail-page subject-detail-page",
    )


def collection_graph(
    name: str,
    description: str,
    canonical: str,
    breadcrumbs: list[tuple[str, str]],
    items: list[tuple[str, str]],
) -> dict:
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": canonical + "#collection",
                "url": canonical,
                "name": name,
                "description": description,
                "inLanguage": "ko-KR",
                "dateModified": UPDATED_AT,
                "isPartOf": {"@id": DOMAIN + "/#website"},
                "breadcrumb": {"@id": canonical + "#breadcrumb"},
                "mainEntity": {"@id": canonical + "#itemlist"},
                "hasPart": [
                    {
                        "@type": "WebPage",
                        "@id": item_url + "#webpage",
                        "name": item_name,
                        "url": item_url,
                    }
                    for item_name, item_url in items
                ],
            },
            {
                "@type": "BreadcrumbList",
                "@id": canonical + "#breadcrumb",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": index,
                        "name": crumb_name,
                        "item": crumb_url,
                    }
                    for index, (crumb_name, crumb_url) in enumerate(breadcrumbs, 1)
                ],
            },
            {
                "@type": "ItemList",
                "@id": canonical + "#itemlist",
                "name": f"{name} 목록",
                "numberOfItems": len(items),
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": index,
                        "item": {
                            "@id": item_url + "#webpage",
                            "name": item_name,
                            "url": item_url,
                        },
                    }
                    for index, (item_name, item_url) in enumerate(items, 1)
                ],
            },
            {
                "@type": "Organization",
                "@id": DOMAIN + "/#organization",
                "name": SITE_NAME,
                "url": DOMAIN + "/",
                "telephone": "+82-10-6839-8283",
            },
            {
                "@type": "WebSite",
                "@id": DOMAIN + "/#website",
                "url": DOMAIN + "/",
                "name": SITE_NAME,
                "inLanguage": "ko-KR",
                "publisher": {"@id": DOMAIN + "/#organization"},
            },
        ],
    }


def render_parent_hub() -> str:
    canonical = absolute_url(PARENT)
    category_url = absolute_url(PARENT, CATEGORY)
    description = (
        "과목 구성별로 전국 지역 학습 안내를 찾는 허브입니다. 국어·영어·수학을 함께 "
        "점검하는 국영수학원 371개 지역 페이지로 이동할 수 있습니다."
    )
    graph = collection_graph(
        PARENT,
        description,
        canonical,
        [("홈", DOMAIN + "/"), (PARENT, canonical)],
        [(CATEGORY, category_url)],
    )
    head = head_html(
        f"{PARENT} | {SITE_NAME}",
        description,
        1,
        canonical,
        asset_absolute("assets/generated/coaching-center-hero-v2.webp"),
        graph,
        og_type="website",
    )
    body = f"""{nav_html(1, PARENT)}
  <main>
    <section class="academy-hero">
      <div class="academy-hero-main">
        <nav class="breadcrumb" aria-label="breadcrumb"><a href="../index.html">홈</a><span>›</span><span>{PARENT}</span></nav>
        <p class="eyebrow">SUBJECT ACADEMY HUB</p>
        <h1>{PARENT}</h1>
        <p>{esc(description)}</p>
        <ul class="academy-route">
          <li><span>1</span>과목 구성을 선택합니다.</li>
          <li><span>2</span>지역 검색 또는 광역·시군구 목록으로 동네를 찾습니다.</li>
          <li><span>3</span>센터 정보와 원고를 읽고 상담 기준을 확인합니다.</li>
        </ul>
      </div>
      <aside class="academy-side-card">
        <div><p class="eyebrow">현재 카테고리</p><strong>국어·영어·수학을 함께 보는 학습관리</strong><p>과목별 약점은 따로 진단하고 주간 실행 계획은 하나로 연결하는 기준을 정리했습니다.</p></div>
      </aside>
    </section>
    <section class="academy-directory subject-parent-directory">
      <div class="directory-head">
        <h2>과목 구성 선택</h2>
        <p>현재 생성된 카테고리만 표시합니다. 각 카드를 누르면 371개 지역 안내와 동네 검색 기능을 이용할 수 있습니다.</p>
      </div>
      <div class="category-grid">
        <a class="category-card subject-category-card" href="{CATEGORY}/index.html">
          <span>국어 · 영어 · 수학</span>
          <strong>{CATEGORY}</strong>
          <small>전국 371개 지역별 학습관리 안내</small>
        </a>
      </div>
    </section>
  </main>
{footer_html(1)}"""
    return page_shell(
        head,
        body,
        "core-page academy-page nationwide-page nationwide-root-page subject-root-page",
    )


def render_category_hub(rows: list[dict[str, str]]) -> str:
    canonical = absolute_url(PARENT, CATEGORY)
    description = (
        "전국 371개 동네별 국영수학원 상담 기준을 정리했습니다. 지역·시군구·동네 검색을 "
        "통해 국어·영어·수학 진단, 학교 시험, 과제와 오답 관리 안내를 확인할 수 있습니다."
    )
    items = [
        (
            f"{row['근처 수업가능 동네'].strip()} {CATEGORY}",
            absolute_url(PARENT, CATEGORY, slug_ko(row["근처 수업가능 동네"])),
        )
        for row in rows
    ]
    graph = collection_graph(
        f"{CATEGORY} 지역 안내",
        description,
        canonical,
        [
            ("홈", DOMAIN + "/"),
            (PARENT, absolute_url(PARENT)),
            (CATEGORY, canonical),
        ],
        items,
    )
    head = head_html(
        f"{CATEGORY} 지역 안내 | {SITE_NAME}",
        description,
        2,
        canonical,
        asset_absolute("assets/generated/coaching-center-hero-v2.webp"),
        graph,
        og_type="website",
        directory=True,
    )
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row.get("지역", "").strip() or "기타"].append(row)
    blocks = []
    for region, region_rows in grouped.items():
        links = "\n".join(
            f'<a href="{slug_ko(row["근처 수업가능 동네"])}/" '
            f'data-district="{esc(row.get("시or구", ""))}">'
            f'<strong>{esc(row["근처 수업가능 동네"])}</strong>'
            f'<small>{esc(row.get("시or구", ""))} 국영수</small></a>'
            for row in region_rows
        )
        blocks.append(
            '<div class="region-block">'
            f'<div class="region-title"><h3>{esc(region)}</h3>'
            f"<span>{len(region_rows)}개 지역</span></div>"
            f'<div class="local-button-grid">{links}</div></div>'
        )
    body = f"""{nav_html(2, PARENT)}
  <main>
    <section class="academy-hero">
      <div class="academy-hero-main">
        <nav class="breadcrumb" aria-label="breadcrumb"><a href="../../index.html">홈</a><span>›</span><a href="../index.html">{PARENT}</a><span>›</span><span>{CATEGORY}</span></nav>
        <p class="eyebrow">KOREAN · ENGLISH · MATH DIRECTORY</p>
        <h1>{CATEGORY}</h1>
        <p>{esc(description)}</p>
      </div>
      <aside class="academy-side-card">
        <div><p class="eyebrow">총 지역</p><strong>{len(rows)}개</strong><p>서울부터 제주까지 광역·시군구·동네 순서로 탐색할 수 있습니다.</p></div>
      </aside>
    </section>
    <section class="academy-directory">
      <div class="directory-head"><h2>지역별 {CATEGORY} 바로가기</h2><p>동네 이름을 검색하거나 광역 지역과 시군구를 순서대로 선택해 해당 지역 안내로 이동하세요.</p></div>
      {"".join(blocks)}
    </section>
  </main>
{footer_html(2)}"""
    return page_shell(
        head,
        body,
        "core-page academy-page directory-page nationwide-page nationwide-category-page subject-category-page",
    )


def update_existing_navigation() -> int:
    updated = 0
    nav_pattern = re.compile(
        r'(<div class="nav-links">)(.*?)(</div>)', re.DOTALL
    )
    nationwide_pattern = re.compile(
        r'(<a(?:\s+class="[^"]*")?\s+href="([^"]*전국학원[^"]*)">전국학원</a>)'
    )
    for path in SITE.glob("**/index.html"):
        if any(part in {".git", ".vercel", "node_modules"} for part in path.parts):
            continue
        source = path.read_text(encoding="utf-8")
        match = nav_pattern.search(source)
        if not match or "과목별학원" in match.group(2):
            continue
        nationwide = nationwide_pattern.search(match.group(2))
        if not nationwide:
            continue
        subject_href = nationwide.group(2).replace("전국학원", "과목별학원")
        replacement = (
            nationwide.group(1)
            + f'\n        <a href="{subject_href}">과목별학원</a>'
        )
        new_nav = nationwide_pattern.sub(replacement, match.group(2), count=1)
        source = source[: match.start(2)] + new_nav + source[match.end(2) :]
        write_preserving_newline(path, source)
        updated += 1
    return updated


def update_stylesheet_versions() -> int:
    updated = 0
    pattern = re.compile(r"(assets/site\.css\?v=)[0-9-]+")
    for path in SITE.glob("**/index.html"):
        if any(part in {".git", ".vercel", "node_modules"} for part in path.parts):
            continue
        source = path.read_text(encoding="utf-8")
        replaced = pattern.sub(rf"\g<1>{ASSET_VERSION}", source)
        if replaced == source:
            continue
        write_preserving_newline(path, replaced)
        updated += 1
    return updated


def update_llms() -> None:
    path = SITE / "llms.txt"
    source = path.read_text(encoding="utf-8")
    lines = [
        f"- 과목별학원: {absolute_url(PARENT)}",
        f"- 국영수학원 지역 목록: {absolute_url(PARENT, CATEGORY)}",
        "- 국영수학원 지역 페이지는 371개 동네별 제공 원고, 센터 주소, 가능 학년, 학교 참고, 교습비와 지도 정보를 포함합니다.",
    ]
    additions = [line for line in lines if line not in source]
    if additions:
        source = source.rstrip() + "\n" + "\n".join(additions) + "\n"
        path.write_text(source, encoding="utf-8", newline="\n")


def main() -> None:
    rows = read_csv(COMMON / "센터정보 정리.csv")
    enrich_center_rows(rows)
    manuscripts = load_manuscripts()
    if len(rows) != 371:
        raise ValueError(f"Expected 371 center rows, found {len(rows)}")
    row_by_local = {
        row["근처 수업가능 동네"].strip(): row
        for row in rows
    }
    manuscript_locals = [
        locality_from_title(sections["페이지타이틀"].strip())
        for sections in manuscripts
    ]
    if len(set(manuscript_locals)) != 371:
        raise ValueError("Duplicate manuscript locality")
    if set(manuscript_locals) != set(row_by_local):
        raise ValueError(
            "Manuscript/center mismatch: "
            f"missing={sorted(set(row_by_local) - set(manuscript_locals))} "
            f"extra={sorted(set(manuscript_locals) - set(row_by_local))}"
        )

    representatives = representative_paths(len(manuscripts))
    target = SITE / PARENT / CATEGORY
    target.mkdir(parents=True, exist_ok=True)
    seen_slugs: set[str] = set()
    for index, sections in enumerate(manuscripts):
        local = locality_from_title(sections["페이지타이틀"].strip())
        slug = slug_ko(local)
        if slug in seen_slugs:
            raise ValueError(f"Duplicate slug: {slug}")
        seen_slugs.add(slug)
        output = target / slug / "index.html"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            render_detail(
                sections,
                row_by_local[local],
                representatives[index],
                rows,
            ),
            encoding="utf-8",
            newline="\n",
        )

    (SITE / PARENT).mkdir(parents=True, exist_ok=True)
    (SITE / PARENT / "index.html").write_text(
        render_parent_hub(),
        encoding="utf-8",
        newline="\n",
    )
    (target / "index.html").write_text(
        render_category_hub(rows),
        encoding="utf-8",
        newline="\n",
    )
    nav_updates = update_existing_navigation()
    stylesheet_updates = update_stylesheet_versions()
    update_llms()
    print(
        json.dumps(
            {
                "detail_pages": len(manuscripts),
                "hubs": 2,
                "navigation_pages_updated": nav_updates,
                "stylesheet_pages_updated": stylesheet_updates,
                "representative_images": len(set(representatives)),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
