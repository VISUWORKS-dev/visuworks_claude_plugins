#!/usr/bin/env python3
"""PreToolUse(Bash) — 에이전트가 git 훅(commit-msg)을 끄는 명령을 막는다.

`permissions.deny`는 명령 앞부분 일치라 `git commit -m x --no-verify`, `-nm`이 통과한다(#19).
이 훅은 명령을 셸 토큰으로 쪼개 플래그 위치와 무관하게 본다. 막는 것:

| 경로 | 예 |
|---|---|
| 모든 git 하위 명령의 `--no-verify`(축약 `--no-veri` 포함) | `git commit -m x --no-verify`, `git merge --no-verify` |
| commit의 `-n`(묶음 포함) | `git commit -nm x`, `git commit -anm x` |
| 훅 경로 바꾸기 | `git -c core.hooksPath=...`, `--config-env`, `git config core.hooksPath x`, `--unset` |
| 환경변수로 설정 주입 | `GIT_CONFIG_PARAMETERS=`, `GIT_CONFIG_COUNT=`/`KEY_n`/`VALUE_n` |
| 감싸기 | `sh -c "..."`, `bash -lc`, `eval "..."`, `( ... )`, `$( ... )` |

플러그인 훅이라 플러그인을 켠 모든 레포에서 발화한다. `.claude/harness.config.json`이 없으면 즉시 끝낸다.
python 3.9에서 돈다(#9).
"""
import json
import os
import re
import shlex
import sys

PUNCT = ";&|(){}`\n"
SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
WRAP = {"command", "exec", "nice", "nohup", "time", "sudo", "xargs", "timeout", "stdbuf", "env", "ionice"}
KEYWORDS = {"if", "then", "else", "elif", "do", "while", "until", "!"}
HEREDOC_RE = re.compile(r"<<-?\s*(['\"])(\w+)\1")
ENV_RE = re.compile(r"GIT_CONFIG_(PARAMETERS|COUNT|KEY_\w*|VALUE_\w*)=")
HOOKS_KEY = "core.hookspath"
# commit에서 값을 받는 짧은 옵션 — 묶음에서 이 뒤 글자는 값이다(-mn은 메시지 "n")
COMMIT_ARG = set("mFCct")
CONFIG_WRITE = {"--add", "--replace-all", "set", "unset"}
CONFIG_READ = {"--get", "--get-all", "--get-regexp", "-l", "--list", "get", "list"}


def no_verify(tok):
    # git은 유일한 접두어 축약을 받는다. --no-ver는 --no-verbose와 겹쳐 git이 거부한다
    return len(tok) > len("--no-ver") and "--no-verify".startswith(tok)


def commit_n(tok):
    if not tok.startswith("-") or tok.startswith("--"):
        return False
    for ch in tok[1:]:
        if ch == "n":
            return True
        if ch in COMMIT_ARG:
            return False
    return False


def alias_bypass(s):
    """`alias.ci="commit --no-verify"` 같은 별칭 정의."""
    s = s.lower()
    return "alias." in s and ("--no-veri" in s or re.search(r"\bcommit\b.*\s-[a-z]*n", s) is not None)


def check_git(args):
    """`git` 뒤 토큰. 막을 이유를 돌려준다."""
    i = 0
    while i < len(args) and args[i].startswith("-"):
        a = args[i]
        if a == "-c" and i + 1 < len(args):
            if args[i + 1].lower().startswith(HOOKS_KEY):
                return "git -c core.hooksPath"
            if alias_bypass(args[i + 1]):
                return "git -c alias로 훅 우회"
            i += 1
        elif a.startswith("--config-env") and HOOKS_KEY in a.lower():
            return "git --config-env core.hooksPath"
        elif a == "--config-env" and i + 1 < len(args) and HOOKS_KEY in args[i + 1].lower():
            return "git --config-env core.hooksPath"
        elif a in ("-C", "--git-dir", "--work-tree", "--namespace") and i + 1 < len(args):
            i += 1
        i += 1
    if i >= len(args):
        return None
    sub, rest = args[i], args[i + 1:]
    if "--" in rest and sub != "config":  # config는 `--` 뒤에도 키를 받는다
        rest = rest[:rest.index("--")]
    if any(no_verify(t) for t in rest):
        return f"git {sub} --no-verify"
    if sub == "commit":
        skip = False
        for t in rest:
            if skip:
                skip = False
                continue
            if commit_n(t):
                return "git commit -n"
            skip = t in ("-m", "-F", "-C", "-c", "-t")  # 다음 토큰은 값
    if sub == "config" and alias_bypass(" ".join(rest)):
        return "git config alias로 훅 우회"
    if sub == "config" and "core" in (t.lower() for t in rest) and any(t.lstrip("-") in ("remove-section", "rename-section") for t in rest):
        return "git config core 섹션 삭제"
    if sub == "config" and any(t.lower() == HOOKS_KEY for t in rest):
        write = any(t.startswith("--unset") or t in CONFIG_WRITE for t in rest)
        if write or (not any(t in CONFIG_READ for t in rest) and len([t for t in rest if not t.startswith("-")]) != 1):
            return "git config core.hooksPath 변경"
    return None


def check_segment(words):
    for w in words:
        # 큰따옴표 안의 "$(...)"·`...`는 한 토큰으로 남는다 — 다시 쪼개 본다
        if "$(" in w or "`" in w:
            r = check(w)
            if r:
                return r
    while words:
        w = words[0]
        if ENV_RE.match(w):
            return "GIT_CONFIG_* 환경변수"
        if "=" in w and not w.startswith("-") and re.match(r"[A-Za-z_]\w*=", w):
            words = words[1:]  # 앞에 붙은 VAR=값
            continue
        base = os.path.basename(w)
        if base in KEYWORDS:
            words = words[1:]
            continue
        if base in ("env", "export", "declare", "typeset", "local") and any(ENV_RE.match(t) for t in words[1:]):
            return "GIT_CONFIG_* 환경변수"
        if base in WRAP:
            # 래퍼 옵션·값(timeout 120, nice -n 5)을 건너뛰고 실제 명령으로 간다
            nxt = [j for j, t in enumerate(words) if j and os.path.basename(t) in SHELLS | {"git", "eval"}]
            words = words[nxt[0]:] if nxt else []
            continue
        if base == "eval":
            return check(" ".join(words[1:]))
        if base in SHELLS:
            for j, t in enumerate(words[1:], 1):
                if t.startswith("-") and not t.startswith("--") and "c" in t and j + 1 < len(words):
                    return check(words[j + 1])
            return None
        if base == "git":
            return check_git(words[1:])
        return None
    return None


def strip_heredocs(cmd):
    """따옴표 구분자 heredoc(<<'EOF') 본문은 글자 그대로라 명령이 아니다 — 커밋 메시지 본문을 명령으로 읽지 않게 지운다.
    셸에 먹이는 heredoc(bash <<'EOF')은 본문이 명령이라 남긴다."""
    out, end = [], None
    for line in cmd.split("\n"):
        if end is not None:
            if line.strip() == end:
                end = None
                out.append(line)
            continue
        out.append(line)
        m = HEREDOC_RE.search(line)
        first = line.split()[0] if line.split() else ""
        if m and os.path.basename(first) not in SHELLS:
            end = m.group(2)
    return "\n".join(out)


def check(cmd):
    cmd = strip_heredocs(cmd.replace("\\\n", " "))  # 줄 잇기 \⏎는 한 명령이다
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=PUNCT)
        lex.whitespace = " \t\r"
        lex.whitespace_split = True
        toks = list(lex)
    except ValueError:
        # 따옴표 짝이 안 맞아 못 쪼갠다(heredoc 본문 등). 쪼개지는 줄만 보고, 의심 문자열이 있으면 막는다
        if "\n" in cmd:
            for line in cmd.split("\n"):
                r = check(line)
                if r:
                    return r
        low = cmd.lower()
        if "git" in low and ("--no-veri" in low or HOOKS_KEY in low or "git_config_" in low):
            return "해석할 수 없는 명령에 훅 우회 의심 문자열"
        return None
    seg = []
    for t in toks + [";"]:
        # punctuation_chars가 연속 구두점을 한 토큰으로 묶는다("&&", ");" 등) — 구두점 토큰은 모두 구분자
        if t and all(c in PUNCT for c in t):
            r = check_segment(seg)
            if r:
                return r
            seg = []
        else:
            seg.append(t)
    return None


def harness_repo(cwd):
    d = os.path.abspath(cwd or ".")
    while True:
        if os.path.isfile(os.path.join(d, ".claude", "harness.config.json")):
            return True
        up = os.path.dirname(d)
        if up == d:
            return False
        d = up


if __name__ == "__main__":
    try:
        p = json.load(sys.stdin)
        cmd = (p.get("tool_input") or {}).get("command") or ""
        if "git" not in cmd.lower() or not harness_repo(p.get("cwd")):
            sys.exit(0)
        why = check(cmd)
    except Exception:
        sys.exit(0)  # 훅 고장이 모든 Bash를 막으면 안 된다. git commit-msg 훅이 본 게이트다
    if why:
        print(f"차단: {why} — git 훅(commit-msg)을 끄는 명령은 에이전트가 쓸 수 없다. "
              "훅이 막으면 메시지·변경을 고쳐 다시 커밋한다. 정말 필요하면 사람이 터미널에서 직접 한다.",
              file=sys.stderr)
        sys.exit(2)
