---
name: harness-state
description: "하네스의 실행 상태 정본 — `.harness/issue-<N>/state.json` 스키마와 갱신 규약, events.jsonl 기록 훅, 전이 규칙. 에이전트 작업 시작·완료·차단 시 상태 기록, 다음 에이전트 호출 판단, 세션 재개·컴팩션 후 진행 지점 복원, '어디까지 했지', '누가 막혀있지', '다시 이어서' 상황에서 반드시 이 스킬을 읽는다."
---

# Harness State — 실행 상태의 정본

`.harness/issue-<N>/state.json` 하나가 이슈의 진행 상태를 담는다.
오케스트레이터가 이 파일을 읽어 다음 차례를 판정하고, 에이전트의 최종 보고를 여기에 옮긴다.

## 왜 파일 하나인가

에이전트는 서로의 컨텍스트를 못 본다. 세션이 재개·컴팩션되면 오케스트레이터의 기억도 사라진다.
상태가 대화 안에만 있으면 **재개할 때 무엇이 끝났는지 알 수 없어 처음부터 다시 한다.**
파일에 있으면 읽고 이어서 한다.

`.harness/`는 **gitignore**다. 커밋으로 워크트리에 전달되지 않으며, 그래야 한다 —
정본은 primary 체크아웃의 `.harness/` 하나다. 워크트리 구현자는 상태 파일을 읽지도
쓰지도 않는다. 워크트리로 가는 것은 tracked인 spec(`<spec_dir>/issue-<N>.md`)뿐이고,
그 밖에 필요한 상태는 오케스트레이터가 프롬프트에 담는다.

## 스키마

```jsonc
{
  "issue": 12,
  "title": "주문 내보내기 API 추가",
  "branch": "12-order-export",
  "updated_at": "<ISO8601>",

  // 현재 진행 지점 — 재개 시 여기부터
  "phase": "3-implement",        // 아래 "Phase 식별자" 참조
  "sub_stage": "3b-implement",
  "status": "in_progress",       // pending | in_progress | blocked | done | failed

  // 계약 확정 상태 — 계약 정본(contract_skill)과 동기화
  "contracts": {
    "order_export": "confirmed",     // undecided | provisional | confirmed
    "export_job_status": "provisional"
  },

  "mode": "full",                    // full (유일값)
  "spec": "docs/specs/issue-12.md",  // tracked. 없는 이슈는 null
  "test_list": {                     // 진행 정본은 커밋 로그다 (아래). 여기는 요약
    "T1": { "attempts": 1, "last_result": "pass" },
    "T2": { "attempts": 3, "last_result": "fail" }   // 3회 → blocker(owner: human)
  },
  "complexity": {},

  // 에이전트별 진행. **오케스트레이터만 쓴다** — 에이전트는 보고로 올린다.
  // 키는 접두사 없는 역할 이름
  "agents": {
    "issue-planner": {
      "status": "done",
      "started_at": "<ISO8601>",
      "finished_at": "<ISO8601>",
      "last_event_at": "<ISO8601>",
      "notes": "TODO(확인필요) 3건 — 사람 입력 대기 후 해소됨"
    },
    "contract-guardian": { "status": "done", "notes": "내보내기 스키마 확정, 전원 통보 완료" },
    "implementer": {
      "status": "in_progress",
      "name": "impl-12",                              // SendMessage 대상 — 다음 묶음 go
      "worktree": ".claude/worktrees/agent-a1b2c3",   // Agent isolation 완료 알림에서 옮긴다
      "branch": "worktree-agent-a1b2c3",
      "last_event_at": null,
      "notes": null
    },
    "integration-qa": { "status": "pending" }
  },

  // 사람이 답해야 하는 것. 비어있지 않으면 구현에 들어가지 않는다
  "open_questions": [
    { "id": "q1", "question": "내보내기 파일 형식", "asked_at": "<ISO8601>", "answer": null }
  ],

  // 진행을 막는 것. demo_blocker가 있으면 최우선
  "blockers": [
    {
      "id": "b1",
      "severity": "demo_blocker",   // demo_blocker | defect | improvement
      "description": "외부 패키지 미설치 — 의존성 추가는 사람 소관이라 에이전트가 설치 불가",
      "owner": "human",             // human | <agent-name>
      "raised_by": "implementer",
      "resolved": false
    }
  ],

  // 2단계 검증과 계약 TDD 상태 — issue-harness:verification-protocol
  "verification": {
    "blind": { "status": "done", "output": "_workspace/verify_12_blind.md" },
    "spec":  { "status": "pending", "output": null },
    "mismatches": 2,        // 1단계와 2단계가 갈라진 지점 수
    "contract_tests": { "written": 7, "failing_at_write": 7, "passing_now": 5 }
  },

  // 사람이 실행할 명령 — **push·PR만.** 로컬 머지는 오케스트레이터가 이미 했다
  "handoff_to_human": [
    "git push -u origin 12-order-export",
    "gh pr create --base main --title \"...\" --body-file _workspace/pr_12.md"
  ]
}
```

**`severity`의 `demo_blocker`는 "다음 단계 진행을 막는 결함"이다.** 이름은 하위 호환으로 유지한다.

**`history` 키는 없다.** 경과 기록은 같은 디렉터리의 `events.jsonl`이다(아래).

## 파일 셋 — 무엇을 누가 쓰는가

```
.harness/
├── ACTIVE                 # 현재 작업 중인 이슈 디렉터리 이름 한 줄 (예: issue-12)
└── issue-N/
    ├── state.json         # 상태. 오케스트레이터만 쓴다. history 키 없음
    └── events.jsonl       # 경과. 한 줄 = 한 이벤트. 훅만 append
```

| 파일 | 쓰는 주체 | 규약 |
|---|---|---|
| `state.json` | **오케스트레이터만** | 읽고-고치고-쓴다 (아래 갱신 규약) |
| `events.jsonl` | **훅만** — `SubagentStop`(플러그인 훅)과 git hook | append 전용. 사람도 에이전트도 손대지 않는다 |
| `ACTIVE` | 오케스트레이터 (이슈 시작·전환·종료 시) | 끝난 이슈를 가리킨 채 두지 않는다 |
| `<spec_dir>/issue-N.md` | `issue-planner`가 직접 쓴다 → 오케스트레이터가 커밋 | tracked |

**에이전트는 어떤 상태 파일도 쓰지 않는다.** 자기 진행·발견한 `blockers`·
`open_questions`를 **최종 보고에** 적고, 오케스트레이터가 `state.json`에 옮긴다.
여럿이 같은 JSON을 읽고-고치고-쓰면 정본이 갈라진다.
필요한 상태는 오케스트레이터가 프롬프트에 담아 준다.

**경과(`events.jsonl`)는 훅이 쓴다.** `source` 필드로 누가 쓴 줄인지 구분한다 —
`subagent`(서브에이전트 종료) / `githook`(커밋 차단). 오래된 기록에는 `worktree`(별 세션
워크트리 종료)·`migrated`(이관)가 남아 있을 수 있다.

> **왜 이렇게 나눴나.** 여럿이 한 JSON 파일을 읽고-고치고-쓰면 락·임시파일 교체·병합이
> 필요하고, 그 전부가 조용히 깨질 수 있는 지점이다. append 전용 로그는 그 문제가 없다.
> 상태(지금 어디인가)와 경과(무슨 일이 있었나)는 수명도 접근 패턴도 다르다.

### `events.jsonl` 한 줄의 모양

```jsonc
// 서브에이전트 종료
{"at":"...","source":"subagent","agent":"qa-12","agent_id":"a-2","cwd":"...","msg":"item: T3\nresult: pass\n..."}
// git hook이 커밋을 막았을 때
{"at":"...","source":"githook","hook":"pre-commit","event":"commit_blocked","reason":"skip/xfail 추가: ..."}
```

`msg`는 **최종 보고 원문 전체**다. 훅은 파싱하지 않는다 — 형식이 어긋나도 기록은 남고,
해석은 읽는 쪽이 한다. 파싱 실패로 기록이 통째로 비는 것이 가장 나쁜 결과이기 때문이다.

### 훅 — `${CLAUDE_PLUGIN_ROOT}/scripts/record-agent-event.py`

플러그인의 `SubagentStop` 훅이다. **에이전트가 기록을 깜빡할 수 없다** — 종료하면 발화한다.
격리 워크트리의 구현자도 이 세션의 서브에이전트이므로 여기서 잡힌다(`SendMessage`로 재개할
때마다 한 줄).

**플러그인이 켜진 모든 세션에서 발화한다.** 그래서 하네스 밖이면 먼저 빠진다:

- git 레포가 아니면 — 로그도 없이 끝낸다.
- `.harness/ACTIVE`가 없으면 — 로그도 없이 끝낸다. 하네스를 쓰지 않는 세션마다 `FAILED`가
  쌓이면 진짜 실패가 묻힌다.

하네스 안이면:

- `agent_id`가 없으면 건너뛴다 — 메인 세션이다(서브에이전트에만 이 필드가 온다).
- 내장 에이전트(`general-purpose`, `Explore`, `Plan` 등)·빈 `agent_type`이면 건너뛴다.
  **나머지는 전부 기록한다** — 다른 플러그인의 에이전트도.
- `ACTIVE`로 대상 이슈를 정한다. **"가장 최근 수정된 state.json" 추측은 하지 않는다** —
  틀리면 조용히 엉뚱한 곳에 쌓인다.
- `last_assistant_message` **원문 전체**를 `msg`에 담아 append한다. 파싱하지 않는다.
- 락도 임시파일 교체도 없다. append는 그 자체로 안전하다.

**한계 — `SubagentHandback`.** auto 모드 등에서 서브에이전트가 `SubagentHandback` 도구로 보고하면
`last_assistant_message`에는 보고가 아니라 맺음말이 온다. 그때 `msg`는 비거나 짧다.
오케스트레이터는 `msg`가 보고 형식이 아니면 완료 알림의 결과 본문을 정본으로 쓴다.

### `agent_type`은 타입이 아니라 "이름 또는 타입"이다

실측(v2.1.285):

| 호출 | 무엇이 되나 | `agent_type`에 오는 값 |
|---|---|---|
| `Agent(subagent_type: "issue-harness:issue-planner")` | 서브에이전트 | `"issue-harness:issue-planner"` — **타입** |
| `Agent(subagent_type: "issue-harness:implementer", name: "impl-1", isolation: "worktree")` | 서브에이전트 | `"issue-harness:implementer"` — **타입** |
| `Agent(subagent_type: "issue-harness:integration-qa", name: "qa-1")` (대화형, agent teams 켜짐) | 팀원 | `"qa-1"` — **이름** |

**팀원은 이름으로 오고, 그때는 타입을 알 방법이 없다.** 그래서 훅은 타입 화이트리스트를 쓰지 않는다 —
**내장 에이전트만 제외하는 블랙리스트**다. 화이트리스트로 거르면 이름으로 호출된 에이전트
기록이 0건이 된다.

기록이 없는 것이 잡음이 남는 것보다 나쁘다. 잡음은 보면 알지만 누락은 보이지 않는다.

> **훅을 고치면 반드시 실제 에이전트를 돌려 검증한다.** 합성 페이로드는 증거가 아니다 —
> 테스트 페이로드에 타입명을 손으로 넣으면 실제로는 이름이 오는 경우를 놓친다.

### 워크트리에서도 정본은 하나다

훅은 `cwd`로 `.harness/`를 찾되, `git rev-parse --git-common-dir`로
**primary 체크아웃을 찾아 거기에만 쓴다.** 워크트리와 primary가 각자 자기 파일에 append하면
정본이 갈라진다. `.harness/`는 gitignore되어 있으므로 워크트리에는 애초에 따라오지 않는다.

따라서 **워크트리 안의 `.harness/`는 읽기용 사본으로 취급한다.** 거기에 쓰인 것은
머지 전까지 정본이 아니다.

**동시 종료.** 훅은 락 없이 한 이벤트를 한 줄로 append(`open(..., "a")`)만 한다.
읽고-고치고-쓰는 단계가 없으므로 병렬 종료가 서로의 기록을 덮어쓰지 않는다.
한계: 보고 원문이 쓰기 버퍼(약 8KB)를 넘으면 한 줄이 여러 `write`로 나뉘어, 같은 순간
끝난 다른 줄과 섞일 수 있다. 깨진 줄이 보이면 그때 락을 단다.

> 훅이 조용히 실패하면 없는 것만 못하다. 훅은 하네스 안에서 **기본으로**
> `~/.claude/harness-hook.log`에 기록/건너뜀(사유 포함)/실패를 남긴다
> (`HARNESS_HOOK_LOG`로 경로 변경). **훅이 발화했는지 의심되면 이 로그를 먼저 본다.**

## 갱신 규약

**에이전트는 최종 보고에 적고 오케스트레이터가 옮긴다.** 자기 진행, 발견한
`blockers`·`open_questions` 모두 보고로 올린다. `state.json`을 쓰는 것은 오케스트레이터
하나이고, `phase`·`sub_stage`·`status` 전이도 오케스트레이터만 바꾼다.
쓰는 주체가 둘 이상이면 누가 진실인지 모른다.

**읽고-고치고-쓴다.** 기억으로 재구성해 통째로 덮어쓰지 않는다 — 기억에 없는 키가 날아간다.
JSON 전체를 읽어 해당 키만 바꾸고 다시 쓴다.

**`events.jsonl`은 훅만 append한다.** 오케스트레이터는 읽기만 하고 지우지 않는다.
지우면 재개 시 판단 근거가 사라진다.

**`updated_at`을 항상 갱신한다.** 오래된 `in_progress`는 죽은 에이전트의 흔적이다.

**`status`는 5값뿐이다 — `pending` / `in_progress` / `blocked` / `done` / `failed`.**
`stopped`·`paused`처럼 상황을 설명하는 말을 새로 만들지 않는다. 중단된 에이전트는
`pending`(재개 가능)이나 `failed`(재호출 필요)이고, 사정은 `notes`에 적는다.
검사기가 거부하므로 **쓴 뒤 반드시 돌린다** (아래).

## `evidence`와 `rationale` — 무엇과 왜를 나눠 적는다

에이전트는 **최종 보고에** 두 줄을 적는다(훅이 원문을 `events.jsonl`에 저장한다).

| 필드 | 담는 것 | 나쁜 예 | 좋은 예 |
|---|---|---|---|
| `evidence` | **실행한 명령과 실제 출력** | "테스트 통과함" | "`<check_cmd>` → 12 passed, lint clean" |
| `rationale` | **왜 그렇게 했는가** | (비워둠) | "파일 기반을 택함 — DB는 이번 범위에 불필요" |

**`evidence`에 주장을 쓰지 않는다.** "통과함"은 증거가 아니라 주장이다. 무엇을 돌렸고
무엇이 나왔는지를 적는다. 이것이 `4c`와 전이 판정의 근거가 된다.

**`rationale`이 왜 필요한가.** 커밋 메시지의 "왜"는 diff에 없다. 예를 들어 경로에 날짜를
넣은 변경은 diff로 한 줄이지만, 이유("덮어쓰면 백필 원본이 사라진다")는 여러 단계에 걸친
결정이다. 나중에 커밋 메시지를 쓰거나 PR 본문을 채울 때 이 필드가 원료가 된다.

설계 판단이 없는 단순 실행 단계는 `rationale`을 비워도 된다. 다만 **`2a-plan-draft`와
`3a-contract`는 비우지 않는다** — 그 두 단계는 판단이 본체다.

## Phase 식별자

`phase` / `sub_stage`에 쓰는 값. `issue-harness:issue-harness`의 Phase와 1:1 대응한다.
검사기(`scripts/check-state.py`의 `SUB_STAGES`)가 이 표와 같다 — 하나를 바꾸면 둘 다 바꾼다.

| phase | sub_stage | 담당 에이전트 | 워크트리 |
|---|---|---|---|
| `0-context` | `0a-git-check`<br>`0b-state-read` | 오케스트레이터 | — |
| `1-prepare` | `1a-issue-read`<br>`1b-dependency-check`<br>`1c-branch` | 오케스트레이터 | — |
| `2-plan` | `2a-plan-draft` | `issue-planner` | 불필요 |
|  | `2b-human-questions` | 오케스트레이터 (`AskUserQuestion`) | — |
|  | `2c-handoff-commit` | 오케스트레이터 | — |
| `3-implement` | `3a-contract` | `contract-guardian` (+ 도메인 에이전트) | 불필요 |
|  | `3a-test` | `integration-qa` — 실패 테스트 먼저 | 불필요 |
|  | `3b-implement` | `implementer` | **필요** |
|  | `3c-incremental-qa` | `integration-qa` | 불필요 |
| `4-verify` | `4a-verify-blind` | `integration-qa` (무컨텍스트) | 불필요 |
|  | `4b-verify-spec` | `integration-qa` (컨텍스트, 다른 인스턴스) | 불필요 |
|  | `4c-make-check` | 오케스트레이터 (`check_cmd`) | — |
|  | `4d-placeholder-scan` | 오케스트레이터 | — |
|  | `4e-merge` — 로컬 머지 + 머지 후 `check_cmd` | 오케스트레이터 | — |
| `5-report` | `5a-report`<br>`5b-human-handoff` | 오케스트레이터 | — |

`3a` → `3a-test` → `3b` → `3c` 순서다. `3b`↔`3c`는 모듈 묶음(spec의 `### M<n>`) 단위로 반복한다
(묶음 하나 완성 → 즉시 검증 → 다음 묶음 "go").
`4a`(무컨텍스트) → `4b`(컨텍스트) 순서를 뒤집지 않는다 — `issue-harness:verification-protocol`.

## 다음 에이전트 호출 판단 — 훅이 아니라 오케스트레이터가 한다

**훅을 쓰지 않는 이유:** 훅은 `PostToolUse`·`SubagentStop` 같은 **도구 이벤트**에 붙는다.
"계약이 확정됨", "이 모듈은 검증 준비가 됨"은 도구 이벤트가 아니라 의미적 판단이다.
상태 전이 판단은 오케스트레이터가 `state.json`을 읽고 한다.

**훅을 쓰는 곳은 기계적 게이트뿐이다** — 커밋 메시지 형식, 테스트 약화 차단, 종료 기록처럼
판단이 필요 없고 도구 이벤트에 정확히 대응하는 것.

### 언제 읽는가 — 호출 **전과 후** 둘 다

"판정한다"만 있고 언제 읽는지가 없으면 실제로 안 읽는다. 시점을 못박는다:

| 시점 | 하는 일 |
|---|---|
| **에이전트 호출 직전** | 읽는다. 전이 규칙 1~5(멈춤 조건)로 **지금 불러도 되는지** 판정하고, `agents.<이름>.status`를 `in_progress`로 쓴다 |
| **에이전트 종료 직후** | `events.jsonl` **마지막 줄**을 읽고 보고를 `state.json`에 옮긴다 — `agents.<이름>.status`·`last_event_at`, `test_list.<ID>.attempts`/`last_result`, `blockers`, `open_questions`. 그 뒤 전이 규칙을 **1번부터** 판정한다 |
| **사용자에게 보고하기 전** | 읽는다. 보고 내용의 근거는 기억이 아니라 파일이다 |

`events.jsonl` **전체**를 읽는 것은 세션 시작·컴팩션 후·`state.json`과 실제가 안 맞을 때만이다
(마지막 20줄). 매번 전체를 읽으면 컨텍스트가 경과 로그로 찬다.

**테스트 목록 진행 상황은 커밋 로그가 정본이다.** `state.json`의 `test_list`는 요약이다:

```bash
git log --oneline --grep "^\[behavioral\] T"    # 완료된 항목
```

### 스키마 검사 — 문서가 아니라 검사가 지킨다

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-state.py"
```

검사하는 것:
- `phase`·`status`·`agents.*.status`·`contracts.*`·`blockers[].severity` 유효값
- `blockers[]`·`open_questions[]` 필수 키
- `sub_stage`가 `phase`와 맞는가
- `spec`이 있는 파일을 가리키는가
- **워크트리와 primary의 `state.json`이 갈라졌는가**

> **왜 있는가.** 검증자가 `blockers`를 다른 키로 써서 오케스트레이터가 미해결 블로커를 세다가
> `KeyError`로 멈출 수 있다. 스키마가 문서에만 있고 아무도 검사하지 않으면 생기는 일이다.

`check_cmd`에 넣지 않는다 — CI 체크아웃에는 워크트리가 없어 분기 검사가 무의미하고
`.harness/`는 제품 코드가 아니다. **오케스트레이터가 에이전트 호출 전후로 돌린다.**

**기억으로 순서를 진행하지 않는다.** 기억으로 진행하고 `state.json`을 사후 기록으로 쓰면,
구현자가 일을 끝낸 것을 사용자가 "멈춘 것 같은데?"라고 물어서야 알게 된다.

### 별도 세션에 인계한 작업은 완료 알림이 오지 않는다

서브에이전트(`Agent` 툴)는 종료 시 알림이 온다 — **격리 워크트리의 구현자도 여기에 해당한다.**
그러나 **사람이 따로 띄운 세션이나 peer 세션은 알림도 훅 기록도 없다.** 그때는 오케스트레이터가
직접 확인해야 한다:

```bash
# 워크트리 세션의 진척 — 커밋이 근거다
git -C <워크트리경로> log --oneline -5
# 정본 state.json (워크트리 쪽이 아니라 primary를 본다)
python3 -c "import json;d=json.load(open('.harness/issue-<N>/state.json'));print(d['sub_stage'],d['agents'])"
```

**`in_progress`로 멈춰 있는 항목이 있으면 그것이 확인 대상이다.** 사용자가 물어볼 때까지
기다리지 않는다.

### 전이 규칙

**전이 판정의 정본은 이 절이다.** 다른 문서는 여기를 참조만 한다.

오케스트레이터는 에이전트가 끝날 때마다 `state.json`을 읽고 **1번부터 순서대로** 판정한다.
먼저 걸리는 것에서 멈춘다. 1~5는 멈춤·되돌림 조건, 6~7은 진행 조건이다.

1. **`blockers`에 `resolved: false`이고 `severity: demo_blocker`가 있는가?**
   → 다음 에이전트를 부르지 않는다. `owner`가 `human`이면 사용자에게 보고하고 멈춘다.
2. **`open_questions`에 `answer: null`이 있는가?**
   → 구현(`3b`)에 들어가지 않는다. `AskUserQuestion`으로 먼저 묻는다.
   추측으로 채운 답으로 구현하면 그것을 읽는 후속 이슈가 전부 틀어진다.
3. **같은 `test_list` 항목의 `attempts`가 3 이상인가?**
   → 다시 보내지 않는다. `blockers`에 `owner: "human"`으로 올리고 멈춘다.
   4회째는 같은 실패를 반복할 뿐이고, 기대값 자체가 틀렸을 가능성이 높다.
4. **`contracts`에 `undecided`가 있고 다음 단계가 그것을 소비하는가?**
   → `3b`로 가지 않고 `3a`로 되돌린다. 미확정 계약 위에 구현하면 재작업이 확정된다.
5. **`3a-test`의 계약 테스트가 작성 시점에 통과했는가?**
   → `contract_tests.failing_at_write` < `written`이면 비어 있는 테스트다.
   `3b`로 보내지 않고 다시 쓰게 한다. 통과하는 테스트를 써두면 나중에 통과해도 의미가 없다.
6. **현재 `sub_stage`의 담당 에이전트가 모두 `done`인가?**
   → 다음 `sub_stage`로 전이하고 담당 에이전트를 호출한다.
7. **`3b` 안에서 모듈 묶음 하나가 끝났는가?** (구현자 완료 알림)
   → `3c`(`integration-qa`)를 즉시 호출한다. 전체 완성 후 한 번에 검증하면
   경계면 버그를 마감 직전에 발견한다.

## 재개 절차

세션 재개·컴팩션·워크트리 진입 후:

```bash
git status --short --branch          # 의도한 브랜치인가
cat .harness/ACTIVE                  # 활성 이슈
cat .harness/issue-<N>/state.json    # 어디까지 했는가
```

`status`가 `in_progress`인데 `updated_at`이 오래됐으면 그 에이전트는 죽었다.
해당 항목을 `failed`로 바꾸고 재호출하거나 작업을 재할당한다.

**끝났다고 기록된 것을 다시 하지 않는다.** 단, `integration-qa`의 검증 결과는 예외 —
"수정했다"는 주장은 재확인한다.

### 구현 워크트리가 남은 채로 세션이 바뀌었을 때

같은 세션 안에서는 `SendMessage(to: agents.implementer.name)`로 이어 간다. 새 세션에서
이전 구현자에게 메시지가 닿는다고 가정하지 않는다. 새 `Agent(isolation: worktree)`를 부르면
**새 워크트리**가 HEAD에서 갈라지므로 이전 워크트리의 커밋이 없다. 그래서:

```bash
git worktree list                                                   # worktree-agent-<id>가 남았는가
git -C <agents.implementer.worktree> log --oneline <핸드오프커밋>..HEAD   # 끝낸 묶음
```

1. 남은 커밋이 있으면 끝난 묶음까지 **이슈 브랜치로 로컬 머지**하고 `check_cmd`
   (`issue-harness:issue-workflow` 8절과 같은 명령).
2. 그다음 남은 묶음부터 새 구현자를 부른다 — 머지된 HEAD에서 갈라지므로 앞 작업을 이어받는다.
3. 머지한 이전 워크트리는 8절 절차로 지운다.

## 초기화

이슈 착수 시 오케스트레이터가 만들고 `ACTIVE`에 `issue-<N>`을 쓴다:

```jsonc
{
  "issue": <N>, "title": "<이슈 제목>", "branch": "<이슈 브랜치>",
  "updated_at": "<ISO8601>",
  "phase": "1-prepare", "sub_stage": "1a-issue-read", "status": "in_progress",
  "contracts": {}, "agents": {},
  "mode": "full", "spec": null, "test_list": {}, "complexity": {},
  "verification": { "blind": null, "spec": null, "mismatches": null, "contract_tests": null },
  "open_questions": [], "blockers": [], "handoff_to_human": []
}
```

`spec`은 `2c-handoff-commit` 후 경로로 채운다. spec 없이 도는 이슈(하네스 자체 개선 등)는 `null`로 둔다.

이슈가 끝나면(`5b` 이후) `ACTIVE`를 다음 이슈로 바꾸거나 지운다.
