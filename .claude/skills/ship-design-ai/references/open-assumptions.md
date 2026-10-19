# 未確定事項（OPEN）

リポジトリの正本は `docs/10-assumptions.md`。Skill から実装するときも同じ ID を使う。

| ID | 仮定 |
|---|---|
| OPEN-01 | 船種: Handymax ばら積み |
| OPEN-03 | 設計速力 14 kn |
| OPEN-05 | Lpp 150–220、B 25–38、T 8–13、Cb 0.60–0.85 |
| OPEN-07 | 海水密度 1.025 t/m³ |
| OPEN-08 | ∇ = Lpp × B × T × Cb |
| OPEN-10 | デモは認証なし |
| OPEN-11 | デモは BackgroundTasks。本番 Celery |
| OPEN-12 | CFD / 水槽なし。抵抗を実船性能と呼ばない |
| OPEN-13 | Cm 既定 0.98。Cp = Cb / Cm |
| OPEN-16 | LWT/DWT は教育用質量分割。軽荷重量鑑定ではない |
| OPEN-23 | LLM は抽出と説明のみ |
| OPEN-24 | Holtrop-1982 サブセット + ITTC-57。試運転・CFD・船級ではない |
| OPEN-25 | SFOC 180 g/kWh、海余裕 15%、航程既定 6,000 nm |
| OPEN-26 | Lwl = 1.01 × Lpp |
| OPEN-27 | ηD = 0.62。プロペラ設計ではない |
| OPEN-29 | LCB = 9(Cp−0.68)−2 %L。線図の LCB ではない |

未評価: 復原性、構造強度、船級規則、試運転推進、耐波性。モデル `geom-v3`。
