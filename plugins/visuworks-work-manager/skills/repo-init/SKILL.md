---
name: repo-init
description: 새로 만든 레포에 README 포맷·이슈/PR 템플릿·.gitignore를 깐다. "레포 세팅해줘", "레포 초기 설정", "repo init", "README·템플릿·gitignore 깔아줘" 시 사용한다. 이미 있는 파일은 덮어쓰지 않는다.
---

# /visuworks-work-manager:repo-init

레포 루트에서 실행한다. 원본은 `${CLAUDE_PLUGIN_ROOT}/skills/repo-init/assets/`. **이미 있는 파일은 덮어쓰지 않는다** —
다르면 diff만 보여주고 사람이 고른다.

## 1. 이슈·PR 템플릿 — 그대로 복사
```bash
mkdir -p .github/ISSUE_TEMPLATE
cp -n "${CLAUDE_PLUGIN_ROOT}"/skills/repo-init/assets/.github/ISSUE_TEMPLATE/*.yml .github/ISSUE_TEMPLATE/
cp -n "${CLAUDE_PLUGIN_ROOT}/skills/repo-init/assets/.github/PULL_REQUEST_TEMPLATE.md" .github/
```
템플릿 라벨(`bug`·`enhancement`·`chore`)이 레포에 없으면 `gh label create <이름>`으로 만든다(원격이 있을 때만).

## 2. .gitignore — 공통 + 언어별
1. 레포 파일로 언어를 판단한다(`package.json`→Node, `pyproject.toml`/`requirements.txt`→Python,
   `build.gradle`/`pom.xml`→Java, `go.mod`→Go 등). 파일이 없으면 사용자에게 묻는다.
2. `assets/gitignore-base`에 GitHub 공식 템플릿을 붙인다:
   ```bash
   { cat "${CLAUDE_PLUGIN_ROOT}/skills/repo-init/assets/gitignore-base"; echo; echo "# <언어> (github/gitignore)"; gh api /gitignore/templates/<언어> --jq .source; } > .gitignore
   ```
   `gh` 미설치·미인증이면 공통 부분만 쓰고 그렇게 알린다.
3. `.gitignore`가 이미 있으면 덮어쓰지 않고, 없는 줄만 추가할지 묻는다.

## 3. README — 포맷에 채우기
`assets/README.md`를 깔고 `{{…}}`를 레포에서 확인한 사실로 채운다.
- 명령은 **복사해 바로 돌아가는 정확한 명령**만 쓴다. 사람과 AI 에이전트가 같은 README를 읽는다
- 확인 못 한 값은 지어내지 말고 `{{…}}`를 남긴 뒤 목록으로 보고한다
- 섹션을 늘리지 않는다. 배지·목차·라이선스 장문·기여 가이드 장문은 넣지 않는다
- README가 이미 있으면 덮어쓰지 않고, 포맷에 없는 필수 항목(시작하기 명령)만 제안한다

## 4. 보고
만든 파일 / 건너뛴 파일(이미 있음) / 남은 `{{…}}` 를 나눠 보여준다. 커밋은 요청받을 때만 한다.
