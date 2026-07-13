# visuworks-marketplace

비쥬웍스 Claude 플러그인 마켓플레이스. **public repo로 배포한다** — 인증·토큰이 필요
없어 누구나 등록·설치할 수 있다. vault 경로 등 환경값은 repo에 넣지 않고
설치 시 입력받으므로(userConfig), 공개돼도 개인 환경이 노출되지 않는다.

## 구조
```
visuworks-marketplace/                 ← 이 repo (PUBLIC)
├── .claude-plugin/
│   └── marketplace.json               ← 카탈로그
└── plugins/
    └── visuworks-work-manager/        ← 플러그인 (상대경로 소스)
        ├── .claude-plugin/plugin.json ← userConfig로 vault 경로 입력받음
        ├── skills/obsidian-vault-manager/SKILL.md   ← 정본(Obsidian) 관리
        ├── skills/visuworks-work-manager/SKILL.md   ← Notion 회의록·공용 문서
        ├── hooks/hooks.json
        ├── scripts/gate-notion-search.sh
        ├── CLAUDE.md                  ← 각자 프로젝트 루트에 복사하는 템플릿
        └── README.md
```

## 설치
```
/plugin marketplace add <org>/visuworks-marketplace
/plugin install visuworks-work-manager@visuworks-marketplace
```
활성화하면 Obsidian vault 절대 경로 1개를 입력받는다.
이 값은 각자 환경에만 저장되고 repo에는 들어가지 않는다.

## 공개 전 확인 (커밋하면 안 되는 것)
- **실제 vault 경로·Notion URL 금지** — vault 경로는 plugin.json의 userConfig로
  처리되므로 SKILL.md에 하드코딩하지 말 것.
- **CLAUDE.md의 실제 경로 금지** — 동봉된 CLAUDE.md는 템플릿이며, 각자 로컬 프로젝트
  루트에 복사한 뒤 값을 채운다. 채운 파일은 이 repo에 커밋하지 않는다.
- SKILL.md 예시는 내부 고유명 없이 일반화되어 있다(추가로 넣지 말 것).

## 업데이트
`plugins/...`를 수정하고 version을 올린 뒤 push하면, 등록한 사용자는
`/plugin update`(또는 재설치)로 최신본을 받는다.
