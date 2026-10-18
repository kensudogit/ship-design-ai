# 構成

```
Browser (Next.js :3060, Three.js 点群)
  → FastAPI :8060 (Pydantic 検証 → 制約検査 → 評価 / ジョブ)
    → PostgreSQL :5438
```

デモのジョブは BackgroundTasks（OPEN-11）。本番は Redis/Celery。

計算モデルは `geom-v3`。乱数シード・入力・出力・制約違反を `audit_logs` に残す。
探索は制約検査のあと LHS＋差分進化。パレートは教育用貨物 DWT（最大化）と体積差・初期推定 Pd（最小化）。
LLM（OpenAI）は仕様抽出と説明支援に限定する。`.env` の `OPENAI_API_KEY` は API プロセスだけが読む。
