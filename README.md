# 船舶基本設計AI（教育用）

Skill `ship-design-ai` の実行成果です。**実船の設計承認・船級・航行安全の判定には使いません。**

排水容積は ∇ = Lpp × B × T × Cb。海水密度は 1.025 t/m³（OPEN-07）。
DWT・Holtrop 系 Rt/Pd・燃料は初期設計の教育用目安です。試運転抵抗・船級判定は出しません。

## 仮定

未確定項目は [`docs/10-assumptions.md`](docs/10-assumptions.md)。船種は Handymax ばら積み（OPEN-01）。

## 起動

```bash
cd C:\devlop\ship-design-ai
docker compose up --build
```

| 役割 | URL |
|---|---|
| UI | http://localhost:3060 |
| API | http://localhost:8060/docs |
| PostgreSQL | localhost:5438 |

## テスト

```bash
cd backend
pip install -r requirements.txt
pytest
python ../.claude/skills/ship-design-ai/scripts/evaluate_hull.py --length 180 --beam 30 --draft 10 --cb 0.75
```

## API

- `POST /api/projects`
- `GET /api/projects/{id}`
- `POST /api/design/evaluate`
- `POST /api/optimization/jobs`（202 + job_id）
- `GET /api/optimization/jobs/{id}`
- `GET /api/projects/{id}/candidates`
- `POST /api/design/reviews`
- `POST /api/design/extract`（OpenAI 仕様抽出。計算は geom-v3）
- `POST /api/design/explain`（OpenAI 説明。船級判定ではない）
- `PATCH /api/projects/{id}`（案件要件）
- `GET /api/projects/{id}/compare`
- `POST /api/design/report`

モデル `geom-v3`。探索は体積差・DWT 差・初期推定 Pd の合成です。実船性能ではありません。承認しても船級確認は別です。
"# ship-design-ai" 
