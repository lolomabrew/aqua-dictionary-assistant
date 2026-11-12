# 公開手順

公開先の構成：GitHub（コード）→ Streamlit Community Cloud（Python実行）→ `*.streamlit.app`（利用者のURL）。
2026-11-12：GitHub公開とStreamlit Community Cloudへのデプロイ、公開版のサンプル動作確認まで完了。

公開アプリ：<https://aqua-dictionary-assistant.streamlit.app/>

## 1. GitHub（完了）

- 公開リポジトリ：<https://github.com/lolomabrew/aqua-dictionary-assistant>
- アップロード済み：このフォルダ内のコード、設定、架空サンプル・回帰評価文、評価結果、説明書。
- 対象外：仮想環境、元のキカガク課題フォルダ、添付、実際の履歴、認証情報、モデル重み。
- モデル2つと候補表は初回起動時に配布元から取得する。
- Linux/Python 3.12の自動検証：[実行結果](https://github.com/lolomabrew/aqua-dictionary-assistant/actions/runs/43140504385)（7件の動作検証・架空データ評価とも成功）。

以後の修正はこのリポジトリへpushする。新規作成やgit initを繰り返さない。

## 2. Streamlit Community Cloud（配置済み）

1. <https://share.streamlit.io/> にサインイン。GitHubとの必要な連携を設定する。
2. Create appで上記リポジトリ、ブランチ`main`、ファイル`app.py`を選ぶ。
3. Advanced settingsでPython **3.12**を指定する。
4. Secretsは不要。デプロイし、公開URLを記録する。
5. 共有設定を、サインイン不要で第三者が利用できる状態にする。

アカウント作成・規約への同意・新たな権限付与が必要な場合は本人が確認する。

## 3. 公開後チェック

- サインアウトしたブラウザーでURLを開ける。
- 架空サンプルを入れ、分析ボタンで候補が表示される。
- 正しい表記の確認→必要な編集→本人確認のチェック→テキスト保存が動く。
- 入力変更後に古い結果の警告が出る。
- 再起動後も依存パッケージとモデルが正常にロードされる。
- ローカルのStreamlitを停止しても公開URLが動く。
- モデル2つの重み・PyTorchの実行メモリが公開先の枠に収まるか実測する。無料枠で動くとはまだ確認できていない。ローカルで動くことだけでクラウド上の動作保証とはしない。
- 公開版に実際の履歴や認証情報が含まれない。

公開URL・GitHub URLはREADME・REQUIREMENTS・提出原稿へ反映済み。提出PDFは別途作成する。確認した内容はVALIDATION.mdを参照。
