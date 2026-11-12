# 使用モデル・データの出典と条件

## モデル（各MIT License）

- `umiyosh/modernbert-ja-130m-typo-detector`：<https://huggingface.co/umiyosh/modernbert-ja-130m-typo-detector>
  固定リビジョン：`822bfc9df5b556237a7b92139861be5b43bc3fbc`
- `umiyosh/modernbert-ja-130m-homophone-scorer`：<https://huggingface.co/umiyosh/modernbert-ja-130m-homophone-scorer>
  固定リビジョン：`00f1a531c55bae03502a58967df9dee2fade4e62`
- 作者：umiyosh。元のモデルはSB Intuitionsの`sbintuitions/modernbert-ja-130m`（MIT）。
- 作者の説明ではJWTD、Common Voiceの音声書き起こし等で学習。詳細は各モデルカードの学習データ・出典を参照。
- アプリ独自の追加学習・重み変更はしていない。重みは配布元から取得し、リポジトリに再配布しない。
- 配布元の性能値は本アプリの実測値ではない。本アプリの性能として引用しない。

## 候補表（CC BY-SA 3.0）

`umiyosh/jwtd-misconversion-table`：<https://huggingface.co/datasets/umiyosh/jwtd-misconversion-table>
固定リビジョン：`5822e4ec72e61d48a29f2cb7ca7add33fc9619ee`
`confusions.json`、`voice-confusions.json`をそのまま取得して、比較する語の候補に使う。表自体はこのリポジトリに同梱しない。

出典：京都大学言語メディア研究室、日本語Wikipedia入力誤りデータセット（JWTD）v2 train。元の文章の著作者はWikipedia執筆者。表の作成者はumiyosh。
田中佑・村脇有吾・河原大輔・黒橋禎夫「日本語 Wikipedia の編集履歴に基づく入力誤りデータセットと訂正システムの改良」言語処理学会第27回年次大会、2021。
音声の表にはMozilla Common Voice（CC0）由来の取り違えも含まれる。個々の出典と作成手順は配布元のカードを参照。

CC BY-SA 3.0：<https://creativecommons.org/licenses/by-sa/3.0/>
この表を改変・再配布する場合は出典・変更の明示と同じライセンスの条件を維持する。本文・音声の元データは本アプリで取得・再配布しない。

## ライブラリ

- Transformers：Apache-2.0 / <https://github.com/huggingface/transformers>
- PyTorch：BSD系 / <https://github.com/pytorch/pytorch/blob/main/LICENSE>
- SudachiPy：Apache-2.0 / <https://github.com/WorksApplications/SudachiPy>
- SudachiDict：<https://github.com/WorksApplications/SudachiDict> のLEGAL・NOTICEを参照。
- Streamlit：Apache-2.0 / <https://github.com/streamlit/streamlit/blob/develop/LICENSE>

インストールした各パッケージのライセンス・NOTICEを保持する。

## 自作データ

`sample.py`、`data/evaluation.json`は本アプリ用に作成した架空文。実際の履歴・業務情報は使用しない。
評価文には公開の誤変換パターンと重なるものがあり、モデルの学習元との非重複は確認できない。
