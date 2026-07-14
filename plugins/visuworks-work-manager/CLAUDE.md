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
  4. 이어서 `<vault>/projects/<프로젝트>/index.md`(있으면) — 프로젝트 자산(지식 문서·첨부·소통 기록) 파악용
- 지식 문서(`knowledge/`)·`history.md`·`communications/`는 필요할 때만(on-demand) 읽는다.
- vault 경로에 접근할 수 없으면 사용자에게 해당 폴더 연결을 요청한다. 추측으로 다른 경로를 뒤지지 않는다.

## 프로젝트 범위 제한

- 프로젝트가 특정되면 vault 읽기·검색은 전역 `claude.md`/`context.md` + 해당
  `projects/<프로젝트>/` 폴더로 한정한다(프로젝트 내에서도 index.md 먼저, 필요한 문서만).
- 다른 프로젝트 폴더는 사용자가 명시적으로 요청했을 때만 읽는다.
- 전역 `knowledge/`는 프로젝트 무관 공용 지식이 필요할 때만 on-demand로 읽는다.

## 자동 기록 (명시 요청 없어도 적용)

- 대화에 파일이 첨부되면 obsidian-vault-manager 스킬로 해당 프로젝트에 원본 보관
  (`assets/`) + 마크다운 자료화를 진행한다(보관 의도가 보이면 바로, 다른 목적의
  첨부면 해당 작업 후 보관 여부를 한 번 제안).
- 외부 업체·부서와 주고받은 내용·파일 전달이 언급되면 소통 기록
  (`communications/<주제>.md`)을 남긴다.

## Notion (회의록·팀 공용 문서 전용)

- Notion에는 규칙·상태·지식·이력 레이어가 없다. 작업 컨텍스트를 Notion에서 찾지 않는다.
- Notion 읽기·쓰기는 사용자가 지정한 페이지에 한한다.
- 워크스페이스 전체 검색(notion-search)·쿼리(notion-query 계열)는 사용자 인가 없이 실행하지 않는다.

## 공통 원칙

- 저장·기록 요청은 기본적으로 Obsidian vault로(obsidian-vault-manager 스킬).
- 회의록·팀 공용 문서, "Notion에" 명시 요청만 Notion으로(visuworks-work-manager 스킬).
- 같은 내용을 두 저장소에 중복 기록하지 않는다.
