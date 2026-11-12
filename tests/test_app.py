import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analyzer import analyze, chunks, dictionary_export, load_model, parse_known
from sample import SAMPLE, EXAMPLE_DICTIONARY


class AnalyzerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nlp = load_model()

    def test_model_and_variants(self):
        result = analyze(SAMPLE, EXAMPLE_DICTIONARY, self.nlp)
        self.assertGreater(result['entity_mentions'], 0)
        found = {x['term']: x for x in result['candidates']}
        self.assertIn('GitHub', found)
        self.assertEqual(found['GitHub']['count'], 2)
        self.assertTrue(found['GitHub']['registered'])
        self.assertIn('辞書登録', [a['term'] for a in found['自社登録']['alternatives']])
        for item in result['candidates']:
            for example in item['examples']:
                self.assertEqual(SAMPLE[example['position']-1:][:len(item['term'])], item['term'])

    def test_empty_and_limits(self):
        for text in ('', '  ', 'あ'*20001):
            with self.assertRaises(ValueError):
                analyze(text, nlp=self.nlp)
        with self.assertRaises(ValueError):
            parse_known('\n'.join('用語'+str(x) for x in range(201)))

    def test_chunking_preserves_input(self):
        text = 'あ'*1700 + '\n短い文章。\n' + 'い'*1800
        parts = list(chunks(text))
        self.assertEqual(''.join(x[1] for x in parts), text)
        self.assertTrue(all(len(x[1]) <= 800 for x in parts))
        for offset, part in parts:
            self.assertEqual(text[offset:offset+len(part)], part)

    def test_maximum_input(self):
        text = ('GitHubで練習します。机を片付けます。\n' * 1000)[:20000]
        result = analyze(text, nlp=self.nlp)
        self.assertEqual(result['characters'], 20000)
        self.assertLessEqual(len(result['candidates']), 160)

    def test_export(self):
        self.assertEqual(dictionary_export([' GitHub ', 'GitHub', 'Notion']), 'GitHub\nNotion\n')
        with self.assertRaises(ValueError):
            dictionary_export(['正しい語\n別の語'])


class UITests(unittest.TestCase):
    def test_paste_inference_selection_and_stale(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=60).run()
        self.assertFalse(app.exception)
        self.assertTrue(app.button[1].disabled)
        app.button[0].click().run()
        self.assertEqual(app.text_area[0].value, SAMPLE)
        app.button[1].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state['result']['candidates'])
        # Pick a visible candidate, save and verify selection survives reruns.
        candidate_check = [x for x in app.checkbox if x.label == '選ぶ'][0]
        candidate_check.check().run()
        [x for x in app.button if x.label == 'このページの選択をリストへ追加'][0].click().run()
        prefix = f"run-{app.session_state['run_id']}"
        self.assertTrue(app.session_state[f'{prefix}-chosen'])
        app.text_area[0].set_value('別の文章です。').run()
        self.assertTrue(any('入力が変わっています' in x.value for x in app.warning))
        self.assertTrue([x for x in app.button if x.label == 'このページの選択をリストへ追加'][0].disabled)


if __name__ == '__main__':
    unittest.main()
