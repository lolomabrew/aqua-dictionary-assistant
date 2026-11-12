import streamlit as st
from analyzer import analyze, dictionary_export, load_model
from sample import SAMPLE

st.set_page_config(page_title='ことばの辞書候補', page_icon='📖', layout='wide')
st.markdown('''<style>
.block-container {max-width: 1120px; padding-top: 2.6rem;}
h1 {letter-spacing: -.04em;}
div[data-testid="stMetric"] {background:#EEEFEA;padding:18px;border-radius:12px;}
div[data-testid="stTextArea"] textarea {line-height:1.8;}
</style>''', unsafe_allow_html=True)
st.caption('音声入力を、少しずつ使いやすく。')
st.title('ことばの辞書候補')
st.write('音声入力の履歴を貼ると、辞書に登録したい名称や、確認したい表記の候補を見つけます。')
st.info('公開版には架空の文章を入力してください。個人情報・職場の業務情報は入力しないでください。')

if 'transcript' not in st.session_state:
    st.session_state.transcript = ''
if 'known_terms' not in st.session_state:
    st.session_state.known_terms = ''
left, right = st.columns([3, 1])
with left:
    st.subheader('1. 履歴を貼り付ける')
with right:
    if st.button('架空のサンプルで試す', use_container_width=True):
        st.session_state.transcript = SAMPLE
        st.session_state.known_terms = '辞書登録'
        st.session_state.pop('result', None)
text = st.text_area('音声入力の履歴', key='transcript', height=260, max_chars=20000,
                    placeholder='複数の履歴をまとめて、そのまま貼り付けてください。最大20,000文字。')
with st.expander('既存の辞書と照合する（任意）'):
    st.text_area('登録済みの正しい表記を1行に1語', key='known_terms', height=120,
                 help='未入力でも分析できます。入力すると登録済みの語を区別し、似た読みの語と照合します。最大200語。')
st.caption('文章だけでは誤認識を断定できません。表示するのは登録・確認の候補です。')

@st.cache_resource(show_spinner=False)
def model():
    return load_model()

if st.button('辞書候補を見つける', type='primary', disabled=not text.strip()):
    try:
        with st.spinner('文章から名称や表記の候補を探しています…'):
            result = analyze(text, st.session_state.known_terms, model())
        st.session_state.result = result
        st.session_state.analyzed_input = (text, st.session_state.known_terms)
        st.session_state.run_id = st.session_state.get('run_id', 0) + 1
    except ValueError as exc:
        st.error(str(exc))
    except Exception:
        st.error('分析を完了できませんでした。文章を短くして再試行してください。サンプルでも失敗する場合は管理者にモデルの設定確認を依頼してください。')

if 'result' in st.session_state:
    result = st.session_state.result
    stale = st.session_state.analyzed_input != (text, st.session_state.known_terms)
    if stale:
        st.warning('入力が変わっています。以下は前回の結果です。再度分析してください。')
    candidates = result['candidates']
    a, b, c = st.columns(3)
    a.metric('登録・確認の候補', f'{len(candidates)} 語')
    b.metric('似た表記のある候補', f"{sum(bool(x['alternatives']) for x in candidates)} 語")
    c.metric('登録済みの候補', f"{sum(x['registered'] for x in candidates)} 語")
    st.subheader('2. 根拠を見て、登録する言葉を選ぶ')
    st.caption('優先順は登録の検討順です。正しさの確率や、誤認識の回数を示すものではありません。')
    show_registered = st.checkbox('登録済みの語も表示する', value=False)
    shown = [x for x in candidates if show_registered or not x['registered']]
    if result['candidate_limit_reached']:
        st.warning('候補が多いため、優先度の高い160語を対象に比較しました。履歴を分けると詳しく確認できます。')
    if not shown:
        st.info('新しい候補は見つかりませんでした。登録済みの表示を切り替えるか、別の文章を試してください。')
    page_size = 12
    pages = max(1, (len(shown) + page_size - 1) // page_size)
    page = st.number_input('候補のページ', min_value=1, max_value=pages, step=1, key=f"page-{st.session_state.run_id}-{show_registered}")
    prefix = f"run-{st.session_state.run_id}"
    for idx, item in enumerate(shown[(page-1)*page_size:page*page_size], (page-1)*page_size):
        label = '登録済み' if item['registered'] else ('似た語あり・要確認' if item['alternatives'] else '登録候補')
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{item['term']}**")
                st.caption(f"{label} ｜ 原文一致 {item['count']}回")
            with col2:
                st.checkbox('選ぶ', key=f"{prefix}-select-{item['term']}", disabled=stale)
            st.write(' / '.join(item['reasons']))
            if item['alternatives']:
                st.write('比較する表記：' + '、'.join(f"{a['term']}（{'既存の辞書' if a['known'] else '同じ履歴'}・{a['basis']}）" for a in item['alternatives']))
                st.caption('似ていても別の言葉の可能性があります。置き換えの自動適用は行いません。')
            for example in item['examples'][:2]:
                st.text(f"原文 {example['position']}文字目：…{example['text']}…")
            # Store editor values separately: Streamlit clears widget state on pagination.
            edit_key = f"{prefix}-edit-{item['term']}"
            saved_key = f"{prefix}-saved-{item['term']}"
            known_options = [a['term'] for a in item['alternatives'] if a['known']]
            default_term = known_options[0] if len(known_options) == 1 else item['term']
            if known_options:
                st.caption('既存辞書にある表記との比較です。既に登録済みなら追加は不要です。候補が意図した言葉か確認してください。')
            st.text_input('登録する表記（必要なら修正）', value=st.session_state.get(saved_key, default_term), key=edit_key, max_chars=40, disabled=stale)
            st.session_state[saved_key] = st.session_state[edit_key]
            with st.expander('抽出の根拠'):
                st.write('抽出方法：' + ' / '.join(item['sources']))
                if item['entities']:
                    st.write('モデルの分類：' + ', '.join(item['entities']))
    st.subheader('3. 確認した言葉を持ち出す')
    st.caption('ページを移動する前に、下の選択リストへ追加してください。')
    if st.button('このページの選択をリストへ追加', disabled=stale):
        saved = st.session_state.get(f'{prefix}-chosen', [])
        for item in shown[(page-1)*page_size:page*page_size]:
            if st.session_state.get(f"{prefix}-select-{item['term']}"):
                saved.append(st.session_state.get(f"{prefix}-saved-{item['term']}", item['term']))
        st.session_state[f'{prefix}-chosen'] = list(dict.fromkeys(saved))
    chosen = st.session_state.get(f'{prefix}-chosen', [])
    if chosen:
        st.code(dictionary_export(chosen), language=None)
        st.download_button('登録語をテキストで保存', dictionary_export(chosen), 'dictionary-candidates.txt', mime='text/plain', disabled=stale)
        if st.button('選択リストを空にする'):
            st.session_state[f'{prefix}-chosen'] = []
            st.rerun()
    else:
        st.caption('登録する語を選び、リストへ追加するとコピー・保存できます。')
    st.caption('Aqua VoiceのDictionaryに正しい表記を登録してください。このアプリから設定は変更しません。テキストの保存は一括インポートの対応を意味しません。')

with st.expander('このアプリについて・モデルと限界'):
    st.write('GiNZAの公開学習済みモデル ja_ginza 5.2.0をPython内で読み込み、固有表現を推論します。外部AI推論APIは使いません。英字・名詞・出現回数・読みの比較は補助ルールです。')
    st.write('誤認識の正解を生成するモデルではありません。既存の辞書または同じ履歴にある表記だけを比較します。辞書が空でも名称の候補は抽出しますが、未知の誤表記の正解は出せない場合があります。')
    st.write('入力のファイル保存・DB保存・本文のログ出力は実装していません。入力と結果はセッションのメモリに残ります。公開版では入力がホスティング先へ送信されます。')
    st.markdown('[GiNZA・モデルの出典とライセンス](https://github.com/megagonlabs/ginza/tree/v5.2.0) ｜ [Aqua Voice 辞書の説明](https://aquavoice.com/guide/dictionary)')
    st.caption('機械学習アプリ最終課題の試作品。公開URLでの動作確認と提出PDFの確定は別途必要です。')
