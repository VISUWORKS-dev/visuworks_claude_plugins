#!/usr/bin/env python3
"""`.harness/issue-*/state.json`의 스키마와 정본 분기를 검사한다 (v3).

왜 있는가: 검증자가 `blockers`를 다른 키(`detail`/`title`/`status`)로 써서
오케스트레이터가 미해결 블로커를 세다가 `KeyError`로 멈춘 적이 있다. 스키마는 문서가 아니라 검사가 지킨다.

v3: 진행 지점(phase·agents·test_list 등)은 git 로그가 정본이다. state.json에 다시 적으면 커밋과 갈라지므로
허용 키 밖은 거부한다.

사용: python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-state.py" [경로...]
      인자가 없으면 primary의 `.harness/ACTIVE` 이슈 하나. ACTIVE가 없으면 검사할 것이 없다.
      끝난 이슈의 옛(v2) state.json은 검사하지 않는다 — 활성 이슈마다 실패하면 안 된다.
종료 코드: 0 통과 / 1 위반
"""
import json
import subprocess
import sys
from pathlib import Path

# issue-harness:harness-state 스킬 「스키마」와 1:1이다. 하나를 바꾸면 둘 다 바꾼다.
ALLOWED = {"issue", "updated_at", "open_questions", "blockers", "handoff_to_human"}
REQUIRED = {"issue", "open_questions", "blockers", "handoff_to_human"}
SEVERITY = {"demo_blocker", "defect", "improvement"}
BLOCKER_REQUIRED = {"id", "severity", "description", "owner", "resolved"}
QUESTION_REQUIRED = {"id", "question", "answer"}


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


def check(path: Path) -> list:
    bad = []
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"{path}: 읽을 수 없다 — {e}"]
    if not isinstance(d, dict):
        return [f"{path.parent.name}: 최상위가 객체가 아니다"]

    def err(msg):
        bad.append(f"{path.parent.name}: {msg}")

    extra = set(d) - ALLOWED
    if extra:
        err(f"허용하지 않는 키 {sorted(extra)} — 진행 지점은 git 로그가 정본이다 (harness-state 「진행 지점 복원」)")
    missing = REQUIRED - set(d)
    if missing:
        err(f"필수 키 없음 {sorted(missing)} — harness-state 스킬의 초기화 블록을 따른다")

    for key, req in (("blockers", BLOCKER_REQUIRED), ("open_questions", QUESTION_REQUIRED)):
        items = d.get(key)
        if items is None:
            continue
        if not isinstance(items, list):
            err(f"{key}는 배열이어야 한다 — {type(items).__name__}")
            continue
        for i, x in enumerate(items):
            if not isinstance(x, dict):
                err(f"{key}[{i}]는 객체여야 한다 — {type(x).__name__}")
                continue
            miss = req - set(x)
            if miss:
                # 어떤 키를 대신 썼는지도 보여준다 — 고치는 사람이 바로 안다.
                err(f"{key}[{i}] 필수 키 없음 {sorted(miss)} — 실제 키 {sorted(x)}")
            if key == "blockers":
                if "severity" in x and x["severity"] not in SEVERITY:
                    err(f"blockers[{i}].severity={x['severity']!r} 유효하지 않다 (허용: {sorted(SEVERITY)})")
                if "resolved" in x and not isinstance(x["resolved"], bool):
                    err(f"blockers[{i}].resolved는 bool이어야 한다 — {x['resolved']!r}")

    h = d.get("handoff_to_human")
    if h is not None and not (isinstance(h, list) and all(isinstance(c, str) for c in h)):
        err("handoff_to_human은 문자열 배열이어야 한다")

    return bad


def check_fork(root: Path) -> list:
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


def main(argv: list) -> int:
    root = primary_root()
    active = root / ".harness/ACTIVE"
    paths = [Path(a) for a in argv]
    if not paths and active.exists():
        paths = [root / ".harness" / active.read_text(encoding="utf-8").strip() / "state.json"]
        paths = [p for p in paths if p.exists()]
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
