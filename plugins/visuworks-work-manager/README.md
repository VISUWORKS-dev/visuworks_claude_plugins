# visuworks-work-manager

비쥬웍스 작업 컨텍스트 관리 플러그인. **정본은 Obsidian vault 하나**이고, Notion은
회의록·팀 공용 문서 작성 전용이다. **vault 경로는 repo에 저장되지 않고 설치 시
입력받는다(userConfig).**

## 역할 분담
- **Obsidian (정본)**: 규칙·상태·지식·이력의 모든 기록 → `obsidian-vault-manager` 스킬
- **Notion (보조)**: 회의록·팀 공용 문서 작성만 → `visuworks-work-manager` 스킬
  (Notion에는 claude.md/context.md/knowledge/history 레이어가 없다)

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
- `hooks/hooks.json` + `scripts/gate-notion-search.sh` — 워크스페이스 검색·쿼리 → 사용자 인가(ask) 게이트 (Cowork 전용)
- `CLAUDE.md` — 각자 Cowork 프로젝트 루트에 복사해 두는 "항상 로드" 읽기 절차 템플릿

## 설치 시 입력받는 값 (userConfig)
- `obsidian_vault_path` — 정본 기록소 Obsidian vault 절대 경로

값은 각자 환경에만 저장되고 공개 repo에는 들어가지 않는다.
SKILL.md는 이를 `${user_config.obsidian_vault_path}`로 참조한다.

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