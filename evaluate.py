"""Measure error-span detection and correction; no frequency/NER benchmark."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import time
from analyzer import analyze,load_model
from context_model import DETECTOR_REVISION,CORRECTOR_REVISION,LEXICON_REVISION
ROOT=Path(__file__).resolve().parent

def evaluate():
    path=ROOT/'data/evaluation.json'
    fixture=json.loads(path.read_text())
    model=load_model()
    rows=[]
    for case in fixture['cases']:
        t=time.perf_counter()
        result=analyze(case['text'],model=model)
        gold=[]
        for error in case['errors']:
            start=case['text'].index(error['wrong'])
            gold.append((start,start+len(error['wrong']),error['correct']))
        detected=set()
        corrected=set()
        predictions=[]
        false_marks=0
        for item in result['candidates']:
            for ex in item['examples']:
                hits=[i for i,(a,b,_) in enumerate(gold) if ex['start']<b and ex['end']>a]
                detected.update(hits)
                if not hits:
                    false_marks+=1
                for i in hits:
                    if any(gold[i][2] in s['term'] for s in item['suggestions']):
                        corrected.add(i)
            predictions.append({'original':item['original'],'suggestions':[s['term'] for s in item['suggestions']], 'basis':item['basis']})
        row={'id':case['id'],'split':case['split'],'expected':case['errors'],'predictions':predictions,
             'errors':len(gold),'detected_errors':len(detected),'correct_in_top3':len(corrected),'false_marks':false_marks,
             'clean_characters':len(case['text']) if not gold else 0,'seconds':round(time.perf_counter()-t,3)}
        rows.append(row)
        print(case['id'],json.dumps(predictions,ensure_ascii=False),flush=True)
    test=[r for r in rows if r['split']=='evaluation']
    total=sum(r['errors'] for r in test)
    found=sum(r['detected_errors'] for r in test)
    correct=sum(r['correct_in_top3'] for r in test)
    clean_chars=sum(r['clean_characters'] for r in test)
    clean_false=sum(r['false_marks'] for r in test if r['clean_characters'])
    payload={'scope':'作者作成の架空文12件（誤りあり6件・正しい文6件）の評価。実際のAqua Voice履歴ではない。',
             'evaluation_note':'初回の結果で候補の広げ過ぎと品詞の見落としを修正し、このデータを回帰確認に再利用した。未使用のホールドアウトではない。',
             'limitations':'誤りパターンは公開候補表やモデルの学習に含まれる可能性がある。学習データとの非重複は確認できず、独立した実運用精度とは扱わない。音声と本人の意図の正解はない。',
             'target_before_evaluation':'誤り箇所の再現率 >= 0.60、正しい文への誤警告 1000字あたり <= 10。未達も報告。',
             'definitions':'再現率は正解箇所と指摘範囲が重なる割合。修正Top3は正しい語を含む候補が上位3件にある誤りの割合（未検出も分母）。',
             'summary':{'evaluation_cases':len(test),'gold_errors':total,'detected_errors':found,
                        'detection_recall':round(found/total,4) if total else None,
                        'correction_top3_including_missed':round(correct/total,4) if total else None,
                        'correct_in_top3':correct,'false_marks_in_clean_text':clean_false,'false_marks_all_evaluation_text':sum(r['false_marks'] for r in test),
                        'clean_characters':clean_chars,'false_marks_per_1000_clean_characters':round(clean_false/clean_chars*1000,3) if clean_chars else None,
                        'mean_seconds':round(sum(r['seconds'] for r in test)/len(test),3)},
             'fixture_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'python':platform.python_version(),
             'revisions':{'detector':DETECTOR_REVISION,'scorer':CORRECTOR_REVISION,'lexicon':LEXICON_REVISION},
             'packages':{n:importlib.metadata.version(n) for n in ('torch','transformers','sudachipy','sudachidict-core','streamlit')},'cases':rows}
    (ROOT/'evaluation-results.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(payload['summary'],ensure_ascii=False,indent=2),flush=True)
    return payload

if __name__=='__main__':
    evaluate()
