#!/usr/bin/env python3
"""`/harness:init` — 프로젝트에 하네스 설정 파일을 깐다.

규칙: **이미 있는 파일은 덮어쓰지 않는다.** 같으면 건너뛰고, 다르면 diff를 보여주고 둔다.
병합이 필요한 파일(settings.json, .gitignore, CLAUDE.md)은 없을 때만 만들고, 있으면 빠진 것만 출력한다.
두 번째 실행은 쓰기 0건이어야 한다.

사용: python3 init.py [--dry-run]
종료 코드: 0 / 1 (다른 파일이 있어 사람이 병합해야 함) / 2 (git 레포 아님)
"""
import difflib
import json
import pathlib
import subprocess
import sys

TPL = pathlib.Path(__file__).resolve().parent.parent / "templates"
DRY = "--dry-run" in sys.argv

# (템플릿, 대상, 실행 비트, 프로젝트가 고쳐 쓰는 파일인가)
COPIES = [
    ("harness.config.json", ".claude/harness.config.json", False, True),
    ("agent-permissions.md", ".claude/rules/agent-permissions.md", False, False),
    ("githooks/commit-msg", ".githooks/commit-msg", True, False),
    ("githooks/pre-commit", ".githooks/pre-commit", True, False),
    ("githooks/_harness.py", ".githooks/_harness.py", False, False),
]
DENY = ["Bash(git commit --no-verify*)", "Bash(git commit -n *)"]
IGNORE = [".claude/worktrees/", ".harness/", ".harness.bak-*/", "_workspace/", "_workspace_*/"]


def git(*a):
    r = subprocess.run(["git", *a], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


rc, top = git("rev-parse", "--show-toplevel")
if rc:
    print("git 레포가 아니다 — 레포 루트에서 다시 실행한다.")
    sys.exit(2)
root = pathlib.Path(top)
wrote, diffs, notes = [], [], []


def write(rel, text, exe=False):
    wrote.append(rel)
    if DRY:
        return
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    if exe:
        p.chmod(0o755)


# 1. 그대로 복사하는 파일
for src, dst, exe, owned in COPIES:
    new = (TPL / src).read_text(encoding="utf-8")
    p = root / dst
    if not p.exists():
        write(dst, new, exe)
    elif owned:
        pass  # 프로젝트 값을 채운 파일이다 — 템플릿과 다른 것이 정상
    elif p.read_text(encoding="utf-8") != new:
        diffs.append(dst)
        print(f"\n[다름 — 건드리지 않음] {dst}")
        sys.stdout.writelines(difflib.unified_diff(
            p.read_text(encoding="utf-8").splitlines(True), new.splitlines(True),
            f"{dst} (현재)", f"{dst} (템플릿)"))

# 2. settings.json — 없으면 만들고, 있으면 빠진 키만 보여준다
sp = root / ".claude/settings.json"
want = {"permissions": {"deny": DENY}, "worktree": {"baseRef": "head"}}
if not sp.exists():
    write(".claude/settings.json", json.dumps(want, ensure_ascii=False, indent=2) + "\n")
else:
    try:
        cur = json.loads(sp.read_text(encoding="utf-8"))
    except Exception as e:
        cur = None
        notes.append(f".claude/settings.json을 읽을 수 없다 ({e}) — 아래 키를 직접 넣는다: {json.dumps(want)}")
    if cur is not None:
        miss = [d for d in DENY if d not in (cur.get("permissions") or {}).get("deny", [])]
        if miss:
            notes.append(f".claude/settings.json permissions.deny에 추가: {json.dumps(miss, ensure_ascii=False)}")
        if (cur.get("worktree") or {}).get("baseRef") != "head":
            notes.append('.claude/settings.json에 추가: "worktree": {"baseRef": "head"} '
                         "— 없으면 구현 워크트리가 기본 브랜치에서 갈라져 핸드오프 커밋이 없다")
        if "hooks" in cur and "SubagentStop" in cur["hooks"]:
            notes.append(".claude/settings.json hooks.SubagentStop이 있다 — 플러그인 훅과 이중으로 기록되면 지운다")

# 3. .gitignore — 없으면 만들고, 있으면 빠진 줄만
gp = root / ".gitignore"
if not gp.exists():
    write(".gitignore", "# harness 런타임 상태·작업 공간\n" + "\n".join(IGNORE) + "\n")
else:
    have = {l.strip() for l in gp.read_text(encoding="utf-8").splitlines()}
    miss = [l for l in IGNORE if l not in have]
    if miss:
        notes.append(".gitignore에 추가:\n    " + "\n    ".join(miss))

# 4. core.hooksPath — 비어 있을 때만 설정
_, hp = git("config", "--local", "--get", "core.hooksPath")
if not hp:
    wrote.append("git config core.hooksPath .githooks")
    if not DRY:
        git("config", "--local", "core.hooksPath", ".githooks")
elif (root / hp).resolve() != (root / ".githooks").resolve():
    notes.append(f"core.hooksPath가 {hp!r}다 — .githooks의 commit-msg·pre-commit이 돌지 않는다. 직접 정한다")

# 5. CLAUDE.md — 쓰지 않는다. 조각만 안내
cm = root / "CLAUDE.md"
if not cm.exists() or "harness:issue-harness" not in cm.read_text(encoding="utf-8"):
    notes.append(f"CLAUDE.md에 하네스 절을 붙인다 — 조각: {TPL / 'claude-md-snippet.md'}")

print("\n== harness init" + (" (dry-run — 아무것도 쓰지 않음)" if DRY else ""))
print("만듦: " + (", ".join(wrote) if wrote else "없음"))
print("다름(건드리지 않음): " + (", ".join(diffs) if diffs else "없음"))
for n in notes:
    print("직접 할 것: " + n)
sys.exit(1 if diffs else 0)
