# 誤変換を見つける辞書アシスト

音声入力で**自分の意図と違う変換が起きた箇所をモデルに特定させ、人間が正しい言葉を辞書登録して次回以降の誤変換を減らす**ためのアプリ。
Aqua Voiceとは独立した非公式の支援ツールです。

## 使い方

1. 音声入力の履歴をまとめてコピペする。正しい表記・修正前後の学習データは不要。
2. 「意図しない変換を探す」を押す。
3. 原文の怪しい表記、文脈から推定した修正候補、原文を確認する。
4. 「意図した正しい表記」を必要なら編集し、意図と合っているかチェックする。
5. 確認した正しい言葉だけをコピー・保存し、Aqua Voice等の辞書へ**人間が登録する**。

例（架空文。推論には正しい表記を渡さない）：

| 原文 | 修正候補 |
|---|---|
| Aqua Voiceの自社登録に単語を追加して誤変換を防ぎたいです。 | 自社登録 → 辞書登録 |
| 概論ではなく格論から説明してください。 | 格論 → 各論 |
| これは日本語の誤植を検出する真相学習モデルです。 | 真相学習モデル → 深層学習モデル |

頻出語や固有名詞という理由だけで一覧を出す旧版（v0.1）から、文脈内の誤変換を推定する版（v0.2）へ変更しました。見つけられない場合は「見つけられなかった」と表示し、一般的な単語一覧で代用しません。

## 実行

Python 3.12。初回はモデル2つと候補表をダウンロードするためネット接続・ディスク容量が必要です。その後の推論はPythonプロセス内のCPUで行い、外部AI推論API・APIキーは使いません。

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

## モデルが判断する部分

`context_model.py`で以下を読み込み、`analyzer.py`が推論を組み合わせます。重みは公開学習済みのものを再利用し、独自の追加学習は行っていません。

- **誤変換箇所の検出**：`umiyosh/modernbert-ja-130m-typo-detector`。音声入力の同音語の取り違え等で学習されたトークン分類モデル。
- **修正候補の文脈比較**：`umiyosh/modernbert-ja-130m-homophone-scorer`。原文と別の語を入れた文について、語と前後3トークンを1つずつマスクした擬似対数尤度を比較するモデル。
- モデルは`AutoModelForTokenClassification` / `AutoModelForMaskedLM`で自コードへ読み込んで実行。リビジョンを固定し、`trust_remote_code`は使用しません。

## 辞書・ルールが担当する部分

- 公開取り違え表（JWTD由来、音声の取り違えを含む）とSudachiの読み情報から、**比較する語**を集める。
- 同音語、公開表の候補、同じかな行内の1文字の違いを候補にする。候補表だけでは誤りと判定しない。
- 既存の辞書は任意。入力時は候補に補い、登録済みの語を表示する。
- 検出モデルの値が0.05以上の語を文脈比較へ回す。最終的な表示は、検出モデル0.995以上、または文脈スコア差7.0以上。
- 修正候補は最大3語。読みが一致する語の順位に2点の補助を付け、最高の文脈スコアから4点以内かつ7.0以上の候補を表示する。点数は本人の意図や正しさの確率ではない。
- 同音の候補を集める処理と、文脈内で誤りを判断するモデル推論を区別している。

上記閾値の基本値は配布モデルの利用例に基づく設計値。Aqua Voiceの実際の履歴で最適化した値ではありません。

## 上限と限界

入力上限20,000文字。全文を文単位・最大62内容トークンの窓で検出し、長文は12トークン重ねて分割します。原文の位置を保持し、黙って末尾を切り捨てません。
修正候補の詳しい文脈比較は最大60箇所。超過時は画面で通知します。比較しきれない箇所も、検出モデルで高い疑いが出たものは修正候補なしで表示します。

- テキストだけでは本人の意図や実際の音声を確定できない。
- どちらでも文が通る同音異義語、未知の固有名詞、大きく読みの違う聞き違いには弱い。
- 比較する正しい語が候補表や読み辞書にないと、検出できても正解を提案できない。
- 正しい語を誤って疑うこともある。チェックを入れた語だけを持ち出し、自動修正・辞書の自動変更は行わない。
- 辞書登録による認識改善の効果そのものは未検証。

## データとプライバシー

同梱サンプルと回帰評価文は自作の架空文。ユーザーの添付・実際の音声履歴・個人情報・業務内容は同梱しません。
公開版には個人情報・職場の業務情報を入力しないでください。
入力本文のファイル・DB保存や本文ログ出力は実装していません。入力と結果はセッションメモリに保持され、公開版ではホスティング先へ送信されます。
出力は確認した単語だけのテキストです。一括インポート形式の対応を意味しません。

## 検証

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python evaluate.py
.venv/bin/python -m pip check
```

誤り箇所の検出、修正候補、正しい文への誤警告を測ります。旧版の「登録対象語の抽出精度」は今回の目的の評価には使いません。
`VALIDATION.md` / `evaluation-results.json`を参照。架空文は開発中の修正にも使った回帰データで、未使用のホールドアウトや実際のAqua Voiceでの精度を示しません。

## 公開・提出の状態

公開アプリ：<https://aqua-dictionary-assistant.streamlit.app/>

GitHubへ公開済み：<https://github.com/lolomabrew/aqua-dictionary-assistant>

ローカル実装と[GitHub上のLinux検証](https://github.com/lolomabrew/aqua-dictionary-assistant/actions/runs/43140504385)に加え、Streamlit Community Cloudでの入力→モデル推論→結果表示→本人確認→単語保存を確認済み。提出PDFは原稿段階で、未提出。
GitHubはコード保管先。Pythonの実行先はStreamlit Community Cloud等が必要で、GitHub Pagesだけでは動きません。
公開先のPython 3.12 / CPU環境でモデル2つの取得・読み込みと、架空サンプルの推論を確認済み。長文や同時アクセスの負荷試験は未実施。
`DEPLOY.md`、`REQUIREMENTS.md`、`SUBMISSION_DRAFT.md`に残作業を記録しています。

## 出典

- [検出モデル](https://huggingface.co/umiyosh/modernbert-ja-130m-typo-detector) / [文脈比較モデル](https://huggingface.co/umiyosh/modernbert-ja-130m-homophone-scorer)（MIT、元モデルSB Intuitions ModernBERT）
- [公開取り違え表](https://huggingface.co/datasets/umiyosh/jwtd-misconversion-table)（CC BY-SA 3.0）
- [SudachiPy / SudachiDict](https://github.com/WorksApplications/SudachiDict)
- [Aqua Voice Dictionary](https://aquavoice.com/guide/dictionary)
- [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)

詳しいクレジット・ライセンスは`THIRD_PARTY_NOTICES.md`。
