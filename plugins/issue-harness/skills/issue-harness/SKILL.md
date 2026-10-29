---
name: issue-harness
description: "이슈 하나를 계획 → 계약 확정 → 테스트 목록 TDD 구현 → 검증 → 로컬 머지까지 태우는 멀티 에이전트 오케스트레이터. 이슈 유형에 따라 full(계약 신설·변경)·light(화면 수정·기존 계약 소비) 경로를 고른다. '이슈 N 시작', '이슈 N 구현', '이 기능 만들어'(이슈가 있는 레포), 'QA만 다시 돌려', '계약 다시 확인', '이 부분만 다시', 재실행·재개·보완, 경계면 불일치 조사, 마감 전 최종 점검 요청 시 사용. .claude/harness.config.json이 있는 프로젝트에서 동작한다."
---

# Issue Harness — 오케스트레이터

이슈 하나를 받아 계획 → 구현 → 검증 → 로컬 머지까지 태운다. 검증 강도는 이슈 유형에 맞춘다.

## 프로젝트 설정 — 먼저 읽는다

```bash
cat .claude/harness.config.json
```

없으면 멈추고 `/issue-harness:init`을 안내한다. 이후 `<키>`는 그 파일의 값이다.

| 키 | 쓰는 곳 |
|---|---|
| `models.<역할>` · `model` | `Agent` 호출의 `model` — 아래 「모델」. 둘 다 없으면 넣지 않는다 |
| `check_cmd` | 구현자의 묶음 끝, `4c`, `4e`(조건부) |
| `test_file_cmd` | 구현자의 항목별 부분 테스트(`{files}` 치환). 없으면 `check_cmd` |
| `contract_test_cmd` | `3a-test`의 실패 확인 |
| `src_dirs`·`tests_dir`·`contract_tests_dir` | 권한, 프롬프트 |
| `spec_dir` | spec 경로 `<spec_dir>/issue-<N>.md` |
| `contract_skill` | 계약 정본 스킬. `null`이면 spec의 「이 이슈가 확정하는 계약」 절이 정본 |
| `domain_agents` | 팀에 넣을 수 있는 프로젝트 에이전트와 결정 범위 |
| `domain_skills.scope`·`.workflow` | 범위 판정 사례, 이슈 의존 순서 |
| `pr_mode.light`·`.full` | `pr-writing` 모드(`basic`·`review`·`full`). 없으면 `basic` |
| `push_pr` | `orchestrator`면 Phase 5에서 오케스트레이터가 push·PR 생성. 없거나 `human`이면 명령만 출력 |

에이전트에게는 필요한 값만 프롬프트에 담아 준다.

### 모델

| 호출 | 키 |
|---|---|
| `issue-planner` (`2a`) | `models.plan` |
| `contract-guardian` (`3a`) | `models.contract` |
| `implementer` (`3b`) | `models.implement` |
| `integration-qa` — `3a-test`·`3c` | `models.qa` |
| `integration-qa` — `4a` 무컨텍스트 | `models.verify_blind` |
| `integration-qa` — `4b` 컨텍스트 | `models.verify_spec` |
| 탐색(`Explore` 등 내장 에이전트) | `models.explore` |
| 도메인 에이전트·그 밖 | `model` |

`models`에 키가 없으면 `model`을 쓴다. **`implement`에 `haiku`를 쓰지 않는다** — 재시도 1회가 `check_cmd` 1회다.
설정에 `haiku`가 있으면 `model`로 대신하고 사용자에게 알린다.

## 경로 — full / light

`1a`에서 이슈를 읽고 정한다. spec 머리의 `경로:` 줄에 적고 `2b` 승인 게이트에서 사람에게 함께 확인받는다.

| 경로 | 이슈 | 생략하는 것 |
|---|---|---|
| **full** | 계약(스키마·상태값·경로) 신설·변경, 여러 단계 통합 | 없음 |
| **light** | 화면 수정, 기존 계약만 소비, 문서·설정 | `contract-guardian`(`3a`), 계약 테스트 선작성(`3a-test`), `3c`, 무컨텍스트 검증(`4a`). 팀 없음 |

판정이 애매하면 full이다. light 진행 중 계약 변경이 필요해지면 full로 올린다(`issue-harness:harness-state` 전이 규칙 6).

**작은 이슈** — 테스트 목록이 3항목 이하·묶음 1개로 예상되면 `issue-planner`를 부르지 않고 오케스트레이터가 spec을
직접 쓴다. 입력(부모 이슈·GLOSSARY·ADR)·형식·테스트 목록 규약은 `issue-harness:issue-planner` 정의를 그대로 따르고, 승인 게이트(`2b`)는 생략하지 않는다.

## 에이전트

| 에이전트 | subagent_type | 역할 |
|---|---|---|
| `issue-planner` | `issue-harness:issue-planner` | 이슈 → spec |
| `contract-guardian` | `issue-harness:contract-guardian` | 경계면 계약 소유 (full) |
| `implementer` | `issue-harness:implementer` | 격리 워크트리에서 구현·커밋 |
| `integration-qa` | `issue-harness:integration-qa` | 계약 테스트 선작성·경계면 검증·최종 검증 |
| `<domain_agents[].name>` | 그 이름 그대로 | 도메인 판단 (`decides`) |

**`name`은 의미가 있다.** agent teams가 켜진 대화형 세션에서 `name`을 준 `Agent` 호출은 **팀원**이 된다
(`isolation`을 준 호출은 예외 — 서브에이전트로 남는다).

| 호출 | `name` | 무엇이 되나 |
|---|---|---|
| 계획(`2a`), 최종 검증(`4a`·`4b`) | 주지 않는다 | 서브에이전트 — 팀에서 분리 |
| 구현(`3b`) | `impl-<N>` + `isolation: "worktree"` | 서브에이전트 (`SendMessage`로 이어감) |
| full의 Phase 3 팀원 | `contract`·`domain`·`qa` | 팀원 |

권한(쓰기 허용·워크트리·커밋)은 각 에이전트 정의와 `.claude/rules/agent-permissions.md`가 정본이다.
워크트리는 `implementer`만 쓴다.

## 상태

**진행 지점은 git 로그가 정본이다.** `state.json`은 `open_questions`·`blockers`·`handoff_to_human`만 담는다.
스키마·진행 지점 복원 표·전이 규칙은 **`issue-harness:harness-state`** 에 있다 — 여기에 다시 적지 않는다.

- 에이전트는 상태 파일을 쓰지 않는다. 보고에 적고 오케스트레이터가 옮긴다.
- 에이전트가 끝날 때마다: 보고 읽기 → 블로커·질문을 `state.json`에 옮기기 → `check-state.py` →
  진행 지점 복원 → 전이 규칙 1번부터.
- 이슈 착수 시 `state.json`을 초기화하고 `ACTIVE`를 쓴다. 끝나면 `ACTIVE`를 넘기거나 지운다.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-state.py"
```

훅은 기계적 게이트(커밋 메시지 형식, 테스트 변경 선언, 종료 기록)에만 쓴다. 다음 에이전트 판단은
오케스트레이터가 한다.

## 워크플로우

### Phase 0: 컨텍스트

```bash
git status --short --branch
pwd
cat .harness/ACTIVE
cat .harness/issue-<N>/state.json
```

그 뒤 `issue-harness:harness-state` 「진행 지점 복원」으로 위치를 정하고 거기서 이어 간다.
끝난 단계를 다시 하지 않는다. 단 `integration-qa`의 "수정했다"는 재확인한다.
`ACTIVE`가 요청받은 이슈와 다르면 이전 이슈 상태를 확인하고 넘긴다.

부분 재실행("QA만 다시")은 해당 에이전트만 부르고, 이전 산출물 경로를 프롬프트에 넣는다.

### Phase 1: 준비

1. 이슈 번호 확정. 불명확하면 `gh issue list`로 확인하고 묻는다.
2. `gh issue view <N> --json title,body,parent,blockedBy` — 언급된 연관 이슈도 읽는다. `parent`가 있으면
   부모 스펙 이슈 본문도 읽는다(`gh issue view <parent.number> --json body` — `parent`에는 본문이 없다).
   그 뒤 **경로(full/light)를 정한다.**
3. 선행 이슈 — `blockedBy`에 열린 이슈가 있으면 사용자에게 확인한다. `domain_skills.workflow`가 있으면 의존 순서도 본다.
   선행 계약이 미확정이면 사용자에게 확인한다.
   이슈가 모호하고 스킬 목록에 `mattpocock-skills:` 접두 스킬(예: `mattpocock-skills:tdd`)이 보이면
   `AskUserQuestion`으로 [`/mattpocock-skills:grill-with-docs` 먼저 / 그대로 진행]을 묻는다. grill은 사람만 실행할 수
   있으므로 먼저를 고르면 멈춘다. 보이지 않으면 묻지 않는다.
4. 이슈 브랜치 확인·생성 (`branch_pattern`).
5. `_workspace/` 생성 (갱신 실행이면 기존 것을 `_workspace_<타임스탬프>/`로 옮긴다).
6. `state.json` 초기화, `ACTIVE` 기록.

### Phase 2: 계획

**`2a-plan-draft`** — 작은 이슈는 오케스트레이터가 직접 쓴다(위). 아니면:

```
Agent(
  subagent_type: "issue-harness:issue-planner",
  model: <models.plan>,
  prompt: "이슈 #<N>의 작업 계획을 작성한다. <이슈 본문>.
           경로: <full|light> — spec 머리에 적는다.
           계약 정본: <contract_skill 또는 '없음 — spec에 계약 절을 쓴다'>.
           범위 판정: issue-harness:scope-guard (+ 프로젝트 사례: <domain_skills.scope>).
           마감: <있으면 날짜>.
           <spec_dir>/issue-<N>.md 에 직접 써라(Write). 그 파일 하나만 쓴다.
           보고는 짧게: 파일 경로, 항목 수, open_questions, 계약 공백. 본문을 붙이지 마라."
)
```

보고의 `open_questions`·계약 공백(blocker)을 `state.json`에 옮긴다. spec 본문은 파일에서 읽는다 —
메시지 전달이 수백 행을 자른다.

**`2b-human-questions`** — 한 게이트에서 셋을 받는다. `AskUserQuestion`, 항목별 선택지 2~4개.

- `TODO(확인필요)`·`open_questions`의 답 → `open_questions[].answer`
- `## 테스트 목록` 승인 — 구현자는 기대값을 바꿀 수 없으므로 승인 없이 들어가면 사람이 확정하지 않은 기대값이 정본이 된다
- 경로(full/light) 확인

지적을 받으면 spec을 고친다(`issue-planner` 재호출 또는 직접). `answer: null`이 남으면 `3b`로 가지 않는다.

**`2c-handoff-commit`** — 승인 뒤에만 커밋한다. 이 커밋이 "승인됨"의 기록이다.

```bash
git add <spec_dir>/issue-<N>.md   # grill 등으로 바뀐 GLOSSARY.md·docs/adr/가 있으면 함께 — 워크트리는 커밋만 받는다
git commit -m "docs : 이슈 #<N> spec — 테스트 목록 <n>항목"
```

### Phase 3: 구현

#### full — `3a-contract` → `3a-test`

팀(primary): `contract-guardian` + `integration-qa` (+ 도메인 판단이 필요하면 도메인 에이전트).
팀원이 1명이면 팀을 만들지 않고 서브에이전트로 부른다.

```
Agent(subagent_type: "issue-harness:contract-guardian", name: "contract", model: <models.contract>, prompt: "...")
Agent(subagent_type: "<domain_agents[0].name>",         name: "domain",   model: <model>,           prompt: "...")
Agent(subagent_type: "issue-harness:integration-qa",    name: "qa",       model: <models.qa>,       prompt: "...")
```

팀원 프롬프트에 넣는 규칙:
- 계약이 바뀌면 `contract`가 **팀 전원과 오케스트레이터에게 통보한다.** 구현자에게는 오케스트레이터가 다음 "go"에 담는다.
- `qa`가 `demo_blocker`를 찾으면 오케스트레이터에게 즉시 알린다.
- 팀원 보고는 `SendMessage`로 온다 — 훅이 `source: "message"` 줄로 남긴다.

agent teams가 꺼졌거나 `-p` 세션이면 같은 호출이 서브에이전트로 돈다 — 통보는 오케스트레이터가 잇는다.

**`3a-test`** — 계약이 `confirmed`가 되면 `qa`가 `contract_tests_dir`에 실패 테스트를 쓰고
`contract_test_cmd`로 실패를 확인한다. 형태만 건다 — `issue-harness:verification-protocol` 「계약 TDD」.
실패를 확인하면 **오케스트레이터가 커밋한다** — 워크트리는 HEAD에서 갈라지므로 커밋해야 구현자에게 간다.

```bash
git add <contract_tests_dir>
git commit -m "test : 이슈 #<N> 계약 테스트 — <n>건 (실패 확인)"
```

#### `3b-implement` ↔ `3c-incremental-qa`

부르기 직전 `git branch --show-current`가 이슈 브랜치이고 spec(·계약 테스트) 커밋이 HEAD에 있는지 확인한다
(`.claude/settings.json`의 `worktree.baseRef: "head"`가 없으면 기본 브랜치에서 갈라진다).

```
① 첫 go — 워크트리 생성과 기동이 한 번에 된다
Agent(subagent_type: "issue-harness:implementer", isolation: "worktree", name: "impl-<N>",
      run_in_background: true, model: <models.implement>, prompt: <템플릿>)
   → 완료 알림: 보고 + 워크트리 경로·브랜치

② 판정
   - git -C <워크트리> log --oneline <이전>..HEAD 로 커밋 확인
   - full: 3c — integration-qa(model: <models.qa>)에 <워크트리 경로>와 이 묶음의 경계면을 준다
   - 전이 규칙 1번부터

③ 다음 go — 같은 워크트리·같은 맥락
SendMessage(to: "impl-<N>", message: <템플릿 — 다음 묶음, 3c 지적은 [이전 실패 원인]>)
```

| 경로 | go 단위 | 묶음 사이 |
|---|---|---|
| full | 묶음 하나 | `3c`를 거친 뒤 다음 go |
| light | 묶음 전체 한 번 | 없음 (구현자가 묶음마다 `check_cmd`) |

**템플릿** — 이번 go에만 해당하는 것만 담는다. 규칙·보고 형식은 정의 파일에서 온다.

```
이슈 #<N>의 모듈 묶음 <M1: 이름> (<T1>~<T3>)을 구현한다.   (light: "묶음 M1~M<k> 전부")

[spec] <spec_dir>/issue-<N>.md 의 <M1> — 워크트리에 커밋돼 있다
[프로젝트 값] check_cmd=<…>, test_file_cmd=<…>, src_dirs=<…>, tests_dir=<…>, contract_tests_dir=<…>
[계약] 이 묶음이 소비·생산하는 스키마만 발췌 (<contract_skill>)
[답변된 전제] answer가 있는 open_questions만
[이전 실패 원인] 재호출·3c 지적이 있을 때만 — 빼먹으면 같은 실패를 반복한다
[주의] 이 묶음에 걸리는 기존 blocker
```

spec을 발췌하지 않는다(워크트리에 있다). 완료 알림은 "끝났다"만 뜻한다 — 성공 여부는 보고의 `result:`·커밋·`3c`로 판정한다.

**`3c`는 `check_cmd`를 다시 돌리지 않는다.** 구현자 보고의 `check_cmd` 출력이 근거이고, `3c`는 경계면 교차 비교와
계약 테스트(`contract_test_cmd`)만 돌린다.

구현자가 도메인 판단·계약 변경·의존성 추가를 요청하면 도메인 에이전트·`contract-guardian`·사람에게 넘기고
답을 다음 go에 담는다.

### Phase 4: 최종 검증

full은 팀원을 종료하고 서브에이전트로 검증한다 — 팀 안에서 검증하면 구현 맥락에 물든다.

**`4a-verify-blind`** (full만) — 명세를 주지 않는다. 프롬프트: `issue-harness:verification-protocol` 1단계.
`model: <models.verify_blind>` → `_workspace/verify_<N>_blind.md`

**`4b-verify-spec`** — **`4a`와 다른 인스턴스**, `model: <models.verify_spec>`. 프롬프트:
`issue-harness:verification-protocol` 2단계(full은 1단계 보고서 대조, light는 코드 직접 대조).
→ `_workspace/verify_<N>_spec.md`. 불일치 수와 지점은 이 파일과 보고에 남는다.

`4a` → `4b` 순서를 뒤집지 않는다 — 명세를 먼저 읽으면 코드를 명세대로 본다.

검증이 수정을 요구하면 `SendMessage(to: "impl-<N>")`로 되돌리고, 수정 커밋 뒤 해당 검증만 다시 한다.

**`4c-make-check`** — **워크트리에서** `check_cmd` 1회. 머지 전 이슈 브랜치는 구조상 깨져 있으므로
(`issue-harness:issue-workflow` 8절) primary가 아니라 워크트리 HEAD를 검사한다.

```bash
(cd <워크트리> && <check_cmd>)
```

**`4d-placeholder-scan`** — 변경 파일에서 skip·only, 빈 assert, `pass`만 있는 함수, `TODO` 미구현 분기.
있으면 완료가 아니다.

**`4e-merge`** — 머지 조건·명령은 `issue-harness:issue-workflow` 8절이 정본이다. 머지 후 `check_cmd`는
**이슈 브랜치에 워크트리가 모르는 커밋이 있을 때만** 돌린다:

```bash
git switch <이슈브랜치>
git merge --no-ff <워크트리브랜치> -m "chore : 워크트리 브랜치를 이슈 브랜치에 반영한다 (#<N>)"
# 기본 브랜치가 앞서 있으면 반영한다 (issue-workflow 8절 2단계)
git fetch origin <기본 브랜치>
git merge-base --is-ancestor origin/<기본 브랜치> HEAD || git merge --no-ff origin/<기본 브랜치> -m "chore : <기본 브랜치>를 이슈 브랜치에 반영한다 (#<N>)"
# 머지 결과 트리가 4c에서 검사한 트리와 같으면 다시 돌리지 않는다
[ "$(git rev-parse HEAD^{tree})" = "$(git rev-parse <워크트리브랜치>^{tree})" ] || <check_cmd>
```

**`4f-review`** — `pr_mode.<경로>`가 `review`·`full`일 때만. `4e` 뒤 이슈 브랜치에서 `pr-writing` 7절 리뷰를 실행하고
결과를 `_workspace/review_<N>.md`에 남긴다. 결함은 `SendMessage(to: "impl-<N>")`로 되돌리고 수정 커밋 뒤 `4c`·`4e`를 다시 한다
(테스트 목록 대응이 바뀌면 `4b`도).

### Phase 5: 보고

1. `_workspace/`는 보존한다.
2. `handoff_to_human`을 채우고 사용자에게 보고한다 — 검증된 완료, 미완료·블로커, 남은 `TODO(확인필요)`,
   사람이 실행할 명령. 워크트리 브랜치는 origin에 올리지 않는다.
   PR 본문은 `pr-writing`으로 `_workspace/pr_<N>.md`에 쓴다. `push_pr: orchestrator`면 오케스트레이터가
   `pr-writing` 6절대로 push·PR을 실행하고 링크를 보고한다 — 역할 에이전트는 여전히 push하지 않는다.
   아니면 아래 명령을 출력한다.

   ```
   머지·검증 완료. 다음 명령을 실행하세요:

     git push -u origin <이슈브랜치>
     gh pr create --base <기본 브랜치> --title "..." --body-file <경로>
   ```
3. `ACTIVE`를 넘기거나 지운다.
4. `pr_mode.<경로>`가 `full`이면 PR 뒤 같은 세션에서 `pr-writing` 8절 회고를 실행한다.
   `pr_mode`가 없으면 스킬 목록에 `mattpocock-skills:`가 보일 때 code-review·retro를 안내만 한다.
   PR 본문은 팀 `pr-writing`을 따른다(`mattpocock-skills:pr`을 쓰지 않는다).
5. "결과나 팀 구성에서 바꾸고 싶은 점이 있나요?" — 강요하지 않는다.

## 에러 핸들링

| 상황 | 전략 |
|---|---|
| `.claude/harness.config.json` 없음 | 멈추고 `/issue-harness:init` 안내 |
| 팀원 1명 실패 | 1회 재시작. 재실패 시 남은 팀원에게 재할당하고 보고서에 누락 명시 |
| 팀원 과반 실패 | 중단하고 사용자에게 확인 |
| `check_cmd` 실패 | 고친다. 테스트를 지우거나 skip하지 않는다 |
| 계약과 구현 충돌 | 임의 판정 금지. 더 많은 소비자가 따르는 쪽을 제안하고 사용자에게 보고 |
| 도메인 정보 부재 | `TODO(확인필요)` + `AskUserQuestion`. 추측으로 채우지 않는다 |
| 의존성 추가 필요 | 사람의 결정. 멈추고 보고 |
| 외부 의존 접근 불가 | 우회 구현을 만들지 말고 보고 |
| 선행 이슈 미완 | 진행 여부를 사용자에게 확인 |
| 계약 테스트가 작성 시점에 통과 | 빈 테스트다. 다시 쓰게 하고 `3b`로 보내지 않는다 |
| `4a`가 명세를 요청 | 주지 않는다 |
| `4a`·`4b` 불일치 | 임의 판정 금지. 근거와 함께 사람에게 보고 |
| 구현자가 계약 테스트를 고치려 함 | 막는다. 구현을 고치거나 `contract-guardian`에게 판단 요청 |
| light 중 계약 변경 필요 | full로 올린다 — 부분 머지 후 spec 수정·`3a`, 남은 묶음은 새 구현자 (`issue-harness:harness-state` 전이 규칙 6) |

## 테스트 시나리오

**full:** "이슈 12 시작" → spec 없음 → 계약 신설 이슈라 full → `issue-planner` spec, `TODO(확인필요)` 3건 →
`AskUserQuestion`으로 답·테스트 목록·경로 승인 → spec 커밋 → 팀(`contract`·`qa`) 계약 확정 → `qa` 실패 테스트 → 커밋 →
`implementer` 묶음 1 → `3c` → `SendMessage` 묶음 2 … → `4a` → `4b` → 워크트리에서 `check_cmd` → 머지(트리 같음, 재실행 생략) →
push 명령 출력.

**light:** "이슈 20 시작" → 목록 화면 정렬 수정, 기존 계약만 소비 → light, 예상 2항목이라 오케스트레이터가 spec 작성 →
승인 → spec 커밋 → `implementer` 한 번에 전체(묶음 끝 `check_cmd`) → `4b` 1회 → `4c` → 머지 → push 명령 출력.

**에러:** 구현자가 외부 패키지 미설치로 import 실패 → blocker(`owner: human`)로 보고하고 멈춤 → 오케스트레이터가
`state.json`에 옮기고 설치를 요청 → 의존성과 무관한 묶음은 계속 → Phase 5 보고에 "의존성 설치 대기" 명시.
