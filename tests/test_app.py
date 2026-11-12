import sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from analyzer import analyze,dictionary_export,load_model,parse_known
from sample import SAMPLE

class AnalyzerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=load_model()

    def test_intended_conversion_without_correct_text(self):
        result=analyze(SAMPLE,model=self.model)
        by_original={x['original']:x for x in result['candidates']}
        for wrong,correct in [('自社登録','辞書登録'),('格論','各論'),('真相学習モデル','深層学習モデル')]:
            self.assertIn(wrong,by_original)
            self.assertEqual(by_original[wrong]['suggestions'][0]['term'],correct)
        self.assertNotIn('登録',by_original)
        for item in result['candidates']:
            for ex in item['examples']:
                self.assertEqual(SAMPLE[ex['start']:ex['end']],item['original'])

    def test_correct_sentence_is_not_a_word_list(self):
        result=analyze('今日は図書館で本を借りました。',model=self.model)
        self.assertEqual(result['candidates'],[])

    def test_empty_and_limits(self):
        for text in ('','  ','あ'*20001):
            with self.assertRaises(ValueError):
                analyze(text,model=self.model)
        with self.assertRaises(ValueError):
            parse_known('\n'.join('単語'+str(i) for i in range(201)))

    def test_window_offsets_and_token_limits(self):
        text='\n\nこれは長い文章です。\n'+('長い文章の途中に空白 と改行\nがあります。'*70)+'終わりです。'
        covered=set()
        for offset,part in self.model.sentence_windows(text):
            self.assertEqual(text[offset:offset+len(part)],part)
            count=len(self.model.tokenizer(part)['input_ids'])
            self.assertLessEqual(count,64)
            covered.update(range(offset,offset+len(part)))
        self.assertTrue(all(i in covered for i,c in enumerate(text) if not c.isspace()))

    def test_context_limit_is_explicit(self):
        result=analyze('概論ではなく格論から説明してください。',model=self.model,max_context_spans=0)
        self.assertEqual(result['context_checked'],0)
        self.assertTrue(result['context_limit_reached'])

    def test_export_only_confirmed_spelling(self):
        self.assertEqual(dictionary_export([' 辞書登録 ','辞書登録','各論']),'辞書登録\n各論\n')
        with self.assertRaises(ValueError):
            dictionary_export(['辞書\n登録'])

class UITests(unittest.TestCase):
    def test_inference_human_confirmation_and_stale(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=180).run()
        self.assertFalse(app.exception)
        self.assertTrue(app.button[1].disabled)
        app.button[0].click().run()
        self.assertEqual(app.text_area[0].value,SAMPLE)
        self.assertEqual(app.text_area[1].value,'')
        app.button[1].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state['result']['candidates'])
        self.assertEqual(app.text_input[0].value,'辞書登録')
        self.assertFalse(app.code)
        app.checkbox[0].check().run()
        self.assertIn('辞書登録',app.code[0].value)
        app.text_input[0].set_value('ユーザー辞書').run()
        self.assertIn('ユーザー辞書',app.code[0].value)
        app.text_area[0].set_value('別の文章です。').run()
        self.assertTrue(any('入力が変わっています' in x.value for x in app.warning))
        self.assertTrue(all(x.disabled for x in app.checkbox))

if __name__=='__main__':
    unittest.main()
