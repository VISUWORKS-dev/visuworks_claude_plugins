#!/usr/bin/env python3
"""플러그인 저장소 검사 — plugin.json·marketplace.json 버전 일치, 「」 참조가 제목·굵은 문단 이름으로 이어지는지."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# 참조가 아니라 출력 형식 문자열 — 새로 생기면 여기에 더한다
NOT_REFS = {"안 함 — 이유", "선통과 — T<m> 구현으로", "네"}

errors = []
for p in json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())["plugins"]:
    v = json.loads((ROOT / p["source"] / ".claude-plugin/plugin.json").read_text())["version"]
    if v != p["version"]:
        errors.append(f"{p['name']}: plugin.json {v} ≠ marketplace.json {p['version']}")

for plugin in sorted((ROOT / "plugins").iterdir()):
    # docs/는 평가·회고 기록이라 당시 이름을 그대로 둔다
    files = [f for f in plugin.rglob("*") if f.suffix in (".md", ".py") and "docs" not in f.relative_to(plugin).parts]
    # ponytail: 참조가 가리키는 파일을 따지지 않고 플러그인 전체 제목·굵은 이름과 맞춘다 — 다른 파일의 같은 이름이면 통과한다
    names = set()
    for f in files:
        if f.suffix == ".md":
            t = f.read_text()
            names |= {m.strip() for m in re.findall(r"^#+\s+(.+)$", t, re.M)}
            names |= {m.strip().rstrip(".:") for m in re.findall(r"\*\*(.+?)\*\*", t)}
    for f in files:
        for i, line in enumerate(f.read_text().splitlines(), 1):
            for ref in re.findall(r"「([^」]+)」", line):
                # 제목 앞부분만 불러도 된다 — 「진행 지점 복원」 → ## 진행 지점 복원 — git이 정본
                if ref in NOT_REFS or any(n == ref or n.startswith(ref + " ") for n in names):
                    continue
                errors.append(f"{f.relative_to(ROOT)}:{i}: 「{ref}」를 가리키는 제목·굵은 문단 이름이 없다")

print("\n".join(errors) or "OK")
sys.exit(1 if errors else 0)
