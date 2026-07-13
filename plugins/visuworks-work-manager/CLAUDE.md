# 비쥬웍스 작업 컨텍스트 — 항상 로드 (읽기 절차)

> **사용법**: 이 파일을 각자 Cowork 프로젝트 루트에 복사하고 아래 `<...>` 값을
> 로컬에서 채운다. **채운 파일은 공개 repo에 커밋하지 않는다.**
> 쓰기 절차는 플러그인 스킬이 담당한다(obsidian-vault-manager = 정본 / visuworks-work-manager = Notion 회의록·공용 문서).

## 정본: Obsidian vault (유일한 기록소)

- vault 경로: `<Obsidian vault 절대 경로>` (플러그인 userConfig와 동일 값)
- 세션 시작 시(작업 맥락이 필요한 첫 시점에) 다음을 읽는다:
  1. `<vault>/claude.md` — 전역 규칙·표준 (항상 준수)
  2. `<vault>/context.md` — 활성 프로젝트 목록 + 링크
  3. 현재 대화의 프로젝트가 특정되면 `<vault>/projects/<프로젝트>/context.md`
- 지식 문서(`knowledge/`)와 `history.md`는 필요할 때만(on-demand) 읽는다.
- vault 경로에 접근할 수 없으면 사용자에게 해당 폴더 연결을 요청한다. 추측으로 다른 경로를 뒤지지 않는다.

## Notion (회의록·팀 공용 문서 전용)

- Notion에는 규칙·상태·지식·이력 레이어가 없다. 작업 컨텍스트를 Notion에서 찾지 않는다.
- Notion 읽기·쓰기는 사용자가 지정한 페이지에 한한다.
- 워크스페이스 전체 검색(notion-search)·쿼리(notion-query 계열)는 사용자 인가 없이 실행하지 않는다.

## 공통 원칙

- 저장·기록 요청은 기본적으로 Obsidian vault로(obsidian-vault-manager 스킬).
- 회의록·팀 공용 문서, "Notion에" 명시 요청만 Notion으로(visuworks-work-manager 스킬).
- 같은 내용을 두 저장소에 중복 기록하지 않는다.
