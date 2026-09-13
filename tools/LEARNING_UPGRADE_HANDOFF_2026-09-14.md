# 코칭센터.com 공식 학습 자료 기반 업그레이드

작업일: 2026-09-14 / 기준 커밋: `6840db69e`

## 현재 상태

- 최초 업그레이드는 로컬에서 완료했으며, 이후 **2026-09-14 사용자가 공개 배포를 승인**했다. 검증본을 기존 GitHub → Vercel 자동 배포 경로로 공개한다. 최종 배포 ID·커밋·정식 도메인 검증 결과는 `tools/reports/learning-upgrade/release-receipt.json` 및 바탕화면 작업 기록을 확인할 것.
- 기존 홈페이지는 정적 HTML 저장소다. Sites 프로젝트로 전환하지 않았다.
- 로컬 미리보기: `http://127.0.0.1:8803/` (Python 정적 서버).
- 정식 도메인: `https://코칭센터.com` / `https://xn--zj4b74v1taq8c.com`.

## 변경 범위

총 30페이지: 기존 홈·학습가이드·상담문의 3개, 기존 허브 26개, 신규 `/학습코칭/` 1개.

1. 홈: 새 학습관리 소개와 공식 영어 Daily Checkup 이미지, 4C 요약, AI 역할 구분, 학교급별 내부링크, 브랜드 영상, FAQ.
2. 학습코칭·AI: 브랜드 설명, 4C 네 요소, 계획·학습·생활 관리, AI 영어/수학/국어/독서 대상과 구성, 상담 질문, 공식 영상3개, FAQ.
3. 학습가이드: 진단·학교급·플래너·오답·시험·피드백 섹션 ID와 목차, 관련 학습코칭 안내와 지역·상담 링크.
4. 상담문의: 진단·AI 프로그램·실제 지점 운영을 묻는 질문과 관련 링크. 기존 폼과 전화·SMS 흐름은 보존.
5. 허브26개: 지역·분류 찾기를 긴 설명보다 앞에 배치. 학년·과목별 고유 요약26개/본문52문단, AI·코칭과 일반 학습가이드로 문맥별 연결. 과목별학원 루트의21개 카드를 유형/고등/중등/초등으로 구분.
6. 신규 검색 JS: 시도+시군구+동네 복합 검색, 띄어쓰기 정규화, 초기화/Escape, 결과 없음 안내, 다른 시도 이동 시 검색 해제, 검색된 지점·시군구 수 동기화. 기존 링크와 순서 유지.
7. scoped CSS: 모바일 3열×2행 메뉴, 본문16px 이상 중심, 제목·버튼·FAQ 간격, 이미지 원본 비율 유지, 기존 하단 상담 CTA 보존.
8. sitemap8,546 / RSS54: 신규 안내1개 추가. 기존 URL·순서·388개 noindex 제외 정책 보존. 기존 llms 안내에 새 안내 링크와 범위 고지 추가.

## 보호한 기존 자료

- 비대상 기존 HTML **8,904개**, 기존 자산 **766개** 바이트 동일.
- 허브26개의 title/H1/canonical/og:url 동일.
- 실제 센터 카드78개, 센터·목록 구조화 데이터 노드130개 동일.
- 디렉터리 링크8,928개의 목적지와 순서 동일.
- 동네 원고·센터명·주소·등록정보·가능 학년·교습비·기존 대표/본문/지도 이미지 변경 없음.
- 새로운 프로그램 소개를 모든 지점의 실제 개설 사실로 확대하지 않았다.

## 공식 자료 / 정확성 주의

출처와 원본 자산 SHA-256: `tools/data/learning-upgrade/sources.json`.

- https://www.wawacenter.com/brand/wawacenter
- https://www.wawacenter.com/intro/coachingSystem
- https://www.wawacenter.com/intro/AISystem
- 공식 내용에서 4C는 Check 맞춤 진단, Curriculum 맞춤 처방, Coaching 맞춤 지도, Consulting 맞춤 상담. 고정 순서를 공식 의무 절차라고 단정하지 않는다.
- AI영어·수학 초1~고3, AI국어 중1~고3, AI독서 초1~중2. 이는 공통 프로그램 범위이며 실제 센터 운영은 별도 확인.
- 공식 교실/플래너 사진은 공통 예시. 특정 센터의 실제 시설이라고 쓰지 않는다.
- 공식 페이지 일부 LIVE 카드 설명이 실제 YouTube 제목과 불일치했다. live oEmbed/썸네일 확인 후 브랜드소개 `59Tna9pZWrk`, 원장인터뷰 `f_skFu40U04`, 은평점 공부법 `UIXUaBZdNXU`로 연결했다. 동영상 전체 재생 내용 검증은 하지 않았다.
- 콘텐츠 이미지6개·영상썸네일3개 원본 그대로 로컬 보관. 영상은 클릭 시 YouTube 새 창, 자동재생/초기 iframe 없음.
- 검색 최적화 참고: https://searchadvisor.naver.com/guide/content-basic / https://searchadvisor.naver.com/guide/structured-data-intro . 검색 순위나 AEO/GEO 노출을 보장하거나 실제 순위 점수를 부여하지 않았다.

## 생성·검증·재작업

원본 편집: `tools/data/learning-upgrade/home.html`, `coaching.html`, `hub-briefs.json`.

생성기: `tools/upgrade_learning_20260914.py`. 고정 Git baseline에서 대상만 읽고, 이전 생성 해시와 다른 미확인 편집은 중단한다. 기존 대량 생성기를 실행하지 않는다. 과거 허브 생성기를 다시 실행했다면 이 업그레이드 결과가 지워질 수 있으므로 범위를 검토해야 한다.

PowerShell:

```powershell
$env:PYTHONPATH='C:/Users/1992k/Desktop/CodexData/tmp/wawa4-upgrade-deps'
python tools/upgrade_learning_20260914.py
python tools/audit_learning_20260914.py
node --check assets/directory-learning-v2.js
git diff --check
```

자산 캐시가 없어도 저장된 sources.json과 신규 assets 폴더의 검증된 원본으로 재생성 가능. RSS 생성 시각은 첫 생성값을 유지해 미래 시각/재실행 변동을 방지한다.

독립 정적 QA: `tools/reports/learning-upgrade/independent-static-audit.json`

- 내부 참조9,946건·앵커406건, FAQ143쌍(보이는 원고와 JSON-LD 정확히 일치), 이미지64개 사용 위치의 ALT/치수 검사 통과.
- H1 1개, 중복 HTML/JSON-LD ID 없음, 기존 앵커 ID 유지, 새 공식 자산9개 원본 해시 일치.

편집 QA: `tools/reports/learning-upgrade/editorial-review.md`.

브라우저 QA: `tools/reports/learning-upgrade/browser-layout.json`.

- 30페이지×320/430/1280px 총90검사: 가로 넘침·카드 잘림 없음, H1각1개.
- 390px 직접 확인: 메뉴 이동, FAQ 열기, 검색(서울 강동구→2개), 결과 없음, 다른 시도 선택, 명일동 검색, 집계 갱신, 초기화(371개 복구), 기존 명일동 중2수학 페이지 이동.
- 상담 폼 필드와 전화·SMS 링크만 확인. 실제 전화/문자 발송은 하지 않음.
- 브라우저 임시 화면 크기는 작업 종료 전 원래대로 복원.

승인된 공개 배포는 기존 GitHub `01039578283-hub/new8` → Vercel `new8` 경로를 사용하고 정식 도메인에서 다시 검증한다. 계정 요금제나 DNS를 임의 변경하지 않는다.
