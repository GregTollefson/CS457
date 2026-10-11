"""Research mapping validation, independent of FRED and PostgreSQL."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.mapping import get_series_mapping, load_series_mapping, REQUIRED_FIELDS


class MappingTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'mapping.json'
        self.mapping = load_series_mapping()

    def write(self, data):
        self.path.write_text(json.dumps(data), encoding='utf-8')

    def test_default_mapping(self):
        self.assertEqual(set(self.mapping), {'APU000072610', 'CAPG2211S'})
        self.assertEqual(self.mapping['CAPG2211S']['metric_code'], 'utility_capacity')
        self.assertEqual(self.mapping['APU000072610']['category_code'], 'price')
        for entry in self.mapping.values():
            self.assertEqual(set(entry), set(REQUIRED_FIELDS))

    def test_malformed_json(self):
        self.path.write_text('{', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Malformed.*line'):
            load_series_mapping(self.path)

    def test_missing_file(self):
        with self.assertRaisesRegex(FileNotFoundError, 'not found'):
            load_series_mapping(self.path)

    def test_invalid_structure(self):
        for data in ([], {}, {'series': []}, {'series': {'X': []}}):
            with self.subTest(data=data):
                self.write(data)
                with self.assertRaises(ValueError):
                    load_series_mapping(self.path)

    def test_missing_fields(self):
        for field in REQUIRED_FIELDS:
            with self.subTest(field=field):
                entry = dict(self.mapping['CAPG2211S'])
                del entry[field]
                self.write({'series': {'X': entry}})
                with self.assertRaisesRegex(ValueError, field):
                    load_series_mapping(self.path)

    def test_invalid_field_values(self):
        for field in REQUIRED_FIELDS:
            for value in ('', '  ', None, 12, ' spaced '):
                with self.subTest(field=field, value=value):
                    entry = dict(self.mapping['CAPG2211S'], **{field: value})
                    self.write({'series': {'X': entry}})
                    with self.assertRaisesRegex(ValueError, field):
                        load_series_mapping(self.path)

    def test_unknown_series(self):
        with self.assertRaisesRegex(ValueError, 'Unknown configured series ID'):
            get_series_mapping('UNKNOWN', self.mapping)

    def test_conflicting_codes(self):
        for field, value in (('category_name', 'Another name'),
                             ('category_code', 'another_code'),
                             ('metric_name', 'Another metric')):
            with self.subTest(field=field):
                entry = dict(self.mapping['CAPG2211S'])
                self.write({'series': {'X': entry, 'Y': dict(entry, **{field: value})}})
                with self.assertRaisesRegex(ValueError, 'Conflicting|multiple codes'):
                    load_series_mapping(self.path)


if __name__ == '__main__':
    unittest.main()
