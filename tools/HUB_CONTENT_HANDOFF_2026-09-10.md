# 코칭센터.com 허브 보강 — 2026-09-10

## 요청과 범위

- 사용자 요청: 이전 사이트와 같은 허브 내용 보강 및 공개 배포.
- 작업 폴더: 새 홈페이지8. 기존 GitHub 01039578283-hub/new8 → Vercel new8 사용. 도메인·요금제·호스팅 변경 없음.
- 초기 clean HEAD: 29e967bfae4a515c812eb2f9ad6dbe1f217c7c19.
- 대상26: 전국학원 root와 고등수학/고등영어/고등영수3허브, 과목별학원 root와 국영수/보습/소수정예3허브, 초3~초6·중1~중3·고1~고2 영어/수학18허브.
- 기존 동네 HTML8,907개 및 기존 assets763개(이미지758개), 기존 title/H1/canonical/og:url·연락처·디렉터리 링크·검색JS 보존.

## 내용 및 구현

- 주제별 원고: tools/data/hub-guides/subject-copy.json. 실제 학년별 학습 상황을 구분하며 성과·교육과정·지점 운영정책을 임의로 확정하지 않음.
- 센터 자료: tools/data/hub-guides/center-examples.json. 실제 기존 leaf의 주소·등록 정보·과목·학년을 대조한 카탈로그 사용.
- 정확한 학년 포함 여부, 국영수3과목/영수2과목의 동일 학년 교집합을 확인. 원문 제한조건은 별도 표시하고 다른 학년에 한정된 조건을 섞지 않음.
- 새8의 실제 조직ID 보존: 과목별학원 공통 entity-academy ID, 전국학원 고등 카테고리는 실제 해당 페이지 organization ID. 상대형은 동일 도메인으로 절대화.
- 공통 학습공간 사진2개는 기존 검토된 제공 WebP. 특정 지점 내부라고 단정하지 않고 원본 비율 전체 노출, 접기/자르기 없음.
- 기존 dark/navy 디자인 유지, 새 읽기 구간은 밝은 카드/녹색 강조. 제목·본문·검색버튼·빠른이동·하단CTA 모바일 조정.
- 메타 설명/CollectionPage/ItemList/FAQPage/hasPart/mentions와 실제 센터 관계 정리. 허브를 실제 단일 학원으로 오인하지 않도록 사이트 publisher는 Organization.
- 전국학원 고등영수 기존 FAQ3개 블록은 새 주제 FAQ와 공통 안내로 재구성. 동네 본문/후기는 변경하지 않음.
- sitemap 기존8,545 URL 순서·목록 유지 및26개 수정일 갱신. 기존 noindex388개를 추가하지 않음. RSS 기존50개를 보존하고 빠져 있던 전국 고등3허브를 추가해53개.

## 재실행과 기록

- python tools/enrich_top_hubs_site8.py --date YYYY-MM-DD
- python tools/refresh_enriched_hub_discovery.py --modified YYYY-MM-DDTHH:MM:SS+09:00
- 기존 전체 페이지 생성기를 다시 실행한 경우 마지막에 허브 보강 생성기를 실행해야 함. 원고 전체 재생성은 이번 요청 범위가 아님.
- tools/는 .vercelignore로 공개 배포에서 제외. tools/reports/는 로컬 검수·배포 기록용.
- 독립 검수 경로: C:/Users/1992k/Desktop/CodexData/tmp/site8-hub-enrichment-2026-09-10/qa
- 최종 검수·배포 결과는 아래와 tools/reports/hub-enrichment/RELEASE.md에 기록할 것.

## 최종 검수

- 26개 허브의 고유78섹션·156문단·전용FAQ78개, 공통FAQ52개를 합쳐130쌍 반영. 다른 사이트 주제 원고 재사용0.
- 센터32개 카탈로그722개경로/ID쌍검증, 실제 표시78카드·112과목 검증 PASS. 정확학년조건·파닉스/수능/수행 독립조건 회귀27건 PASS.
- 독립 정적 검사715/715 PASS. 대상 외 HTML8,907개·기존assets763개·기존앵커9,212개·디렉터리8,928개 목적지 보존.
- canonical/H1/title/og:url 및 기존 검색JS 유지. FAQ130쌍과JSON-LD 일치, 실제센터ID78쌍·내부참조9,472건 정상.
- CSS 최종 v20260910-2: 26허브 ×320/390/430/900/1280px =130화면에서 가로넘침/작은주요버튼0. PC하단CTA도3열동일폭.
- 모바일 검색대표5개(고2수학/중2영어/초3영어/소수정예/전국고등영수): 명일동1/없는동네0/지우기371건, 모두접기0/펼치기13지역, 목차·FAQ 정상. 과목root FAQ·21개분류카드도확인.
- 긴 전체동작검사 중 브라우저연결시간초과가있어 그 결과는 PASS에 포함하지 않고 대표6개를 개별확인해기록. 전체24개검색동작검증이라고 주장하지 않음.
- 사진2개 실제로딩·원본비율·비접힘 확인. 고2수학 명일동 실제하위페이지이동 확인.
- 같은날짜 재실행 changed=0. 최종파일만선별커밋하고기존GitHub→Vercel배포후정식도메인26개+6리소스+비공개3경로확인할것.
- 실제 배포 결과는 tools/reports/hub-enrichment/RELEASE.md 및 바탕화면 홈페이지 작업 기록.txt에 보관. 검수 PASS는 검색순위 보장이 아님.
