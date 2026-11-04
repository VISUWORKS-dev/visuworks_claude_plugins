#!/bin/bash
# check-state.py·훅 시나리오 — 브랜치로 이슈 판정(머지된 다른 spec 커밋 무시, 훅 기록 위치), 대상 없음, 다른 이슈 잔여 파일 무시, 활성 이슈 분기, 병렬 세션, --init. PY=/usr/bin/python3 로 인터프리터 지정
S=$(cd "$(dirname "$0")/../scripts" && pwd)/check-state.py; PY=${PY:-python3}
R=$(mktemp -d); cd $R && git init -q -b main p && cd p && git commit -q --allow-empty -m x && git worktree add -q ../wt -b 75-old
mkdir -p .harness/issue-95 ../wt/.harness/issue-75
echo '{"issue":95,"open_questions":[],"blockers":[],"handoff_to_human":[]}' > .harness/issue-95/state.json
echo '{}' > ../wt/.harness/issue-75/state.json
pass=0; fail=0
expect() { # $1=기대 종료 코드 $2=설명 $3=실행 위치(기본 primary)
  if (cd "${3:-.}" && $PY "$S") >$R/out 2>&1; then got=0; else got=1; fi
  if [ "$got" = "$1" ]; then pass=$((pass+1)); echo "PASS $2"; else fail=$((fail+1)); echo "FAIL $2 (got $got)"; cat $R/out; fi
}
expect 1 '이슈 브랜치가 아니면 위반'
git switch -qc 88-x;  expect 1 '브랜치 이슈의 state.json 없음'
git switch -qc 95-a;  expect 0 '다른 이슈(75) 워크트리 잔여 파일은 무시'
git commit -q --allow-empty -m 'docs : 이슈 #95 spec — 테스트 목록 1항목'
git worktree add -q ../agent -b worktree-agent-abc; expect 0 '구현 워크트리는 spec 커밋으로 이슈를 찾는다' ../agent
git worktree add -q ../b -b 60-b; expect 1 'B 세션(60) 초기화 전'  ../b
(cd ../b && $PY "$S" --init 60 >/dev/null); expect 0 'B가 --init 해도 A(95) 검사는 그대로'
expect 0 'B 세션(60) 초기화 후' ../b
rm -rf .harness/issue-60; expect 0 'B가 끝나 상태를 지워도 A(95) 검사는 그대로'
# 기본 브랜치에서 다른 이슈(96)의 spec 커밋이 머지돼 들어와도 구현 워크트리는 95다 (5a 머지)
git switch -q main && git switch -qc 96-c && git commit -q --allow-empty -m 'docs : 이슈 #96 spec — 테스트 목록 1항목'
git switch -q main && git merge -q --no-ff 96-c -m 'merge 96' && git switch -q 95-a && git merge -q --no-ff main -m 'merge main'
mkdir -p .harness/issue-96 && cp .harness/issue-95/state.json .harness/issue-96/
git worktree add -q ../agent2 -b worktree-agent-def
(cd ../agent2 && $PY -c "import importlib.util as u; s=u.spec_from_file_location('c','$S'); m=u.module_from_spec(s); s.loader.exec_module(m); print(m.active_issue())") >$R/out
grep -qx issue-95 $R/out && pass=$((pass+1)) || { fail=$((fail+1)); echo 'FAIL 머지로 들어온 다른 이슈 spec 커밋을 집음'; cat $R/out; }
# 훅도 각 세션의 브랜치 이슈에 기록한다 — 하네스 밖(git 아님)은 기록하지 않는다
mkdir -p .harness/issue-60 && cp .harness/issue-95/state.json .harness/issue-60/
for c in $PWD ../agent2 ../b $R; do echo "{\"cwd\":\"$c\",\"agent_id\":\"a1\",\"agent_type\":\"x\"}" | HARNESS_HOOK_LOG=$R/log $PY "$(dirname "$S")/record-agent-event.py" >/dev/null; done
(cd ../b && $PY -c "import sys; sys.path.insert(0, '$(dirname "$S")/../templates/githooks'); import _harness; _harness.record('commit-msg', 'r')")
[ "$(wc -l < .harness/issue-95/events.jsonl)" -eq 2 ] && [ "$(wc -l < .harness/issue-60/events.jsonl)" -eq 2 ] && [ ! -e .harness/issue-96/events.jsonl ] \
  && pass=$((pass+1)) || { fail=$((fail+1)); echo 'FAIL 훅이 브랜치 이슈별로 기록하지 않음'; wc -l .harness/*/events.jsonl; }
mkdir -p ../wt/.harness/issue-95 && echo '{}' > ../wt/.harness/issue-95/state.json
expect 1 '활성 이슈의 워크트리 분기'
init() { # $1=기대 종료 코드 $2=설명 $3...=인자 — 워크트리에서 돌려도 primary에 쓴다
  if (cd ../wt && $PY "$S" --init "${@:3}") >$R/out 2>&1; then got=0; else got=1; fi
  if [ "$got" = "$1" ]; then pass=$((pass+1)); echo "PASS $2"; else fail=$((fail+1)); echo "FAIL $2 (got $got)"; cat $R/out; fi
}
init 0 '--init 새 이슈' 61
if [ -f .harness/issue-61/state.json ] && [ ! -e ../wt/.harness/issue-61 ] && [ ! -e .harness/ACTIVE ]; then pass=$((pass+1)); echo 'PASS --init은 primary state.json만 쓴다'
else fail=$((fail+1)); echo 'FAIL --init이 primary state.json에만 쓰지 않음'; fi
echo '{"issue":61,"open_questions":[{"id":"q1","question":"?","answer":null}],"blockers":[],"handoff_to_human":[]}' > .harness/issue-61/state.json
init 1 '--init 기존 상태는 덮어쓰지 않는다' 61
grep -q q1 .harness/issue-61/state.json && pass=$((pass+1)) || { fail=$((fail+1)); echo 'FAIL 기존 질문 보존'; }
init 1 '--init 번호가 아님' abc
init 1 '--init 번호가 숫자 문자이지만 ASCII가 아님' ²
init 1 '--init 인자 초과' 62 junk
grep -q Traceback $R/out && { fail=$((fail+1)); echo 'FAIL --init 오류가 traceback'; }
rm -rf $R; echo "pass=$pass fail=$fail"; [ $fail -eq 0 ]
