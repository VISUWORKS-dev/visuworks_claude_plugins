---
name: harness-state
description: "하네스의 실행 상태 정본 — `.harness/issue-<N>/state.json`(사람 질문·블로커·인계만) 스키마, 진행 지점을 git 로그로 복원하는 표, events.jsonl 기록 훅, 전이 규칙. 에이전트 작업 완료·차단 시 상태 기록, 다음 에이전트 호출 판단, 세션 재개·컴팩션 후 진행 지점 복원, '어디까지 했지', '누가 막혀있지', '다시 이어서' 상황에서 반드시 이 스킬을 읽는다."
---

# Harness State — 실행 상태의 정본

| 무엇 | 정본 |
|---|---|
| 진행 지점 (어디까지 했나) | **git 로그·파일** — 아래 「진행 지점 복원」 |
| 사람이 답할 것·막힌 것·사람이 실행할 명령 | `.harness/issue-<N>/state.json` |
| 경과 (무슨 일이 있었나) | `.harness/issue-<N>/events.jsonl` — 훅만 append |

진행을 `state.json`에 따로 적으면 커밋과 갈라진다. 커밋은 거짓말을 하지 않으므로 진행은 커밋에서 읽는다.

`.harness/`는 **gitignore**다. 정본은 primary 체크아웃의 `.harness/` 하나다. 워크트리 구현자는 상태 파일을
읽지도 쓰지도 않는다 — 필요한 것은 오케스트레이터가 프롬프트에 담는다.

## 스키마

```jsonc
{
  "issue": 12,
  "updated_at": "<ISO8601>",

  // 사람이 답해야 하는 것. answer: null이 있으면 구현(3b)에 들어가지 않는다
  "open_questions": [
    { "id": "q1", "question": "내보내기 파일 형식", "asked_at": "<ISO8601>", "answer": null }
  ],

  // 진행을 막는 것
  "blockers": [
    {
      "id": "b1",
      "severity": "demo_blocker",   // demo_blocker(다음 단계 진행 불가) | defect | improvement
      "description": "외부 패키지 미설치 — 의존성 추가는 사람 소관",
      "owner": "human",             // human | <에이전트 역할 이름>
      "raised_by": "implementer",
      "resolved": false
    }
  ],

  // 사람이 실행할 명령 — push·PR만. 로컬 머지는 오케스트레이터가 이미 했다
  "handoff_to_human": [
    "git push -u origin 12-order-export",
    "gh pr create --base main --title \"...\" --body-file _workspace/pr_12.md"
  ]
}
```

이 밖의 키(`phase`·`sub_stage`·`status`·`agents`·`contracts`·`test_list`·`verification`·`mode`·`history` 등)는
두지 않는다. 검사기가 거부한다.

## 파일 셋 — 누가 쓰는가

```
.harness/
├── ACTIVE            # 작업 중인 이슈 디렉터리 이름 한 줄 (예: issue-12)
└── issue-N/
    ├── state.json    # 오케스트레이터만 쓴다
    └── events.jsonl  # 훅만 append
```

| 파일 | 쓰는 주체 | 규약 |
|---|---|---|
| `state.json` | **오케스트레이터만** | 읽고-고치고-쓴다. 기억으로 재구성해 덮어쓰지 않는다. `updated_at` 갱신 |
| `events.jsonl` | **훅만** — `SubagentStop`·`PostToolUse(SendMessage)` 플러그인 훅, git hook | append 전용. 오케스트레이터는 읽기만 한다 |
| `ACTIVE` | 오케스트레이터 | 이슈 시작 시 쓰고, 끝나면(`5b` 이후) 다음 이슈로 바꾸거나 지운다 |

**에이전트는 어떤 상태 파일도 쓰지 않는다.** 발견한 `blockers`·`open_questions`는 최종 보고에 적고
오케스트레이터가 옮긴다.

**쓴 뒤 반드시 검사한다:**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-state.py"
```

검사 대상: 허용 키, `blockers[]`·`open_questions[]` 필수 키, `severity` 유효값, `resolved` bool,
워크트리와 primary의 `state.json` 분기. `check_cmd`에 넣지 않는다 — `.harness/`는 제품 코드가 아니다.

## 진행 지점 복원 — git이 정본

세션 시작·재개·컴팩션 후, 그리고 **에이전트 종료 직후마다** 아래로 지금 위치를 정한다.
위에서부터 보고 **처음으로 "아니오"인 행이 현재 단계**다.

| 확인 | 명령 | 단계 |
|---|---|---|
| spec이 있는가 | `test -f <spec_dir>/issue-<N>.md` | `2a` |
| spec이 커밋됐는가 (사람 승인 후 커밋) | `git log --oneline --grep "^docs : 이슈 #<N> spec"` | `2b`·`2c` |
| (full) 계약이 전부 `confirmed`인가 | `events.jsonl`의 마지막 `contract-guardian` 보고 `contracts:` 줄 | `3a` |
| (full) 계약 테스트가 커밋됐는가 | `git log --oneline --grep "^test : 이슈 #<N> 계약 테스트"` | `3a-test` |
| 구현 워크트리가 있는가 | `git branch --contains <spec 커밋> --list 'worktree-agent-*'` | `3b` 시작 |
| 테스트 목록 항목이 전부 커밋됐는가 | `git -C <워크트리> log <spec 커밋>..HEAD --grep "^Tests: T" --format=%B` | `3b`↔`3c` |
| (full) 무컨텍스트 검증이 있는가 | `test -f _workspace/verify_<N>_blind.md` | `4a` |
| 컨텍스트 검증이 있는가 | `test -f _workspace/verify_<N>_spec.md` | `4b` |
| 로컬 머지됐는가 | `git log --oneline --grep "^chore : 워크트리 브랜치를 이슈 브랜치에 반영한다 (#<N>)"` | `4c`~`4e` |
| `handoff_to_human`이 채워졌는가 | `state.json` | `5` |

`<spec 커밋>` = `git log -1 --format=%H --grep "^docs : 이슈 #<N> spec"`. **범위 없이 `Tests:`를 세지 않는다** — 기본 브랜치에
다른 이슈의 `Tests: T1`이 이미 있어 끝나지 않은 항목이 끝난 것으로 보인다.

경로(`full`/`light`)는 spec 머리의 `경로:` 줄이다. `(full)` 행은 `light`이면 건너뛴다.

**구현 워크트리 찾기.** 워크트리 브랜치 이름에는 이슈 번호가 없다. 워크트리는 spec 커밋 뒤의 HEAD에서
갈라지므로 **spec 커밋을 포함하는 `worktree-agent-*` 브랜치**가 이 이슈의 것이다. 경로는
`git worktree list`에서 그 브랜치 줄이다.

**끝난 묶음.** `<spec 커밋>..HEAD` 커밋 꼬릿말 `Tests: T<n>`의 합집합이 통과한 항목이다. spec의 묶음(`### M<n>`) 중
모든 항목이 들어간 묶음이 끝난 묶음이다.

`events.jsonl` 마지막 20줄은 단계 안에서 무슨 일이 있었는지(막힘·실패 사유) 볼 때만 읽는다.

### 별도 세션·죽은 에이전트

완료 알림은 서브에이전트(`Agent` 툴, 격리 워크트리 구현자 포함)에만 온다. 사람이 따로 띄운 세션은
알림도 훅 기록도 없다 — 워크트리 커밋(`git -C <워크트리> log --oneline -5`)으로 직접 확인한다.

새 세션에서 이전 구현자에게 `SendMessage`가 닿는다고 가정하지 않는다. 새 `Agent(isolation: worktree)`는
HEAD에서 새로 갈라지므로 이전 워크트리 커밋이 없다:

1. 이전 워크트리에 끝난 묶음 커밋이 있으면 이슈 브랜치로 로컬 머지하고 `check_cmd`.
   메시지는 **`chore : 끝난 묶음을 이슈 브랜치에 반영한다 (#<N>, M1~M<k>)`** — 최종 머지 메시지(`4e`)를 쓰면
   복원 표가 `4e`가 끝난 것으로 읽는다.
2. 남은 묶음부터 새 구현자를 부른다.
3. 머지한 이전 워크트리는 8절 절차로 지운다.

## 경과 — `events.jsonl`

훅 `${CLAUDE_PLUGIN_ROOT}/scripts/record-agent-event.py`가 쓴다. 에이전트가 기록을 깜빡할 수 없다.

```jsonc
{"at":"...","source":"subagent","agent":"issue-harness:integration-qa","agent_id":"a-2","cwd":"...","msg":"item: M1\nresult: pass\n..."}
{"at":"...","source":"message","agent":"qa","agent_id":"aqa-…","cwd":"...","to":"team-lead","msg":"result: pass\n..."}
{"at":"...","source":"githook","hook":"commit-msg","event":"commit_blocked","reason":"선언 없이 지우거나 바꾼 테스트 2개"}
```

| 이벤트 | `source` | `msg` |
|---|---|---|
| `SubagentStop` | `subagent` | 마지막 텍스트 — 서브에이전트는 이것이 보고 |
| `PostToolUse`(`SendMessage`) | `message` | 에이전트가 보낸 메시지 원문 — 팀원은 보고가 여기 있고, `subagent` 줄은 맺음말 |

- `msg`는 원문 전체다. 훅은 파싱하지 않는다 — 형식이 어긋나도 기록은 남는다.
- 오케스트레이터(메인 스레드)의 메시지는 기록하지 않는다(`agent_id` 없음).
- 하네스 밖(git 레포 아님, `ACTIVE` 없음)이면 로그도 없이 끝난다. 대상 이슈는 `ACTIVE`로만 정한다.
- 내장 에이전트(`general-purpose`·`Explore`·`Plan` 등)만 제외한다. 팀원은 `agent_type`에 타입 대신
  **이름**이 오므로 화이트리스트를 쓰지 않는다.
- 워크트리에서 돌아도 `--git-common-dir`로 primary의 `.harness/`에만 쓴다.
- 락 없이 한 줄 append. 보고가 약 8KB를 넘으면 동시 종료한 줄과 섞일 수 있다 — 깨진 줄이 보이면 그때 락을 단다.
- 발화가 의심되면 `~/.claude/harness-hook.log`(`HARNESS_HOOK_LOG`)를 먼저 본다.
- **한계:** `SubagentHandback`으로 보고하면 `msg`는 맺음말이다. 보고 형식이 아니면 완료 알림의 결과를 정본으로 쓴다.
- 훅을 고치면 실제 에이전트를 돌려 검증한다. 합성 페이로드는 증거가 아니다.

## `evidence`와 `rationale`

에이전트는 최종 보고에 두 줄을 적는다.

| 필드 | 담는 것 | 나쁜 예 | 좋은 예 |
|---|---|---|---|
| `evidence` | 실행한 명령과 실제 출력 | "테스트 통과함" | "`<check_cmd>` → 12 passed, lint clean" |
| `rationale` | 왜 그렇게 했는가 | (비움) | "파일 기반 — DB는 이번 범위에 불필요" |

`2a-plan-draft`와 `3a-contract`는 `rationale`을 비우지 않는다. 커밋 메시지·PR 본문의 "왜"가 여기서 나온다.

## Phase 식별자

`issue-harness:issue-harness`의 Phase와 1:1이다. 보고·대화에서 위치를 부를 때 쓴다(상태 파일에는 적지 않는다).

| phase | sub_stage | 담당 | full | light |
|---|---|---|---|---|
| `0-context` | `0a-git-check` / `0b-state-read` | 오케스트레이터 | ○ | ○ |
| `1-prepare` | `1a-issue-read` / `1b-dependency-check` / `1c-branch` | 오케스트레이터 | ○ | ○ |
| `2-plan` | `2a-plan-draft` | `issue-planner` (작은 이슈는 오케스트레이터) | ○ | ○ |
| | `2b-human-questions` / `2c-handoff-commit` | 오케스트레이터 | ○ | ○ |
| `3-implement` | `3a-contract` | `contract-guardian` (+ 도메인 에이전트) | ○ | — |
| | `3a-test` | `integration-qa` — 실패 테스트 먼저 | ○ | — |
| | `3b-implement` | `implementer` (격리 워크트리) | ○ | ○ |
| | `3c-incremental-qa` | `integration-qa` | ○ | — |
| `4-verify` | `4a-verify-blind` | `integration-qa` (무컨텍스트) | ○ | — |
| | `4b-verify-spec` | `integration-qa` (컨텍스트, 다른 인스턴스) | ○ | ○ |
| | `4c-make-check` / `4d-placeholder-scan` / `4e-merge` | 오케스트레이터 | ○ | ○ |
| `5-report` | `5a-report` / `5b-human-handoff` | 오케스트레이터 | ○ | ○ |

## 전이 규칙

**전이 판정의 정본은 이 절이다.** 에이전트가 끝날 때마다 보고를 읽고 「진행 지점 복원」으로 위치를 정한 뒤
1번부터 판정한다. 먼저 걸리는 것에서 멈춘다.

1. **`blockers`에 `resolved: false` + `severity: demo_blocker`가 있는가?**
   → 다음 에이전트를 부르지 않는다. `owner`가 `human`이면 사용자에게 보고하고 멈춘다.
2. **`open_questions`에 `answer: null`이 있는가?**
   → `3b`에 들어가지 않는다. `AskUserQuestion`으로 먼저 묻는다.
3. **구현자 보고가 `result: blocked`인가?** (같은 항목 3회 실패 — `issue-harness:tdd-cycle`)
   → 다시 보내지 않는다. `blockers`에 `owner: "human"`으로 올리고 멈춘다.
4. **`contract-guardian` 보고에 `confirmed`가 아닌 계약이 있고 다음 묶음이 그것을 소비하는가?**
   → `3b`로 가지 않고 `3a`로 되돌린다.
5. **`3a-test` 보고에서 작성 시점 실패 수 < 작성 수인가?**
   → 빈 테스트다. 다시 쓰게 하고 `3b`로 보내지 않는다.
6. **light 이슈에서 계약 신설·변경이 필요해졌는가?** (구현자·`4b` 보고)
   → full로 올린다. 워크트리가 도는 동안 이슈 브랜치에 커밋하지 않으므로 순서를 지킨다:
   ① 구현자를 멈추고 끝난 묶음을 「별도 세션·죽은 에이전트」 1번처럼 부분 머지 ② spec `경로:` 수정 커밋
   ③ `3a`→`3a-test`(계약 테스트 커밋) ④ 남은 묶음은 **새** 구현자 — 이전 워크트리는 계약 테스트를 모른다.
7. **현재 단계의 산출물(위 표의 커밋·파일)이 생겼는가?**
   → 다음 단계로 간다. `3b` 안에서 묶음 하나가 끝났으면 full은 `3c`를 즉시 부른다.

## 초기화

이슈 착수 시 오케스트레이터가 만들고 `ACTIVE`에 `issue-<N>`을 쓴다:

```json
{ "issue": <N>, "updated_at": "<ISO8601>", "open_questions": [], "blockers": [], "handoff_to_human": [] }
```
