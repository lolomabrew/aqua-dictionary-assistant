import streamlit as st
from analyzer import analyze, dictionary_export, load_model, VERSION
from sample import SAMPLE

st.set_page_config(page_title='誤変換を見つける辞書アシスト',page_icon='🔎',layout='wide')
st.markdown('''<style>
.block-container{max-width:1120px;padding-top:2.6rem}h1{letter-spacing:-.04em}
div[data-testid="stMetric"]{background:#EEEFEA;padding:18px;border-radius:12px}
div[data-testid="stTextArea"] textarea{line-height:1.8}
</style>''',unsafe_allow_html=True)
st.caption('意図と違う変換を見つけて、次の音声入力に備える。')
st.title('誤変換を見つける辞書アシスト')
st.write('履歴の文脈から、意図しない変換の疑いと修正候補をモデルが推定します。確認した正しい言葉を、あなたの辞書に登録してください。')
st.info('公開版には架空の文章を入力してください。個人情報・職場の業務情報は入力しないでください。')
if st.session_state.get('app_version')!=VERSION:
    st.session_state.clear()
    st.session_state.app_version=VERSION
st.session_state.setdefault('transcript','')
st.session_state.setdefault('known_terms','')
left,right=st.columns([3,1])
with left:
    st.subheader('1. 音声入力の履歴を貼る')
with right:
    if st.button('架空のサンプルで試す',use_container_width=True):
        st.session_state.transcript=SAMPLE
        st.session_state.known_terms=''
        st.session_state.pop('result',None)
text=st.text_area('音声入力の履歴',key='transcript',height=240,max_chars=20000,
                  placeholder='複数の履歴をまとめて貼れます。正しい表記や、修正前後のデータの用意は不要です。')
with st.expander('登録済みの辞書を照合する（任意）'):
    st.text_area('登録済みの正しい表記を1行1語',key='known_terms',height=110,
                 help='空欄でも推定します。入力すると追加候補として比較し、登録済みかも表示します。最大200語。')
st.caption('音声や本人の意図がないため、誤変換は断定しません。人間が確認するための候補です。')

@st.cache_resource(show_spinner=False)
def model():
    return load_model()

if st.button('意図しない変換を探す',type='primary',disabled=not text.strip()):
    try:
        bar=st.progress(0,text='モデルを準備しています。初回はダウンロードに時間がかかります。')
        result=analyze(text,st.session_state.known_terms,model(),progress=lambda p,msg:bar.progress(p,text=msg))
        bar.empty()
        st.session_state.result=result
        st.session_state.analyzed_input=(text,st.session_state.known_terms)
        st.session_state.run_id=st.session_state.get('run_id',0)+1
    except ValueError as exc:
        st.error(str(exc))
    except Exception:
        st.error('分析を完了できませんでした。短い文章で再試行してください。初回のモデル取得にはインターネット接続が必要です。')

if 'result' in st.session_state:
    result=st.session_state.result
    stale=st.session_state.analyzed_input!=(text,st.session_state.known_terms)
    if stale:
        st.warning('入力が変わっています。以下は前回の結果です。再度分析してください。')
    candidates=result['candidates']
    a,b=st.columns(2)
    a.metric('誤変換の疑い',f'{len(candidates)} 種類')
    b.metric('修正候補を推定できたもの',f"{sum(bool(x['suggestions']) for x in candidates)} 種類")
    st.subheader('2. 意図した言葉か確認する')
    st.caption('頻出語や固有名詞という理由だけでは表示しません。同じ表記でも文脈ごとに判定します。')
    if result['context_limit_reached']:
        st.warning(f"全文の誤り検出は行いましたが、修正候補の詳しい比較は{result['context_checked']}箇所までです。履歴を分けると残りも比較できます。")
    if not candidates:
        st.success('今回の基準では、誤変換の疑いを見つけられませんでした。誤変換がないことを保証する結果ではありません。')
    prefix=f"run-{st.session_state.run_id}"
    for i,item in enumerate(candidates):
        with st.container(border=True):
            st.markdown(f"**原文の表記：{item['original']}**")
            st.caption(f"疑いとして検出した文脈：{item['count']}箇所")
            if item['suggestions']:
                st.write('意図した言葉の候補：'+' / '.join(s['term'] for s in item['suggestions']))
                st.caption('読みの近い別の語を入れた文と原文をモデルで比べ、文脈に合うと推定した候補です。')
            else:
                st.write('モデルは怪しい箇所を検出しましたが、十分に優位な修正候補は出せませんでした。意図した表記を入力できます。')
            for example in item['examples'][:3]:
                st.text(f"原文 {example['position']}文字目：…{example['text']}…")
            default=item['suggestions'][0]['term'] if item['suggestions'] else ''
            value=st.text_input('意図した正しい表記',value=default,key=f'{prefix}-term-{i}',max_chars=40,disabled=stale)
            st.checkbox('この表記が自分の意図と合っている',key=f'{prefix}-approve-{i}',disabled=stale or not value.strip())
            if any(s['registered'] for s in item['suggestions']):
                st.caption('候補の中に登録済みの語があります。重複登録は不要です。')
            with st.expander('判定の根拠と限界'):
                st.write('検出の根拠：'+item['basis'])
                st.write('文脈からの推定で、音声との照合結果ではありません。似た読みの別語が正しい場合や、候補が間違っている場合もあります。')
                if item['suggestions']:
                    st.caption('文脈スコアの差は正解の確率ではありません。')
                    for s in item['suggestions']:
                        st.text(f"{s['term']}：文脈スコア差 {s['context_gain']:.2f}、読みの類似度 {s['reading_similarity']:.2f}")
    st.subheader('3. 確認した正しい言葉を登録する')
    terms=[]
    for i in range(len(candidates)):
        if st.session_state.get(f'{prefix}-approve-{i}'):
            value=st.session_state.get(f'{prefix}-term-{i}','').strip()
            if value:
                terms.append(value)
    if terms:
        exported=dictionary_export(terms)
        st.code(exported,language=None)
        st.download_button('正しい表記をテキストで保存',exported,'confirmed-dictionary.txt',mime='text/plain',disabled=stale)
    else:
        st.caption('候補を確認してチェックすると、登録用の正しい表記だけをコピー・保存できます。')
    st.caption('Aqua VoiceのDictionaryへの登録は人間が行います。このアプリは原文やAqua Voiceの設定を自動変更しません。保存ファイルは単語リストです。')

with st.expander('モデル・データの出典と限界'):
    st.write('誤変換検出モデルと、同音語の文脈比較用モデル（ModernBERT）をこのアプリのPython内で実行します。外部AI推論APIは使いません。公開された取り違え表と読み辞書は、比較する語の候補を出すために使います。')
    st.write('未知の名前、読みの大きく違う聞き違い、音声がないと区別できない語は見逃すことがあります。見つけられない場合に、一般的な単語の一覧を代わりに表示することはありません。')
    st.write('本文のファイル・DB保存や本文ログ出力は実装していません。入力と結果はセッションメモリに残り、公開版ではホスティング先に送信されます。')
    st.markdown('[誤変換検出モデル・MIT](https://huggingface.co/umiyosh/modernbert-ja-130m-typo-detector) ｜ [文脈比較モデル・MIT](https://huggingface.co/umiyosh/modernbert-ja-130m-homophone-scorer) ｜ [候補表・CC BY-SA 3.0](https://huggingface.co/datasets/umiyosh/jwtd-misconversion-table)')
    st.caption('候補表の元データ：田中佑ほか「日本語 Wikipedia の編集履歴に基づく入力誤りデータセットと訂正システムの改良」(2021)。Wikipedia執筆者・京都大学言語メディア研究室。')
