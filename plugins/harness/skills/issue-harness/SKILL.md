---
name: issue-harness
description: "이슈 하나를 계획 → 계약 확정 → 테스트 목록 TDD 구현 → 2단계 검증 → 로컬 머지까지 태우는 멀티 에이전트 오케스트레이터. '이슈 N 시작', '이슈 N 구현', '이 기능 만들어'(이슈가 있는 레포), 'QA만 다시 돌려', '계약 다시 확인', '이 부분만 다시', 재실행·재개·보완, 경계면 불일치 조사, 마감 전 최종 점검 요청 시 사용. .claude/harness.config.json이 있는 프로젝트에서 동작한다."
---

# Issue Harness — 오케스트레이터

이슈 하나를 받아 계획 → 구현 → 검증까지 태운다. 경계면 불일치를 마감 직전이 아니라
모듈 완성 직후에 잡는 것이 목표다.

## 프로젝트 설정 — 먼저 읽는다

```bash
cat .claude/harness.config.json
```

없으면 멈추고 `/harness:init`을 안내한다. 이후 이 문서의 `<키>`는 그 파일의 값이다.

| 키 | 쓰는 곳 |
|---|---|
| `model` | 모든 `Agent`·`TeamCreate` 호출의 `model`. 없으면 넣지 않는다 |
| `check_cmd` | `4c`·`4e`, 구현자의 커밋 전 검증 |
| `contract_test_cmd` | `3a-test`의 실패 확인 |
| `src_dirs`·`tests_dir`·`contract_tests_dir` | 권한, 프롬프트 |
| `spec_dir` | spec 경로 `<spec_dir>/issue-<N>.md` |
| `contract_skill` | 계약 정본 스킬. `null`이면 spec의 「이 이슈가 확정하는 계약」 절이 정본 |
| `domain_agents` | 팀에 넣을 수 있는 프로젝트 에이전트와 결정 범위 |
| `domain_skills.scope`·`.workflow` | 범위 판정 사례, 이슈 의존 순서 |

**에이전트에게는 필요한 값만 프롬프트에 담아 준다.** 에이전트가 설정을 찾으러 다니게 하지 않는다.

## 실행 모드: 하이브리드

| Phase | 모드 | 이유 |
|---|---|---|
| Phase 2 (계획) | 서브 에이전트 | 단일 플래너. 결과만 받으면 충분하고 팀 통신 오버헤드가 이득보다 크다 |
| Phase 3 (구현) | 에이전트 팀 + 격리 워크트리 서브에이전트 | 계약소유자↔도메인판단↔QA는 primary에서 팀으로 실시간 피드백한다. `implementer`는 오케스트레이터가 `isolation: worktree`로 부르는 서브에이전트라 팀에 넣지 않는다 — 모듈 묶음마다 오케스트레이터가 "go"를 보낸다 |
| Phase 4 (최종 검증) | 서브 에이전트 | 독립 QA. 팀에서 분리해야 검증이 구현에 물들지 않는다 |

## 에이전트 구성

| 에이전트 | subagent_type | 역할 | 참조 스킬 |
|---|---|---|---|
| `issue-planner` | `harness:issue-planner` | 이슈 → spec 문서 | `harness:issue-workflow`, `harness:scope-guard` |
| `contract-guardian` | `harness:contract-guardian` | 경계면 계약 소유 | `<contract_skill>` |
| `implementer` | `harness:implementer` | 구현·커밋 | `<contract_skill>`, `harness:tdd-cycle`, `harness:scope-guard` |
| `integration-qa` | `harness:integration-qa` | 경계면 검증 | `<contract_skill>`, `harness:verification-protocol` |
| `<domain_agents[].name>` | 그 이름 그대로 | 도메인 판단 (`decides`) | 프로젝트 정의 |

**모든 호출에 `name`을 준다** (예: `planner-<N>`, `impl-<N>`, `qa-<N>-blind`). 훅이 기록하는
`agent` 값이 호출 이름으로 고정되고, `SendMessage`의 대상이 된다.
`state.json`의 `agents` 키는 접두사 없는 역할 이름(`implementer`)으로 쓴다.

### 권한 · 워크트리

| 에이전트 | 쓰기 허용 | 워크트리 | 커밋 |
|---|---|---|---|
| `issue-planner` | `<spec_dir>/issue-<N>.md` 만 | 불필요 | 안 함 |
| `contract-guardian` | 계약 문서 | 불필요 | 안 함 |
| 도메인 에이전트 | `domain_agents[].writes` | 불필요 | 안 함 |
| `implementer` | `src_dirs`, `tests_dir` | **필요** | **함** |
| `integration-qa` | `contract_tests_dir`, `_workspace/` | 불필요 | 안 함 |

**`implementer`만 워크트리가 필요하다.** 제품 코드를 쓰는 유일한 에이전트이므로
이슈 브랜치 오염 방지·병렬 이슈 격리의 이득이 있다. 나머지는 이슈 브랜치에서 직접 호출한다 —
워크트리는 생성 비용이 있으므로 이득 없이 비용만 내지 않는다.

상세: `.claude/rules/agent-permissions.md`

## 상태 정본 — state.json + events.jsonl

**상태는 `state.json`, 경과는 `events.jsonl`을 읽는다.** 스키마와 갱신 규약은
**`harness:harness-state`** 스킬에 있다.

```
.harness/
├── ACTIVE                 # 작업 중인 이슈 디렉터리 이름 (예: issue-12)
└── issue-N/
    ├── state.json         # 계획·현재 상태. 오케스트레이터만 쓴다
    └── events.jsonl       # 경과. 훅만 append (SubagentStop·git hook)
```

**에이전트는 어떤 상태 파일도 쓰지 않는다.** 자기 진행과 발견한 `blockers`·
`open_questions`를 최종 보고에 적고, 오케스트레이터가 `state.json`에 옮긴다.
`phase`·`sub_stage`·`status` 전이도 **오케스트레이터만** 바꾼다.

**`events.jsonl`은 훅만 쓴다.** 최종 보고에 `evidence:`/`rationale:`을 적으면
훅이 원문을 남긴다.

**`state.json`을 쓴 뒤에는 반드시 검사한다:**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-state.py"
```

이슈 착수 시 오케스트레이터가 `state.json`을 초기화하고 `ACTIVE`를 쓴다.
**이슈가 끝나면 `ACTIVE`를 다음 이슈로 넘기거나 지운다** — 남겨 두면 이후 세션의
서브에이전트 기록이 끝난 이슈에 쌓인다.

## Phase × sub-stage × 담당

| phase | sub_stage | 담당 | 워크트리 |
|---|---|---|---|
| `0-context` | `0a-git-check` / `0b-state-read` | 오케스트레이터 | — |
| `1-prepare` | `1a-issue-read` / `1b-dependency-check` / `1c-branch` | 오케스트레이터 | — |
| `2-plan` | `2a-plan-draft` | `issue-planner` | 불필요 |
| | `2b-human-questions` | 오케스트레이터 (`AskUserQuestion`) | — |
| | `2c-handoff-commit` | 오케스트레이터 | — |
| `3-implement` | `3a-contract` | `contract-guardian` (+ 도메인 에이전트) | 불필요 |
| | `3a-test` | `integration-qa` — 실패 테스트 먼저 | 불필요 |
| | `3b-implement` | `implementer` | **필요** |
| | `3c-incremental-qa` | `integration-qa` | 불필요 |
| `4-verify` | `4a-verify-blind` | `integration-qa` (무컨텍스트) | 불필요 |
| | `4b-verify-spec` | `integration-qa` (컨텍스트, 다른 인스턴스) | 불필요 |
| | `4c-make-check` / `4d-placeholder-scan` | 오케스트레이터 | — |
| | `4e-merge` — 로컬 머지 + 머지 후 `check_cmd` | 오케스트레이터 | — |
| `5-report` | `5a-report` / `5b-human-handoff` | 오케스트레이터 | — |

`4c-make-check`는 식별자다 — 실제 명령은 `check_cmd`다.

`3a` → `3a-test` → `3b` → `3c` 순서다. `3b`↔`3c`는 모듈 묶음 단위로 반복한다 —
묶음 하나 완성 → 즉시 검증 → 다음 묶음 "go" (Phase 3 「`3b`↔`3c` 루프」).

`4a`(무컨텍스트) → `4b`(컨텍스트) 순서를 **뒤집지 않는다.** 명세를 먼저 읽으면 코드를
그 명세대로 보게 되는 확증편향이 생기고, 그러면 두 번 볼 이유가 없어진다.
상세: `harness:verification-protocol`.

## 다음 에이전트 호출 판단 — 훅이 아니라 오케스트레이터가 한다

**훅을 쓰지 않는 이유:** 훅은 `PostToolUse`·`SubagentStop` 같은 **도구 이벤트**에 붙는다.
"계약이 확정됨", "이 모듈은 검증 준비가 됨"은 도구 이벤트가 아니라 의미적 판단이다.
훅이 이걸 판정하려면 훅 스크립트 안에 오케스트레이션 로직을 복제해야 하고, 훅은 실패해도
조용하고 디버깅이 어렵다. **오케스트레이터가 `state.json`을 읽고 판정한다.**

훅은 판단이 필요 없는 기계적 게이트에만 쓴다 (예: 커밋 메시지 형식, 테스트 약화 차단).

### 전이 판정 순서

**정본은 `harness:harness-state` 「전이 규칙」이다.** 에이전트가 끝날 때마다 1번부터 순서대로
적용하고 먼저 걸리는 것에서 멈춘다. 여기에 규칙을 다시 적지 않는다 — 두 곳에 두면 갈라진다.

## 워크플로우

### Phase 0: 컨텍스트 확인

**먼저 상태를 확인한다.** 세션 재개·컴팩션·워크트리 진입 후에는 가정이 틀어져 있다.

```bash
git status --short --branch              # 0a: 의도한 브랜치인가
pwd                                      # 워크트리인가 primary checkout인가
cat .claude/harness.config.json          # 프로젝트 값
cat .harness/ACTIVE                      # 0b: 어느 이슈가 활성인가
cat .harness/issue-<N>/state.json        # 0b: 어디까지 했는가 (정본)
tail -20 .harness/issue-<N>/events.jsonl # 0b: 무슨 일이 있었는가 (경과)
```

`state.json`이 있으면 **그것이 진행 지점의 정본이다.** `phase`/`sub_stage`부터 이어서 한다.
`status`가 `in_progress`인데 `updated_at`이 오래됐으면 그 에이전트는 죽었다 —
`failed`로 바꾸고 재호출하거나 재할당한다.

`ACTIVE`가 요청받은 이슈와 다르면 이전 이슈의 상태를 확인한다. 끝났으면 `ACTIVE`를 넘긴다.

끝났다고 기록된 것을 다시 하지 않는다. 단 `integration-qa`의 "수정했다" 주장은 재확인한다.

실행 모드 판정:

| 상태 | 모드 |
|---|---|
| `<spec_dir>/issue-<N>.md` 없음 | **초기 실행** — Phase 1로 |
| 있음 + 사용자가 부분 수정 요청 | **부분 재실행** — 해당 에이전트만 호출. 기존 산출물 중 수정 대상만 갱신 |
| 있음 + 새 입력 제공 | **갱신 실행** — 기존 계획을 읽고 증분 갱신. 덮어쓰지 않는다 |
| 있음 + 구현 미착수 | **구현 재개** — Phase 3으로 직행 |

부분 재실행 시 이전 산출물 경로를 에이전트 프롬프트에 포함해, 에이전트가 기존 결과를 읽고
피드백만 반영하게 한다.

### Phase 1: 준비

1. 이슈 번호 확정. 불명확하면 `gh issue list`로 확인하고 사용자에게 묻는다.
2. `gh issue view <N>`으로 본문을 읽는다. 연관 이슈가 언급되면 그것도 읽는다.
3. **선행 이슈 확인** — `domain_skills.workflow`가 있으면 그 스킬의 의존 순서를 본다.
   선행 계약이 미확정이면 사용자에게 알리고 진행 여부를 확인한다. 추측으로 진행하면 재작업이다.
4. 이슈 브랜치 확인·생성 (`branch_pattern`).
5. `_workspace/` 생성 (중간 산출물 보관. 갱신 실행이면 기존 것을 `_workspace_<타임스탬프>/`로 이동).
6. **`state.json` 초기화** — `harness:harness-state`의 초기화 블록을 따른다. `ACTIVE`를 이 이슈로 쓴다.
   이후 모든 단계 전이에서 `phase`·`sub_stage`·`updated_at`을 갱신한다.

### Phase 2: 계획

**실행 모드: 서브 에이전트**

```
Agent(
  subagent_type: "harness:issue-planner",
  name: "planner-<N>",
  model: <model>,
  prompt: "이슈 #<N>의 작업 계획을 작성한다. <이슈 본문>.
           계약 정본: <contract_skill 또는 '없음 — spec에 계약 절을 쓴다'>.
           범위 판정: harness:scope-guard (+ 프로젝트 사례: <domain_skills.scope>).
           마감: <있으면 날짜>.
           **<spec_dir>/issue-<N>.md 에 본문을 직접 써라** (Write 툴). 그 파일 하나만
           쓴다 — 제품 코드·테스트·.harness/ 는 건드리지 않는다.
           보고는 짧게: 파일 경로, 테스트 목록 항목 수, open_questions 개수,
           contract-guardian 판정 대기 항목. **본문을 보고에 붙이지 마라.**"
)
```

**`2a-plan-draft`.** `issue-planner`가 spec을 직접 쓴다.
오케스트레이터는 그 파일을 읽고 상태 정보를 `state.json`에 기록한다:
`agents.issue-planner`, `open_questions`, 계약 공백은 `blockers`.

> **본문을 반환받지 않는 이유:** spec은 수백 행이고 메시지 전달이 자른다.
> `## 테스트 목록`이 잘리면 사람 승인 게이트에 올릴 것이 없어진다.

**사람 입력이 필요한 항목이 계획에 있으면 여기서 멈추고 묻는다.** `TODO(확인필요)`를
그대로 두고 구현에 들어가면, 구현자가 추측으로 채운다. 추측으로 채운 것은 그럴듯해 보여서
아무도 다시 묻지 않는다 — 가장 비싼 실수다.

**`2b-human-questions`.** `AskUserQuestion`으로 묻는다 — 항목별 선택지 2~4개.
줄글 질문으로 끝내지 않는다. 받은 답을 `state.json`의 `open_questions[].answer`에 채운다.
`answer: null`이 남아 있으면 `3b`로 가지 않는다.

**같은 게이트에서 테스트 목록 승인도 받는다.** spec 문서의 `## 테스트 목록`을 사람에게
보여주고 승인받는다. 구현자는 이 목록 안에서만 움직이고 기대값을 바꿀 수 없으므로
(`harness:tdd-cycle`), 승인 없이 구현에 들어가면 **사람이 확정하지 않은 기대값이 정본이 된다.**
항목이 틀렸거나 빠졌다는 지적을 받으면 `issue-planner`에게 되돌린다.

### Phase 3: 구현

**실행 모드: 에이전트 팀**

**`2c-handoff-commit`** — spec만 `[handoff]` 커밋 (`harness:issue-workflow` 3절).

```bash
git add <spec_dir>/issue-<N>.md
git commit -m "[handoff] 이슈 #<N> spec — 테스트 목록 <n>항목"
```

**워크트리로 가는 것은 셋이다.**

| 무엇 | 어떻게 |
|---|---|
| spec·계약 테스트 | tracked — 핸드오프 커밋으로. 워크트리는 primary의 **현재 HEAD**에서 갈라진다 |
| 구현자의 역할·규칙·보고 형식 | `subagent_type: "harness:implementer"`로 적용 |
| 이번 단위에만 해당하는 정보 + 프로젝트 값 | 오케스트레이터가 프롬프트에 담는다 (아래 템플릿) |

`.harness/`(런타임 상태)는 gitignore라 따라오지 않는다. 구현자는 상태 파일을 읽지도
쓰지도 않는다. 돌아온 보고는 **오케스트레이터가 primary의 `state.json`에 반영한다.**
경과는 `SubagentStop` 훅이 primary에 기록한다.

**`3a-contract` → `3a-test` → `3b-implement` → `3c-incremental-qa`.**

**`3a-test` — 계약 TDD.** 계약이 `confirmed`가 되면 `integration-qa`가 `contract_tests_dir`에
실패 테스트를 먼저 쓴다. 스키마 필드·빈 결과·None·상태값·경로 같은 **형태**만 건다.
비결정적 출력의 내용(생성된 문안의 품질 등)은 assert하지 않는다.
QA가 쓰는 이유는 구현자가 쓰면 자기 설계에 맞춘 테스트가 되기 때문이다.
반드시 `contract_test_cmd`로 실패를 확인하고 `3b`로 넘긴다. 상세: `harness:verification-protocol`.

`3a`가 끝나기 전에 `3b`를 시작하지 않는다 (`harness:harness-state` 전이 규칙 4번).

**`3b` 프롬프트를 조립하는 것이 오케스트레이터의 일이다.** 구현자는 워크트리에 있어
`.harness/`를 못 본다.

#### `3b`↔`3c` 루프 — 오케스트레이터가 모듈 묶음마다 "go"를 보낸다

spec의 `## 테스트 목록`은 **모듈(경계면) 묶음**으로 나뉘어 있다(`issue-planner`가 묶는다).
한 번의 "go"가 한 묶음이다. 묶음이 끝날 때마다 `3c`를 거친 뒤에만 다음 "go"를 보낸다 —
Kent Beck의 Augmented Coding에서 사람이 테스트마다 "go"를 말하는 자리를 오케스트레이터가 맡는다.

```
① 첫 묶음 — 워크트리 생성과 기동이 한 번에 된다
Agent(
  subagent_type: "harness:implementer",
  isolation: "worktree",
  name: "impl-<N>",
  run_in_background: true,
  model: <model>,
  prompt: <템플릿>
)
   → 완료 알림: 결과(최종 보고) + 워크트리 경로·브랜치

② 오케스트레이터 판정
   - 보고·커밋을 state.json에 옮긴다 (agents.implementer: name·worktree·branch·status)
   - git -C <워크트리> log --oneline <이전>..HEAD 로 커밋 확인
   - 3c: integration-qa에게 <워크트리 경로>와 이 묶음의 경계면을 주고 검증시킨다
   - harness:harness-state 전이 규칙 1번부터 적용

③ 다음 묶음 — 같은 워크트리·같은 맥락에서 이어진다
SendMessage(to: "impl-<N>", message: <템플릿 — 다음 묶음, 3c 지적은 [이전 실패 원인]>)
   → 완료 알림 → ② …
```

**부르기 직전에 브랜치를 확인한다.** 워크트리는 primary의 **현재 HEAD**에서 갈라진다
(`.claude/settings.json`의 `worktree.baseRef: "head"`). `git branch --show-current`가
이슈 브랜치이고 핸드오프 커밋이 들어가 있어야 한다. 설정이 없으면 기본 브랜치에서 갈라져
spec도 계약 테스트도 없는 워크트리가 된다.

**템플릿 — 프롬프트에는 이번 묶음에만 해당하는 것만 담는다.** 규칙·권한·보고 형식은
정의 파일에서 들어오므로 다시 쓰지 않는다 — 두 곳에 두면 갈라진다.

```
이슈 #<N>의 모듈 묶음 <M1: 이름> (<T1>~<T3>)을 구현한다.

[spec] <spec_dir>/issue-<N>.md 의 <M1> — 워크트리에 커밋돼 있다
[프로젝트 값] check_cmd=<…>, src_dirs=<…>, tests_dir=<…>, contract_tests_dir=<…>
[계약] 이 묶음이 소비·생산하는 스키마만 발췌 (<contract_skill>)
[답변된 전제] open_questions 중 answer가 있는 것만
[이전 실패 원인] 재호출·3c 지적이 있을 때만
[주의] 이 묶음에 걸리는 기존 blocker
```

- **묶음은 한 번에 하나다.** 다음 묶음은 `3c`를 거친 뒤 `SendMessage`로 보낸다.
- **spec을 발췌하지 않는다.** 이미 워크트리에 있다 — 경로와 묶음 ID만 준다.
- **`answer: null`인 `open_questions`는 넘기지 않는다** — 먼저 `AskUserQuestion`으로 묻는다.
- **이전 실패 원인을 빼먹지 않는다.** 없으면 같은 실패를 반복한다.

**완료 알림은 "끝났다"만 뜻한다.** 막혀서 멈춘 것과 끝낸 것을 구별하지 않는다. 진척과
성공 여부는 보고의 `result:`·커밋·`3c`로 판정한다.

1. 팀 구성 — **primary에서 도는 에이전트(`contract-guardian`·도메인 에이전트·`integration-qa`)로만
   꾸린다.** `implementer`는 위 루프로 직접 부르는 격리 워크트리 서브에이전트다 —
   팀원과 직접 주고받지 않고 오케스트레이터가 잇는다.
   이슈 성격에 따라 팀원을 고른다. 전원 투입이 기본값이 아니다.

   | 이슈 유형 | 팀 (primary) | 격리 워크트리 |
   |---|---|---|
   | 문서·프로세스 정의 | 팀 없음 — 도메인 에이전트 서브에이전트 | — |
   | 계약 신설·변경을 포함 | `contract-guardian` + 도메인 에이전트 + `integration-qa` | `implementer` |
   | 기존 계약 소비 | `integration-qa` + (도메인 판단 필요 시 도메인 에이전트) | `implementer` |
   | 여러 단계 통합 | `contract-guardian` + `integration-qa` | `implementer` |

   팀원이 1명이면 팀을 만들지 않고 서브에이전트(`Agent`)로 부른다.

   ```
   TeamCreate(
     team_name: "issue-<N>",
     members: [
       { name: "contract", agent_type: "harness:contract-guardian", model: <model>, prompt: "..." },
       { name: "domain",   agent_type: "<domain_agents[0].name>",   model: <model>, prompt: "..." },
       { name: "qa",       agent_type: "harness:integration-qa",    model: <model>, prompt: "..." }
     ]
   )
   ```

   팀이 플러그인 에이전트 타입을 받지 않으면 같은 역할을 `Agent` 서브에이전트로 부르고,
   팀원 간 통보는 오케스트레이터가 `SendMessage`로 잇는다.

2. 작업 등록 — spec 문서의 작업 단위 중 **팀이 하는 것만** 옮긴다. 구현 단위는 팀 작업이
   아니다 — 오케스트레이터가 위 루프로 넘긴다.
   ```
   TaskCreate(tasks: [
     { title: "<계약 확정>",       assignee: "contract" },
     { title: "<계약 테스트 작성>", assignee: "qa", depends_on: ["<계약 확정>"] },
     { title: "<경계면 검증>",     assignee: "qa" }   // 구현 커밋 확인 후 오케스트레이터가 시작
   ])
   ```

3. 팀 통신 규칙 — 팀원 프롬프트에 명시한다:
   - 계약이 미확정이면 `contract`가 먼저 확정하고 **팀 전원에게 통보한다.** 통보 없는 계약 변경이
     가장 비싼 실수다. 워크트리의 구현자에게는 오케스트레이터가 다음 "go"에 담는다.
   - **구현 묶음이 끝나면 오케스트레이터가 커밋을 확인하고 `qa`를 호출한다**(`3c`).
     `qa`에게 워크트리 경로를 준다 — 구현 코드는 primary가 아니라 워크트리에 있다.
     묶음마다 확인한다 — 전체 완성 후 한 번에 검증하면 경계면 버그를 마감 직전에 발견한다.
   - `qa`가 `demo_blocker` 등급을 찾으면 오케스트레이터에게도 즉시 알린다.
   - 구현자는 도메인 판단·의존성 추가가 필요하면 스스로 정하지 않고 **멈추고 보고한다**.
     오케스트레이터가 도메인 에이전트에 묻거나 사람에게 올리고, 답을 다음 프롬프트에 담는다.
   - **팀원은 상태 파일을 쓰지 않는다.** 진행·`blockers`·`open_questions`를 최종 보고에
     `evidence:`/`rationale:`과 함께 적는다. 훅이 원문을 `events.jsonl`에 남기고, 오케스트레이터가
     `state.json`에 옮긴다. 보고하지 않으면 전이를 판정할 수 없고, 세션 재개 시 그 작업은 없던 일이 된다.

4. 오케스트레이터 모니터링 — 팀원 유휴 알림을 받으면 `state.json`·`events.jsonl`과 `TaskGet`으로
   진행률을 확인하고 막힌 팀원에게 `SendMessage`로 지시한다. 구현자는 묶음마다 완료 알림으로 받는다.
   에이전트가 끝날 때마다 **전이 판정 순서**를 적용한다.

### Phase 4: 최종 검증

**실행 모드: 서브 에이전트**

1. 팀 정리 (`TeamDelete`). 구현 산출물은 커밋·`_workspace/`에 남아 있다.
   **구현 팀에서 분리해서 호출하는 이유:** 팀 안에서 검증하면 검증자가 구현 맥락에 물들어
   "아마 될 것 같다"를 통과로 준다.

2. **`4a-verify-blind` — 무컨텍스트 검증.** 명세를 주지 않는다.
   ```
   Agent(
     subagent_type: "harness:integration-qa",
     name: "qa-<N>-blind",
     model: <model>,
     prompt: "이슈 #<N> '<제목>' 구현의 실제 동작을 기록한다.
              너는 명세·계약 문서·작업 계획을 받지 못한다. 요청하지도 마라.
              gh issue view, <contract_skill>, spec 문서를 읽지 않는다.
              코드와 테스트를 읽고 가능하면 돌려서 기록한다 —
              각 모듈이 실제로 내보내는 것(필드명·타입·중첩·nullable),
              실제로 기대하는 입력, 빈 입력·None·실패 시 동작, 모듈 간 실제 연결.
              맞다/틀리다를 판정하지 마라. 무엇을 하는지만 기록한다.
              → _workspace/verify_<N>_blind.md"
   )
   ```

3. **`4b-verify-spec` — 컨텍스트 검증.** **다른 인스턴스**로 호출한다.
   ```
   Agent(
     subagent_type: "harness:integration-qa",
     name: "qa-<N>-spec",
     model: <model>,
     prompt: "_workspace/verify_<N>_blind.md를 읽는다. 명세를 모르는 검증자가 기록한
              코드의 실제 동작이다. 이제 <contract_skill>, spec 문서, 이슈 #<N>을 읽고
              대조한다 — 실제 동작 vs 계약 요구, 계약에 있는데 1단계가 발견 못 한 것,
              1단계가 기록했는데 계약에 없는 것, spec 문서 완료 조건 충족 여부.
              불일치는 어느 쪽이 맞는지 임의 판정하지 말고 근거와 함께 보고한다.
              → _workspace/verify_<N>_spec.md"
   )
   ```

   **두 결과가 불일치하는 지점이 가장 값진 발견이다** — 명세와 구현이 갈라진 곳이다.
   `state.json`의 `verification.mismatches`에 개수를 기록한다.

4. **`4c-make-check`** — `check_cmd` 실행 및 결과 확인 (`contract_tests_dir` 포함).
5. **`4d-placeholder-scan`** — 완료 주장 전 확인. 변경된 파일에서 skip·only, 빈 assert,
   `pass`만 있는 함수, `TODO` 미구현 분기를 찾는다. 있으면 완료가 아니다. 구현하거나 블로커로 보고한다.

6. **`4e-merge`** — 오케스트레이터가 로컬 머지하고 primary에서 `check_cmd`.
   머지 조건·이유·"머지 전 계약 테스트 실패는 정상"은 **`harness:issue-workflow` 8절이 정본이다.**
   ```bash
   git switch <이슈브랜치>
   git merge --no-ff <워크트리브랜치> -m "[chore] 워크트리 브랜치를 이슈 브랜치에 반영한다 (#<N>)"
   <check_cmd>
   ```

### Phase 5: 정리 및 보고

1. `_workspace/`는 **보존한다** (사후 검증·감사 추적).
   `state.json`의 `phase`를 `5-report`, `status`를 `done`(또는 `blocked`)으로 갱신한다.
2. 사용자에게 보고한다:
   - 완료한 것 (검증된 것만)
   - 미완료·블로커 (있으면 명시적으로)
   - `TODO(확인필요)`로 남은 사람 입력 항목
   - **사람이 실행할 명령** — push·PR만. 로컬 머지는 `4e`에서 이미 했다

   ```
   머지·검증 완료. 다음 명령을 실행하세요:

     git push -u origin <이슈브랜치>
     gh pr create --base <기본 브랜치> --title "..." --body-file <경로>
   ```

   **워크트리 브랜치는 origin에 올리지 않는다** (`harness:issue-workflow` 8절).

3. 피드백 요청 — "결과나 팀 구성에서 바꾸고 싶은 점이 있나요?" 강요하지 않되 기회를 준다.

## 데이터 흐름

```
이슈 (#N)
   ↓ Phase 2 (서브)
issue-planner → <spec_dir>/issue-<N>.md
   ↓ 핸드오프 커밋
   ↓ Phase 3 (팀: contract·domain·qa / 격리 워크트리: implementer)
[contract] ←SendMessage→ [qa]        [implementer] (Agent isolation: worktree)
    ↓                       ↑            ↑ go(묶음)   ↓ 완료 알림
<contract_skill>     오케스트레이터 ── 커밋 확인 → qa 호출(3c) → 다음 go
   ↓ 4e 로컬 머지 (워크트리 브랜치 → 이슈 브랜치)
   ↓ Phase 4 (서브)
integration-qa → 최종 검증 보고 + check_cmd
   ↓ Phase 5
사람: push · PR
```

## 에러 핸들링

| 상황 | 전략 |
|---|---|
| `.claude/harness.config.json` 없음 | 멈추고 `/harness:init`을 안내 |
| 팀원 1명 실패 | 1회 재시작. 재실패 시 그 작업을 남은 팀원에게 재할당하고 보고서에 누락 명시 |
| 팀원 과반 실패 | 중단하고 사용자에게 진행 여부 확인 |
| `check_cmd` 실패 | 통과할 때까지 고친다. 테스트를 지우거나 skip해서 통과시키지 않는다 |
| 계약과 구현 충돌 | 임의 판정 금지. 더 많은 소비자가 따르는 쪽을 정본으로 제안하고 사용자에게 보고 |
| 도메인 정보 부재 | `TODO(확인필요)`로 남기고 `AskUserQuestion`으로 묻는다. 추측으로 채우지 않는다 |
| 의존성 추가 필요 | 의존성 매니페스트를 바꾸는 사람의 결정이라 에이전트가 실행하지 않는다. 멈추고 사람에게 보고 |
| 외부 의존 접근 불가 (다른 레포·외부 API) | 우회 구현을 만들지 말고 보고. 일정 리스크이므로 사람이 알아야 한다 |
| 선행 이슈 미완 | 진행 여부를 사용자에게 확인. 재작업 위험을 함께 알린다 |
| 계약 테스트가 작성 시점에 통과 | 비어 있는 테스트다. 다시 쓰게 하고 `3b`로 보내지 않는다 |
| `4a`가 명세를 요청 | 주지 않는다. 명세 없이 가능한 범위만 기록하게 한다 |
| `4a`·`4b` 불일치 | 어느 쪽이 맞는지 임의 판정 금지. 근거와 함께 사람에게 보고 |
| 구현자가 계약 테스트를 고치려 함 | 막는다. 구현을 고치거나 `contract-guardian`에게 계약 판단 요청 |

## 테스트 시나리오

**정상 흐름:**
1. "이슈 12 시작" → Phase 0에서 spec 없음 확인 → 초기 실행
2. Phase 1에서 선행 이슈 미완 감지 → 사용자에게 알리고 진행 확인
3. Phase 2에서 `issue-planner`가 계획 작성, `TODO(확인필요)` 3건 → `AskUserQuestion`으로 확인, 테스트 목록 승인
4. Phase 3에서 팀(`contract`·`domain`·`qa`) 구성 → 계약 확정·통보 → `qa`가 실패 테스트 →
   `implementer`를 `isolation: worktree`로 실행(묶음 1) → 완료 알림 → `qa` 검증 → `SendMessage`로 묶음 2 …
5. Phase 4에서 무컨텍스트 → 컨텍스트 검증, `check_cmd` 통과, 로컬 머지
6. Phase 5에서 push 명령 출력하고 멈춤

**에러 흐름:**
1. Phase 3에서 구현자가 외부 패키지 미설치로 import 실패
2. 의존성 추가는 사람의 결정 → 구현자가 최종 보고에 blocker로 적고 멈춤
3. 오케스트레이터가 사용자에게 설치를 요청 (사람이 실행할 명령 출력)
4. 해당 작업을 블로커로 표시하고, 의존성과 무관한 나머지 묶음은 계속 진행
5. Phase 5 보고에 "연동 미완 — 의존성 설치 대기" 명시
