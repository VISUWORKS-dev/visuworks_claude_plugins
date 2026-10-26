#!/bin/bash
# init.py 신규 설치·기존 프로젝트 업그레이드 시나리오. PY=/usr/bin/python3 로 인터프리터 지정
# 옛 pre-commit·commit-msg는 이 레포 git 이력(c08396a)에서 꺼낸다 — shallow clone이면 실패한다
D=$(cd "$(dirname "$0")" && pwd); I=$D/../scripts/init.py; PY=${PY:-python3}
OLD=c08396a:plugins/issue-harness/templates/githooks
old() { git -C "$D" show "$OLD/$1" || { echo "옛 템플릿을 꺼낼 수 없다 — $OLD/$1" >&2; exit 9; }; }
pass=0; fail=0
ok() { if eval "$2"; then pass=$((pass+1)); echo "PASS $1"; else fail=$((fail+1)); echo "FAIL $1 (rc=$(cat $R/rc))"; cat $R/out; fi; }
new() { R=$(mktemp -d); git -C $R init -q; git -C $R config user.email t@t; git -C $R config user.name t; }
run() { (cd ${W:-$R} && $PY $I "$@" >$R/out 2>&1; echo $? >$R/rc); }
rc() { [ "$(cat $R/rc)" = "$1" ]; }
# 1 신규 설치, 두 번째 실행은 쓰기 0건
new; run; ok "신규 설치" "rc 0 && [ -f $R/.githooks/_harness.py ] && [ -x $R/.githooks/commit-msg ]"
run; ok "재실행 쓰기 0건" "rc 0 && grep -q '^만듦: 없음' $R/out"; rm -rf $R
# 2 옛 프로젝트: 하네스가 깐 pre-commit을 커밋해 둠, 옛 commit-msg, 새 키 없는 config, 진행 중인 v2 state
new; mkdir -p $R/.githooks $R/.claude $R/.harness/issue-3
old pre-commit > $R/.githooks/pre-commit; old commit-msg > $R/.githooks/commit-msg; old _harness.py > $R/.githooks/_harness.py
echo '{"model": "opus", "check_cmd": "make check"}' > $R/.claude/harness.config.json; cp $R/.claude/harness.config.json $R/cfg
echo issue-3 > $R/.harness/ACTIVE; echo '{"issue": 3, "phase": "3-implement", "status": "in_progress"}' > $R/.harness/issue-3/state.json
git -C $R add .githooks; git -C $R commit -qm init
run --dry-run; ok "dry-run은 pre-commit을 남긴다" "[ -f $R/.githooks/pre-commit ] && grep -q '삭제 .githooks/pre-commit' $R/out"
run
ok "옛 pre-commit 삭제, commit-msg 달라 rc 1" "rc 1 && [ ! -e $R/.githooks/pre-commit ]"
ok "추적 파일 삭제 커밋 안내" "grep -q '삭제한 .githooks/pre-commit을 커밋한다' $R/out"
ok "commit-msg 교체 안내" "grep -q 'cp .*/.githooks/commit-msg$' $R/out"
ok "config 그대로" "cmp -s $R/cfg $R/.claude/harness.config.json"
ok "models·test_file_cmd 생략 가능 안내" "grep -q \"'models'가 없다\" $R/out && grep -q \"'test_file_cmd'가 없다\" $R/out"
ok "옛 state 경고" "grep -q '경고: .harness/issue-3/state.json가 옛 형식' $R/out"
git -C $R worktree add -q $R/wt 2>/dev/null; W=$R/wt run; W=
ok "워크트리에서도 primary의 옛 state 경고" "grep -q '경고: .harness/issue-3/state.json' $R/out"
run; ok "업그레이드 후 재실행 쓰기 0건" "grep -q '^만듦: 없음' $R/out"; rm -rf $R
# 3 사람이 고친 옛 pre-commit은 지우지 않고 rc 1 / 하네스와 무관한 pre-commit은 언급도 안 한다
new; mkdir -p $R/.githooks; { old pre-commit; echo '# 우리 팀 추가'; } > $R/.githooks/pre-commit; run
ok "고친 pre-commit 보존·안내·rc 1" "rc 1 && [ -f $R/.githooks/pre-commit ] && grep -q '고친 옛 하네스 훅' $R/out"; rm -rf $R
new; mkdir -p $R/.githooks; printf '#!/bin/sh\nruff check .\n' > $R/.githooks/pre-commit; run
ok "무관한 pre-commit 보존·무언급" "rc 0 && [ -f $R/.githooks/pre-commit ] && ! grep -q 'pre-commit' $R/out"; rm -rf $R
# 4 깨진 입력에서 죽지 않는다: config가 객체 아님, ACTIVE 비었음·디렉터리, state 깨짐
new; mkdir -p $R/.claude $R/.harness; echo 5 > $R/.claude/harness.config.json; : > $R/.harness/ACTIVE
echo '{"phase": 1}' > $R/.harness/state.json; run
ok "config 숫자·ACTIVE 빔" "rc 0 && grep -q 'JSON 객체로 읽을 수 없다' $R/out && ! grep -q '경고:' $R/out"
rm $R/.harness/ACTIVE; mkdir $R/.harness/ACTIVE; run; ok "ACTIVE가 디렉터리" "rc 0"
rmdir $R/.harness/ACTIVE; echo issue-1 > $R/.harness/ACTIVE; mkdir $R/.harness/issue-1; echo '{' > $R/.harness/issue-1/state.json
run; ok "state.json 깨짐" "rc 0 && ! grep -q '경고:' $R/out"; rm -rf $R
echo "pass=$pass fail=$fail"; [ $fail = 0 ]
