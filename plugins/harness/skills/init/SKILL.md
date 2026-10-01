---
name: init
description: "현재 git 레포에 harness 하네스 설정을 깐다 — .claude/harness.config.json, .claude/rules/agent-permissions.md, .githooks/(커밋 규약), core.hooksPath. settings.json·.gitignore·CLAUDE.md는 병합이 필요한 것만 안내한다. 이미 있는 파일은 덮어쓰지 않는다."
disable-model-invocation: true
---

# /harness:init

아래 명령을 레포 루트에서 그대로 실행한다. **파일을 직접 쓰거나 고치지 않는다** — 복사와 비교는
스크립트가 한다. 모델이 다시 쓰면 "두 번째 실행은 변경 없음"을 보장할 수 없다.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init.py" $ARGUMENTS
```

`--dry-run`을 인자로 주면 아무것도 쓰지 않고 할 일만 보여준다.

## 출력을 사람에게 전한다

- **만듦** — 새로 깐 파일과 설정.
- **다름(건드리지 않음)** — 이미 있고 템플릿과 다른 파일. diff가 함께 출력된다. 덮어쓰지 않았다.
  어느 쪽을 쓸지는 사람이 정한다. 종료 코드 1이 이 경우다.
- **직접 할 것** — `settings.json`에 넣을 키, `.gitignore`에 넣을 줄, `core.hooksPath` 충돌,
  `CLAUDE.md`에 붙일 조각 경로. 사람이 요청하지 않으면 이 파일들을 고치지 않는다.

출력 원문을 줄이지 말고 보여준 뒤, 다음 단계를 한 줄로 안내한다:
`.claude/harness.config.json`의 값(`check_cmd`, `src_dirs`, `tests_dir`, `contract_skill`,
`domain_agents`)을 이 프로젝트에 맞게 고친다.

## 깔리는 것

| 파일 | 역할 |
|---|---|
| `.claude/harness.config.json` | 프로젝트 값 — 오케스트레이터·에이전트·git hook이 읽는다 |
| `.claude/rules/agent-permissions.md` | 에이전트 권한 규칙. 플러그인은 rules를 로드하지 않으므로 프로젝트에 둔다 |
| `.githooks/commit-msg`·`pre-commit`·`_harness.py` | 커밋 메시지 형식·테스트 약화 차단 |
| `git config core.hooksPath .githooks` | 비어 있을 때만 |
| `.claude/settings.json` | 없을 때만 생성: `permissions.deny`(`--no-verify` 차단), `worktree.baseRef: "head"` |
| `.gitignore` | 없을 때만 생성: `.harness/`, `.claude/worktrees/`, `_workspace/` 등 |

`.harness/`와 spec 디렉터리는 만들지 않는다 — 이슈 착수 시 오케스트레이터가 만든다.
