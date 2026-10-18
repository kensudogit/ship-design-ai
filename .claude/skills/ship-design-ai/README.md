# ship-design-ai Skill

Claude Codeで船舶基本設計AIの設計・実装を支援するSkillです。

## インストール
このZIPを展開し、フォルダ `ship-design-ai` を対象プロジェクトの `.claude/skills/` に配置します。

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

Claude Codeを再起動するか、新しいセッションで「ship-design-aiを使って船舶基本設計AIの要件定義を作成して」と依頼してください。環境によっては `/ship-design-ai` で呼び出せます。

## 例
- 「ship-design-aiを使い、ばら積み船の基本設計AIのAPIとDBを作成して」
- 「ship-design-aiでNSGA-IIの多目的最適化を設計して」
- 「ship-design-aiでNext.jsの船型比較画面を作成して」

## デモ
```bash
python scripts/evaluate_hull.py --length 180 --beam 30 --draft 10 --cb 0.75
python scripts/optimize_demo.py
```

最適化サンプルはSciPyが必要です：`pip install scipy`。

## 注意
教育・プロトタイプ用です。実船設計、船級承認、航行安全の判定には使用できません。
