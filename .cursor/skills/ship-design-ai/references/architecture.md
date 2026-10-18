# 推奨構成

Next.js/React/TypeScript + React Three Fiber → FastAPI/Pydantic → PostgreSQL/SQLAlchemy/Alembic。
計算ジョブはRedis/Celery workerに分離し、成果物をオブジェクトストレージに保存。

## API
- POST /api/projects
- GET /api/projects/{id}
- POST /api/design/evaluate
- POST /api/optimization/jobs (202 + job_id)
- GET /api/optimization/jobs/{id}
- GET /api/projects/{id}/candidates
- POST /api/design/reviews

## データ
projects、requirements、candidates、performance_results、optimization_jobs、reviews、audit_logs。

## AI
初期：物理的な制約チェック＋ヒューリスティック探索。次期：NSGA-II、学習済み代理モデル、CFDとの照合。LLMは仕様抽出と説明支援に限定。
