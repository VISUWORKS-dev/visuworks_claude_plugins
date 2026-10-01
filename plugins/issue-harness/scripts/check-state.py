#!/usr/bin/env python3
"""`.harness/issue-*/state.json`의 스키마와 정본 분기를 검사한다 (v2).

왜 있는가: 검증자가 `blockers`를 다른 키(`detail`/`title`/`status`)로 써서
오케스트레이터가 미해결 블로커를 세다가 `KeyError`로 멈춘 적이 있다. 스키마가 문서에만
있고 아무도 검사하지 않으면 생기는 일이다. 스키마는 문서가 아니라 검사가 지킨다.

사용: python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-state.py" [경로...]
      인자가 없으면 primary의 .harness/issue-*/state.json 전부.
종료 코드: 0 통과 / 1 위반
"""
import glob
import json
import subprocess
import sys
from pathlib import Path

# issue-harness:harness-state 스킬 「Phase 식별자」 표와 1:1이다. 표를 바꾸면 여기도 바꾼다.
SUB_STAGES = {
    "0-context": {"0a-git-check", "0b-state-read"},
    "1-prepare": {"1a-issue-read", "1b-dependency-check", "1c-branch"},
    "2-plan": {"2a-plan-draft", "2b-human-questions", "2c-handoff-commit"},
    "3-implement": {"3a-contract", "3a-test", "3b-implement", "3c-incremental-qa"},
    "4-verify": {"4a-verify-blind", "4b-verify-spec", "4c-make-check",
                 "4d-placeholder-scan", "4e-merge"},
    "5-report": {"5a-report", "5b-human-handoff"},
}
PHASES = set(SUB_STAGES)
STATUS = {"pending", "in_progress", "blocked", "done", "failed"}
SEVERITY = {"demo_blocker", "defect", "improvement"}
CONTRACT = {"undecided", "provisional", "confirmed"}

BLOCKER_REQUIRED = {"id", "severity", "description", "owner", "resolved"}
QUESTION_REQUIRED = {"id", "question", "answer"}
MODE = {"full"}
V2_REQUIRED = {"mode", "spec", "test_list", "complexity"}
TEST_RESULT = {"pass", "fail", "blocked"}


def primary_root() -> Path:
    """워크트리에서 돌아도 primary를 찾는다 — 정본은 하나다."""
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return Path(common).parent
    except Exception:
        return Path.cwd()


def check(path: Path) -> list[str]:
    bad = []
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"{path}: 읽을 수 없다 — {e}"]

    def err(msg):
        bad.append(f"{path.parent.name}: {msg}")

    if d.get("phase") not in PHASES:
        err(f"phase={d.get('phase')!r} 유효하지 않다 (허용: {sorted(PHASES)})")
    if d.get("status") not in STATUS:
        err(f"status={d.get('status')!r} 유효하지 않다 (허용: {sorted(STATUS)})")

    # sub_stage는 그 phase의 허용 목록 안에 있어야 한다 — 앞 글자만 보면 "3z-oops"도 통과한다
    sub, phase = d.get("sub_stage"), d.get("phase")
    if sub and phase in SUB_STAGES and sub not in SUB_STAGES[phase]:
        err(f"sub_stage={sub!r}가 phase={phase!r}에 없다 (허용: {sorted(SUB_STAGES[phase])})")

    for i, b in enumerate(d.get("blockers") or []):
        missing = BLOCKER_REQUIRED - set(b)
        if missing:
            # 어떤 키를 대신 썼는지도 보여준다 — 고치는 사람이 바로 안다.
            err(f"blockers[{i}] 필수 키 없음 {sorted(missing)} — 실제 키 {sorted(b)}")
        if "severity" in b and b["severity"] not in SEVERITY:
            err(f"blockers[{i}].severity={b['severity']!r} 유효하지 않다")
        if "resolved" in b and not isinstance(b["resolved"], bool):
            err(f"blockers[{i}].resolved는 bool이어야 한다 — {b['resolved']!r}")

    for i, q in enumerate(d.get("open_questions") or []):
        missing = QUESTION_REQUIRED - set(q)
        if missing:
            err(f"open_questions[{i}] 필수 키 없음 {sorted(missing)} — 실제 키 {sorted(q)}")

    # v2: 경과는 events.jsonl이다. history가 되살아나면 정본이 둘이 된다.
    if "history" in d:
        err("history 키가 남아 있다 — 경과는 events.jsonl이다")

    missing_v2 = V2_REQUIRED - set(d)
    if missing_v2:
        err(f"필수 키 없음 {sorted(missing_v2)} — harness-state 스킬의 초기화 블록을 따른다")

    if "mode" in d and d["mode"] not in MODE:
        err(f"mode={d['mode']!r} 유효하지 않다 (허용: {sorted(MODE)})")

    # spec이 없는 파일을 가리키면 읽는 쪽에서 터진다. 조용히 두면 마감 직전에 안다.
    # null은 허용한다 — spec 없이 도는 이슈가 있다(하네스 개선 자체 같은 것).
    spec = d.get("spec")
    if spec is not None:
        if not isinstance(spec, str):
            err(f"spec은 문자열 또는 null이어야 한다 — {spec!r}")
        elif not (path.parent.parent.parent / spec).exists():
            err(f"spec={spec!r}가 없는 파일을 가리킨다")

    # test_list는 {ID: {attempts, last_result}}. 같은 항목 3회 실패는 오케스트레이터가 blocker로 올린다.
    tl = d.get("test_list")
    if tl is not None and not isinstance(tl, dict):
        err(f"test_list는 객체여야 한다 — {type(tl).__name__}")
    elif tl:
        for tid, item in tl.items():
            if not isinstance(item, dict):
                err(f"test_list.{tid}는 객체여야 한다 — {type(item).__name__}")
                continue
            if not isinstance(item.get("attempts", 0), int):
                err(f"test_list.{tid}.attempts는 정수여야 한다 — {item.get('attempts')!r}")
            lr = item.get("last_result")
            if lr is not None and lr not in TEST_RESULT:
                err(f"test_list.{tid}.last_result={lr!r} 유효하지 않다 (허용: {sorted(TEST_RESULT)})")

    for name, a in (d.get("agents") or {}).items():
        if "commits" in a or "outputs" in a:
            err(f"agents.{name}에 v1 키가 남아 있다 {sorted({'commits','outputs'} & set(a))}")
        if not isinstance(a, dict) or a.get("status") not in STATUS:
            err(f"agents.{name}.status={a.get('status') if isinstance(a, dict) else a!r} 유효하지 않다")

    for name, v in (d.get("contracts") or {}).items():
        if v not in CONTRACT:
            err(f"contracts.{name}={v!r} 유효하지 않다 (허용: {sorted(CONTRACT)})")

    return bad


def check_fork(root: Path) -> list[str]:
    """워크트리에 정본과 다른 state.json이 있으면 분기다 — 각자 기록하면 정본이 갈라진다."""
    bad = []
    try:
        out = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, check=True, cwd=root,
        ).stdout
    except Exception:
        return bad

    for line in out.splitlines():
        if not line.startswith("worktree "):
            continue
        wt = Path(line[len("worktree "):])
        if wt == root:
            continue
        for wt_state in wt.glob(".harness/issue-*/state.json"):
            mine = root / wt_state.relative_to(wt)
            if not mine.exists():
                bad.append(f"정본 분기: 워크트리에만 있다 — {wt_state}")
            elif wt_state.read_bytes() != mine.read_bytes():
                bad.append(
                    f"정본 분기: 워크트리와 primary가 다르다 — {wt_state}\n"
                    f"  정본은 primary다. 워크트리 쪽은 읽기용 사본이다 (issue-harness:issue-workflow 8절)"
                )
    return bad


def main(argv: list[str]) -> int:
    root = primary_root()
    paths = [Path(a) for a in argv] or [
        Path(p) for p in sorted(glob.glob(str(root / ".harness/issue-*/state.json")))
    ]
    if not paths:
        print("state.json 없음 — 검사할 것이 없다")
        return 0

    bad = [e for p in paths for e in check(p)] + check_fork(root)
    if bad:
        print(f"state.json 검사 실패 ({len(bad)}건):", file=sys.stderr)
        for b in bad:
            print(f"  - {b}", file=sys.stderr)
        return 1
    print(f"state.json 검사 통과 ({len(paths)}개)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
