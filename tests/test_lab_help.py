import unittest
from html.parser import HTMLParser

from nour import research_view


class Tags(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.tags = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class LaboratoryHelp(unittest.TestCase):
    def test_native_disclosure_is_closed_and_named(self):
        tags = Tags(research_view.help_panel()).tags
        details = next(attrs for tag, attrs in tags if tag == 'details')
        self.assertNotIn('open', details)
        summary = next(attrs for tag, attrs in tags if tag == 'summary')
        self.assertEqual(summary['aria-label'], 'Comprendre le laboratoire')
        self.assertEqual(summary['aria-controls'], 'lab-help-content')

    def test_explanation_is_static_and_keeps_financial_limits(self):
        markup = research_view.help_panel()
        self.assertNotIn('<script', markup)
        for text in ('20 et 50', 'clôture suivante', '5, 20 ou 60',
                     'Exemple fictif', '60 cas sur 100', 'ne prédit pas demain',
                     'moins de 30', 'dividendes', 'fiscalité', 'supports',
                     'Fréquence positive', 'Médiane nette', 'Percentiles 10 / 90'):
            self.assertIn(text, markup)


if __name__ == '__main__':
    unittest.main()
