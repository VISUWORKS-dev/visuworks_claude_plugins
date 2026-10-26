#!/usr/bin/env python3
"""`/issue-harness:init` — 프로젝트에 하네스 설정 파일을 깐다.

규칙: **이미 있는 파일은 덮어쓰지 않는다.** 같으면 건너뛰고, 다르면 diff를 보여주고 둔다.
병합이 필요한 파일(settings.json, .gitignore, CLAUDE.md)은 없을 때만 만들고, 있으면 빠진 것만 출력한다.
두 번째 실행은 쓰기 0건이어야 한다.
업그레이드: 하네스가 깐 옛 `.githooks/pre-commit`(개수 비교, #9에서 폐기)은 내용이 그대로일 때만 지운다.

사용: python3 init.py [--dry-run]
종료 코드: 0 / 1 (다른 파일·고친 옛 pre-commit이 있어 사람이 병합해야 함) / 2 (git 레포 아님)
"""
import difflib
import hashlib
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
    ("githooks/_harness.py", ".githooks/_harness.py", False, False),
]
DENY = ["Bash(git commit --no-verify*)", "Bash(git commit -n *)"]
# #9 이전 템플릿 pre-commit의 sha256. 한 번도 바뀐 적 없는 단일 버전이다.
OLD_PRE_COMMIT = "bacb5a8e0971a73e83baf2ce6d8c82af56139a62e30690cb92d1e9c48d2e0534"
# check-state.py ALLOWED와 같다. 밖의 키가 있으면 옛(v2) state.json이다
STATE_KEYS = {"issue", "updated_at", "open_questions", "blockers", "handoff_to_human"}
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
        notes.append(f"{dst}를 템플릿으로 바꾸려면: cp {TPL / src} {root / dst}")

# 1b. 옛 pre-commit — 하네스가 깐 그대로면 지우고, 사람이 고쳤으면 안내만
pc = root / ".githooks/pre-commit"
if pc.exists():
    if hashlib.sha256(pc.read_bytes()).hexdigest() == OLD_PRE_COMMIT:
        wrote.append("삭제 .githooks/pre-commit (옛 개수 검사)")
        if not DRY:
            pc.unlink()
        if git("ls-files", "--error-unmatch", ".githooks/pre-commit")[0] == 0:
            notes.append("삭제한 .githooks/pre-commit을 커밋한다 — 커밋 전엔 구현 워크트리·다른 클론에서 옛 훅이 계속 돈다")
    elif "from _harness import" in pc.read_text(encoding="utf-8", errors="replace"):
        diffs.append(".githooks/pre-commit")
        notes.append(".githooks/pre-commit이 고친 옛 하네스 훅이다 — 테스트 개수 검사는 commit-msg "
                     "Test-Change 게이트로 옮겨졌다. 개수 검사 부분을 직접 지운다")

# 1c. config — 새 키는 없어도 돈다. 파일은 건드리지 않는다
cp = root / ".claude/harness.config.json"
try:
    cfg = json.loads(cp.read_text(encoding="utf-8")) if cp.exists() else {}
except Exception:
    cfg = None
if not isinstance(cfg, dict):
    notes.append(".claude/harness.config.json을 JSON 객체로 읽을 수 없다 — 템플릿과 비교해 직접 고친다")
    cfg = {}
for k, why in (("models", "역할별 모델, 없으면 model"), ("test_file_cmd", "부분 테스트, 없으면 check_cmd")):
    if cfg and k not in cfg:
        notes.append(f".claude/harness.config.json에 {k!r}가 없다 — 생략 가능({why}). 템플릿: {TPL / 'harness.config.json'}")

# 1d. 진행 중인 이슈의 옛(v2) state.json — 새 스키마는 phase 등 진행 키를 거부한다.
# 정본은 primary에 있다 — 워크트리에서 돌아도 primary를 본다 (check-state.py primary_root와 같은 방식)
_, common = git("rev-parse", "--path-format=absolute", "--git-common-dir")
prim = pathlib.Path(common).parent if common else root
try:
    name = (prim / ".harness/ACTIVE").read_text(encoding="utf-8").strip()
    st = prim / ".harness" / name / "state.json"
    d = json.loads(st.read_text(encoding="utf-8")) if name and "/" not in name and ".." not in name else {}
    old = isinstance(d, dict) and bool(set(d) - STATE_KEYS)
except Exception:
    old = False
if old:
    notes.append(f"경고: .harness/{name}/state.json가 옛 형식(phase 등)이다 — 진행 중인 이슈를 옛 버전으로 "
                 "끝낸 뒤 업그레이드한다. 새 check-state.py가 이 파일을 거부한다")

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
    notes.append(f"core.hooksPath가 {hp!r}다 — .githooks의 commit-msg가 돌지 않는다. 직접 정한다")

# 5. CLAUDE.md — 쓰지 않는다. 조각만 안내
cm = root / "CLAUDE.md"
if not cm.exists() or "issue-harness:issue-harness" not in cm.read_text(encoding="utf-8"):
    notes.append(f"CLAUDE.md에 하네스 절을 붙인다 — 조각: {TPL / 'claude-md-snippet.md'}")

print("\n== harness init" + (" (dry-run — 아무것도 쓰지 않음)" if DRY else ""))
print("만듦: " + (", ".join(wrote) if wrote else "없음"))
print("다름(건드리지 않음): " + (", ".join(diffs) if diffs else "없음"))
for n in notes:
    print("직접 할 것: " + n)
sys.exit(1 if diffs else 0)
