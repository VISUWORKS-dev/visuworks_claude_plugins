#!/usr/bin/env python3
"""서브에이전트 종료(`SubagentStop`)를 `events.jsonl`에 한 줄 append한다.

플러그인 훅이라 **플러그인이 켜진 모든 세션**에서 발화한다. 하네스를 쓰지 않는 곳
(git 레포가 아님, `.harness/ACTIVE` 없음)에서는 로그도 없이 즉시 끝낸다 — 그런 세션마다
`FAILED`가 쌓이면 진짜 실패가 묻힌다.

`agent_type`에는 타입 대신 Agent 툴의 `name`이 온다. 따라서 타입 화이트리스트로는
거를 수 없다 — 화이트리스트로 거르면 이름으로 호출된 에이전트 기록이 0건이 된다.
내장 에이전트만 제외한다(블랙리스트).

append 전용이라 락도 임시파일 교체도 필요 없다. 파싱도 하지 않는다 —
보고 원문(msg)을 그대로 저장하고 해석은 읽는 쪽이 한다.

대상 이슈는 `.harness/ACTIVE` 한 줄로 정한다. "가장 최근 수정된 state.json"
추측은 하지 않는다 — 틀리면 조용히 엉뚱한 곳에 쌓인다.
"""

import datetime
import json
import os
import pathlib
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


try:
    p = json.load(sys.stdin)
    cwd = p.get("cwd")
    h = harness_dir(cwd)
    # git 레포가 아니거나 활성 이슈가 없으면 하네스 밖이다. 로그도 없이 끝낸다.
    if h is None or not (h / "ACTIVE").exists():
        sys.exit(0)

    agent = p.get("agent_type") or ""
    if not p.get("agent_id") or agent in BUILTIN:
        log(f"subagent-stop skipped: agent_type={agent!r} agent_id={p.get('agent_id')!r}")
        sys.exit(0)

    issue = (h / "ACTIVE").read_text(encoding="utf-8").strip()
    # source는 필수다 — git hook도 같은 파일에 append한다. 없으면 누가 쓴 줄인지 모른다.
    ev = {"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
          "source": "subagent", "agent": agent, "agent_id": p["agent_id"],
          "cwd": cwd, "msg": (p.get("last_assistant_message") or "").strip()}
    with open(h / issue / "events.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    log(f"subagent recorded: {agent} -> {issue}")
except Exception as e:
    log(f"hook FAILED {type(e).__name__}: {e}")
