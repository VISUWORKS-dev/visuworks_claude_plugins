## 하네스

**트리거:** 이슈 착수·구현·검증 요청 시 `harness:issue-harness` 스킬을 사용하라.
단순 질문은 직접 응답 가능.

**작업 단위:** GitHub 이슈 = 워크트리 = PR (`harness:issue-workflow`).
push · PR 생성 · 기본 브랜치 머지 · 의존성 추가는 사람이 한다. 로컬 머지(워크트리 → 이슈 브랜치)는
오케스트레이터가 한다.

**프로젝트 값:** `.claude/harness.config.json` — 검증 명령, 소스·테스트 경로, 계약 스킬, 도메인 에이전트.

**정본 분리:** spec은 `<spec_dir>/issue-<N>.md`(tracked), 런타임 상태는 `.harness/`(gitignore).
`state.json`은 오케스트레이터만 쓰고 `events.jsonl`은 훅만 append한다. 활성 이슈는 `.harness/ACTIVE`
(`harness:harness-state`).

**구현은 테스트 목록 기반 TDD** (`harness:tdd-cycle`). 진행 정본은 `git log --grep "^\[behavioral\] T"`.

**검증은 2단계** — 무컨텍스트 → 컨텍스트 (`harness:verification-protocol`).

**권한:** `.claude/rules/agent-permissions.md`.

**커밋 메시지는 `commit-msg` 훅이 강제한다:** `[behavioral] T<n>: <설명>` / `[structural] <설명>` /
`[handoff] <설명>` / `[chore] <설명>`. 테스트 약화는 `pre-commit`이 막는다.
