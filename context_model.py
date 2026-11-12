"""Japanese misconversion detection and contextual scoring, all in this process.

Candidate words come from a public confusion lexicon/readings. Models decide
whether an occurrence is suspicious and which alternative fits its context.
No user sentence is sent to an inference API, nor used to train a model.
"""
from __future__ import annotations
from collections import defaultdict
from difflib import SequenceMatcher
from functools import lru_cache
import json
import re
import threading

DETECTOR_ID = 'umiyosh/modernbert-ja-130m-typo-detector'
DETECTOR_REVISION = '822bfc9df5b556237a7b92139861be5b43bc3fbc'
CORRECTOR_ID = 'umiyosh/modernbert-ja-130m-homophone-scorer'
CORRECTOR_REVISION = '00f1a531c55bae03502a58967df9dee2fade4e62'
LEXICON_ID = 'umiyosh/jwtd-misconversion-table'
LEXICON_REVISION = '5822e4ec72e61d48a29f2cb7ca7add33fc9619ee'
DETECTION_THRESHOLD = .995
CONTEXT_THRESHOLD = 7.0


class ContextModels:
    def __init__(self):
        import os
        os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
        import torch
        from transformers import AutoTokenizer, AutoModelForTokenClassification, AutoModelForMaskedLM
        from huggingface_hub import hf_hub_download
        from sudachipy import dictionary, tokenizer
        torch.set_num_threads(4)
        self.torch = torch
        self.lock = threading.RLock()
        self.tokenizer = AutoTokenizer.from_pretrained(DETECTOR_ID, revision=DETECTOR_REVISION)
        self.detector = AutoModelForTokenClassification.from_pretrained(DETECTOR_ID, revision=DETECTOR_REVISION, use_safetensors=True, attn_implementation='eager').eval()
        self.corrector = AutoModelForMaskedLM.from_pretrained(CORRECTOR_ID, revision=CORRECTOR_REVISION, use_safetensors=True, attn_implementation='eager').eval()
        other = AutoTokenizer.from_pretrained(CORRECTOR_ID, revision=CORRECTOR_REVISION)
        if self.tokenizer.get_vocab() != other.get_vocab():
            raise RuntimeError('検出モデルと採点モデルの語彙が一致しません。')
        self.sudachi = dictionary.Dictionary().create()
        self.mode_a = tokenizer.Tokenizer.SplitMode.A
        self.mode_c = tokenizer.Tokenizer.SplitMode.C
        self.confusions = defaultdict(set)
        self.frequency = defaultdict(int)
        for name in ('confusions.json','voice-confusions.json'):
            path = hf_hub_download(LEXICON_ID, name, repo_type='dataset', revision=LEXICON_REVISION)
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            for term, entry in data.items():
                self.confusions[term].update(entry['to'])
                self.frequency[term] += entry['kept']
                for target in entry['to']:
                    self.frequency[target] += entry['wrong']
        self.by_reading = defaultdict(set)
        self.near_reading = defaultdict(set)
        for word in self.frequency:
            if 1 <= len(word) <= 8 and re.fullmatch(r'[一-龯ぁ-んァ-ヶー]+',word):
                yomi=self.reading(word)
                self.by_reading[yomi].add(word)
                for i in range(len(yomi)):
                    self.near_reading[(len(yomi),yomi[:i]+yomi[i+1:])].add(yomi)

    @lru_cache(maxsize=100000)
    def reading(self, word):
        return ''.join(t.reading_form() for t in self.sudachi.tokenize(word,self.mode_c))

    def sentence_windows(self,text):
        """Exact source offsets and at most 62 content tokens per detector window."""
        for match in re.finditer(r'[^。！？!?\n]+[。！？!?]?|[。！？!?]',text):
            start,end=match.span()
            sentence=text[start:end]
            enc=self.tokenizer(sentence,add_special_tokens=False,return_offsets_mapping=True)
            offsets=enc['offset_mapping']
            if len(offsets)<=62:
                yield start,sentence
            else:
                # Overlap 12 tokens: no silent truncation, merge repeated marks later.
                for i in range(0,len(offsets),50):
                    window=offsets[i:i+62]
                    a,b=window[0][0],window[-1][1]
                    if b>a:
                        yield start+a,sentence[a:b]
                    if i+62>=len(offsets):
                        break

    def detect(self,text,progress=None):
        detected={}
        windows=list(self.sentence_windows(text))
        for i,(offset,part) in enumerate(windows):
            enc=self.tokenizer(part,return_offsets_mapping=True,return_tensors='pt')
            offsets=enc.pop('offset_mapping')[0].tolist()
            with self.torch.inference_mode():
                scores=self.detector(**enc).logits.softmax(-1)[0,:,1].tolist()
            for (a,b),score in zip(offsets,scores):
                for position in range(a+offset,b+offset):
                    detected[position]=max(detected.get(position,0.),score)
            if progress:
                progress(.3*(i+1)/max(1,len(windows)),'全文から誤変換の疑いを調べています')
        return detected

    def spans(self,text,detected):
        result={}
        for offset in range(0,len(text),1000):
            tokens=list(self.sudachi.tokenize(text[offset:offset+1000],self.mode_a))
            for j,token in enumerate(tokens):
                a,b=offset+token.begin(),offset+token.end()
                word=text[a:b]
                if token.part_of_speech()[0] not in {'名詞','形状詞','副詞','形容詞'} or not re.fullmatch(r'[一-龯ぁ-んァ-ヶー]{1,6}',word):
                    continue
                result[(a,b)]=None
                if j+1<len(tokens):
                    nxt=tokens[j+1]
                    if nxt.begin()==token.end() and nxt.part_of_speech()[0]=='名詞' and len(word+nxt.surface())<=6:
                        combined=word+nxt.surface()
                        if combined in self.confusions or token.is_oov() or len(word)==1:
                            result[(a,offset+nxt.end())]=None
        for pos,score in detected.items():
            if score>=DETECTION_THRESHOLD and not any(a<=pos<b for a,b in result):
                result[(pos,pos+1)]=None
        return sorted(result,key=lambda ab:(-max([detected.get(i,0.) for i in range(*ab)] or [0]),ab[0],-(ab[1]-ab[0])))

    def alternatives(self,word,known=()):
        yomi=self.reading(word)
        direct=set(self.confusions.get(word,()))
        readings={yomi}
        for i in range(len(yomi)):
            readings.update(self.near_reading.get((len(yomi),yomi[:i]+yomi[i+1:]),()))
        exact=set(self.by_reading[yomi])
        extra=set(known)
        ranked=list(sorted(direct,key=lambda w:-self.frequency.get(w,0)))[:6]
        ranked+=sorted(exact,key=lambda w:-self.frequency.get(w,0))[:6]
        # Diversify near readings: frequent unrelated homophones must not crowd
        # out a vowel-confusion alternative (e.g. ジシャ vs ジショ).
        def common_prefix(a,b):
            return next((i for i,(x,y) in enumerate(zip(a,b)) if x!=y),min(len(a),len(b)))
        kana_groups=['アイウエオ','カキクケコ','ガギグゲゴ','サシスセソ','ザジズゼゾ','タチツテト','ダヂヅデド','ナニヌネノ','ハヒフヘホ','バビブベボ','パピプペポ','マミムメモ','ヤユヨ','ャュョ','ラリルレロ','ワヰヱヲ']
        def near_sound(a,b):
            differences=[(x,y) for x,y in zip(a,b) if x!=y]
            return len(a)==len(b) and len(differences)==1 and any(differences[0][0] in g and differences[0][1] in g for g in kana_groups)
        for read in sorted((r for r in readings-{yomi} if near_sound(yomi,r)),key=lambda r:(-common_prefix(yomi,r),r)):
            ranked+=sorted(self.by_reading[read],key=lambda w:-self.frequency.get(w,0))[:2]
        ranked+=sorted(extra)
        return list(dict.fromkeys(w for w in ranked if w!=word and 1<=len(w)<=8))[:28]

    def pll(self,text,start,end):
        """Sum tokenwise pseudo-log-likelihood of word and three neighbors each side.

        Each target is masked separately, as prescribed by the scorer model card.
        A 32-token context keeps inference memory bounded. No text-keyed cache.
        """
        torch=self.torch
        enc=self.tokenizer(text,return_offsets_mapping=True)
        ids=enc['input_ids']; offsets=enc['offset_mapping']
        targets=[i for i,(a,b) in enumerate(offsets) if b>start and a<end and b>a]
        if not targets:
            return None
        first,last=min(targets),max(targets)
        lo=max(1,first-max(0,(30-(last-first+1))//2))
        hi=min(len(ids)-1,lo+30)
        lo=max(1,hi-30)
        window=[ids[0]]+ids[lo:hi]+[ids[-1]]
        selected=[i-lo+1 for i in range(max(lo,first-3),min(hi,last+4))]
        if not selected:
            return None
        x=torch.tensor([window]*len(selected))
        original=x[torch.arange(len(selected)),torch.tensor(selected)].clone()
        x[torch.arange(len(selected)),torch.tensor(selected)]=self.tokenizer.mask_token_id
        total=0.
        with torch.inference_mode():
            for batch_start in range(0,len(selected),4):
                part=x[batch_start:batch_start+4]
                out=self.corrector(input_ids=part,attention_mask=torch.ones_like(part)).logits
                positions=torch.tensor(selected[batch_start:batch_start+4])
                logp=out[torch.arange(len(part)),positions].log_softmax(-1)
                total+=float(logp[torch.arange(len(part)),original[batch_start:batch_start+4]].sum())
        return total

    def propose(self,text,start,end,known=()):
        original=text[start:end]
        alternatives=self.alternatives(original,known)
        if not alternatives:
            return []
        # Bound character context too: tokenizer still chooses a 32-token window.
        lo,hi=max(0,start-100),min(len(text),end+100)
        context=text[lo:hi]; a,b=start-lo,end-lo
        baseline=self.pll(context,a,b)
        if baseline is None:
            return []
        proposals=[]
        for alternative in alternatives:
            changed=context[:a]+alternative+context[b:]
            score=self.pll(changed,a,a+len(alternative))
            if score is None:
                continue
            proposals.append({'term':alternative,'context_gain':round(score-baseline,3),
                              'reading_similarity':round(SequenceMatcher(None,self.reading(original),self.reading(alternative)).ratio(),3)})
        return sorted(proposals,key=lambda x:-(x['context_gain'] + (2.0 if x['reading_similarity']==1 else 0.)))[:3]

    def expand(self,text,start,end,term):
        lo,hi=max(0,start-12),min(len(text),end+16)
        tokens=list(self.sudachi.tokenize(text[lo:hi],self.mode_a))
        right=end
        for token in tokens:
            a,b=lo+token.begin(),lo+token.end()
            if a==right and token.part_of_speech()[0]=='名詞' and b-start<=10:
                right=b
        return text[start:right],term+text[end:right],right
