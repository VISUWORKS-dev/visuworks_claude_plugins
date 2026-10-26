# issue-harness

이슈 하나를 **계획 → 계약 확정 → 테스트 목록 TDD 구현 → 2단계 검증 → 로컬 머지**까지 태우는
멀티 에이전트 하네스. 경계면 불일치를 마감 직전이 아니라 모듈 완성 직후에 잡는 것이 목표다.

- 작업 단위: GitHub 이슈 = 워크트리 = PR
- 진행 정본은 git 로그(spec·계약 테스트·`Tests: T<n>` 커밋·머지 커밋). `.harness/issue-<N>/state.json`은
  사람 질문·블로커·인계만(오케스트레이터만 씀), `events.jsonl`은 경과(훅만 append)
- 구현자는 `isolation: worktree` 서브에이전트, 모듈 묶음마다 오케스트레이터가 "go". 항목마다 관련 테스트만, 묶음 끝에 `check_cmd` 1회
- 경로 둘: **full**(계약 신설·변경) — 계약 테스트 선작성, 무컨텍스트 → 컨텍스트 2단계 검증.
  **light**(화면 수정·기존 계약 소비) — 계약 단계·`3c`·무컨텍스트 검증 생략, 컨텍스트 검증 1회
- 역할별 모델(`models`) — 계획·계약·컨텍스트 검증 opus, 구현·QA·무컨텍스트 검증 sonnet, 탐색 haiku
- 커밋 규약(팀 전역 템플릿 `<타입> : <제목>` + 기능 커밋의 `Tests: T<n>` 꼬릿말)과 선언 없는 테스트 삭제·변경 차단은 git hook이 강제

설계와 결정 근거: [`docs/design.md`](docs/design.md)

## 구성

| 종류 | 이름 | 역할 |
|---|---|---|
| 스킬 | `issue-harness:issue-harness` | 오케스트레이터. 트리거 |
| 스킬 | `issue-harness:harness-state` | state.json 스키마·전이 규칙·재개 절차 |
| 스킬 | `issue-harness:verification-protocol` | 2단계 검증·계약 TDD |
| 스킬 | `issue-harness:tdd-cycle` | 테스트 목록 한 항목씩 |
| 스킬 | `issue-harness:scope-guard` | 범위 절제 판정 |
| 스킬 | `issue-harness:issue-workflow` | 브랜치·핸드오프·워크트리·로컬 머지 |
| 스킬 | `/issue-harness:init` | 프로젝트에 설정 깔기 (사람이 직접 호출) |
| 에이전트 | `issue-harness:issue-planner` | 이슈 → spec(테스트 목록) |
| 에이전트 | `issue-harness:contract-guardian` | 경계면 계약 소유 |
| 에이전트 | `issue-harness:implementer` | 격리 워크트리에서 TDD 구현·커밋 |
| 에이전트 | `issue-harness:integration-qa` | 계약 테스트 선작성, 경계면·2단계 검증 |
| 훅 | `SubagentStop`, `PostToolUse`(`SendMessage`) | 에이전트 종료와 에이전트가 보낸 메시지(팀원 보고)를 `events.jsonl`에 기록 |

## 설치

```
/plugin marketplace add VISUWORKS-dev/visuworks_claude_plugins
/plugin install issue-harness@visuworks-marketplace
```

### 프로젝트 단위로 켜기

레포의 `.claude/settings.json`에 넣으면 그 레포를 연 사람에게 마켓플레이스와 플러그인이 적용된다
(워크스페이스 신뢰 후에만 — 신뢰 전·`-p` 실행에서는 무시된다):

```json
{
  "extraKnownMarketplaces": {
    "visuworks-marketplace": {
      "source": { "source": "github", "repo": "VISUWORKS-dev/visuworks_claude_plugins" }
    }
  },
  "enabledPlugins": { "issue-harness@visuworks-marketplace": true }
}
```

### 업그레이드

```
claude plugin marketplace update visuworks-marketplace
claude plugin update issue-harness@visuworks-marketplace
```

Claude Code를 재시작한 뒤, 하네스를 쓰는 레포마다 `/issue-harness:init`을 다시 실행한다 —
훅·설정은 프로젝트에 깔린 사본이라 플러그인 업데이트만으로는 바뀌지 않는다
([기존 프로젝트 업그레이드](skills/init/SKILL.md#기존-프로젝트-업그레이드)).

- **진행 중인 이슈는 끝낸 뒤 업그레이드한다.** 0.2.0에서 `state.json` 스키마가 바뀌었다(진행 지점은 git 로그로 복원).
  옛 형식(`phase` 키)의 `state.json`은 새 오케스트레이터가 이어받지 못한다 — init이 경고한다
- 새 설정 키 `models`·`test_file_cmd`는 생략해도 된다. 넣으면 역할별로 싼 모델을 쓰고 항목마다 관련 테스트만 돌려
  검증 비용이 준다(아래 [`harness.config.json`](#claudeharnessconfigjson))

### 개발 중 로컬 로드

```
claude --plugin-dir <이 레포>/plugins/issue-harness
```

## 프로젝트에 깔기 — `/issue-harness:init`

레포 루트에서 `/issue-harness:init`을 실행한다. 이미 있는 파일은 덮어쓰지 않고 diff만 보여준다
(`harness.config.json`은 값을 채워 쓰는 파일이라 있으면 비교도 하지 않는다).
두 번째 실행은 아무것도 쓰지 않는다. `--dry-run`으로 미리 볼 수 있다.

| 깔리는 것 | 왜 프로젝트에 있어야 하나 |
|---|---|
| `.claude/harness.config.json` | 프로젝트 값 — 아래 |
| `.claude/rules/agent-permissions.md` | 플러그인은 `.claude/rules/`를 로드하지 않는다 |
| `.githooks/` + `core.hooksPath` | `core.hooksPath`에 플러그인 캐시 경로를 걸면 버전이 바뀔 때마다 깨진다 |
| `.claude/settings.json`의 `permissions.deny`, `worktree.baseRef: "head"` | 플러그인 `settings.json`은 `agent`·`subagentStatusLine`만 반영된다 |
| `.gitignore`의 `.harness/`, `.claude/worktrees/`, `_workspace/` | |

`settings.json`·`.gitignore`·`CLAUDE.md`가 이미 있으면 넣을 내용만 출력한다.
`CLAUDE.md`에 붙일 조각: `templates/claude-md-snippet.md`.

## `.claude/harness.config.json`

tracked 파일이다. 오케스트레이터·에이전트(모델)와 git hook(스크립트)이 같은 값을 읽는다.

```jsonc
{
  "model": "opus",                         // models에 없는 호출(도메인 에이전트 등)의 model. 생략하면 넣지 않는다
  "models": {                              // 역할별 model. 없는 키는 model로 간다
    "plan": "opus",                        // issue-planner
    "contract": "opus",                    // contract-guardian
    "verify_spec": "opus",                 // 4b 컨텍스트 검증
    "implement": "sonnet",                 // implementer — haiku 금지(재시도 1회가 check_cmd 1회)
    "qa": "sonnet",                        // 3a-test·3c
    "verify_blind": "sonnet",              // 4a 무컨텍스트 검증
    "explore": "haiku"                     // 오케스트레이터의 탐색용 Agent(Explore 등)
  },
  "check_cmd": "make check",               // 전체 검증 (lint + typecheck + test 등). 묶음 끝·4c·4e
  "test_file_cmd": "uv run pytest -q {files}",  // 항목별 부분 테스트. {files}에 테스트 파일 경로. 없으면 check_cmd
  "contract_test_cmd": "uv run pytest tests/contract/ -v",  // 계약 테스트 실패 확인
  "src_dirs": ["src/"],                    // 구현자 쓰기 허용
  "tests_dir": "tests/",                   // 테스트 변경 선언 검사·refact/style 커밋의 변경 금지 대상
  "contract_tests_dir": "tests/contract/", // integration-qa 소유
  "spec_dir": "docs/specs",                // spec = <spec_dir>/issue-<N>.md
  "branch_pattern": "<N>-<slug>",          // 이슈 브랜치 이름 규칙
  "contract_skill": null,                  // 계약 정본 스킬 이름. null이면 spec의 계약 절이 정본
  "domain_agents": [                       // 팀에 넣을 프로젝트 에이전트
    // { "name": "my-domain-expert", "decides": "무엇을 담을지", "writes": ["docs/", "_workspace/"] }
  ],
  "domain_skills": {                       // 코어 스킬이 함께 읽을 프로젝트 보충
    // "scope": "my-scope-notes",          // scope-guard의 프로젝트 사례
    // "workflow": "my-issue-order"        // 이슈 의존 순서
  },
  "dependency_change": "human"             // 의존성 추가는 사람만
}
```

파일이 없으면 오케스트레이터는 멈추고 `/issue-harness:init`을 안내한다. git hook은 기본값(`tests/`)으로 돈다.

## 상태 검사

오케스트레이터가 `state.json`을 쓸 때마다 돌린다. 터미널에서 직접 돌리려면 플러그인 경로가 필요하다:

```bash
python3 "$(claude plugin list --json | python3 -c 'import json,sys;print(next(p["installPath"] for p in json.load(sys.stdin) if p["id"]=="issue-harness@visuworks-marketplace"))')/scripts/check-state.py"
```

경로는 플러그인 버전마다 바뀐다 — Makefile 등에 고정하지 않는다.

## 훅의 동작 범위

훅(`SubagentStop`, `SendMessage`의 `PostToolUse`)은 플러그인이 켜진 **모든 세션**에서 발화한다. git 레포가 아니거나
`.harness/ACTIVE`가 없으면 로그도 남기지 않고 끝난다. 하네스 안에서의 기록·건너뜀·실패는
`~/.claude/harness-hook.log`(`HARNESS_HOOK_LOG`로 변경)에 남는다.

한계: auto 모드 등에서 서브에이전트가 `SubagentHandback`으로 보고하면 훅이 받는
`last_assistant_message`는 보고가 아니라 맺음말이다. 그때 오케스트레이터는 완료 알림의 결과를 정본으로 쓴다.

## 검증

```
claude plugin validate plugins/issue-harness
```
