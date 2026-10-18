---
name: ship-design-ai
description: 船舶基本設計AIシステムをPython/FastAPI、React/Next.js/TypeScript、PostgreSQL、Dockerで設計・実装・検証する。船型パラメータ、排水容積、設計制約、多目的最適化、3D表示、API、DB、テスト、Docker構成の依頼で使用する。
---

# Ship Design AI Skill

## 目的
船舶の基本設計を支援する再利用可能な開発手順。実船の設計承認を自動化しない。設計者・船級の確認が必要。

## ワークフロー
1. 対象船種、運航海域、速力、積載能力、寸法上限、設計基準を質問・確定する。未確定値は仮定として明記する。
2. 要件を機能/非機能/安全制約/受入基準に分割する。`references/requirements.md`を参照。
3. API・DB・非同期ジョブ・最適化サービスを分離して設計する。`references/architecture.md`を参照。
4. 設計変数Lpp,B,T,Cb,Cp等と単位・範囲を定義する。排水容積の概算はLpp×B×T×Cb。海水密度の仮定を明示する。
5. 最適化は制約検査を先に実装し、候補生成、評価、パレート解比較を行う。実測・CFDのない抵抗値は実船性能と呼ばない。
6. FastAPIのPydantic入力検証、SQLAlchemy/Alembic、Next.js入力画面、Three.js表示を実装する。
7. pytest、Playwright、数値境界テスト、再現性テスト、監査ログを整備する。
8. Docker Composeで起動し、README、OpenAPI、設計根拠、既知の制約を納品する。

## 品質ゲート
- 長さ・幅・喫水は正、係数は0より大きく1以下、単位系を固定する。
- 計算モデルのバージョン、乱数シード、入力値、出力、制約違反を記録する。
- AI推奨結果は設計者の承認なしに正式設計に採用しない。
- 復原性、構造強度、船級規則、推進性能は専用モデル・専門家の検証が必要。
- 本番では認証認可、秘密情報管理、ジョブのタイムアウトとリトライを実装する。

## 付属サンプル
`scripts/evaluate_hull.py` は排水容積・排水質量の教育用計算例。`scripts/optimize_demo.py` は実船抵抗ではない幾何指標の探索例。`assets/templates/` にAPIとComposeの雛形。

## 出力形式
要件定義書、構成図、ER図、API一覧、DB DDL、AIモデルの検証方針、ソース、テスト、Docker、運用手順を段階的に生成する。
