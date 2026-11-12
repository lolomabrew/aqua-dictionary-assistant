"""Reproducible, original synthetic benchmark; never call it real ASR accuracy."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import statistics
import time
from analyzer import analyze, load_model

ROOT = Path(__file__).resolve().parent


def evaluate():
    source = ROOT / 'data/evaluation.json'
    fixture = json.loads(source.read_text())
    start = time.perf_counter()
    nlp = load_model()
    load_seconds = time.perf_counter() - start
    results = []
    for case in fixture['cases']:
        runs = {}
        for mode in ('model', 'without_ner'):
            start = time.perf_counter()
            result = analyze(case['text'], case['known'], nlp, use_ner=mode == 'model')
            top = result['candidates'][:10]
            expected = set(case['expected_terms'])
            predicted = {x['term'] for x in top}
            hits = len(expected & predicted)
            found_pairs = {(x['term'], a['term']) for x in result['candidates'] for a in x['alternatives']}
            pairs = {tuple(x) for x in case['expected_pairs']}
            runs[mode] = {'top_terms': [x['term'] for x in top], 'precision_at_10_available': hits / len(top) if top else None,
                          'recall_at_10': hits / len(expected) if expected else None,
                          'candidate_count': len(result['candidates']), 'pair_hits': len(pairs & found_pairs), 'pair_expected': len(pairs),
                          'entity_mentions': result['entity_mentions'], 'seconds': round(time.perf_counter() - start, 4)}
        results.append({'id': case['id'], 'split': case['split'], 'expected_terms': case['expected_terms'], **runs})
    test = [x for x in results if x['split'] == 'evaluation']
    summaries = {}
    for mode in ('model', 'without_ner'):
        rows = [x[mode] for x in test]
        precision = [x['precision_at_10_available'] for x in rows if x['precision_at_10_available'] is not None]
        recall = [x['recall_at_10'] for x in rows if x['recall_at_10'] is not None]
        summaries[mode] = {'macro_precision_available_top10': round(statistics.mean(precision), 4) if precision else None,
                           'macro_recall_at_10': round(statistics.mean(recall), 4) if recall else None,
                           'pair_hits': sum(x['pair_hits'] for x in rows), 'pair_expected': sum(x['pair_expected'] for x in rows),
                           'mean_seconds': round(statistics.mean(x['seconds'] for x in rows), 4),
                           'mean_candidates_on_no_target_cases': statistics.mean(x[mode]['candidate_count'] for x in test if not x['expected_terms'])}
    payload = {'scope': '作者作成の架空評価8件。実際の音声認識精度・誤認識検出精度ではない。',
               'target_before_run': '評価文の登録対象語 Recall@10 >= 0.70、指定した類似表記ペアの検出率 >= 0.50。未達でも正直に報告する。',
               'precision_definition': '上位最大10件中の指定登録対象語の割合。10件未満では返却件数を分母とする。空の出力は平均から除く。',
               'baseline': '同じ形態素・英字・頻度・読み比較を使い、学習済みNERの抽出だけを無効化。完全な機械学習なしの比較ではない。',
               'test_count': len(test), 'fixture_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
               'python': platform.python_version(), 'packages': {x: importlib.metadata.version(x) for x in ('spacy','ja-ginza','ginza','sudachidict-core','numpy','streamlit')},
               'load_seconds': round(load_seconds, 3), 'summary': summaries, 'cases': results}
    (ROOT / 'evaluation-results.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k:v for k,v in payload.items() if k != 'cases'}, ensure_ascii=False, indent=2))
    return payload


if __name__ == '__main__':
    evaluate()
