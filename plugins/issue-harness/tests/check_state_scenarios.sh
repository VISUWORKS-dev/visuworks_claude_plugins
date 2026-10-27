#!/bin/bash
# check-state.py 시나리오 — ACTIVE 형식·대상 없음, 다른 이슈 잔여 파일 무시, 활성 이슈 분기. PY=/usr/bin/python3 로 인터프리터 지정
S=$(cd "$(dirname "$0")/../scripts" && pwd)/check-state.py; PY=${PY:-python3}
R=$(mktemp -d); cd $R && git init -q p && cd p && git commit -q --allow-empty -m x && git worktree add -q ../wt -b wt
mkdir -p .harness/issue-95 ../wt/.harness/issue-75
echo '{"issue":95,"open_questions":[],"blockers":[],"handoff_to_human":[]}' > .harness/issue-95/state.json
echo '{}' > ../wt/.harness/issue-75/state.json
pass=0; fail=0
expect() { # $1=기대 종료 코드 $2=설명
  if $PY "$S" >$R/out 2>&1; then got=0; else got=1; fi
  if [ "$got" = "$1" ]; then pass=$((pass+1)); echo "PASS $2"; else fail=$((fail+1)); echo "FAIL $2 (got $got)"; cat $R/out; fi
}
expect 0 'ACTIVE 없음'
echo 88 > .harness/ACTIVE;       expect 1 'ACTIVE가 issue-<N> 형식이 아님'
echo issue-88 > .harness/ACTIVE; expect 1 'ACTIVE가 가리키는 state.json 없음'
echo issue-95 > .harness/ACTIVE; expect 0 '다른 이슈(75) 워크트리 잔여 파일은 무시'
mkdir -p ../wt/.harness/issue-95 && echo '{}' > ../wt/.harness/issue-95/state.json
expect 1 '활성 이슈의 워크트리 분기'
rm -rf $R; echo "pass=$pass fail=$fail"; [ $fail -eq 0 ]
