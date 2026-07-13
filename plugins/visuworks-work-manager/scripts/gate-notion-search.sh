#!/usr/bin/env bash
# PreToolUse gate for Notion workspace-wide search/query.
# matcher가 notion-search·notion-query 계열 도구에만 걸리므로, 이 스크립트는 무조건
# permissionDecision: "ask"를 반환해 사용자 승인 프롬프트를 띄운다.
# (자동 워크스페이스 탐색 차단 / 인가받은 탐색은 승인 후 진행)
cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"워크스페이스 검색·쿼리는 사용자가 지정한 페이지 범위 밖입니다. 정말 다른 곳을 탐색할지 승인해 주세요."}}
JSON
exit 0
