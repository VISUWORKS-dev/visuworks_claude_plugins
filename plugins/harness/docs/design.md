# harness 플러그인 설계

이슈 = 워크트리 = PR 단위로 **계획 → 계약 확정 → 구현(TDD) → 2단계 검증**을 태우는
멀티 에이전트 하네스를 플러그인으로 분리한다. 원본은 한 프로젝트의 `.claude/`에
도메인 규약과 섞여 있었다. 이 문서는 무엇을 플러그인으로 옮기고, 무엇을 프로젝트에
남기며, 프로젝트별 값을 어떻게 주입하는지 정한다.

> 이 레포는 public이다. 원본 프로젝트의 고유명·이슈 번호·로컬 경로는 이 문서에도
> 쓰지 않는다. 원본 파일 중 이름 자체가 도메인을 드러내는 셋은 별칭으로 부른다.
>
> | 별칭 | 원본에서의 역할 |
> |---|---|
> | **O** | 오케스트레이터 스킬 (`.claude/skills/<domain>-harness/`) |
> | **C** | 단계 간 데이터 계약 스킬 (`.claude/skills/<domain>-contracts/`) |
> | **D** | 도메인 판단 에이전트 (`.claude/agents/<domain>-domain-expert.md`) |

## 0. 전제 확인 — 공식 문서 대조 결과

작업 전제를 공식 문서(code.claude.com/docs, 2026-10-01 조회)와 대조했다.

| 전제 | 결과 | 근거 |
|---|---|---|
| 플러그인 `settings.json`은 `agent`·`subagentStatusLine`만 반영 | **맞음** | plugins/manifest-reference: "Only `agent` and `subagentStatusLine` take effect; other keys are dropped at load." |
| 플러그인은 `.claude/rules/`·루트 `CLAUDE.md`를 로드하지 않음 | **맞음** | plugins/components: "A CLAUDE.md at the plugin root isn't loaded as context" — `claude plugin validate`도 경고한다 |
| 훅은 `hooks/hooks.json`, `${CLAUDE_PLUGIN_ROOT}`, 켜진 모든 세션에서 발화 | **맞음**. 프로젝트 단위로 좁히는 방법은 문서에 없다 — `matcher`뿐 | plugins/components 「Hooks」 |
| 이름은 `harness:<name>`, 에이전트의 `permissionMode`·`hooks`·`mcpServers` 무시 | **맞음 + 하나 더**: `initialPrompt`도 무시. `model`·`isolation: worktree`는 지원 | plugins/components 「Agents」 |
| 프로젝트 활성화는 `extraKnownMarketplaces` + `enabledPlugins` | **맞음**. 단 **워크스페이스 신뢰(trust) 후에만** 적용되고, 신뢰 전·`-p` 실행에서는 경고 없이 무시된다 | settings-reference 「extraKnownMarketplaces」 |

**전제와 다른 점 — 설계에 반영한다:**

1. **`commands/`는 레거시다.** "Commands are the older format, and skills supersede them for new
   work." → `/harness:init`은 `commands/init.md`가 아니라 `skills/init/SKILL.md` +
   `disable-model-invocation: true`로 만든다. 호출 이름은 `/harness:init` 그대로다.
2. **플러그인 스킬 본문에서 `${CLAUDE_PLUGIN_ROOT}`·`${CLAUDE_SKILL_DIR}`가 치환된다**
   (skills 「Available string substitutions」). → 스크립트를 플러그인에 두고 스킬이
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-state.py"`로 부를 수 있다. Makefile이 필요 없다.
3. **`SubagentHandback`** (v2.1.271+, auto 모드): 서브에이전트가 이 도구로 보고하면
   `SubagentStop`의 `last_assistant_message`에는 **보고가 아니라 맺음말**이 온다(hooks
   「SubagentStop input」). 지금 훅은 `msg`를 그것으로 채우므로 auto 모드에서는 보고가
   유실된다. → questions Q3.
4. **에이전트 팀에 플러그인 에이전트 타입을 쓸 수 있는지 문서에 명시가 없다.**
   agent-teams 문서는 "project, user, or managed subagent scope"만 적는다. → 단계 4 (d)에서
   실측하고, 안 되면 팀 대신 서브에이전트로 부르는 경로를 쓴다.
5. **`SubagentStop`의 `agent_type`**: 문서상 "agent name"이고, 내부 에이전트(프롬프트 제안 등)는
   빈 문자열로 온다. 원본 실측과 같다 — 이름으로 호출하면 이름이 온다. 플러그인 에이전트를
   타입으로 부를 때 `harness:<name>`이 오는지는 단계 4 (b)에서 실측한다.

## 1. 분류

판정: **코어** → 플러그인 / **설정** → `/harness:init`이 프로젝트에 깔아줌 / **도메인** → 프로젝트에 남김.

### 1.1 `.claude/skills/`

| 원본 | 판정 | 플러그인 위치 · 비고 |
|---|---|---|
| O (오케스트레이터) | **코어** + 도메인 절 분리 | `skills/issue-harness/`. Phase 0–5, 실행 모드, 3b↔3c 루프, 4a→4b, 에러 핸들링은 코어. **이슈 유형별 팀 구성 표**(원본 이슈 번호로 된 행), 테스트 시나리오의 도메인 사례, 「외부 의존 접근 불가」 행의 대상 이름은 도메인 → 범용 서술 + `harness.config.json` 참조로 바꾼다 |
| `harness-state` | **코어** | `skills/harness-state/`. 스키마 예시 값(이슈 제목·계약명·블로커 문구)만 범용 예시로 교체 |
| `verification-protocol` | **코어** + 도메인 절 분리 | 1·2단계, 계약 TDD 순서, 소유권, 실패 확인 의무는 코어. **「계약 TDD 범위」 표의 도메인 행**과 **「`--dry-run` 경로만 본다」 절**(원본 파이프라인의 LLM 축 이름)은 원리만 남긴다: "외부 호출을 끈 경로만 계약 테스트가 보면, 꺼진 분기의 제약은 단위 테스트가 맡는다 + mutation으로 확인" |
| `tdd-cycle` | **코어** | 거의 그대로. `make check` → 설정값 |
| `poc-scope-guard` | **분리** | 판정 질문 5개·「만들지 않는 것」 일반 행·「절제하지 않는 것」 원칙·범위 초과 조짐·기록 규칙 → **코어 `skills/scope-guard/`**. 원본 이슈를 근거로 든 행·판정 예시 표·이메일 HTML 항목 → **도메인**(원본에 축소본으로 남음) |
| `issue-workflow` | **분리** — 기본안 수정 | 기본안은 "의존 순서만 도메인"이었다. 확인 결과 1–8절(브랜치, spec, 핸드오프 커밋, isolation 워크트리, `.venv`, 커밋, 로컬 머지, 정리)은 **코어**다 → `skills/issue-workflow/`. **「이슈 의존 순서」 절**과 테스트 시나리오만 도메인. 5절의 `uv`/`.venv` 서술은 "의존성 설치 디렉터리는 워크트리마다 따로"로 범용화하고 명령은 설정값으로 |
| C (계약) | **도메인** | 원본에 남음. 코어는 `contract_skill` 설정으로 이름만 안다 |

### 1.2 `.claude/agents/`

| 원본 | 판정 | 비고 |
|---|---|---|
| `issue-planner` | **코어** | 「입력/출력」 절이 아직 "Write 권한이 없으므로 본문 전체를 반환"이라 적혀 있어 오케스트레이터(직접 쓴다)·권한 표와 **모순**이다. 코어로 옮기면서 "spec 파일 하나만 직접 쓴다"로 맞춘다 |
| `schema-guardian` | **코어** (이름 변경 → 3절) | 「왜 따로 있는가」의 원본 이슈 사례를 이유만 남긴다: "스키마 하나가 여러 소비자에 걸리면 생산자 편의 변경이 소비자를 조용히 깬다" |
| `pipeline-engineer` | **코어** (이름 변경 → 3절) | description의 수집/컨텐츠/HTML/DAG 열거, 「기존 것을 먼저 찾는다」의 외부 레포 사례, 빈 결과/실패 구분의 사례는 범용화 |
| `integration-qa` | **코어** | 경계면 5개 다이어그램·승인 상태값 체크 항목은 도메인 → "경계면 목록은 `contract_skill`에 있다"로 대체 |
| D (도메인 판단) | **도메인** | 원본에 남음. `domain_agents` 설정으로 오케스트레이터가 안다 |

네 코어 에이전트의 공통 절 「상태 기록 — 파일이 아니라 보고로 한다」「최종 보고 형식」은 네 파일에
같은 문장이 복사돼 있다. 플러그인에서도 에이전트마다 둔다 — 에이전트는 다른 에이전트 파일을
읽지 않으므로 공유할 방법이 스킬 참조뿐이고, 짧은 블록이라 복사가 더 싸다.

### 1.3 훅·스크립트

| 원본 | 판정 | 비고 |
|---|---|---|
| `.claude/hooks/record-agent-event.py` | **코어** | `hooks/hooks.json`의 `SubagentStop` → `scripts/record-agent-event.py`. **`Stop` 분기는 뺀다**(4절) |
| `.claude/hooks/check-state.py` | **코어** | `scripts/check-state.py`. `SUB_STAGES`는 `harness-state` 스킬 표와 1:1 — 둘 다 플러그인에 있어 한 곳에서 바뀐다. v1 이관 스크립트 언급은 뺀다(원본 레포 로컬 파일) |
| `.githooks/commit-msg`·`pre-commit`·`_harness.py` | **코어 원본, 설정으로 배포** | 플러그인 `templates/githooks/`에 원본을 두고 init이 프로젝트 `.githooks/`로 복사한다. `core.hooksPath`에 플러그인 캐시 경로를 직접 걸 수 없다 — 캐시 경로에 버전이 들어가 업데이트마다 바뀐다(manifest-reference: "Each version has its own cache directory"). `tests/` 하드코딩 → `harness.config.json`의 `tests_dir`를 읽는다(없으면 `tests/`) |
| `pre-commit`의 `importorskip` 허용 주석 | 코어(규칙) + 도메인(사례) | 규칙 "조건부 skip(`importorskip`)은 무조건 skip과 구분한다"만 남기고 원본 테스트 파일명은 뺀다 |
| `Makefile` `check-state` 타깃 | **삭제** (원본에서) | 스킬이 `${CLAUDE_PLUGIN_ROOT}`로 직접 실행한다. 사람이 터미널에서 돌릴 경로는 README에 적는다 |

### 1.4 설정 파일

| 원본 | 판정 | 비고 |
|---|---|---|
| `settings.json` `hooks.SubagentStop` | **코어** → 플러그인 훅 | 원본에서 **지운다** — 남기면 이중 발화 |
| `settings.json` `hooks.Stop` | **삭제** | 4절 |
| `settings.json` `permissions.deny` (`--no-verify`, `-n`) | **설정** | 플러그인이 넣을 수 없다(settings.json 키 무시). init이 diff로 제시 |
| `settings.json` `worktree.baseRef: "head"` | **설정** | 같은 이유. 이게 없으면 isolation 워크트리가 기본 브랜치에서 갈라져 핸드오프 커밋이 없는 워크트리가 된다 |
| `.gitignore` `.claude/worktrees/`·`.harness/`·`.harness.bak-*/`·`_workspace/`·`_workspace_*/` | **설정** | init이 빠진 줄을 제시 |
| `core.hooksPath=.githooks` | **설정** | git 로컬 설정이라 파일이 아니다. init이 현재 값을 보고 비어 있을 때만 설정, 다른 값이면 멈춘다 |
| `.claude/rules/agent-permissions.md` | **설정** | 플러그인이 rules를 로드하지 않으므로 프로젝트에 있어야 한다. 내용은 범용 — 경로는 설정값 이름으로 쓴 템플릿 |
| `orca.yaml` | **도메인** (원본에 남음) | 사람이 orca로 워크트리를 띄울 때만 쓰는 도구 설정. 하네스 흐름(isolation 서브에이전트)과 무관하다 |
| `CLAUDE.md` 하네스 절 | **설정**(조각) + 도메인 | init은 파일을 쓰지 않고 붙일 조각을 **출력만** 한다 — CLAUDE.md는 거의 항상 이미 있다 |

### 1.5 `docs/harness-architecture.html`

**도메인 쪽에 남기되 범용판을 플러그인 README로 대체한다.** 원본은 1–5·7·8절이 범용 구조,
6절(경계면)이 도메인이다. HTML 878행을 플러그인에 복사하면 스킬과 이중 정본이 된다.
원본에서는 지우고 하네스 절을 `CLAUDE.md`·플러그인 README 링크로 대체하는 안을 제안한다 → Q5.

## 2. 프로젝트별 값 주입 — `.claude/harness.config.json`

**기본안을 채택한다.** tracked JSON 한 파일.

| 대안 | 기각 이유 |
|---|---|
| 플러그인 `userConfig` | 사람마다 다른 값용이다(설치자 로컬 저장). 프로젝트 값을 여기 두면 팀원마다 따로 입력하고 갈라진다 |
| `CLAUDE.md` 산문 | git hook(`pre-commit`의 `tests_dir`)·`check-state.py`가 읽을 수 없다. 기계가 읽는 값과 사람이 읽는 규약은 다른 곳에 둔다 |
| 스킬마다 프로젝트 오버라이드 스킬 | 값 하나 바꾸려고 스킬 본문을 복제하게 된다. 플러그인 업데이트와 갈라진다 |

**결정적 이유는 소비자에 Python 스크립트가 있다는 것이다.** 오케스트레이터·에이전트(모델)와
git hook·check-state(스크립트)가 같은 값을 읽어야 하고, 둘 다 읽을 수 있는 형식은 JSON 파일이다.

### 형식

```jsonc
{
  "model": "opus",                       // Agent·TeamCreate 호출의 model. 생략 시 호출에 model을 넣지 않는다(상속)
  "check_cmd": "make check",             // 4c·4e·tdd-cycle의 전체 검증
  "contract_test_cmd": "uv run pytest tests/contract/ -v",   // 3a-test 실패 확인
  "src_dirs": ["src/"],                  // implementer 쓰기 허용
  "tests_dir": "tests/",                 // pre-commit 약화 검사·[structural] 금지 대상
  "contract_tests_dir": "tests/contract/", // integration-qa 소유
  "spec_dir": "docs/specs",              // spec 경로 = <spec_dir>/issue-<N>.md
  "branch_pattern": "<N>-<slug>",        // 이슈 브랜치 이름 규칙 (설명용 문자열)
  "contract_skill": "my-contracts",      // 계약 정본 스킬 이름. 없으면 null — contract-guardian이 spec의 계약 절을 정본으로 쓴다
  "domain_agents": [                     // 팀에 넣을 수 있는 프로젝트 에이전트
    { "name": "my-domain-expert", "decides": "무엇을 담을지", "writes": ["docs/", "_workspace/"] }
  ],
  "domain_skills": {                     // 코어 스킬이 함께 읽을 도메인 보충
    "scope": "my-scope-notes",           // scope-guard의 프로젝트 사례
    "workflow": "my-issue-order"         // 이슈 의존 순서 (1b-dependency-check)
  },
  "dependency_change": "human"           // 의존성 추가 주체. 현재 값은 human 하나 — 에이전트 금지 규칙의 근거
}
```

- **읽는 쪽:** `issue-harness`는 Phase 0에서 읽어 이후 모든 `Agent`/`TeamCreate` 호출에 반영한다.
  에이전트는 오케스트레이터가 프롬프트에 필요한 값을 담아 준다(상태 파일과 같은 원칙 — 에이전트가
  설정을 찾으러 다니지 않는다). 단 에이전트 본문에도 "없으면 `.claude/harness.config.json`을 읽는다"를 둔다.
- **스크립트:** `pre-commit`·`commit-msg`는 `tests_dir`만, `check-state.py`는 `spec_dir`를 쓰지 않는다
  (state.json의 `spec` 경로를 그대로 검사).
- **파일이 없으면:** 오케스트레이터는 멈추고 `/harness:init`을 안내한다. git hook은 기본값(`tests/`)으로 돈다 —
  설정 누락이 검사를 끄면 안 된다.
- **`model`은 frontmatter가 아니라 호출 파라미터로 준다.** 플러그인 에이전트 frontmatter는 `model: inherit`.
  원본은 "모든 Agent 호출에 `model: "opus"`를 명시한다"였으므로 같은 동작이다.

## 3. 에이전트 이름

| 원본 | 플러그인 | 판단 |
|---|---|---|
| `issue-planner` | `issue-planner` | 유지 — 이미 범용 |
| `schema-guardian` | **`contract-guardian`** | 변경 — 소유 대상이 스키마만이 아니라 상태값·경로까지인 "계약"이고, `contract_skill`·`contract_tests_dir`와 이름이 맞는다 |
| `pipeline-engineer` | **`implementer`** | 변경 — "pipeline"은 원본 도메인(데이터 파이프라인)에 묶인 말이다. 원본 spec 템플릿 주석이 이미 "implementer"라고 쓴다 |
| `integration-qa` | `integration-qa` | 유지 — 경계면 교차 비교라는 역할이 범용 |

호출 형태는 `Agent(subagent_type: "harness:implementer", name: "implementer-<N>", ...)`.

### 기존 `.harness/` 기록과의 호환

- **`state.json`의 `agents` 키:** `check-state.py`는 키 이름을 검사하지 않는다(값의 `status`만).
  옛 이슈 파일은 옛 키 그대로 통과한다. 새 이슈부터 새 이름을 쓴다. **마이그레이션 없음.**
  키에는 접두사 없이 쓴다(`agents.implementer`) — `:`는 사람이 jq로 읽을 때 걸린다.
- **`events.jsonl`의 `agent` 값:** 이미 자유 문자열이다. 원본 기록을 집계하면 타입명보다
  호출 이름(`planner16`, `qa16-blind` 등)이 많다. 이름이 바뀌어도 깨지는 소비자가 없다.
- **오케스트레이터는 항상 `name`을 준다** — 그러면 `agent`에 `harness:` 접두사가 붙든 말든
  기록이 호출 이름으로 고정된다. 타입명으로 기록되는 경우(이름 없이 호출)는 `harness:<name>`이
  올 것으로 예상하며 단계 4 (b)에서 실측한다.
- **원본의 활성 이슈가 진행 중이면** 전환 시점에 그 이슈의 `agents` 키를 손으로 바꿀 필요는 없다 —
  오케스트레이터가 새 이름으로 새 키를 쓰고 옛 키는 기록으로 남는다. 섞이는 것이 싫으면 전환 전에
  이슈를 끝낸다 → Q4.

## 4. 훅

### 4.1 `SubagentStop` → 플러그인

```json
{ "hooks": { "SubagentStop": [ { "hooks": [ {
  "type": "command",
  "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/record-agent-event.py\""
} ] } ] } }
```

`matcher`를 두지 않는다 — `agent_type`이 이름일 수 있어 타입으로 거를 수 없다
(타입 화이트리스트로 거르면 이름으로 호출된 에이전트 기록이 0건이 된다). 내장 에이전트
블랙리스트는 스크립트가 한다.

### 4.2 `Stop` → 뺀다 (기본안 확인)

- `Stop`은 **플러그인이 켜진 모든 레포의 매 턴**에 발화한다. 지금 스크립트는 `ACTIVE` 확인 전에
  `git rev-parse`를 돌린다 — 하네스를 안 쓰는 레포에서도 매 턴 git 프로세스 하나.
- 쓰임새는 사람이 orca 등으로 **별 세션**을 띄운 경우뿐이다. 하네스 흐름의 구현자는
  `isolation: worktree` 서브에이전트라 `SubagentStop`으로 잡힌다(원본 실측).
- 남길 이유를 찾지 못했다. 별 세션 완료는 오케스트레이터가 워크트리 커밋으로 확인하는 절차가
  `harness-state`에 이미 있다(「별도 세션에 인계한 작업은 완료 알림이 오지 않는다」).
- 스크립트에서 `Stop` 분기와 그 docstring을 지운다. 스킬의 `source: "worktree"` 설명은
  "과거 기록에 남아 있을 수 있다"로 한 줄 남긴다(원본 `events.jsonl`에 실재).

### 4.3 하네스를 안 쓰는 레포에서의 안전성 — **가드 보강 필요**

지금 순서: stdin 파싱 → `git_dirs(cwd)` → `ACTIVE` 확인.

| 상황 | 지금 동작 | 문제 |
|---|---|---|
| git 레포, `.harness/ACTIVE` 없음 | 조용히 종료 | 없음 |
| **git 레포가 아닌 디렉터리** | `git_dirs`가 `RuntimeError` → **`hook FAILED` 로그** | 플러그인을 켠 모든 비-git 세션에서 서브에이전트가 끝날 때마다 FAILED가 쌓여 진짜 실패를 묻는다 |
| `cwd` 키 없음 | `KeyError` → FAILED | 같은 문제 |

→ **비-git·`cwd` 없음은 "하네스 밖"으로 보고 로그 없이 종료한다.** `git_dirs`의 명시적 실패는
`ACTIVE`가 있는데 경로가 깨진 경우를 위한 것이었으므로, 순서를 바꿔 "git 아님 → 조용히 종료"를
먼저 판정한다. 단계 4 (f)가 이것을 실측한다.

`print("{}")`를 맨 앞에 두는 것, 예외를 삼키는 것은 유지한다 — 어떤 경우에도 세션을 막지 않는다.

### 4.4 같은 마켓플레이스의 기존 플러그인 훅과의 간섭 — 없음

| | 기존 플러그인 (Notion 게이트) | harness |
|---|---|---|
| 이벤트 | `PreToolUse` | `SubagentStop` |
| matcher | `mcp__.*notion.*(search|query).*` | 없음 |
| 출력 | `permissionDecision: "ask"` | `{}` (결정 없음) |

이벤트가 다르므로 같은 호출에 함께 걸리지 않는다. 서브에이전트가 Notion 검색을 하면 그 도구 호출에
ask가 뜨는 것은 하네스와 무관하게 원래 동작이다. OMC 등 다른 플러그인의 `SubagentStop` 훅과도
독립적으로 각자 실행된다 — `{}`는 다른 훅의 결정을 덮지 않는다. 단계 4 (h)가 확인한다.

### 4.5 git hook (`.githooks/`)

플러그인 훅이 아니라 git 훅이다. 4.3과 같은 문제가 없다 — 프로젝트가 `core.hooksPath`로 켤 때만 돈다.
`_harness.record()`는 이미 `ACTIVE`가 없으면 기록만 생략한다(검사는 그대로).

## 5. `/harness:init` 명세

`skills/init/SKILL.md` (`disable-model-invocation: true`) + `scripts/init.py`.
스킬은 `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init.py"`를 돌리고 결과를 사람에게 보여준다.
**복사·비교를 모델이 아니라 스크립트가 한다** — 두 번째 실행이 정확히 "변경 없음"이어야 하고,
모델이 파일을 다시 쓰면 그 보장이 없다.

### 쓰는 것

| 대상 | 원본 | 없을 때 | 있고 같을 때 | 있고 다를 때 |
|---|---|---|---|---|
| `.claude/harness.config.json` | `templates/harness.config.json` | 생성 | 건너뜀 | **diff 출력, 건드리지 않음** |
| `.claude/rules/agent-permissions.md` | `templates/agent-permissions.md` | 생성 | 건너뜀 | diff 출력 |
| `.githooks/commit-msg`·`pre-commit`·`_harness.py` | `templates/githooks/` | 생성 + 실행 비트 | 건너뜀 | diff 출력 |

### 쓰지 않고 제시만 하는 것 (병합이 필요한 파일)

| 대상 | 출력 |
|---|---|
| `.claude/settings.json` | 빠진 키만: `permissions.deny`의 두 줄, `worktree.baseRef: "head"`, (선택) `enabledPlugins`·`extraKnownMarketplaces`. 파일이 없으면 생성한다 |
| `.gitignore` | 빠진 줄만 |
| `git config core.hooksPath` | 비어 있으면 `.githooks`로 설정. 다른 값이면 현재 값을 보여주고 멈춤 |
| `CLAUDE.md` | 붙일 하네스 절 조각 |

### 동작 규칙

- **한 파일이라도 "있고 다름"이면 종료 코드 1**, 나머지 생성 대상은 그대로 처리한다
  (덮어쓰지 않을 뿐 멈춤의 범위는 그 파일). 출력 끝에 "다른 파일 N개 — 직접 병합"을 적는다.
- `--dry-run`: 아무것도 쓰지 않고 할 일만 출력.
- git 레포가 아니면 즉시 종료.
- `.harness/`·`docs/specs/`는 만들지 않는다 — 이슈 착수 시 오케스트레이터가 만든다.
- **두 번째 실행:** 모든 항목이 "건너뜀"이고 쓰기 0건이어야 한다. 단계 4 (g)가 확인한다.

### check-state

`Makefile`에 의존하지 않는다. 스킬 본문:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-state.py"
```

사람이 터미널에서 돌릴 때는 플러그인 경로를 모르므로 README에
`claude plugin` 설치 경로 확인법을 적는다. 프로젝트가 원하면 자기 Makefile에 타깃을 둘 수 있지만
init은 만들지 않는다(경로가 버전마다 바뀐다).

## 6. 하드코딩된 이름·값

원본 파일 기준 행 번호다. 플러그인에서 바꿀 값:

| 항목 | 바꿀 값 |
|---|---|
| A1 `subagent_type` | `"harness:<name>"` (코어) / `domain_agents[].name` (도메인) |
| A2 `TeamCreate` `agent_type` | 같음. 플러그인 타입이 팀에서 안 되면 서브에이전트 호출로 대체 (0절 4) |
| A3 `model: "opus"` | `harness.config.json`의 `model`. 에이전트 frontmatter는 `inherit` |
| A4 `make check` | `check_cmd` |
| A5 check-state 경로 | `${CLAUDE_PLUGIN_ROOT}/scripts/check-state.py` |
| A6 계약 스킬명 C | `contract_skill` |
| A7 도메인 에이전트 D | `domain_agents` |
| A8 오케스트레이터 스킬명 O | `issue-harness` |
| A9 `tests/contract/` | `contract_tests_dir` |
| A10 `uv`/`pytest`/`.venv`/`pyproject` | `contract_test_cmd`, "의존성 설치 디렉터리", "의존성 매니페스트"로 범용화 |
| A11 역할 에이전트명 | `schema-guardian` → `contract-guardian`, `pipeline-engineer` → `implementer` |
| A12 `src/`·`tests/` | `src_dirs`·`tests_dir` |

<!-- 아래 표는 원본 레포에서 스크립트로 뽑았다. 행 번호는 원본 HEAD 기준 -->

| 파일 | 항목 | 행 |
|---|---|---|
| O | A1 | 20, 159, 208, 244, 357, 373 |
| O | A2 | 312, 313, 314 |
| O | A3 | 28, 160, 248, 312, 313, 314, 358, 374 |
| O | A4 | 42, 84, 101, 391, 395, 400, 441, 452, 471 |
| O | A6 | 23, 24, 26, 162, 276, 361, 376, 438 |
| O | A7 | 25, 36, 77, 294, 301, 302, 303, 313 |
| O | A8 | 2 |
| O | A9 | 224, 391 |
| O | A10 | 42, 292, 455, 476 |
| O | A11 | 15, 23, 24, 35, 37, 40, 77, 79, 167, 208, 244, 254, 294, 295, 302, 303, 304, 312, 461 |
| O | A12 | 37 |
| `skills/harness-state/SKILL.md` | A1·A2 | 217, 218 |
| | A4 | 196, 283, 316, 330, 368, 443 |
| | A5 | 274, 352, 355 |
| | A6 | 36 |
| | A7 | 74, 308 |
| | A11 | 60, 65, 92, 172, 217, 308, 310, 372, 434, 440 |
| `skills/verification-protocol/SKILL.md` | A6 | 35, 49, 73 |
| | A9 | 131, 146, 150, 152, 160 |
| | A10 | 160 |
| | A11 | 115, 129, 147, 148, 152, 153, 188, 194 |
| | A12 | 35, 36, 147, 148, 150 |
| `skills/tdd-cycle/SKILL.md` | A4 | 21, 68 |
| | A9 | 51 |
| | A11 | 52 |
| | A12 | 39 |
| `skills/poc-scope-guard/SKILL.md` | A4 | 52 |
| `skills/issue-workflow/SKILL.md` | A1 | 72 |
| | A4 | 106, 136, 193, 199, 268 |
| | A6 | 259 |
| | A8 | 76, 90 |
| | A10 | 93, 104, 106, 107, 108, 111, 114, 115, 231 |
| | A11 | 25, 68, 72, 84, 264, 265 |
| `agents/issue-planner.md` | A3 | 4 |
| | A4 | 34 |
| | A7 | 121 |
| | A11 | 101, 102, 104, 120, 148 |
| `agents/schema-guardian.md` | A3 | 4 |
| | A6 | 24, 50, 68, 88 |
| | A7 | 76, 82 |
| | A11 | 2, 56, 80, 106 |
| | A12 | 48, 89, 93 |
| `agents/pipeline-engineer.md` | A3 | 4 |
| | A4 | 3, 17, 48, 68, 96, 131 |
| | A6 | 15, 60, 114 |
| | A7 | 61, 87, 104 |
| | A9 | 114, 139 |
| | A10 | 48, 49 |
| | A11 | 2, 26, 86, 97, 104, 114, 140 |
| | A12 | 62, 64, 112 |
| `agents/integration-qa.md` | A3 | 4 |
| | A6 | 76, 82 |
| | A9 | 132, 137, 159 |
| | A11 | 49, 98, 102, 104, 119, 123 |
| | A12 | 133, 140 |
| `hooks/check-state.py` | A5 | 8 |
| `.githooks/commit-msg` | A12 | 46 |
| `.githooks/pre-commit` | A9·A10 | 15, 17 |
| | A12 | 19 |

## 7. public 정리

코어로 옮길 파일에서 걸린 행과 처리 방침이다. **원문은 이 문서에 옮기지 않는다** — 행 번호와 분류만.

### 처리 방침

| 분류 | 처리 |
|---|---|
| **B1 고유명·도메인 서술** (기관명, 매체명, 외부 레포, 원본 파이프라인 단계명·산출물 파일명·외부 API) | 역할 이름으로 바꾼다: "생산자 → 소비자", "외부 의존(다른 레포·외부 API)", "산출물 파일". 예시가 필요하면 범용 예시(`orders.json`의 `created_at` vs `createdAt`) |
| **B2 이슈 번호를 단 사고 사례** | 사례는 지우고 **이유만 일반화**해 남긴다. 예: "타입 화이트리스트로 거르면 이름으로 호출된 에이전트 기록이 0건이 된다" / "검증자가 `blockers`를 다른 키로 써서 오케스트레이터가 집계 중 `KeyError`로 멈췄다 → 스키마는 문서가 아니라 검사가 지킨다" / "워크트리와 primary가 각자 기록해 정본이 갈렸다" / "`worktree.baseRef`가 없으면 워크트리가 기본 브랜치에서 갈라져 spec이 없다" / "공유 가상환경이 메인의 옛 코드를 읽었다" |
| **B3 날짜 사고** (「2026-09-29 사고」 등) | 날짜를 지우고 이유만: "여럿이 같은 JSON을 읽고-고치고-쓰다 정본이 갈렸다". 스키마 예시의 타임스탬프는 `<ISO8601>`로 |
| **B4 로컬 경로** | `~/.claude/harness-hook.log`는 사용자 홈 상대 기본값이라 개인 경로가 아니다 → **유지**(특정 사용자의 절대경로가 아니다). 그 외 0건 |
| **B5 orca** | 특정 도구명. "사람이 별 세션으로 띄운 워크트리"로 바꾼다. `.venv` 공유 설정 이야기는 도메인 쪽(원본 `CLAUDE.md`)에만 남긴다 |
| **B6 데모·PoC 전제** | `scope-guard`는 "마감이 있는 작업"으로 일반화한다. `demo_blocker` **값 자체는 유지**(→ Q2), 설명을 "다음 단계 진행을 막는 결함"으로 바꾼다. "내일 데모" 같은 시점 표현은 지운다 |

### 대상 행

| 파일 | 분류 | 행 |
|---|---|---|
| O | B1 | 3, 6, 226, 456, 475, 479 |
| | B2 | 53, 146, 147, 181, 267, 283, 301, 302, 303, 304, 465, 467 |
| | B5 | 291, 292 |
| | B6 | 3, 163, 334, 335, 456 |
| `skills/harness-state/SKILL.md` | B1 | 3, 27, 82, 90 |
| | B2 | 120, 172, 226, 235, 253, 335, 364, 371 |
| | B3 | 29, 55, 56, 57, 62 |
| | B4 | 252 (유지) |
| | B5 | 167, 173, 378 |
| | B6 | 284, 415 |
| `skills/verification-protocol/SKILL.md` | B1 | 3, 91, 93, 96, 98, 99, 105, 107, 110, 112, 116, 123 |
| | B2 | 94, 98, 99, 192 |
| | B6 | 102 |
| `skills/poc-scope-guard/SKILL.md` (코어로 갈 부분) | B1 | 3, 22, 23, 39, 47 |
| | B2 | 8, 23, 37, 38, 39, 48, 51 |
| | B6 | 3, 6, 8, 9, 15, 16, 18, 19, 38, 41, 45, 47, 51, 60 |
| | (판정 예시 표 73–81은 도메인 — 옮기지 않음) | |
| `skills/issue-workflow/SKILL.md` (1–8절) | B1 | 3 |
| | B2 | 82, 93, 107, 109 |
| | B5 | 92, 114 |
| | (의존 순서 242–259·시나리오 261–269는 도메인) | |
| `agents/issue-planner.md` | B1 | 9, 86, 87, 121 |
| | B2 | 23, 27 |
| | B3 | 137 |
| | B6 | 9, 17, 30, 79 |
| `agents/schema-guardian.md` | B1 | 3, 9, 15, 16 |
| | B2 | 14, 15, 16, 36, 40 |
| | B3 | 101 |
| | B6 | 32, 35 |
| `agents/pipeline-engineer.md` | B1 | 3, 9, 32, 33, 39, 85, 98 |
| | B2 | 32, 41 |
| | B6 | 9, 28, 30, 40, 84, 99 |
| `agents/integration-qa.md` | B1 | 3, 9, 17, 19, 34, 42 |
| | B2 | 17, 19, 78 |
| | B3 | 147 |
| | B6 | 24, 49, 93, 94, 105, 154 |
| `hooks/record-agent-event.py` | B3 | 39 |
| | B4 | 38 (유지) |
| | B5 | 12 (Stop 분기와 함께 삭제) |
| `hooks/check-state.py` | B2 | 4, 75, 99, 136 |
| | B6 | 98 |
| `.githooks/pre-commit` | B1 | 15 (원본 테스트 파일명) |

단계 2 끝에 `plugins/harness/` 전체를 원본 고유명·마켓플레이스 소유자명·절대경로 접두사·이슈 번호
표기로 grep하고, 0건이 아닌 행은 남는 이유를 적는다. 단어 목록은 이 문서에 적지 않는다 — 적으면 이 문서가 걸린다.

## 8. 플러그인 구성 (단계 2 목표)

```
plugins/harness/
├── .claude-plugin/plugin.json      # name: harness, version: 0.1.0
├── README.md                       # 설치·활성화·harness.config.json 형식·check-state 수동 실행
├── docs/design.md                  # 이 문서
├── hooks/hooks.json                # SubagentStop
├── scripts/
│   ├── record-agent-event.py
│   ├── check-state.py
│   └── init.py
├── skills/
│   ├── issue-harness/SKILL.md      # 오케스트레이터 (O의 코어)
│   ├── harness-state/SKILL.md
│   ├── verification-protocol/SKILL.md
│   ├── tdd-cycle/SKILL.md
│   ├── scope-guard/SKILL.md
│   ├── issue-workflow/SKILL.md
│   └── init/SKILL.md               # /harness:init (disable-model-invocation)
├── agents/
│   ├── issue-planner.md
│   ├── contract-guardian.md
│   ├── implementer.md
│   └── integration-qa.md
└── templates/
    ├── harness.config.json
    ├── agent-permissions.md
    ├── claude-md-snippet.md
    └── githooks/{commit-msg,pre-commit,_harness.py}
```

스킬 이름이 원본 프로젝트의 남는 도메인 스킬과 겹치지 않는지: 원본에 남는 것은 C·D·축소된
scope/workflow 보충 스킬이다. 원본의 `issue-workflow`·`poc-scope-guard`를 같은 이름으로 남기면
`issue-workflow`(프로젝트)와 `harness:issue-workflow`(플러그인)가 공존한다 — 이름은 접두사로
구별되지만 모델이 둘 다 트리거할 수 있다. 원본에 남길 도메인 보충은 다른 이름으로 바꾸는 안을
제안한다 → Q1.

## 9. 질문

- **Q1 — 원본에 남길 도메인 보충 스킬의 이름.** `poc-scope-guard`·`issue-workflow`를 도메인 부분만
  남겨 같은 이름으로 두면 플러그인의 `harness:scope-guard`·`harness:issue-workflow`와 트리거가 겹친다.
  예: `<domain>-scope-notes`, `<domain>-issue-order`로 바꾸고 `domain_skills`에서 가리키는 안. 이름을 정해 달라.
- **Q2 — `demo_blocker` 값.** 범용 플러그인에는 `blocker`/`critical`이 맞는 이름이지만, 바꾸면 원본의
  옛 `state.json`이 `check-state`에서 거부된다. 유지(설명만 범용화) / 새 이름 + 옛 값 허용 중 어느 쪽인가.
  설계는 **유지**로 진행한다.
- **Q3 — `SubagentHandback`.** auto 모드에서는 `last_assistant_message`가 보고가 아니다. 대응안:
  (a) 지금은 auto 모드를 쓰지 않으므로 README에 한계로 적고 넘어간다 / (b) `PostToolUse`(matcher
  `SubagentHandback`)로 `tool_input.message`를 기록하고, `SubagentStop`은 그 경우 건너뛴다.
  (b)는 두 이벤트가 같은 에이전트를 가리키는지 `agent_id`로 맞춰야 하고 실측이 필요하다. 설계는 **(a)**로 진행한다.
- **Q4 — 원본의 진행 중 이슈.** 전환 시점에 `ACTIVE`가 가리키는 이슈가 끝나지 않았다면 그 이슈의
  `agents` 키에 옛 이름과 새 이름이 섞인다. 그대로 둬도 되는가.
- **Q5 — `docs/harness-architecture.html`.** 원본에서 지우고 플러그인 README로 대체 / 원본에 두되
  6절(경계면)만 남겨 축소 / 그대로 둠. 설계는 **지우고 대체**를 제안한다(이중 정본 방지).
- **Q6 — `defaultEnabled`.** 매니페스트에 `defaultEnabled: false`를 두면 사용자 범위로 설치해도
  프로젝트가 `enabledPlugins`로 켠 곳에서만 훅이 돈다. 단 `/plugin install`이 사용자 범위에
  `enabledPlugins: true`를 쓰면 무력하다(동작 실측 필요). 넣을 것인가.
