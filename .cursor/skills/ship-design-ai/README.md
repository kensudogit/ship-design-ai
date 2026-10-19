# ship-design-ai Skill

船舶基本設計AI（`geom-v3`）の設計・実装を支援する Skill。教育用。実船承認・船級・航行安全の判定には使わない。

## インストール

フォルダ名は **`ship-design-ai`**（`SKILL.md` の `name` と一致させる。Claude 必須）。

```text
project/
  .claude/
    skills/
      ship-design-ai/
        SKILL.md
        README.md
        references/
        scripts/
        assets/
```

Cursor なら同じツリーを `.cursor/skills/ship-design-ai/` または `~/.cursor/skills/ship-design-ai/` にも置く。

## ZIP（カタログ／Claude 互換）

中身のルートはフォルダ `ship-design-ai/`。`ship-design-ai-skill/` にすると「親フォルダ名と name が不一致」になる。

```text
ship-design-ai-skill.zip
└── ship-design-ai/
    ├── SKILL.md
    ├── README.md
    ├── references/
    ├── scripts/
    └── assets/
```

## 例

- 「ship-design-aiを使い、ばら積み船の基本設計AIのAPIとDBを作成して」
- 「geom-v3 の Holtrop 推定を案件要件に接続して」
- 「制約優先で探索し、貨物 DWT と Pd のパレートを画面に出して」

## デモ

```bash
python scripts/evaluate_hull.py --length 180 --beam 30 --draft 10 --cb 0.75
python scripts/optimize_demo.py
```

`optimize_demo.py` は SciPy が必要: `pip install scipy`。

実装リポジトリは `C:\devlop\ship-design-ai`。UI http://localhost:3060 / API http://localhost:8060。
