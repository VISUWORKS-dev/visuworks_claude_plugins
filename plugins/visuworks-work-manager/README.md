# visuworks-work-manager

비쥬웍스 작업 컨텍스트 관리 플러그인. **정본은 Obsidian vault 하나**이고, Notion은
회의록·팀 공용 문서 작성 전용이다. **vault 경로는 repo에 저장되지 않고 설치 시
입력받는다(userConfig).**

## 역할 분담
- **Obsidian (정본)**: 규칙·상태·지식·이력의 모든 기록 → `obsidian-vault-manager` 스킬
- **Notion (보조)**: 회의록·팀 공용 문서 작성만 → `visuworks-work-manager` 스킬
  (Notion에는 claude.md/context.md/knowledge/history 레이어가 없다)
- **보고서 사고 정리**: 주장 Frame → AI 비판(Challenge) → 논증 흐름 승인(Shape) →
  근거/반론/대안(Enrich) → Report Spec 확정 → `report-thinking` 스킬
  (디자인 없는 low-fi 프리뷰까지만 만들고 최종 HTML은 만들지 않는다)
- **HTML 산출 (읽기 전용)**: Report Spec 또는 원자료 → 공유용 단일 HTML 문서 →
  `report-rendering` 스킬 (어디에도 기록하지 않는다. 문서를 만들어 전달만 한다)
- **주간 보고**: `2026 업무 DB`의 이번 주 Sprint·내 업무 → 완료 여부·사유·산출물 링크
  확인 → `연구노트(주간 업무 보고)` 금주 진행 사항 작성 → `weekly-report` 스킬

## 구성
- `skills/obsidian-vault-manager/SKILL.md` — Obsidian vault 관리 스킬 (정본)
  - vault 구조: 전역 `claude.md`/`context.md`/`knowledge/`/`assets/` +
    `projects/<프로젝트>/`(context.md·history.md·index.md + knowledge/·assets/·communications/·archive/)
  - 첨부 파일 처리: 원본은 `assets/YYYY-MM-DD_파일명`으로 보관 + 내용 정리본은 `knowledge/` 주제 문서에 통합 + `index.md` 갱신
  - 외부 소통 기록: `communications/<주제>.md`에 날짜·상대·전달 파일·요약을 append (history.md는 내부 결정 이력만)
  - 자산 인덱스: `projects/<p>/index.md`에 knowledge/assets/communications 전체 목록 + 1줄 설명
  - 스냅샷: 지식 문서를 크게 rewrite하기 전 `archive/`에 날짜 사본 보관
  - 읽기 범위: 프로젝트 특정 시 전역 claude.md/context.md + 해당 프로젝트 폴더만 읽기 (지시문 강제, 훅 없음)
  - Obsidian 네이티브: YAML frontmatter, [[위키링크]](비마크다운은 확장자 포함), 태그
  - 로컬은 바로 쓰기(사후 요약 보고), claude.md만 사전 승인
- `skills/visuworks-work-manager/SKILL.md` — Notion 쓰기 스킬 (회의록·공용 문서 한정)
- `skills/report-thinking/SKILL.md` — 보고서 주장을 정의·비판·검증해 Report Spec으로
  굳히는 스킬 (디자인 없음)
  - 절차(5단계): Frame(사용자 입장 먼저) → Challenge(AI가 비약·반론·대안 지적) →
    Shape(논증 흐름 승인, 목차 아님) → Enrich(주장마다 근거/반론/대안/리스크) →
    Spec(섹션별 Purpose/Message/Evidence/Visual/Decision 확정)
  - 산출: 흰 배경·검은 글씨·장식 없는 low-fi HTML 프리뷰 (heading/paragraph/table/
    simple diagram만) — 사고 확인용이지 최종 문서가 아님
  - 승인된 Report Spec을 `report-rendering`으로 넘김. vault·Notion에 쓰지 않는다
- `skills/report-rendering/SKILL.md` — Report Spec 또는 원자료 → 단일 HTML 문서 산출 스킬
  - 입력: `report-thinking`이 넘긴 Report Spec, 또는 사용자가 준 Notion URL
    (`notion-fetch`만)·첨부 파일·대화 내용·vault 문서
  - 출력: CSS·JS 전부 인라인된 단일 `.html` 1개 (외부 의존은 Pretendard CDN 하나)
  - 디자인 시스템 고정: `:root` 토큰 수정 금지, 액센트 7색 의미 규약(blue=현재 /
    teal=TO-BE / amber=미결 / coral=블로커 / purple=데이터·별도경로 / green=완료 /
    gray=중립), 한 문서 최대 5색, 다크 모드 미지원
  - 컴포넌트 21종 폐쇄 목록 (card-grid, kpi-grid, compare, flow, pc-flow, branch-list,
    state-flow, SVG diagram, tabs, timeline, table, screen-card, field-group,
    priority-grid, code-block, badge 6종, notice-box, details 등) — 목록 밖 신설 금지
  - 절차: 수집 → 구조화 → **목차 승인 게이트** → 조립 → 검증 → 전달
  - 파일명: `{프로젝트}_{문서명}_{버전}_{YYYYMMDD}.html`
  - vault·Notion에 쓰지 않는다 (기록 요청은 obsidian-vault-manager로 넘김)
- `skills/weekly-report/SKILL.md` — 업무 DB → 연구노트 금주/차주 진행 사항 작성 스킬
  - 대상 DB: 업무 DB(이름/작업자/Sprint/시작·종료날짜/프로젝트 relation, 완료
    속성 없음) → 연구노트(주차별 페이지 + 금주/차주 진행 사항·이슈사항·공유사항)
  - **최초 1회 설정 → 이후 재사용**: DB URL·본인 계정 식별은 userConfig
    (`weekly_report_work_db_url`/`weekly_report_notes_db_url`/`weekly_report_my_name`)에
    없으면 스킬을 처음 쓸 때 한 번만 묻고 `.omc/state/weekly-report.json`에
    캐시해, 대화가 바뀌어도 다시 묻지 않는다(`self` 계정 ID와 업무 DB person
    필드 mention ID가 다를 수 있어 이름 대조로 확정)
  - Sprint는 `YYYY-M-주차` 형식으로 이번 주·다음 주 값을 계산해 필터링
  - 완료 여부·미완료 사유는 스키마에 없고 캐시 대상도 아니므로 **매 실행 확인**
    (가능하면 AskUserQuestion 항목별 질문, 사유·요약은 자유 서술)
  - 다음 주 Sprint가 아직 미확정인 업무는 목록을 보여주고 차주 편입 여부를
    선택받아, 편입 시 업무 DB의 Sprint(+ 필요 시 담당자)를 갱신
  - 업무를 프로젝트 relation 기준으로 묶어 `[프로젝트명]` 헤더로 작성, 연구노트
    Multi-select 속성도 등장한 프로젝트에 맞춰 갱신
  - 이슈사항·공유사항은 한 번에 같이 확인, 각 섹션은 목록 외 추가 작성 여부도 확인
  - 해당 주차 연구노트 페이지가 없으면 기존 페이지 템플릿 구조를 따라 새로 생성
  - Git Issue/PR·Figma 등 링크는 사용자가 준 것만 채움(검색·추측 금지)
  - 정리한 내용은 작성 전 사용자 승인 게이트를 거침
- `hooks/hooks.json` + `scripts/gate-notion-search.sh` — 워크스페이스 검색·쿼리 → 사용자 인가(ask) 게이트 (Cowork 전용, weekly-report의 DB 내 필터 쿼리도 포함)
- `CLAUDE.md` — 각자 Cowork 프로젝트 루트에 복사해 두는 "항상 로드" 읽기 절차 템플릿

## 설치 시 입력받는 값 (userConfig)
- `obsidian_vault_path` — 정본 기록소 Obsidian vault 절대 경로
- `weekly_report_work_db_url` — (선택) weekly-report 업무 DB URL, 비워두면 최초 실행 시 질문
- `weekly_report_notes_db_url` — (선택) weekly-report 연구노트 DB URL, 비워두면 최초 실행 시 질문
- `weekly_report_my_name` — (선택) weekly-report에서 본인을 찾을 Notion 표시 이름, 비워두면 최초 실행 시 질문

값은 각자 환경에만 저장되고 공개 repo에는 들어가지 않는다.
SKILL.md는 이를 `${user_config.obsidian_vault_path}` 형태로 참조한다.

## 훅 확인
설치 후 Cowork에서 `/hooks`로 `matcher`("mcp__.*notion.*(search|query).*")가 실제 Notion
검색·쿼리 도구 이름과 맞는지 확인한다. notion-search와 notion-query 계열이 게이트되고,
notion-fetch(지정 페이지 직접 읽기)와 쓰기 도구는 통과하는 것이 정상이다.

## CLAUDE.md (항상 로드) — 각자 로컬에서
동봉된 `CLAUDE.md`(이 폴더의 템플릿)는 플러그인이 아니라 **각 사용자의 Cowork 프로젝트
루트**에 복사해 두는 로컬 파일이다. vault 경로는 **각자 로컬에서 채우며 공개 repo에
커밋하지 않는다.** Cowork는 프로젝트 루트 CLAUDE.md를 매 메시지 자동 주입하므로
"시작 시 vault 읽기" 절차가 항상 걸린다.

## history 정기 유지보수 (Cowork 예약 작업)
Cowork 예약 작업으로 주기 실행(예: 매주 금요일). vault의 history.md를 열어 이번 주
항목을 정리·압축하고, 오래된 항목은 아카이브로 옮길지 제안한다.
※ 예약 작업은 대화 내용을 자동으로 알지 못한다 — 대화 캡처는 사람이 트리거하고,
   예약 작업은 쌓인 history.md의 정리·아카이브를 맡는다.

## 로컬 수동 업로드 
cd plugins/visuworks-work-manager
zip -r visuworks-work-manager.plugin . -x "*.DS_Store" -x ".omc/*" -x ".git/*"

후 ~.plugin파일 업로드