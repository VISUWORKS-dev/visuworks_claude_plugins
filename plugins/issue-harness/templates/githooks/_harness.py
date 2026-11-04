"""git hook 공용 — 설정 읽기와 차단 사유 기록.

현재 브랜치의 이슈에 state.json이 없으면 기록만 생략하고 검사는 그대로 한다. 기록 실패가 검사를 막으면
훅이 조용히 무력화된다. 설정이 없어도 기본값으로 검사한다 — 설정 누락이 검사를 끄면 안 된다.
"""
import datetime
import json
import pathlib
import re
import subprocess


def tests_dir() -> str:
    """`.claude/harness.config.json`의 `tests_dir`. 없으면 `tests/`."""
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True).stdout.strip()
        cfg = json.loads((pathlib.Path(top) / ".claude/harness.config.json").read_text(encoding="utf-8"))
        d = cfg.get("tests_dir") or "tests/"
        return d if d.endswith("/") else d + "/"
    except Exception:
        return "tests/"


def active_issue():
    """현재 브랜치의 이슈 디렉터리 이름(`issue-<N>`). 얻을 수 없으면 None.

    issue-harness 플러그인 scripts/check-state.py `active_issue`와 같다. 하나를 바꾸면 모두 바꾼다."""
    def git(*a):
        return subprocess.run(["git", *a], capture_output=True, text=True).stdout.strip()
    b = git("branch", "--show-current")
    m = re.match(r"([1-9][0-9]*)-", b)
    if not m and b.startswith("worktree-agent-"):
        m = re.search(r"#([1-9][0-9]*) spec", git("log", "-1", "--first-parent", "--format=%s", "-E", "--grep=^docs : 이슈 #[0-9]+ spec"))
    return f"issue-{m.group(1)}" if m else None


def record(hook: str, reason: str) -> None:
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True,
        ).stdout.strip()
        if not common:
            return
        issue = active_issue()
        d = pathlib.Path(common).parent / ".harness" / str(issue)
        if issue is None or not (d / "state.json").exists():
            return
        ev = {"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
              "source": "githook", "hook": hook, "event": "commit_blocked", "reason": reason}
        with open(d / "events.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 기록 실패가 검사를 막으면 안 된다
