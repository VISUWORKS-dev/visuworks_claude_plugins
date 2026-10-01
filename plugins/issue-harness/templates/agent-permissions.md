# 에이전트 권한 범위 · 워크트리 필요 여부

issue-harness 플러그인의 역할 에이전트가 **쓸 수 있는 경로**와 **워크트리가 필요한지**를 정의한다.
플러그인은 `.claude/rules/`를 로드하지 않으므로 이 파일은 프로젝트에 있다(`/issue-harness:init`이 깐다).
경로 이름(`src_dirs` 등)은 `.claude/harness.config.json`의 값이다.

권한을 좁히는 이유는 에이전트를 불신해서가 아니라, 역할 경계가 무너지면 검증이 무력화되기 때문이다.

## 요약

| 에이전트 | 쓰기 허용 | 쓰기 금지 | 워크트리 | 커밋 |
|---|---|---|---|---|
| `issue-harness:issue-planner` | `<spec_dir>/issue-<N>.md` | 그 외 전부 | 불필요 | 안 함 |
| `issue-harness:contract-guardian` | `contract_skill` 디렉터리 | `src_dirs`, `tests_dir`<br>**상태 파일 전부** | 불필요 | 안 함 |
| `issue-harness:implementer` | `src_dirs`, `tests_dir`(`contract_tests_dir` 제외) | `contract_skill`<br>`contract_tests_dir`<br>**상태 파일 전부** | **필요** | **함** |
| `issue-harness:integration-qa` | **`contract_tests_dir`**<br>`_workspace/` | `src_dirs`<br>`tests_dir` 나머지<br>**상태 파일 전부** | 불필요 | 안 함 |
| `domain_agents`의 에이전트 | 각 항목의 `writes` | `src_dirs`, `tests_dir`<br>**상태 파일 전부** | 불필요 | 안 함 |

전원 공통 금지: **상태 파일 전부**(`state.json`·`events.jsonl`·`ACTIVE`), `git push`,
PR 생성, **머지**(로컬 머지·기본 브랜치 머지 둘 다), 의존성 변경, `.claude/rules/`, `.gitignore`,
`.githooks/`, CI 설정. (`issue-harness:issue-workflow` 7·8절)

> **로컬 머지는 오케스트레이터가 한다** — 에이전트가 아니므로 위 금지에 걸리지 않는다.
> 워크트리 → 이슈 브랜치 머지와 머지 후 `check_cmd`가 오케스트레이터 소관이고,
> push·PR·기본 브랜치 머지만 사람이 한다.

## 왜 이렇게 나누는가

**`integration-qa`는 제품 코드를 못 쓴다.** 도구 권한상으로는 가능하지만 금지한다.
검증자가 구현하면 자기 구현을 자기가 검증하는 구조가 되어 검증이 무력화된다.
검증 스크립트는 `_workspace/`에 쓴다 — 제품 코드가 아니므로 허용.

**테스트 디렉터리를 둘로 나눈 이유.** 계약 TDD에서 실패 테스트를 먼저 쓰는 것은 `integration-qa`다 —
구현자가 쓰면 자기 설계에 맞춘 테스트가 되어 구현이 틀려도 같이 틀린다. 그래서
`contract_tests_dir`는 QA가 소유하고 구현자는 고칠 수 없다. 반대로 단위 테스트는 구현 세부에
붙으므로 구현자가 소유한다. 계약(무엇을)과 구현(어떻게)의 분리가 테스트에도 그대로 적용된다.

**`implementer`는 계약 문서를 못 쓴다.** 구현하다 계약이 불편하면 바꾸고 싶어진다.
직접 바꾸면 같은 계약을 읽는 다른 모듈이 조용히 깨진다. `contract-guardian`에게 요청한다.

**`contract-guardian`·도메인 에이전트는 제품 코드를 못 쓴다.**
"무엇을/어떤 형식으로"의 결정권자가 구현까지 하면 결정과 구현이 한 사람 안에서 섞여
계약이 구현 편의에 맞춰 흔들린다.

**`issue-planner`는 spec 파일 하나만 쓴다.** 메시지 전달이 수백 행 본문을 잘라 테스트 목록이
승인 게이트에 도달하지 못하므로 반환이 아니라 직접 쓴다. 계획을 쓰는 것과 제품 코드를 고치는 것은 다른 일이다.

## 워크트리 판정 기준

**제품 코드를 쓰는 에이전트만 워크트리가 필요하다.** → `implementer` 하나.

- 워크트리의 목적은 **이슈 브랜치 오염 방지**와 **병렬 이슈 격리**다. 제품 코드를 안 쓰는
  에이전트는 오염시킬 것이 없다.
- 워크트리는 생성 비용이 있다(첫 `check_cmd`에서 의존성 설치 디렉터리 생성). 이득 없이 비용만 내지 않는다.
- `.claude/`·`.harness/`·`docs/`는 이슈 브랜치에서 오케스트레이터가 관리한다. 여러 워크트리가
  같은 계약 문서를 각자 고치면 병합 충돌이 난다.

### `implementer`의 워크트리 규칙

- 생성: 오케스트레이터가 `Agent(subagent_type: "issue-harness:implementer", isolation: "worktree")`로 부른다.
  기준점은 primary의 현재 HEAD다(`.claude/settings.json`의 `worktree.baseRef: "head"`).
- 의존성 설치 디렉터리는 그 워크트리 전용이다. **의존성 추가 금지** — 사람의 결정이다.
  필요하면 **보고에** blocker(`owner: "human"`)로 올리고 멈춘다.
- 자신의 워크트리 브랜치에만 커밋한다. 이슈 브랜치에 커밋하지 않는다.
- 커밋까지 하고 멈춘다. push·PR 명령은 **보고에** 적고, 오케스트레이터가 `handoff_to_human`에 옮긴다.

## 상태 기록 — 전원 동일하다

**에이전트는 어떤 상태 파일도 쓰지 않는다.** `state.json`은 오케스트레이터만, `events.jsonl`은
훅만 쓴다. 여럿이 같은 JSON을 읽고-고치고-쓰면 정본이 갈라진다.

| | 전원 |
|---|---|
| `state.json` | **쓰지 않는다** |
| `events.jsonl` | **쓰지 않는다** — 최종 보고를 훅이 저장한다 |
| 필요한 상태 | **오케스트레이터가 프롬프트에 담아 준다.** 없으면 추측하지 말고 요청한다 |
| 자기 진행·발견 | **최종 보고에** 적는다 |

`phase`·`sub_stage`·`status` 전이는 **오케스트레이터만** 바꾼다. 상세: `issue-harness:harness-state`.

## 커밋 규약은 git hook이 강제한다

`.githooks/`(`core.hooksPath`)가 모든 워크트리에 적용된다. 에이전트가 우회할 수 없다:

- `commit-msg` — `[behavioral] T<n>:` / `[structural]` / `[handoff]` / `[chore]` 외 차단.
  `[structural]`이 `tests_dir`를 건드리면 차단.
- `pre-commit` — 테스트 함수 순삭, `skip`/`xfail` 추가, `assert` 순삭 차단.

`--no-verify`는 `.claude/settings.json`의 `permissions.deny`로 막혀 있다. 사람만 터미널에서 쓴다.
