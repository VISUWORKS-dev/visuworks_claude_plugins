# visuworks-work-manager

비쥬웍스 작업 컨텍스트 관리 플러그인. **메인 정본은 Obsidian vault**이고, Notion은
회의록·팀 공용 문서 작성과 정보 읽기 전용이다. **vault 경로와 Notion URL은 repo에
저장되지 않고 설치 시 입력받는다.**

## 역할 분담
- **Obsidian (메인)**: 규칙·상태·지식·이력의 모든 기록 → `obsidian-vault-manager` 스킬
- **Notion (보조)**: 회의록·팀 공용 문서 작성 + 정보 읽기 → `visuworks-work-manager` 스킬

## 구성
- `skills/obsidian-vault-manager/SKILL.md` — Obsidian vault 4-레이어 관리 스킬 (메인 기록소)
  - vault 구조: 전역 `claude.md`/`context.md`/`knowledge/` + `projects/<프로젝트>/`(context·history·knowledge)
  - Obsidian 네이티브: YAML frontmatter, [[위키링크]], 태그
  - 로컬은 바로 쓰기(사후 요약 보고), claude.md만 사전 승인
- `skills/visuworks-work-manager/SKILL.md` — Notion 쓰기 스킬 (회의록·공용 문서 한정)
- `hooks/hooks.json` + `scripts/gate-notion-search.sh` — 워크스페이스 검색 → 사용자 인가(ask) 게이트 (Cowork 전용)
- (별도 파일) `CLAUDE.md` — 각자 Cowork 프로젝트 루트에 두는 "항상 로드" 읽기 절차

## 설치 시 입력받는 값 (userConfig)
플러그인을 활성화하면 아래 값들을 물어본다. 값은 각자 환경에만 저장되고
공개 repo에는 들어가지 않는다. SKILL.md는 이를 `${user_config.*}`로 참조한다.
- `obsidian_vault_path` — 메인 기록소 Obsidian vault 절대 경로
- `claude_md_url` — 규칙·표준 정본
- `context_md_url` — 현재 상태 + 지식 문서 인덱스 정본
- `history_md_url` — 대화/작업 이력 정본
- `knowledge_parent_url` — 주제별 지식 문서 부모 페이지

## 훅 확인
설치 후 Cowork에서 `/hooks`로 `matcher`("mcp__.*notion.*search")가 실제 Notion 검색
도구 이름과 맞는지 확인한다. 다르면 실제 도구 id로 교체(필요 시 notion-query 계열 추가).

## CLAUDE.md (항상 로드) — 각자 로컬에서
동봉된 `CLAUDE.md`는 플러그인이 아니라 **각 사용자의 Cowork 프로젝트 루트**에 두는
로컬 파일이다. 여기의 URL은 **각자 로컬에서 채우며 공개 repo에 커밋하지 않는다.**
Cowork는 프로젝트 루트 CLAUDE.md를 매 메시지 자동 주입하므로 "시작 시 fetch" 절차가 항상 걸린다.

## history 정기 유지보수 (Cowork 예약 작업)
Cowork 예약 작업으로 주기 실행(예: 매주 금요일). history.md를 열어 이번 주 항목을 정리·
압축하고, 오래된 항목은 아카이브로 옮길지 제안한다. 변경 전 diff 요약 후 승인 규칙에 따라 기록.
※ 예약 작업은 대화 내용을 자동으로 알지 못한다 — 대화 캡처는 사람이 트리거하고,
   예약 작업은 쌓인 history.md의 정리·아카이브를 맡는다.
