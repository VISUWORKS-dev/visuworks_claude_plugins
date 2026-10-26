#!/bin/bash
# guard-git-bypass.py(PreToolUse Bash) 차단 시나리오. PY=/usr/bin/python3 로 인터프리터 지정
G=$(cd "$(dirname "$0")/../scripts" && pwd)/guard-git-bypass.py; PY=${PY:-python3}
R=$(mktemp -d); mkdir -p $R/h/.claude $R/h/sub $R/plain; echo '{}' > $R/h/.claude/harness.config.json
pass=0; fail=0
expect() { # $1=ok|block $2=명령 $3=cwd(기본 하네스 레포 하위)
  js=$($PY -c 'import json,sys;print(json.dumps({"tool_input":{"command":sys.argv[1]},"cwd":sys.argv[2]}))' "$2" "${3:-$R/h/sub}")
  if echo "$js" | $PY "$G" 2>$R/err; then got=ok; else got=block; fi
  if [ "$got" = "$1" ]; then pass=$((pass+1)); echo "PASS $1 $2"; else fail=$((fail+1)); echo "FAIL $2 (got $got)"; cat $R/err; fi
}
# 플래그 위치·묶음
expect block 'git commit --no-verify -m x'
expect block 'git commit -m "x" --no-verify'
expect block 'git commit -n -m x'
expect block 'git commit -nm "x"'
expect block 'git commit -anm x'
expect block 'git commit -m x --no-veri'
expect block 'git merge --no-verify feat'
expect block '/usr/bin/git commit -m x --no-verify'
expect block 'git -C /tmp commit -m x -n'
# 훅 경로 바꾸기
expect block 'git -c core.hooksPath=/dev/null commit -m x'
expect block 'git -c core.hookspath= commit -m x'
expect block 'git --config-env=core.hooksPath=X commit -m x'
expect block 'git config core.hooksPath /dev/null'
expect block 'git config --local core.hooksPath .x'
expect block 'git config --unset core.hooksPath'
expect block 'git config set core.hooksPath x'
expect block 'GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/dev/null git commit -m x'
expect block "GIT_CONFIG_PARAMETERS=\"'core.hooksPath'='/dev/null'\" git commit -m x"
expect block 'export GIT_CONFIG_COUNT=1; git commit -m x'
expect block 'env GIT_CONFIG_COUNT=1 git commit -m x'
# 감싸기·이어 붙이기
expect block 'cd sub && git commit -m x --no-verify'
expect block 'git add -A; git commit -m $MSG --no-verify'
expect block 'sh -c "git commit -m x --no-verify"'
expect block "bash -lc 'git commit -nm x'"
expect block 'eval "git commit -m x -n"'
expect block '(git commit -m x -n)'
expect block 'echo "$(git commit -m x --no-verify)"'
expect block 'echo `git commit -n -m x`'
expect block $'git status\ngit commit -m x --no-verify'
expect block $'git commit -n -F- <<EOF\nit\'s\nEOF'
# 리뷰에서 나온 우회 경로
expect block $'git commit \\\n  --no-verify \\\n  -m x'
expect block $'git commit -m x \\\n  -n'
expect block 'if git commit -n -m x; then echo ok; fi'
expect block 'if true; then :; else git commit --no-verify -m x; fi'
expect block 'for i in 1; do git commit -n -m x; done'
expect block '! git commit -n -m x'
expect block 'sudo git commit -n -m x'
expect block 'echo y | xargs git commit -n -m'
expect block 'timeout 120 git commit -m x --no-verify'
expect block 'nice -n 5 git commit -n -m x'
expect block 'env -u FOO git commit -n -m x'
expect block 'env -i PATH=$PATH git commit -n -m x'
expect block 'stdbuf -oL git commit -n -m x'
expect block 'command -p git commit -n -m x'
expect block 'git config alias.ci "commit --no-verify"'
expect block 'git config alias.ci "commit -nm"'
expect block 'git -c alias.ci="commit --no-verify" ci -m x'
expect block 'git config -- core.hooksPath /dev/null'
expect block 'git config --remove-section core'
expect block 'git config --rename-section core x'
expect block $'bash <<\'EOF\'\ngit commit -n -m x\nEOF'
expect ok $'git commit -m "$(cat <<\'EOF\'\nfix : x\n\ngit commit --no-verify 로 훅을 끄던 경로를 막는다\nEOF\n)"'
expect ok $'git commit -F- <<\'EOF\'\ndocs: explain why `git commit -n` is blocked\nEOF'
expect ok 'git config alias.lg "log -n 5"'
expect ok 'timeout 60 git status'
# 통과해야 하는 것
expect ok 'git commit -m x'
expect ok 'git commit -m "-n 옵션 설명" -a'
expect ok 'git commit -mn'
expect ok 'git commit -m "--no-verify는 쓰지 않는다"'
expect ok 'git commit -F msg.txt -- -n'
expect ok 'git log -n 3'
expect ok 'git config --get core.hooksPath'
expect ok 'git config core.hooksPath'
expect ok 'git -c user.name=x commit -m y'
expect ok 'echo git commit --no-verify'
expect ok 'grep -rn "no-verify" .'
expect ok 'ls -la'
# 하네스 레포 밖은 건드리지 않는다
expect ok 'git commit -m x --no-verify' $R/plain
echo "pass=$pass fail=$fail"; rm -rf $R; [ $fail = 0 ]
