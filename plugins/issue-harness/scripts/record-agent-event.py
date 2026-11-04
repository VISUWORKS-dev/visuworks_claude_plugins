#!/usr/bin/env python3
"""에이전트의 보고를 `events.jsonl`에 한 줄 append한다. 두 이벤트를 받는다.

| 이벤트 | 무엇 | `source` |
|---|---|---|
| `SubagentStop` | 서브에이전트·팀원이 멈췄다. `msg`는 마지막 텍스트 | `subagent` |
| `PostToolUse`(`SendMessage`) | **에이전트가** 보낸 메시지. 팀원은 보고를 이것으로 보낸다 | `message` |

팀원의 마지막 텍스트는 보고가 아니라 "보냈다"는 맺음말이다 — 보고 본문은 `SendMessage`에 있다.
오케스트레이터(메인 스레드)가 보내는 메시지는 지시라서 기록하지 않는다(`agent_id`가 없다).

플러그인 훅이라 **플러그인이 켜진 모든 세션**에서 발화한다. 하네스를 쓰지 않는 곳
(git 레포가 아님, 현재 브랜치의 이슈에 `state.json` 없음)에서는 로그도 없이 즉시 끝낸다 — 그런 세션마다
`FAILED`가 쌓이면 진짜 실패가 묻힌다.

`agent_type`에는 타입 대신 Agent 툴의 `name`이 온다. 따라서 타입 화이트리스트로는
거를 수 없다 — 화이트리스트로 거르면 이름으로 호출된 에이전트 기록이 0건이 된다.
내장 에이전트만 제외한다(블랙리스트).

append 전용이라 락도 임시파일 교체도 필요 없다. 파싱도 하지 않는다 —
보고 원문(msg)을 그대로 저장하고 해석은 읽는 쪽이 한다.

대상 이슈는 `cwd`의 현재 브랜치로 정한다(`active_issue`). "가장 최근 수정된 state.json"
추측은 하지 않는다 — 틀리면 조용히 엉뚱한 곳에 쌓인다.
"""

import datetime
import json
import os
import pathlib
import re
import subprocess
import sys

print("{}")  # 가장 먼저 — 어떤 경우에도 세션을 막지 않는다

LOG = os.environ.get("HARNESS_HOOK_LOG", os.path.expanduser("~/.claude/harness-hook.log"))
BUILTIN = {"", "general-purpose", "Explore", "Plan", "claude",
           "statusline-setup", "output-style-setup"}


def log(m):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%H:%M:%S} {m}\n")
    except Exception:
        pass  # 로그 실패가 훅을 죽이면 안 된다


def harness_dir(cwd):
    """primary 체크아웃의 `.harness/`. git 레포가 아니면 None — 하네스 밖이다.

    워크트리에서 돌아도 `--git-common-dir`로 primary를 찾는다 — 정본이 갈라지면 안 된다.
    """
    if not cwd:
        return None
    try:
        common = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True,
        ).stdout.strip()
    except Exception:
        return None
    return pathlib.Path(common).parent / ".harness" if common else None


def active_issue(cwd):
    """현재 브랜치의 이슈 디렉터리 이름(`issue-<N>`). 얻을 수 없으면 None.

    check-state.py `active_issue`와 같다. 하나를 바꾸면 모두 바꾼다."""
    def git(*a):
        return subprocess.run(["git", *a], capture_output=True, text=True, cwd=cwd).stdout.strip()
    b = git("branch", "--show-current")
    m = re.match(r"([1-9][0-9]*)-", b)
    if not m and b.startswith("worktree-agent-"):
        m = re.search(r"#([1-9][0-9]*) spec", git("log", "-1", "--first-parent", "--format=%s", "-E", "--grep=^docs : 이슈 #[0-9]+ spec"))
    return f"issue-{m.group(1)}" if m else None


try:
    p = json.load(sys.stdin)
    cwd = p.get("cwd")
    h = harness_dir(cwd)
    # `.harness/`가 없으면 git을 더 돌리지 않는다 — 하네스를 안 쓰는 레포에서도 매번 발화한다
    issue = active_issue(cwd) if h and h.is_dir() else None
    # git 레포가 아니거나 이 브랜치의 이슈가 하네스로 초기화되지 않았으면 하네스 밖이다. 로그도 없이 끝낸다.
    if issue is None or not (h / issue / "state.json").exists():
        sys.exit(0)

    event = p.get("hook_event_name") or "SubagentStop"
    agent = p.get("agent_type") or ""
    if not p.get("agent_id") or agent in BUILTIN:
        log(f"{event} skipped: agent_type={agent!r} agent_id={p.get('agent_id')!r}")
        sys.exit(0)

    # source는 필수다 — git hook도 같은 파일에 append한다. 없으면 누가 쓴 줄인지 모른다.
    ev = {"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
          "source": "subagent", "agent": agent, "agent_id": p["agent_id"], "cwd": cwd}
    if event == "PostToolUse":
        ti = p.get("tool_input") or {}
        msg = ti.get("message")
        ev.update(source="message", to=ti.get("to"),
                  msg=msg.strip() if isinstance(msg, str) else json.dumps(msg, ensure_ascii=False))
    else:
        ev["msg"] = (p.get("last_assistant_message") or "").strip()
    with open(h / issue / "events.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    log(f"{ev['source']} recorded: {agent} -> {issue}")
except Exception as e:
    log(f"hook FAILED {type(e).__name__}: {e}")
