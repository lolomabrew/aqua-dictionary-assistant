"""Find unintended conversion suspects; never list a word merely for frequency."""
from __future__ import annotations
from functools import lru_cache
import re
import unicodedata
from context_model import (ContextModels, DETECTOR_ID, CORRECTOR_ID,
                           DETECTION_THRESHOLD, CONTEXT_THRESHOLD)

VERSION='0.2.0'
MAX_CHARS=20000
MAX_KNOWN=200
DEFAULT_CONTEXT_LIMIT=60

@lru_cache(maxsize=1)
def load_model():
    return ContextModels()


def normalize(text):
    return re.sub(r'\s+','',unicodedata.normalize('NFKC',text)).casefold()


def parse_known(text):
    terms=list(dict.fromkeys(x.strip() for x in text.splitlines() if x.strip()))
    if len(terms)>MAX_KNOWN:
        raise ValueError('既存の辞書は200語以内で入力してください。')
    if any(not 1<=len(x)<=40 for x in terms):
        raise ValueError('既存の辞書は1行1語、各1〜40文字にしてください。')
    return terms


def analyze(text,known_text='',model=None,progress=None,max_context_spans=DEFAULT_CONTEXT_LIMIT):
    if not text.strip():
        raise ValueError('分析する文章を貼り付けてください。')
    if len(text)>MAX_CHARS:
        raise ValueError('文章は20,000文字以内にしてください。')
    if not 0<=max_context_spans<=200:
        raise ValueError('文脈比較の上限は0〜200件です。')
    known=parse_known(known_text)
    model=model or load_model()
    with model.lock:
        detected=model.detect(text,progress)
        spans=model.spans(text,detected)
        # Only spend contextual scoring on words with actual lexical alternatives.
        viable=[(a,b) for a,b in spans if max([detected.get(j,0.) for j in range(a,b)] or [0.])>=.05 and model.alternatives(text[a:b],known)]
        checked=set(viable[:max_context_spans])
        raw=[]
        for i,(start,end) in enumerate(viable[:max_context_spans]):
            p=max([detected.get(j,0.) for j in range(start,end)] or [0.])
            suggestions=model.propose(text,start,end,known)
            best=max([s['context_gain'] for s in suggestions] or [0.])
            positive=[s for s in suggestions if s['context_gain']>=max(CONTEXT_THRESHOLD,best-4.0)]
            if p>=DETECTION_THRESHOLD or positive:
                raw.append({'start':start,'end':end,'probability':p,'suggestions':positive,
                            'basis':'検出モデルと文脈比較' if p>=DETECTION_THRESHOLD and positive else ('文脈比較モデル' if positive else '誤変換検出モデル')})
            if progress:
                progress(.3+.7*(i+1)/max(1,min(len(viable),max_context_spans)),'怪しい表記と修正候補を文脈で比較しています')
        # Preserve high detector marks even if correction candidates are unknown
        # or the contextual comparison budget was reached.
        for start,end in spans:
            p=max([detected.get(j,0.) for j in range(start,end)] or [0.])
            if (start,end) not in checked and p>=DETECTION_THRESHOLD:
                raw.append({'start':start,'end':end,'probability':p,'suggestions':[], 'basis':'誤変換検出モデル'})
        # Prefer a longer error span with a correction, suppress duplicate marks.
        raw.sort(key=lambda x:(not bool(x['suggestions']),-(x['end']-x['start']),-x['probability'],x['start']))
        accepted=[]
        for item in raw:
            if not any(item['start']<x['end'] and item['end']>x['start'] for x in accepted):
                accepted.append(item)
        grouped={}
        registered={normalize(t) for t in known}
        for item in sorted(accepted,key=lambda x:x['start']):
            a,b=item['start'],item['end']
            core=text[a:b]
            proposals=[]
            expanded_end=b
            original=core
            for suggestion in item['suggestions']:
                original,full,expanded_end=model.expand(text,a,b,suggestion['term'])
                proposals.append({**suggestion,'term':full,'registered':normalize(full) in registered})
            key=(original,tuple(s['term'] for s in proposals))
            group=grouped.setdefault(key,{'original':original,'core':core,'suggestions':proposals,'count':0,'examples':[],
                                         'detector_score':round(item['probability'],4),'basis':item['basis']})
            group['count']+=1
            group['detector_score']=max(group['detector_score'],round(item['probability'],4))
            group['examples'].append({'position':a+1,'start':a,'end':expanded_end,
                                      'text':text[max(0,a-35):min(len(text),expanded_end+45)].replace('\n',' ')})
        result={'version':VERSION,'models':[DETECTOR_ID,CORRECTOR_ID],'characters':len(text),
                'context_checked':len(checked),'context_total':len(viable), 'context_limit_reached':len(viable)>len(checked),
                'candidates':list(grouped.values())}
        if progress:
            progress(1.,'分析が終わりました')
        return result


def dictionary_export(terms):
    clean=list(dict.fromkeys(t.strip() for t in terms if t.strip()))
    if any('\n' in t or '\r' in t or len(t)>40 for t in clean):
        raise ValueError('登録語は改行を含まない40文字以内の語にしてください。')
    return '\n'.join(clean)+('\n' if clean else '')
