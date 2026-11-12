# 使用モデル・ライブラリ・データの出典

## GiNZA / ja_ginza 5.2.0

- 配布元：Megagon Labs / <https://github.com/megagonlabs/ginza/tree/v5.2.0>
- モデル：<https://pypi.org/project/ja-ginza/5.2.0/>
- GiNZAと日本語UDモデルはMIT Licenseで配布。モデルを追加学習せず推論に再利用。
- 公式説明による学習元：UD Japanese BCCWJ r2.8（解析）、GSK2014-A (2019) BCCWJ edition（固有表現）。本アプリはその元コーパスを取得・再配布していない。
- 単語ベクトル：chiVe。形態素解析と読み：SudachiPy / SudachiDict-core。
- spaCy：<https://github.com/explosion/spaCy/blob/master/LICENSE>（MIT）
- SudachiPy：<https://github.com/WorksApplications/SudachiPy>（Apache-2.0）
- Sudachi辞書の個別出典・ライセンス：<https://github.com/WorksApplications/SudachiDict> のLEGAL・NOTICEを参照。
- chiVe：<https://github.com/WorksApplications/chiVe> の配布条件・クレジットを参照。
- Streamlit：<https://github.com/streamlit/streamlit/blob/develop/LICENSE>（Apache-2.0）

モデルとライブラリは依存パッケージとして取得し、重みや辞書のコピーをこのリポジトリに同梱しない。インストール先パッケージのライセンス・NOTICEを保持する。

## アプリ用データ

`sample.py`と`data/evaluation.json`は2026-11-12に本アプリ用に作成した架空の文章。実在する製品・組織の名称を含むが、個人の履歴や職場の業務内容を使用していない。実在の組織との提携・推奨を意味しない。
学習用の実データは収集していない。自作評価データはこのリポジトリのコードと同じ条件で利用可能。
