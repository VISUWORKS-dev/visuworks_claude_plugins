#!/bin/bash
# commit-msg Test-Change 게이트 시나리오. 인자: githooks 디렉터리
H=$1; R=$(mktemp -d); cd $R; git init -q; mkdir -p .githooks tests
cp $H/commit-msg $H/_harness.py .githooks/; chmod +x .githooks/commit-msg; git config core.hooksPath .githooks
git config core.quotePath true; git config user.email t@t; git config user.name t
cat > tests/test_a.py <<'P'
import pytest
def test_keep():
    assert 1 + 1 == 2
def test_value():
    assert f() == 115
def test_raises():
    with pytest.raises(ValueError):
        g()
@pytest.mark.parametrize("x", [1, 2])
def test_param(x):
    assert x
class TestK:
    def test_m(self):
        assert True
C = [1, 2]
@pytest.mark.parametrize("y", C)
def test_var(y):
    assert y
@pytest.mark.parametrize(argnames="z", argvalues=[1, 2])
def test_kw(z):
    assert z
def test_dup():
    assert 1
    assert 1
P
printf 'def test_u():\n    assert 1\n' > "tests/test_한.py"
git add -A; git commit -qm "test : 초기" || exit 9; BASE=$(git rev-parse HEAD)
rep() { python3 -c "import sys;p='tests/test_a.py';s=open(p).read();open(p,'w').write(s.replace(sys.argv[1],sys.argv[2],1))" "$1" "$2"; }
pass=0; fail=0
expect() { # $1=ok|block $2=설명 $3=메시지
  if git commit -q -m "$3" >/dev/null 2>$R/err; then got=ok; else got=block; fi
  if [ "$got" = "$1" ]; then pass=$((pass+1)); echo "PASS $2 $( [ $got = block ] && head -1 $R/err)"; else fail=$((fail+1)); echo "FAIL $2 (got $got)"; cat $R/err; fi
  git reset -q --hard $BASE; git clean -qfd
}
# 1 새 테스트 추가
printf 'def test_new():\n    assert 3\n' >> tests/test_a.py; git add -A; expect ok "새 테스트 추가" "test : 추가"
# 2 함수 삭제, 선언 없음 / 있음
python3 - <<'P'
s=open('tests/test_a.py').read().replace("def test_keep():\n    assert 1 + 1 == 2\n",""); open('tests/test_a.py','w').write(s)
P
git add -A; expect block "함수 삭제 선언 없음" "test : 삭제"
python3 - <<'P'
s=open('tests/test_a.py').read().replace("def test_keep():\n    assert 1 + 1 == 2\n",""); open('tests/test_a.py','w').write(s)
P
git add -A; expect ok "함수 삭제 선언 있음" "$(printf 'test : 삭제\n\nTest-Change: test_keep — test_value와 중복')"
# 3 assert 완화
rep 'assert f() == 115' 'assert f() is not None'; git add -A; expect block "assert 완화" "test : 완화"
# 4 assert 추가
rep '    assert 1 + 1 == 2' $'    assert 1 + 1 == 2\n    assert 2 + 2 == 4'; git add -A; expect ok "assert 추가" "test : 강화"
# 5 skip 추가
rep 'def test_value' $'@pytest.mark.skip\ndef test_value'; git add -A; expect block "skip 추가" "test : skip"
# 6 다른 파일로 이동
python3 - <<'P'
s=open('tests/test_a.py').read(); blk="def test_value():\n    assert f() == 115\n"
open('tests/test_a.py','w').write(s.replace(blk,"")); open('tests/test_b.py','w').write(blk)
P
git add -A; expect ok "다른 파일로 이동" "test : 이동"
# 7 parametrize 케이스 추가 / 삭제
rep '[1, 2]' '[1, 2, 3]'; git add -A; expect ok "parametrize 케이스 추가" "test : 케이스"
rep '[1, 2]' '[1]'; git add -A; expect block "parametrize 케이스 삭제" "test : 케이스"
# 8 파일 통째 삭제 + 파일 단위 선언
git rm -q tests/test_a.py; expect ok "파일 삭제 ::* 선언" "$(printf 'test : 파일 정리\n\nTest-Change: tests/test_a.py::* — 모듈 기준 파일로 통합')"
git rm -q tests/test_a.py; expect block "파일 삭제 선언 없음" "test : 파일 정리"
# 9 importorskip 허용
printf 'def test_opt():\n    pytest.importorskip("x")\n    assert 1\n' >> tests/test_a.py; git add -A; expect ok "importorskip" "test : 선택"
# 10 pytest.raises 제거
python3 - <<'P'
s=open('tests/test_a.py').read().replace("    with pytest.raises(ValueError):\n        g()\n","    g()\n"); open('tests/test_a.py','w').write(s)
P
git add -A; expect block "pytest.raises 제거" "test : raises"
# 11 클래스 메서드 삭제는 한정이름으로
python3 - <<'P'
s=open('tests/test_a.py').read().replace("    def test_m(self):\n        assert True\n","    pass\n"); open('tests/test_a.py','w').write(s)
P
git add -A; expect ok "클래스 메서드 한정이름 선언" "$(printf 'test : 메서드\n\nTest-Change: TestK.test_m — 대체 T4')"
# 12 refact가 tests 변경 — 기존 규칙 유지
printf '\n' >> tests/test_a.py; git add -A; expect block "refact의 tests 변경" "refact : 정리"
# 13 모듈 수준 pytestmark skip
rep 'import pytest' $'import pytest\npytestmark = pytest.mark.skip'; git add -A; expect block "모듈 수준 skip" "test : 모듈 skip"
# 14 fixup!도 테스트 검사
python3 -c "p='tests/test_a.py';s=open(p).read();open(p,'w').write(s.replace('def test_keep():\n    assert 1 + 1 == 2\n',''))"; git add -A; expect block "fixup! 삭제" "fixup! 초기"
# 15 비ASCII 경로 삭제 (quotePath=true)
git rm -q "tests/test_한.py"; expect block "비ASCII 경로 삭제" "test : 삭제"
# 16 클래스 skip 데코레이터 / 클래스 pytestmark
rep 'class TestK:' $'@pytest.mark.skip\nclass TestK:'; git add -A; expect block "클래스 skip" "test : skip"
rep 'class TestK:' $'class TestK:\n    pytestmark = pytest.mark.xfail'; git add -A; expect block "클래스 pytestmark" "test : xfail"
# 17 변수 parametrize 케이스 삭제 / 추가
rep 'C = [1, 2]' 'C = [1]'; git add -A; expect block "변수 parametrize 삭제" "test : 케이스"
rep 'C = [1, 2]' 'C = [1, 2, 3]'; git add -A; expect ok "변수 parametrize 추가" "test : 케이스"
# 18 키워드 parametrize 케이스 추가
rep 'argvalues=[1, 2]' 'argvalues=[1, 2, 3]'; git add -A; expect ok "키워드 parametrize 추가" "test : 케이스"
# 19 같은 assert 중복 하나 삭제
rep $'    assert 1\n    assert 1\n' $'    assert 1\n'; git add -A; expect block "중복 assert 하나 삭제" "test : 중복"
echo "pass=$pass fail=$fail"; rm -rf $R
