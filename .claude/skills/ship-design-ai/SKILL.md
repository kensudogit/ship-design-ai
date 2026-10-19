---
name: ship-design-ai
description: >
  船舶基本設計AIを Python/FastAPI、Next.js/TypeScript、PostgreSQL、Three.js で実装・検証する。
  Lpp/B/T/Cb、排水容積、Holtrop初期推定、制約優先探索、3Dの依頼と
  C:\devlop\ship-design-ai の改修で使う。船級・試運転抵抗の判定には使わない。
version: 3.0.0
---

# Ship Design AI

`C:\devlop\ship-design-ai` の実装規約。コードを書く・直す・解説する前に読む。

教育用の初期設計支援。**実船の設計承認を自動化しない。** 設計者レビューと船級確認が必要。

## 先に決まっていること（緩めない）

1. **排水容積は ∇ = Lpp × B × T × Cb。** 海水密度は 1.025 t/m³（OPEN-07/08）。別式に差し替えない。
2. **抵抗・馬力・燃料は初期推定。** 現行モデルは `geom-v3`（Holtrop-1982 サブセット + ITTC-57、OPEN-24）。試運転・CFD・船級の推進性能と呼ばない。
3. **探索は制約検査が先。** 違反候補はパレートに入れない。目的は貨物 DWT 最大化と体積差・Pd 最小化。証明していない解を「最適」と呼ばない。
4. **LLM は仕様抽出と説明だけ。** ∇・制約・Rt/Pd は `engine` / `resistance`。鍵は `.env` の `OPENAI_API_KEY`。キー無しで評価が落ちない。
5. **承認しても船級確認は別。** レビュー `adopt` は設計者確認。復原性・構造・規則は未評価と書く。
6. **UI を変えたら http://localhost:3060 で操作確認する。** コミットと push は頼まれたときだけ。

詳細は [`references/architecture.md`](references/architecture.md)、[`references/requirements.md`](references/requirements.md)、[`references/open-assumptions.md`](references/open-assumptions.md)。

## スタックと起動

| 役割 | 実体 |
|---|---|
| Backend | Python 3.12 / FastAPI / Pydantic / SQLAlchemy。計算は `backend/app/engine.py` と `resistance.py` |
| Frontend | Next.js / React / TypeScript / Three.js。表示と操作。同じ計算を Route Handler に複製しない |
| DB | PostgreSQL 17。ホスト **5438** |
| ジョブ | デモは FastAPI `BackgroundTasks`（OPEN-11）。本番は Redis/Celery |
| LLM | `gpt-4o-mini`。抽出 `/api/design/extract`、説明 `/api/design/explain` |

```bash
cd C:\devlop\ship-design-ai
docker compose up --build
```

| 役割 | URL |
|---|---|
| UI | http://localhost:3060 |
| API | http://localhost:8060/docs |
| PostgreSQL | localhost:5438 |

ローカル API だけなら `backend` で uvicorn `--port 8060`、`.env` から `DATABASE_URL` と `OPENAI_API_KEY`。

## ワークフロー

1. 船種・海域・速力・積載・寸法上限・設計基準を確定する。未確定は OPEN として `docs/10-assumptions.md` に残す。
2. 案件要件（目標 ∇・DWT・速力・航程・幅/喫水上限・閘門）を `projects.assumptions.req` に保存する。
3. `POST /api/design/evaluate` で制約 → ∇/DWT → Holtrop/ITTC → 貨物 DWT。`check_bounds` 時は OPEN-05 範囲も見る。
4. `POST /api/optimization/jobs` は seed 42 既定。LHS → 差分進化。通過点だけパレート。
5. 画面で KPI・速力–Pd 曲線・候補比較。`POST /api/design/report` で Markdown。`POST /api/design/reviews` で設計者判断。
6. pytest（境界・再現性・監査 JSON）。UI 変更はブラウザで評価〜探索〜レビューを通す。
7. 納品物にモデル版 `geom-v3`、OPEN、既知の未評価（復原性・構造・船級・試運転）を書く。

## 品質ゲート

- 長さ・幅・喫水・型深・密度・速力は正。Cb, Cm, Cp は (0, 1]。Cb ≤ Cm。単位は m, kn, t, kW。
- 監査はモデル版・seed・入力・出力・制約違反。`audit_logs.payload` は JSON 化可能な型だけ（UUID は文字列）。
- 既定船型 180×30×10×0.75、D=16、14 kn の目安: ∇ 40,500 m³、Pd 約 6,658 kW、貨物 DWT 約 30,022 t。回帰の基準。実船値ではない。
- Playwright E2E と本番認証は未実装（OPEN-10）。足すときは既存 API 契約を壊さない。

## 付属サンプル

- `scripts/evaluate_hull.py` … ∇ と排水質量（教育用）
- `scripts/optimize_demo.py` … 制約通過後の幾何探索。実船抵抗ではない
- `assets/templates/` … FastAPI と Compose の雛形

```bash
python scripts/evaluate_hull.py --length 180 --beam 30 --draft 10 --cb 0.75
python scripts/optimize_demo.py
```

## Claude 配置

親フォルダ名は **必ず** `ship-design-ai`（この `name` と一致）。`ship-design-ai-skill` にしない。

```text
.claude/skills/ship-design-ai/SKILL.md
```

ZIP のトップも `ship-design-ai/SKILL.md`。アーカイブファイル名が `ship-design-ai-skill.zip` でも、中のフォルダは `ship-design-ai/`。
