"""GiNZA learned NER + transparent vocabulary heuristics, with no inference API.

NER proposes names from context. Noun compounds/Latin extraction complement it.
Reading comparisons only suggest alternatives present in input/known vocabulary;
they never manufacture a correction or estimate an ASR error rate.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from functools import lru_cache
import math
import re
import unicodedata

MODEL = 'ja_ginza'
MAX_CHARS = 20000
MAX_KNOWN = 200
MAX_CANDIDATES = 160
VERSION = '0.1.0'
STOP = set('これ それ あれ ここ そこ こと もの ため よう 方 僕 私 自分 今日 明日 今週 来週 午前 午後 今回 次回 時間 場合 状態 内容 部分 感じ イメージ 確認 お願い 話 文章 メモ 候補 入力 画面 結果 機能 作業 通知 連絡 コード サンプル 会議 テンプレート 一覧 登録'.split())
EXCLUDED_ENTITIES = {'Date', 'Time', 'Period', 'Time_Expression', 'Numex', 'N_Person', 'N_Organization', 'N_Location', 'Rank', 'Percent', 'Money', 'Age', 'Frequency', 'Count', 'Ordinal_Number', 'Latitude_Longitude', 'Email', 'Phone_Number', 'Postal_Address', 'ID_Number', 'URL'}
LATIN = re.compile(r'(?<![A-Za-z0-9_])[A-Za-z][A-Za-z0-9_+.#-]{1,29}(?:[ ][A-Z][A-Za-z0-9_+.#-]{1,19})?(?![A-Za-z0-9_])')


@lru_cache(maxsize=1)
def load_model():
    import spacy
    spacy.require_cpu()
    nlp = spacy.load(MODEL)
    if 'ner' not in nlp.pipe_names:
        raise RuntimeError('固有表現モデルが読み込まれていません。')
    return nlp


def normalize(text):
    return re.sub(r'[\s・･_-]+', '', unicodedata.normalize('NFKC', text)).casefold()


def reading(span):
    return ''.join((t.morph.get('Reading') or [t.text])[0] for t in span)


def chunks(text):
    # Keep every character and exact offsets. Avoid GiNZA's long-sentence limits.
    start = 0
    while start < len(text):
        end = min(start + 800, len(text))
        if end < len(text):
            break_at = max(text.rfind('。', start, end), text.rfind('\n', start, end))
            if break_at > start:
                end = break_at + 1
        yield start, text[start:end]
        start = end


def parse_known(text):
    terms = list(dict.fromkeys(x.strip() for x in text.splitlines() if x.strip()))
    if len(terms) > MAX_KNOWN:
        raise ValueError('既存の辞書は200語以内で入力してください。')
    if any(len(x) > 40 or len(x) < 2 for x in terms):
        raise ValueError('既存の辞書は1行1語、各2〜40文字にしてください。')
    return terms


def valid_term(term):
    return (2 <= len(term) <= 30 and term not in STOP
            and bool(re.search(r'[A-Za-zぁ-んァ-ヶ一-龯]', term))
            and not re.search(r'[\n\r@/:：。！？!?、,]', term)
            and not re.fullmatch(r'[\d\W]+', term))


def analyze(text, known_text='', nlp=None, use_ner=True):
    if not text.strip():
        raise ValueError('分析する文章を貼り付けてください。')
    if len(text) > MAX_CHARS:
        raise ValueError('文章は20,000文字以内にしてください。')
    known = parse_known(known_text)
    nlp = nlp or load_model()
    items = {}
    entity_count = 0

    def add(term, yomi, source, offset, entity=None):
        term = term.strip()
        if not valid_term(term):
            return
        item = items.setdefault(term, {'term': term, 'reading': yomi, 'sources': set(), 'entities': set(), 'offsets': set()})
        item['sources'].add(source)
        item['offsets'].add(offset)
        if entity:
            item['entities'].add(entity)

    docs = list(nlp.pipe([s for _, s in chunks(text)], batch_size=8))
    for (offset, part), doc in zip(chunks(text), docs):
        if use_ner:
            for ent in doc.ents:
                if ent.label_ not in EXCLUDED_ENTITIES:
                    add(ent.text, reading(ent), '学習済みモデルの固有表現', offset + ent.start_char, ent.label_)
                    entity_count += 1
        for token in doc:
            if token.pos_ == 'PROPN':
                add(token.text, reading(doc[token.i:token.i + 1]), '形態素の固有名詞', offset + token.idx)
        # Compound nouns: context-free backup, explicitly separate from learned NER.
        run = []
        def flush():
            if run:
                span = doc[run[0].i:run[-1].i + 1]
                add(span.text, reading(span), '名詞の連続', offset + span.start_char)
                run.clear()
        for token in doc:
            if token.pos_ in {'NOUN', 'PROPN'} and not token.is_space:
                if run and (len(run) >= 5 or token.idx > run[-1].idx + len(run[-1])):
                    flush()
                run.append(token)
            else:
                flush()
        flush()
        for match in LATIN.finditer(part):
            span = doc.char_span(match.start(), match.end(), alignment_mode='expand')
            add(match.group(), reading(span) if span is not None else match.group(), '英字表記', offset + match.start())

    for item in items.values():
        term = item['term']
        # Literal matches, not number of recognizer mistakes. Enforce Latin boundaries.
        pattern = re.escape(term)
        if re.fullmatch(r'[A-Za-z0-9_+.# -]+', term):
            pattern = r'(?<![A-Za-z0-9_])' + pattern + r'(?![A-Za-z0-9_])'
        matches = list(re.finditer(pattern, text))
        item['count'] = len(matches)
        item['examples'] = [{'position': m.start() + 1, 'text': text[max(0, m.start()-24):min(len(text), m.end()+36)].replace('\n', ' ')} for m in matches[:3]]
        item['score'] = round(30 * bool(item['entities']) + 12 * math.log2(1 + item['count']) + 10 * ('英字表記' in item['sources']) + 8 * ('形態素の固有名詞' in item['sources']), 1)
    ordered = sorted(items.values(), key=lambda x: (-x['score'], x['term']))
    truncated = len(ordered) > MAX_CANDIDATES
    ordered = ordered[:MAX_CANDIDATES]
    known_readings = {t: reading(nlp.make_doc(t)) for t in known}
    known_norms = {normalize(t) for t in known}

    for item in ordered:
        alternatives = []
        for term, yomi in list(known_readings.items()) + [(x['term'], x['reading']) for x in ordered if x['count'] >= 2]:
            if term == item['term']:
                continue
            same = normalize(term) == normalize(item['term'])
            left, right = normalize(item['reading']), normalize(yomi)
            ratio = SequenceMatcher(None, left, right).ratio()
            # Similar pronunciation alone is not proof. Reject substring pairs.
            phonetic = (min(len(left), len(right)) >= 4 and ratio >= .80
                        and left not in right and right not in left)
            if same or phonetic or (left == right and len(left) >= 3):
                alternatives.append({'term': term, 'basis': '表記が近い' if same else '読みが近い', 'known': term in known_readings, 'similarity': round(ratio, 3)})
        unique = {a['term']: a for a in alternatives}
        item['alternatives'] = sorted(unique.values(), key=lambda a: (-a['known'], -a['similarity'], a['term']))[:3]
        item['registered'] = normalize(item['term']) in known_norms
        reasons = []
        if item['entities']:
            reasons.append('モデルが固有表現として抽出')
        if '英字表記' in item['sources']:
            reasons.append('英字の名称・略語候補')
        if item['count'] >= 2:
            reasons.append(f"原文に{item['count']}回出現")
        if item['alternatives']:
            reasons.append('読みや表記の近い語あり（要確認）')
            item['score'] += 20
        item['reasons'] = reasons or ['名詞のまとまり。登録の必要性を確認']
        item['sources'] = sorted(item['sources'])
        item['entities'] = sorted(item['entities'])
        del item['offsets']
    ordered.sort(key=lambda x: (-x['score'], x['term']))
    # Single common nouns are low value; keep names, Latin, repeats and variants.
    selected = [x for x in ordered if x['entities'] or '英字表記' in x['sources'] or '形態素の固有名詞' in x['sources'] or x['count'] >= 2 or x['alternatives']]
    return {'version': VERSION, 'model': MODEL, 'characters': len(text), 'entity_mentions': entity_count, 'candidate_limit_reached': truncated, 'candidates': selected}


def dictionary_export(terms):
    clean = list(dict.fromkeys(t.strip() for t in terms if t.strip()))
    if any('\n' in t or '\r' in t or len(t) > 40 for t in clean):
        raise ValueError('登録語は改行を含まない40文字以内の語にしてください。')
    return '\n'.join(clean) + ('\n' if clean else '')
