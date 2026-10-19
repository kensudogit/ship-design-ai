# 推奨構成

```
Browser (Next.js :3060, Three.js)
  → FastAPI :8060 (Pydantic → 制約検査 → evaluate / jobs)
    → PostgreSQL :5438
```

計算モデルは `geom-v3`。乱数シード・入力・出力・制約違反を `audit_logs` に残す。
デモのジョブは `BackgroundTasks`（OPEN-11）。本番は Redis/Celery。
LLM（OpenAI）は仕様抽出と説明だけ。`.env` の `OPENAI_API_KEY` は API プロセスだけが読む。

## API

- `POST /api/projects`
- `GET /api/projects`
- `GET /api/projects/{id}`
- `PATCH /api/projects/{id}`（案件要件 `assumptions.req`）
- `POST /api/design/evaluate`
- `POST /api/design/extract`（LLM。計算は geom-v3）
- `POST /api/design/explain`（LLM。船級判定ではない）
- `POST /api/optimization/jobs`（202 + job_id）
- `GET /api/optimization/jobs/{id}`
- `GET /api/projects/{id}/candidates`
- `GET /api/projects/{id}/compare`
- `POST /api/design/report`
- `POST /api/design/reviews`

`POST /api/design/evaluate` の要件は body の `requirements` を優先。`project_id` は監査用。payload の UUID は JSON 文字列にする。

## データ

`projects`（`assumptions.req` JSON）、`candidates`、`optimization_jobs`、`reviews`、`audit_logs`。

## 探索

制約通過後に LHS と差分進化。パレートは貨物 DWT（大）、体積差と初期推定 Pd（小）。seed 既定 42。実船最適ではない。

## フロント

同一計算を Next.js に複製しない。KPI は ∇・DWT・Rt・Pd・貨物 DWT・燃料。速力–Pd 曲線、候補比較、レポートダウンロード、geom-v3 フィルタ。
