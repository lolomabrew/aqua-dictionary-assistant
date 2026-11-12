# 公開手順

公開先の構成：GitHub（コード）→ Streamlit Community Cloud（Python実行）→ `*.streamlit.app`（利用者のURL）。
現在はローカルのみ。以下は公開承認後に実施する。

## 1. GitHub

- 候補：`lolomabrew/aqua-dictionary-assistant`（新規リポジトリ・public）。作成・公開は未実施。
- アップロード対象：このフォルダ内のコード、設定、架空サンプル・評価文、評価結果、説明書。
- 対象外：仮想環境、元のキカガク課題フォルダ、添付ファイル、実際の音声履歴、認証情報。
- ローカルの仮想環境はリポジトリ外。モデル重みと公開候補表もリポジトリへ直接入れず、初回起動時に配布元から取得する。

```sh
git init -b main
git add .
git commit -m "Build local-model dictionary candidate assistant"
gh repo create lolomabrew/aqua-dictionary-assistant --public --source . --remote origin --push
```

上記はコマンド例。既存リポジトリがある場合は実行せず、対象を再確認する。
GitHub Actionsがインストール、7つの検証、架空データ評価をLinux/Python 3.12で実行する。ワークフローは準備済みだが、GitHub上での実行は未確認。

## 2. Streamlit Community Cloud

1. <https://share.streamlit.io/> にサインイン。GitHubとの必要な連携を設定する。
2. Create appで上記リポジトリ、ブランチ`main`、ファイル`app.py`を選ぶ。
3. Advanced settingsでPython **3.12**を指定する。
4. Secretsは不要。デプロイし、公開URLを記録する。
5. 共有設定を、サインイン不要で第三者が利用できる状態にする。

アカウント作成・規約への同意・新たな権限付与が必要な場合は本人が確認する。

## 3. 公開後チェック

- サインアウトしたブラウザーでURLを開ける。
- 架空サンプルを入れ、分析ボタンで候補が表示される。
- 選択→表記編集→リスト追加→テキスト保存が動く。
- 入力変更後に古い結果の警告が出る。
- 再起動後も依存パッケージとモデルが正常にロードされる。
- ローカルのStreamlitを停止しても公開URLが動く。
- モデル2つの重み・PyTorchの実行メモリが公開先の枠に収まるか実測する。無料枠で動くとはまだ確認できていない。ローカルで動くことだけでクラウド上の動作保証とはしない。
- 公開版に実際の履歴や認証情報が含まれない。

合格後、README・REQUIREMENTS・提出資料のURLと状態を更新する。
