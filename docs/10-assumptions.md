# 未確定事項（OPEN）

Skill 手順1。ユーザー未確定のため仮定。正式設計・船級には使わない。

| ID | 項目 | 仮定 |
|---|---|---|
| OPEN-01 | 船種 | Handymax ばら積み船 |
| OPEN-02 | 運航海域 | 外航一般。海象は未評価 |
| OPEN-03 | 設計速力 | 14 kn。抵抗・推進の入力には使わない |
| OPEN-04 | 積載 | 目標排水容積 40,000 m³（Skill の `optimize_demo` と同じ） |
| OPEN-05 | 寸法範囲 | Lpp 150–220 m、B 25–38 m、T 8–13 m、Cb 0.60–0.85 |
| OPEN-06 | 設計基準 | 教育用。IMO / 船級 / 復原性 / 構造は未評価 |
| OPEN-07 | 海水密度 | 1.025 t/m³ |
| OPEN-08 | 排水容積 | ∇ = Lpp × B × T × Cb（Skill 指定の概算） |
| OPEN-09 | Cp 明示時 | Cb ≤ Cp。未入力時は OPEN-13 |
| OPEN-10 | 認証 | デモは未実装。本番で必須 |
| OPEN-11 | ジョブ基盤 | デモは FastAPI BackgroundTasks。本番は Redis/Celery |
| OPEN-12 | CFD / 水槽 | なし。抵抗を実船性能と呼ばない |
| OPEN-13 | Cm / Cp | Cm 既定 0.98。Cp = Cb / Cm。実船線図の係数ではない |
| OPEN-14 | Cwp | (1 + 2 Cb) / 3（Taylor 型の教育用） |
| OPEN-15 | 乾舷 | 教育用に D − T ≥ 3 m。IMO 乾舷規則ではない |
| OPEN-16 | LWT / DWT | LWT = 0.12 Lpp B D (0.85+0.15 Cb)。DWT = Δ − LWT。軽荷重量鑑定ではない |
| OPEN-17 | 型深 | D 14–20 m |
| OPEN-18 | 倉内容積 | 0.72 Lpp B D Cb。穀物倉の実測ではない |
| OPEN-19 | 濡れ面積 | Mumford 型 S = 1.025 L (Cb B + 1.7 T) |
| OPEN-20 | GM 指標 | KB + BM − 0.55 D。Intact GM / IMO 基準ではない |
| OPEN-21 | パワー指標 | Δ^(2/3) Vs³ / Lpp。実船馬力・燃料ではない |
| OPEN-22 | 水路 | B > 32.31 m は旧パナマ閘門超の警告のみ。制限ではない |
| OPEN-23 | LLM | OpenAI は仕様抽出と説明のみ。∇・制約は geom-v3。鍵は `.env` の `OPENAI_API_KEY` |
| OPEN-24 | 抵抗 | Holtrop 1982 サブセット + ITTC-57 + 付加物 3%。試運転・CFD・船級ではない |
| OPEN-25 | 燃料 | SFOC 180 g/kWh、海余裕 15%、航程既定 6,000 nm |
| OPEN-26 | Lwl | 1.01 × Lpp |
| OPEN-27 | 推進 | ηD = 0.62。プロペラ設計ではない |
| OPEN-29 | LCB | 9(Cp−0.68)−2 %L。線図の LCB ではない |

未評価: 復原性、構造強度、船級規則、試運転推進、耐波性。
計算モデルは `geom-v3`。
