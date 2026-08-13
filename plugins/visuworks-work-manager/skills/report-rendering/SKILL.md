---
name: report-rendering
description: 확정된 Report Spec(섹션별 Purpose/Message/Evidence/Visual/Decision), 또는 Notion 링크·첨부 파일·대화 내용 등 원자료를 받아 하나의 HTML 문서로 구성할 때 사용한다. "HTML로 만들어줘", "핸드오프 문서 만들어줘", "이 노션 정리해서 개발팀 줄 문서로", "자료 합쳐서 한 장으로", "기존 HTML v2로 업데이트", "Spec대로 렌더링해줘" 같은 요청에서 발동한다. 고정된 비쥬웍스 디자인 시스템(사이드바 문서형 · 액센트 7색 의미 규약 · 컴포넌트 21종)으로만 조립하며 문서마다 스타일을 새로 만들지 않는다. 주장·목차 자체를 다시 정의하는 요청("반론 찾아줘", "생각부터 정리")은 report-thinking 담당이므로 이 스킬은 이미 정해진 내용의 렌더링만 한다.
---

# Report Rendering (Report Spec / 원자료 → 단일 HTML)

> **역할 분담**: **무엇을 주장할지**는 `report-thinking`이 정한다. 작업 컨텍스트의
> 정본은 **Obsidian vault**(obsidian-vault-manager), Notion 쓰기는
> **visuworks-work-manager** 담당이다. 이 스킬은 **이미 정해진 내용을 디자인
> 시스템으로 조립**만 한다 — 주장·구조를 새로 만들지 않는다.

## 1. 이 스킬이 하는 것 / 안 하는 것

**하는 것**

1. `report-thinking`이 넘긴 Report Spec(섹션별 Purpose/Message/Evidence/Visual/
   Decision, 필요시 Alternative/Risk)을 그대로 컴포넌트로 렌더링.
2. Spec 없이 바로 요청이 오면, 사용자가 준 Notion 페이지·첨부 파일·대화 내용을
   읽어 하나의 HTML 문서로 조립(§5 매핑 사용).
3. 기존 산출 HTML을 받아 특정 섹션만 갱신(v2, v3).
4. 산출물을 사용자에게 전달(SendUserFile), 요청 시 지정 경로에 저장.

**안 하는 것**

- Spec의 주장·근거·구조를 바꾸거나 새로 판단하지 않는다. 바뀌어야 할 것 같으면
  렌더링을 멈추고 report-thinking으로 되돌아갈지 사용자에게 확인한다.
- vault·Notion에 기록하지 않는다. 문서 생성 후 "vault에도 남겨줘"가 오면
  obsidian-vault-manager로 넘긴다(HTML 원본은 `assets/`, 요약은 `knowledge/`).
- 원자료·Spec에 없는 내용을 만들어 채우지 않는다.
- 디자인 시스템을 문서마다 새로 만들지 않는다.

**발동하지 않는 경우**: 주장·논증 구조 자체가 아직 안 정해짐(→ `report-thinking`
먼저), "기록해줘"(vault 담당), "회의록 Notion에"(Notion 담당), 단순 질의응답,
스프레드시트·docx·pptx가 산출물인 요청.

## 2. 수집 규율

- Report Spec이 이미 있으면(대화에 `report-thinking` 산출물이 있으면) 그것을
  1차 입력으로 쓴다. 원자료를 다시 읽는 건 Spec의 Evidence를 확인할 때만.
- Notion은 **사용자가 준 URL만** `notion-fetch`로 읽는다. 하위 페이지는 따라갈 수 있다.
- `notion-search`·`notion-query` 계열 **워크스페이스 탐색은 자동으로 하지 않는다.**
  필요하면 인가를 요청하고 명시적 승인이 있을 때만 실행한다(플러그인 PreToolUse 훅이
  Cowork에서 이를 강제한다).
- vault 문서를 참조해야 하면 프로젝트 범위 규율(전역 claude.md/context.md +
  해당 `projects/<프로젝트>/`)을 따른다.
- 자료가 부족하면 **여기서 멈추고 물어본다.** 추측으로 채우고 진행하지 않는다.

## 3. 디자인 시스템 규칙 (고정 — 어길 수 없음)

1. **`:root` 블록 수정 금지.** 색·폰트·간격 값을 문서마다 바꾸지 않는다. 새 색이
   필요하다고 느껴지면 그건 새 색이 아니라 정보 구조가 잘못 잡힌 것이다.
2. **인라인 style은 액센트 지정에만.** `style="border-top:3px solid var(--accent-teal)"`
   처럼 의미 색 부여에만 허용. 폰트 크기·여백 하드코딩 금지.
3. **색상 리터럴 금지.** 본문 HTML에 `#2563EB` 같은 hex를 직접 쓰지 않는다. 반드시
   `var(--accent-blue)`. 예외는 인라인 SVG(CSS 변수 상속이 불안정) — 하드코딩하되
   토큰과 **동일한 값**만 쓴다.
4. **외부 라이브러리 추가 금지.** Pretendard CDN 외 CSS·JS 로드 없음. 차트가 필요하면
   인라인 SVG로 직접 그린다.
5. **다크 모드 미지원.** `prefers-color-scheme` 분기를 넣지 않는다.
6. **로고는 "Visuworks AI" 혹은 "Visuworks 마케팅팀" 등 팀이름 확인받아서 작성.**, 문서 제목만 가변. `lang="ko"` 고정.

### 액센트 7색 — 의미 규약

각 색은 `--accent-X`(선) / `--accent-X-bg`(면) / `--accent-X-text`(글자) 3종 세트다.
**색을 장식으로 쓰지 않고 아래 의미에 묶는다. 이 규약이 문서 간 일관성의 실체다.**

| 색 | 의미 | 대표 용도 |
|---|---|---|
| `blue` | 기본 강조 | 현재 상태, 진행 중, nav 활성, 근거·설명(`field-why`) |
| `teal` | 지향·개선 | TO-BE, 착수 가능, 긍정 경로, 신규 도입 영역 |
| `amber` | 주의·대기 | `notice-box`, 미결, 기획 대기, 콘텐츠 필요 |
| `coral` | 문제·차단 | AS-IS, 오류 분기, 블로커, 제약 |
| `purple` | 데이터·별도 경로 | 필드명, 별도 모드, 대체 진입 경로 |
| `green` | 완료 | 확정, 종료 상태. **완료에만** 쓴다 |
| `gray` | 중립·외부 | 미정, 범위 밖, 외부 시스템, 신규 항목 |

**한 문서에서 액센트는 최대 5색.** 초과하면 정보 구조를 다시 잡는다.

배지 6종의 색-의미 매핑도 고정이다. 라벨 텍스트(`확정`/`Done`/`v0.3`)는 문서마다
달라도 되지만 어떤 색을 쓸지는 바뀌지 않는다.

| 배지 | 의미 |
|---|---|
| `badge-done` (green) | 확정·완료 |
| `badge-wip` (blue) | 진행 중·방향 잡힘 |
| `badge-wait` (amber) | 대기·선행 조건 필요 |
| `badge-new` (gray) | 미정·신규 |
| `badge-block` (coral) | 블로커 |
| `badge-draft` (점선) | 초안 — 확정 아님 |

## 4. 컴포넌트 카탈로그 (21종 — 이 목록 밖은 만들지 않는다)

**A. 골격 (모든 문서 필수)**

| 클래스 | 용도 |
|---|---|
| `nav` | 좌측 고정 사이드바. 로고 + 문서 제목 + 넘버링 링크. `nav-divider`로 그룹 분리 |
| `doc-header` | h1 + `meta`(기준일·대상·성격) + `notice-box`(문서 성격·정본 안내) |
| `section` + `sec-num` + `sec-desc` | 번호 배지 + 제목 + **한 문장 요약**(누락 금지) |
| footer div | 문서명 · 기준일 · 작성 주체. 중앙 정렬 12px tertiary |

**B. 구조 표현**

| 클래스 | 용도 |
|---|---|
| `card-grid` / `card` | 2열. 병렬 개념 3~6개. `border-top:3px`로 의미 색 |
| `compare` | AS-IS → TO-BE 2단 비교. 변경된 값만 액센트 색 |
| `flow-container` / `flow-node` / `flow-arrow` | 선형 절차. `border-left:3px`로 경로 구분 |
| `pc-flow` / `pc-card` | 아이콘(번호) + 제목 + 설명 + 부가 기록 한 줄. 물리적·조직적 단계 |
| `branch-list` | 번호 있는 조건 분기. 순서가 곧 우선순위 |
| `state-flow` | 상태 전이. 노드 + 화살표 + 하단 상태별 설명 |
| `diagram-wrap` + inline SVG | 계층·아키텍처. viewBox 기반 반응형, `marker`로 화살표 |
| `tabs` / `tab-panel` | 같은 층위의 대안 뷰 3개 내외 |
| `timeline` / `timeline-item` | 세로 시간축. 날짜/기간 + 제목 + 설명 + 배지. 세로선·마커 색은 `border-color`로 |

**C. 데이터 표현**

| 클래스 | 용도 |
|---|---|
| `table-wrap` / `table` | 3~4열 대조표. 5열 넘으면 `details`로 분해 |
| `screen-card` | ID + 이름(+배지) + 설명. 식별자 있는 항목 목록 |
| `field-group` / `field-item` | 필드명(purple 모노) + 설명 + `field-why`(왜 필요한가, blue) |
| `priority-grid` | 2열 대조 리스트. 가능/대기, P0/P1 |
| `code-block` | 트리 구조, 스키마, 로그. `white-space:pre` |
| `kpi-grid` / `kpi-card` | 라벨 + 큰 숫자 + 보조 설명. 지표 강조가 목적. `border-top:3px`로 의미 색 |

**D. 보조**

| 클래스 | 용도 |
|---|---|
| `badge` (6종) | 상태 라벨 |
| `notice-box` | amber 알림. 문서 성격 고지, 핵심 제약, 초안 경고 |
| `details` / `summary` | 2차 정보 접기. **`open`은 문서당 3개 이하** |

**동작(JS) 2종**

- `showFlowTab` — `btn.closest('section')` 스코프로 섹션별 독립 동작. 탭이 없는
  문서에서는 함수도 생략한다.
- `IntersectionObserver` — nav 스크롤 스파이. **항상 포함**.

## 5. 입력 → 컴포넌트 결정 규칙

### 5-1. 내용 패턴 기준 (1차 판단)

| 원자료 패턴 | → 컴포넌트 | 판단 근거 |
|---|---|---|
| 병렬 개념 3~6개 | `card-grid` | 각 항목이 제목+한두 줄. 7개↑면 `table` |
| 숫자 지표 3~6개, 강조가 목적 | `kpi-grid` | 값 자체가 핵심일 때만. 설명이 주면 `card-grid`, 7개↑면 `table` |
| "기존 → 변경", "전 vs 후" | `compare` | 항목 키가 양쪽 동일할 때만. 아니면 2열 `table` |
| 순서 있는 절차 | `flow-container` | 분기 없는 선형. 담당자·장소가 붙으면 `pc-flow` |
| "~인 경우 → ~한다" 목록 | `branch-list` | 순서=우선순위임을 명시 |
| 상태값 전이 | `state-flow` | 3~5개 상태. 그 이상은 SVG |
| 일정·이력이 날짜순으로 나열 | `timeline` | 시간축이 축일 때. 날짜가 없으면 `flow-container` |
| 계층·포함 관계 | `diagram-wrap` + SVG | 레이어 3개 내외. 복잡하면 `code-block` 트리 |
| ID 붙은 항목 목록 | `screen-card` | 화면 맵, API 목록, 요구사항 ID |
| DB 필드·파라미터 명세 | `field-group` | "왜 필요한가"를 반드시 `field-why`에 |
| 2분류 목록 | `priority-grid` | 가능/대기, P0/P1 |
| 3열 이상 대조 데이터 | `table-wrap` | **기본값. 애매하면 표로** |
| 같은 층위 대안 뷰 | `tabs` | 3개 내외. 그 이상은 섹션 분리 |
| 부연·근거·예시 | `details` | 본문 흐름을 끊는 정보는 전부 접기 |

### 5-2. Notion 블록 기준 (2차 보정)

**블록 타입보다 내용 패턴이 우선한다.** Notion의 표가 실은 AS-IS/TO-BE 비교면
`compare`로 승격한다.

| Notion 블록 | → 기본 변환 | 승격 조건 |
|---|---|---|
| heading_1 / heading_2 | `section` / `h3` | — |
| table / database | `table-wrap` | 2열 대조 → `compare`, ID 열 존재 → `screen-card` |
| bulleted_list | 본문 `ul` 또는 `card-grid` | 각 항목이 제목+설명 구조면 `card-grid` |
| numbered_list | `branch-list` | 조건-결과 형태일 때 |
| toggle | `details` | — |
| callout | `notice-box` | — |
| code | `code-block` | — |
| image / file | base64 인라인 | **500KB 이하만.** 초과 시 자리표시 박스 + 캡션 |

### 5-3. 이미지 처리

단일 파일 원칙을 지키기 위해 **외부 이미지 URL을 그대로 넣지 않는다.**

- 500KB 이하: base64 data URL로 인라인.
- 초과: `notice-box` 또는 `card`로 자리표시 + 캡션 + 원본 위치 안내. 사용자에게
  경량 버전을 별도로 받을지 물어본다.

## 6. 절차 (6단계)

**1. 수집** — Report Spec이 있으면 그것을 읽는다(§2). 없으면 사용자가 준 URL·첨부를
읽는다. 워크스페이스 검색 금지. 부족하면 멈추고 질문.

**2. 구조화** — Spec이 있으면 섹션별 Visual 필드를 §5 매핑에 대입해 컴포넌트를
확정한다(이미 섹션·주장은 정해져 있으므로 재구성하지 않는다). Spec이 없으면
원자료를 섹션 단위로 쪼개고 §5 매핑을 적용해 컴포넌트를 배정한다. 배지가 필요한
상태값(확정/진행/대기/블로커)을 식별한다.

**3. 목차 승인 게이트** — 섹션 번호·제목·배정 컴포넌트를 **텍스트 개요로 먼저 제시하고
승인을 받는다. 승인 없이 HTML을 만들지 않는다.** Report Spec을 이미 승인받고
넘어온 경우나 사용자가 "바로 만들어"라고 하면 생략.

```
제안 목차
1. 제품 구조        — card-grid (4개)
2. 계정 구조        — table + compare(AS-IS→TO-BE) + details 3
3. 데이터 모델      — SVG 3계층 + field-group + state-flow
...
```

**4. 조립** — `assets/template.html`을 그대로 깔고(§9) 승인된 목차대로 `section`을 채운다. 문서가 길면
파일을 먼저 만든 뒤 섹션별로 나눠 편집한다(한 번에 전부 쓰려다 잘리지 않게).

**5. 검증** — §8 체크리스트를 돌린다. 기계 검증 항목은 스크립트로 확인한다.

**6. 전달** — SendUserFile로 전달. 로컬 저장 요청이 있으면 지정 경로에 기록. vault
보관을 원하면 obsidian-vault-manager로 넘긴다.

### 기존 문서 갱신 (v2 이상)

원본 HTML을 읽고 **해당 `section`만 교체**한다. 전체를 재생성하지 않는다.
nav 링크와 footer의 버전·날짜를 함께 갱신한다.

## 7. 파일명·전달 규칙

```
{프로젝트}_{문서명}_{버전}_{YYYYMMDD}.html

LOOCUS_개발_핸드오프_v1_20260317.html
INSIGHT_상담_프로세스_v2_20260803.html
```

- 버전은 사용자가 지정하지 않으면 `v1`. 기존 문서 갱신이면 +1.
- 날짜는 **생성일이 아니라 내용 기준일** — `doc-header`의 기준일과 일치시킨다.
- 공백은 `_`. 한글 파일명 허용.

## 8. 검증 체크리스트 (전달 전 필수)

**기계 검증 — 스크립트로 확인**

1. `nav` 앵커 ↔ `section id` 일치. 누락·오타 0건.
2. body 내 색상 hex 리터럴 0건 (인라인 SVG, 그리고 문서 내용으로 hex를 설명하는
   `<code>` 텍스트는 제외).
3. 태그 균형, `charset="UTF-8"`, 미닫힌 태그 0건.
4. 외부 리소스 = Pretendard CDN 1건 외 0건.

**판단 검증 — 자기 점검**

5. 액센트 5색 이하.
6. `<details open>` 3개 이하.
7. 모든 `section`에 `sec-desc` 한 문장 존재.
8. **원자료에 없는 내용 생성 0건.** 추정이 필요하면 `badge-draft` + `notice-box`로
   초안임을 명시한다.

> 8번이 가장 중요하다. 컴포넌트가 칸을 요구한다고 해서 원자료에 없는 내용을 채워
> 넣지 않는다. 빈 칸은 비워 두거나 컴포넌트를 바꾼다.

검증용 스크립트 예시:

```python
import re
s = open(path, encoding='utf-8').read()
body = s.split('</head>', 1)[1]
ids = set(re.findall(r'<section id="([^"]+)"', body))
anchors = set(re.findall(r'<a href="#([^"]+)"', body)) - {'${e.target.id}'}
assert not (anchors - ids), anchors - ids
print('open details:', body.count('<details open>'))
print('external:', re.findall(r'(?:href|src)="(https?://[^"]+)"', s))
```

## 9. 템플릿 (정본은 `assets/` 파일)

**정본은 이 문서가 아니라 파일이다.** 새 문서를 조립할 때는 아래 3개를 읽어서 시작한다.

| 파일 | 내용 |
|---|---|
| `assets/tokens.css` | `:root` 토큰 한 줄. **수정 금지**(§3-1) |
| `assets/components.css` | 컴포넌트 21종 CSS + `@media` 2개 |
| `assets/template.html` | 골격 + 전 컴포넌트 사용 예시 + `showFlowTab` / `IntersectionObserver` |

절차: `assets/template.html`을 복사 → `{{...}}` 자리를 채움 → 사용하지 않는 컴포넌트
블록만 삭제. **CSS는 건드리지 않는다.**

산출물은 단일 HTML 1장이므로 전달 직전에 `<link rel="stylesheet" href="tokens.css">`
`<link rel="stylesheet" href="components.css">` 두 줄을 두 파일 내용을 이어 붙인
`<style>` 블록으로 치환한다. `<link>` 상태는 `assets/` 안에서 미리 보기 할 때만 쓴다.
(§8-4 "외부 리소스 = Pretendard CDN 1건"은 이 인라인 이후 상태 기준이다.)

### 컴포넌트 사용 예시

아래는 조립할 때 자주 쓰는 마크업 발췌다. **출처는 `assets/template.html`**이고 여기
있는 것은 사본이다. 차이가 나면 항상 파일 쪽이 맞다.

```html
<!-- card-grid: 병렬 개념 3~6개 -->
<div class="card-grid">
  <div class="card" style="border-top:3px solid var(--accent-blue)"><div class="card-label" style="color:var(--accent-blue)">{{분류}}</div><div class="card-title">{{제목}}</div><div class="card-desc">{{설명}}</div></div>
</div>

<!-- kpi-grid: 숫자 지표 3~6개, 강조가 목적 -->
<div class="kpi-grid">
  <div class="kpi-card" style="border-top:3px solid var(--accent-blue)"><div class="kpi-label">{{지표명}}</div><div class="kpi-value">{{값}}<span class="kpi-unit">{{단위}}</span></div><div class="kpi-note">{{증감·비고}}</div></div>
</div>

<!-- compare: AS-IS → TO-BE -->
<div class="compare">
  <div class="compare-side" style="border-top:3px solid var(--accent-coral)"><div class="compare-label" style="color:var(--accent-coral)">AS-IS</div>
    <div class="compare-item"><span class="compare-key">{{항목}}</span><span class="compare-val">{{현재}}</span></div>
  </div>
  <div class="compare-arrow">→</div>
  <div class="compare-side" style="border-top:3px solid var(--accent-teal)"><div class="compare-label" style="color:var(--accent-teal)">TO-BE</div>
    <div class="compare-item"><span class="compare-key">{{항목}}</span><span class="compare-val" style="color:var(--accent-teal)">{{변경}}</span></div>
  </div>
</div>

<!-- branch-list: 조건 분기, 순서=우선순위 -->
<div class="branch-list">
  <div class="branch-item" style="background:var(--accent-teal-bg)"><span class="branch-num" style="background:var(--accent-teal);color:#fff">1</span><div class="branch-text"><strong>{{조건}}</strong> → {{결과}}</div></div>
</div>

<!-- timeline: 날짜순 일정·이력. 세로선+마커 색은 인라인 border-color, 상태는 기존 badge 재사용 -->
<div class="timeline">
  <div class="timeline-item" style="border-color:var(--accent-green)">
    <div class="timeline-date">{{YYYY-MM-DD}}</div>
    <div class="timeline-title">{{항목 제목}} <span class="badge badge-done">확정</span></div>
    <div class="timeline-desc">{{설명}}</div>
  </div>
  <div class="timeline-item">
    <div class="timeline-date">{{미정}}</div>
    <div class="timeline-title">{{항목 제목}} <span class="badge badge-wait">대기</span></div>
    <div class="timeline-desc">{{설명}}</div>
  </div>
</div>

<!-- field-group: 필드 명세 -->
<div class="field-group"><div class="field-group-title">{{엔티티}}</div>
  <div class="field-item"><span class="field-name">{{field_name}}</span><span class="field-desc">{{무엇인가}}</span><div class="field-why">→ {{왜 필요한가}}</div></div>
</div>
```

나머지 컴포넌트(`table-wrap` / `screen-card` / `flow-container` / `pc-flow` /
`priority-grid` / `tabs` / `diagram-wrap`+SVG / `state-flow` / `code-block` /
`details` / `notice-box`)의 마크업은 `assets/template.html`에 전부 들어 있다.

## 10. 하지 말 것

- `:root` 토큰 값 변경, 다크 모드 분기 추가.
- 본문 HTML에 색상 hex 직접 입력(SVG 제외).
- Pretendard 외 외부 CSS·JS·이미지 URL 로드.
- 카탈로그 21종 밖의 새 컴포넌트·클래스 신설.
- 목차 승인 없이 전체 HTML 생성(사용자가 생략을 요청한 경우 제외).
- 원자료에 없는 내용을 컴포넌트 칸을 채우려고 생성.
- vault·Notion에 쓰기(다른 두 스킬 담당).
- 사용자 인가 없이 Notion 워크스페이스 검색·쿼리.
