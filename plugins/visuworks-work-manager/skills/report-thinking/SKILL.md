---
name: report-thinking
description: 보고서·제안서를 쓰기 전에 사용자의 주장을 정의·비판·검증해 Report Spec으로 굳힐 때 사용한다. "보고서 쓸건데 생각 정리부터", "이 주장 좀 검토해줘", "반론 찾아줘", "목차 말고 논증 구조부터" 같은 요청에서 발동한다. 디자인·최종 HTML은 만들지 않는다 — low-fi(흰 배경·검은 글씨·장식 없음) 프리뷰까지만 만들고, 승인된 Report Spec은 report-rendering 스킬로 넘긴다.
---

# Report Thinking (주장 정의 → Report Spec)

> **역할 분담**: 이 스킬은 **무엇을 주장할지**를 정한다. **어떻게 보여줄지**는
> `report-rendering` 스킬(비쥬웍스 디자인 시스템)의 몫이다. 이 스킬은 최종 디자인의
> `:root` 토큰이나 컴포넌트 카탈로그를 알 필요도, 다룰 필요도 없다.

```
사용자의 생각 ──→ [report-thinking]                     [report-rendering]
                  Frame → Challenge → Argument       →   Design System
                  → Evidence → Report Spec               (REPORT_STYLE.md,
                        │                                 tokens.css,
                        ▼                                 components/*)
                  Low-fi Preview (사고용 HTML)                  │
                        │                                       ▼
                  Human decision ──────────────────────→  Final HTML
```

## 1. 이 스킬이 하는 것 / 안 하는 것

**하는 것**

1. 사용자의 초기 입장(Frame)을 먼저 확보한다 — AI가 먼저 답을 내지 않는다.
2. AI가 Critic 역할로 논리적 비약·빠진 이해관계자·반론·대안을 찾는다(Challenge).
3. 사람이 승인한 주장 흐름(목차가 아니라 논증 구조)을 Shape로 고정한다.
4. 각 주장에 근거·반론·대안·리스크를 채워 넣는 분석 레이어를 만든다(Enrich) —
   이건 최종 문서에 그대로 들어가는 게 아니라 사람이 고르는 재료다.
5. 섹션 단위 Report Spec(Purpose/Message/Evidence/Visual/Decision)을 확정한다.
6. Report Spec을 눈으로 확인할 low-fi HTML 프리뷰를 만든다.

**안 하는 것**

- 디자인 시스템 조립, 최종 HTML 산출 — `report-rendering`이 담당.
- 사람 대신 최종 주장을 결정 — 이 스킬은 재료를 넓히고 사람이 고르게 한다.
- vault·Notion 기록 — 각각 obsidian-vault-manager / visuworks-work-manager 담당.

**발동하지 않는 경우**: 이미 주장이 정리돼 있고 "바로 문서로 만들어줘"인 경우
(→ `report-rendering` 직행), 회의록·단순 정리(→ vault/Notion 담당 스킬).

## 2. 절차 (5단계)

### ① Frame — 사람이 먼저 5분 안에 정의

AI가 먼저 초안을 만들지 않는다. 다음 네 가지를 사용자에게 먼저 묻는다.

- **Audience** — 누가 보는가?
- **Decision** — 이 자료를 보고 무엇을 결정/이해해야 하는가?
- **My current position** — 현재 나는 무엇이 맞다고 생각하는가?
- **Desired outcome** — 독자가 이 문서를 다 읽고 나서 무엇을 하길(승인, 예산 배정,
  다음 회의 소집 등) 바라는가, 혹은 최소한 무엇을 이해하고 넘어가길 바라는가?

완벽할 필요 없다. 중요한 건 AI보다 먼저 사용자의 초기 가설이 존재하는 것이다.
넷 다 답이 없으면 진행하지 말고 여기서 멈춘다. Desired outcome은 이후 ⑤Spec의
각 섹션 Decision 필드가 최종적으로 수렴해야 할 기준점이 된다.

### ② Challenge — AI를 Writer가 아니라 Critic으로

Frame이 나오면 바로 HTML로 가지 않는다. 먼저 사용자의 주장을 공격한다.

찾아야 할 것:

1. 논리적 비약
2. 빠진 이해관계자 관점
3. 반대하는 사람이 할 질문
4. 근거가 부족한 주장
5. 다른 가능한 해결책
6. 지나치게 한쪽 관점(예: 기술 중심)으로 보고 있는 부분

이 목록을 사용자에게 제시하고, 어떤 지적을 받아들일지는 사람이 고른다.
받아들이지 않은 지적도 버리지 않는다 — ④Enrich의 counterargument/risk 재료가 된다.

### ③ Shape — 목차가 아니라 주장 흐름을 승인받는다

섹션 제목 나열이 아니라 **논증 흐름**으로 제시하고 승인받는다.

```
현재
  각 서비스가 원본 데이터를 직접 가공한다.
↓
그 결과
  같은 데이터가 서로 다르게 해석된다 / 운영계가 분석 workload까지 부담한다 /
  데이터 사용 이력을 추적할 수 없다.
↓
따라서
  데이터 가공을 서비스에서 공통 데이터 계층으로 이동해야 한다.
↓
이를 위해
  RDS / Airflow / dbt / ... 가 각기 다른 문제를 담당한다.
↓
결과적으로
  정합성 / 추적성 / 재사용성 / 운영 안정성을 확보한다.
```

이 흐름(10~15줄 내외)이 문서의 spine이다. **여기서 승인 없이 다음 단계로 가지 않는다.**

### ④ Enrich — AI가 주장마다 재료를 채운다

승인된 흐름의 각 주장(claim)마다 다음을 채운다. 이건 내부 검증용 분석
레이어이지 최종 문서 본문이 아니다.

- Claim
- Evidence / Internal evidence
- Example
- Counterargument
- Alternative
- Risk / Unknown
- Implication

원자료(사용자가 준 자료·대화·앞선 조사)에 없는 근거는 "추정"이라고 표시하고,
사실인 척 채우지 않는다. 이 레이어를 사람에게 보여주고 세 가지를 고르게 한다:

1. 어떤 근거를 쓸 것인가
2. 어떤 반론을 인정할 것인가
3. 최종적으로 무엇을 주장할 것인가

이 선택이 저자성(authorship)이다 — AI가 아무리 많이 채워도 최종 판단은 사람이 한다.

### ⑤ Spec — 섹션별 Report Spec 확정

각 섹션마다 최소한 이것만 결정한다.

```
SECTION 03
Purpose      — 왜 이 섹션이 필요한가
Message      — 독자가 여기서 기억해야 할 한 문장
Evidence     — 그 주장을 뒷받침할 것 (④Enrich에서 사람이 고른 것)
Visual       — table / diagram / chart / prose / none
Decision     — 그래서 무엇을 해야 하는가
```

중요한 섹션에는 필요할 때만 추가:

```
Alternative considered / Why rejected
Risk / Unknown
```

**모든 섹션에 강제로 넣지 않는다.** 채울 근거가 없는 항목은 비워 두거나
Unknown으로 명시한다 — 없는 내용을 지어내지 않는다.

## 3. Low-fi Preview — 사고 확인용, 디자인 아님

Spec이 나오면 **디자인 없는** HTML로 흐름을 눈으로 확인시킨다. 목적은
"예쁘다"가 아니라 "이 사람이 무슨 문제를 말하고 있고 뭘 하자는 건지 알겠다"는
반응이다.

**규칙 (전부 금지 방향)**

- 흰 배경, 검은 글씨. 브랜드 색·액센트 없음.
- 아이콘 없음, 그라디언트 없음, 카드 없음, 배지 없음, 장식 컴포넌트 없음.
- 쓸 수 있는 것은 딱 다섯: heading, paragraph, table, line(구분선), simple diagram
  (화살표로 잇는 텍스트 박스 수준 — SVG 꾸밈 없음).
- 인라인 CSS 최소(margin/padding 정도), 외부 리소스·폰트 없음, 단일 파일.
- 첫 화면은 표지가 아니라 **Executive Brief**: 문제 3가지 이내 + 핵심 판단
  한 문단 + (있다면) 현재→목표 한 줄 다이어그램.

이 프리뷰는 report-rendering으로 넘기는 산출물이 아니라 **사람이 승인하기 위한
중간 확인물**이다. 승인이 끝나면 버려도 된다.

## 4. 다음 단계로 넘기기

사람이 low-fi 프리뷰와 Spec을 승인하면, 확정된 Report Spec(섹션별
Purpose/Message/Evidence/Visual/Decision, 그리고 필요시 Alternative/Risk)을
그대로 `report-rendering` 스킬에 전달한다. 대화 맥락에 Spec 텍스트를 유지하는
것으로 충분하며 별도 파일 저장은 하지 않는다.

vault 보관이 필요하면 obsidian-vault-manager로, Notion 회의록/공용 문서가
필요하면 visuworks-work-manager로 넘긴다 — 이 스킬은 어디에도 쓰지 않는다.

## 5. 하지 말 것

- Frame 없이(사용자 입장 확인 없이) 바로 주장 흐름 생성.
- Challenge 단계를 건너뛰고 바로 Shape로 직행.
- Shape(주장 흐름) 승인 없이 Enrich·Spec 진행.
- low-fi 프리뷰에 색·아이콘·카드·그라디언트 등 장식 요소 추가.
- 원자료·근거 없는 내용을 Evidence로 채워 넣기 — 없으면 Unknown으로 남긴다.
- 최종 디자인 시스템(tokens/components) 언급·조립 — report-rendering 영역.
