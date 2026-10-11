"""HTTP/cleaning unit tests and integration tests in a disposable local cluster.

The cluster uses only a temporary Unix socket, never the configured live DB.
PostgreSQL server binaries must be installed to run the integration tests.
"""

from contextlib import redirect_stdout
from datetime import date
import io
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch, Mock
from uuid import uuid4

import pandas as pd
import psycopg

from src.fred_api import clean_observations, get_series_metadata, get_series_observations
from src.ingest import ingest_series, upsert_category, upsert_metric, upsert_source
from src.mapping import load_series_mapping
from src.validate_db import validate_connection, main as validate_main

ROOT = Path(__file__).resolve().parent.parent
METADATA = {
    'id': 'CAPG2211S', 'title': 'Fixture capacity', 'frequency': 'Monthly',
    'units': 'Index', 'seasonal_adjustment': 'Seasonally Adjusted',
    'observation_start': '2020-01-01', 'observation_end': '2020-02-01',
    'last_updated': '2020-03-01 12:00:00-05', 'popularity': 1, 'notes': 'Fixture',
}
RAW = [
    {'date': '2020-01-01', 'value': '12.5', 'realtime_start': '2020-03-01',
     'realtime_end': '2020-03-01'},
    {'date': '2020-02-01', 'value': '.', 'realtime_start': '2020-03-01',
     'realtime_end': '2020-03-01'},
]


class FredAndIngestUnitTest(unittest.TestCase):
    def test_mocked_http_and_missing_value_cleaning(self):
        response = Mock()
        response.json.return_value = {'observations': RAW}
        with patch('src.fred_api.requests.get', return_value=response) as get:
            raw = get_series_observations('CAPG2211S')
        response.raise_for_status.assert_called_once()
        self.assertEqual(get.call_args.kwargs['params']['series_id'], 'CAPG2211S')
        cleaned = clean_observations(raw, 'CAPG2211S')
        self.assertEqual(raw.iloc[1]['value'], '.')  # Input is not mutated.
        self.assertTrue(pd.isna(cleaned.iloc[1]['value']))
        self.assertEqual(cleaned.iloc[0]['value'], 12.5)
        self.assertEqual(cleaned.iloc[0]['date'], date(2020, 1, 1))
        self.assertEqual(cleaned.iloc[0]['realtime_start'], date(2020, 3, 1))
        self.assertEqual(cleaned.iloc[0]['series_id'], 'CAPG2211S')

    def test_mocked_metadata_http(self):
        response = Mock()
        response.json.return_value = {'seriess': [METADATA]}
        with patch('src.fred_api.requests.get', return_value=response):
            self.assertEqual(get_series_metadata('CAPG2211S'), METADATA)
        response.raise_for_status.assert_called_once()

    def test_unknown_id_precedes_io(self):
        with patch('src.ingest.get_series_metadata') as fred, \
             patch('src.ingest.get_connection') as connection:
            with self.assertRaisesRegex(ValueError, 'Unknown configured'):
                ingest_series('UNKNOWN')
        fred.assert_not_called()
        connection.assert_not_called()

    def test_wrong_metadata_id_prevents_observation_fetch(self):
        with patch('src.ingest.get_series_metadata', return_value={'id': 'WRONG'}), \
             patch('src.ingest.get_connection') as connection, \
             patch('src.ingest.get_series_observations') as observations:
            with self.assertRaisesRegex(ValueError, 'does not match'):
                ingest_series('CAPG2211S')
        observations.assert_not_called()
        connection.assert_not_called()

    def test_fred_retrieval_and_preparation_precede_connection(self):
        cleaned = clean_observations(pd.DataFrame(RAW), 'CAPG2211S')
        calls = Mock()
        with patch('src.ingest.get_series_metadata', return_value=METADATA) as metadata, \
             patch('src.ingest.get_series_observations', return_value=pd.DataFrame(RAW)) as observations, \
             patch('src.ingest.clean_observations', return_value=cleaned) as clean, \
             patch('src.ingest.pd.to_datetime', wraps=pd.to_datetime) as prepare, \
             patch('src.ingest.get_connection', side_effect=RuntimeError('stop before writes')) as connection, \
             patch('src.ingest.upsert_category') as category:
            for name, mock in (('metadata', metadata), ('observations', observations),
                               ('clean', clean), ('prepare', prepare),
                               ('connection', connection)):
                calls.attach_mock(mock, name)
            with self.assertRaisesRegex(RuntimeError, 'stop before writes'):
                ingest_series('CAPG2211S')
        self.assertEqual([call[0] for call in calls.mock_calls],
                         ['metadata', 'observations', 'clean',
                          'prepare', 'prepare', 'prepare', 'connection'])
        self.assertEqual([call.args[0] for call in prepare.call_args_list],
                         [METADATA['observation_start'], METADATA['observation_end'],
                          METADATA['last_updated']])
        category.assert_not_called()

    def test_unsupported_source_precedes_io(self):
        mapping = load_series_mapping()
        mapping['CAPG2211S']['source'] = 'OTHER'
        with patch('src.ingest.get_series_metadata') as fred:
            with self.assertRaisesRegex(ValueError, 'only supports source FRED'):
                ingest_series('CAPG2211S', mapping)
        fred.assert_not_called()


class IsolatedPostgresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        candidates = sorted(Path('/usr/lib/postgresql').glob('*/bin/initdb'))
        initdb = shutil.which('initdb') or (str(candidates[-1]) if candidates else None)
        if initdb is None:
            raise unittest.SkipTest('PostgreSQL server binaries unavailable')
        cls.bin = Path(initdb).parent
        cls.temp = TemporaryDirectory(prefix='cs457-test-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.base = Path(cls.temp.name)
        cls.data = cls.base / 'data'
        cls.socket = cls.base / 'socket'
        cls.socket.mkdir()
        subprocess.run([str(cls.bin / 'initdb'), '-D', str(cls.data), '-A', 'trust',
                        '-U', 'test_runner', '--no-locale', '--encoding=UTF8'],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([str(cls.bin / 'pg_ctl'), '-D', str(cls.data), '-l',
                        str(cls.base / 'server.log'), '-o',
                        f'-F -k {cls.socket} -h ""', '-w', 'start'],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.addClassCleanup(cls.stop_cluster)

    @classmethod
    def stop_cluster(cls):
        subprocess.run([str(cls.bin / 'pg_ctl'), '-D', str(cls.data), '-m', 'fast',
                        '-w', 'stop'], check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

    def connect(self):
        return psycopg.connect(dbname='postgres', user='test_runner',
                               host=str(self.socket),
                               options=f'-c search_path={self.schema}')

    def setUp(self):
        self.schema = 'test_' + uuid4().hex
        with self.connect() as conn:
            conn.execute(psycopg.sql.SQL('CREATE SCHEMA {}').format(
                psycopg.sql.Identifier(self.schema)))
        self.mapping = load_series_mapping()

    def install(self, legacy=False):
        schema = (ROOT / 'sql/schema.sql').read_text()
        if legacy:
            schema = schema[schema.index('CREATE TABLE IF NOT EXISTS series'):]
            schema = schema.replace(',\n    metric_id INTEGER REFERENCES metric(metric_id),\n'
                                    '    source_id INTEGER REFERENCES source(source_id)', '')
        with self.connect() as conn:
            conn.execute(schema)

    def seed_price(self):
        with self.connect() as conn:
            conn.execute("INSERT INTO series (series_id, title) VALUES ('APU000072610', 'Fixture price')")
            conn.execute("""INSERT INTO observations (series_id, date, value)
                SELECT 'APU000072610', DATE '1970-01-01' + n,
                       CASE WHEN n < 2 THEN NULL ELSE n::float END
                FROM generate_series(0, 573) n""")

    def snapshot(self):
        with self.connect() as conn:
            series = conn.execute('SELECT series_id, title FROM series ORDER BY series_id').fetchall()
            observations = conn.execute('SELECT * FROM observations ORDER BY series_id, date').fetchall()
        return series, observations

    def test_migration_preserves_existing_rows_and_validator_passes(self):
        self.install(legacy=True)
        self.seed_price()
        before = self.snapshot()
        with self.connect() as conn:
            conn.execute((ROOT / 'sql/migrations/001_add_research_model.sql').read_text())
        self.assertEqual(self.snapshot(), before)
        with self.connect() as conn:
            self.assertEqual(conn.execute('SELECT metric_id, source_id FROM series').fetchone(), (None, None))
        messages = []
        with self.connect() as conn:
            conn.read_only = True
            self.assertTrue(validate_connection(conn, messages.append))
        self.assertTrue(all(line.startswith('PASS:') for line in messages))
        self.assertEqual(self.snapshot(), before)

    def test_clean_schema_validator_and_main_read_only(self):
        self.install()
        self.seed_price()
        messages = []
        with self.connect() as conn:
            conn.read_only = True
            self.assertTrue(validate_connection(conn, messages.append))
        with patch('src.validate_db.get_connection', side_effect=self.connect), \
             redirect_stdout(io.StringIO()) as output:
            self.assertEqual(validate_main(), 0)
        self.assertIn('PASS: APU000072610 has 574 observations', output.getvalue())

    def test_validator_reports_unmigrated_schema(self):
        self.install(legacy=True)
        self.seed_price()
        messages = []
        with self.connect() as conn:
            conn.read_only = True
            self.assertFalse(validate_connection(conn, messages.append))
        self.assertIn('FAIL: category table exists', messages)
        self.assertTrue(any('required table or column missing' in m for m in messages))
        with patch('src.validate_db.get_connection', side_effect=self.connect), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(validate_main(), 1)

    def test_validator_detects_incorrect_preservation_count(self):
        self.install()
        messages = []
        with self.connect() as conn:
            conn.read_only = True
            self.assertFalse(validate_connection(conn, messages.append))
        self.assertTrue(any(m.startswith('FAIL: APU000072610 has 574') for m in messages))

    def test_stable_upserts_and_display_changes(self):
        self.install()
        entry = dict(self.mapping['CAPG2211S'])
        with self.connect() as conn:
            with conn.cursor() as cur:
                category = upsert_category(cur, entry)
                metric = upsert_metric(cur, entry, category)
                source = upsert_source(cur, entry)
                entry['category_name'] = 'Updated Capacity'
                entry['metric_name'] = 'Updated Utility Capacity'
                for _ in range(2):
                    self.assertEqual(upsert_category(cur, entry), category)
                    self.assertEqual(upsert_metric(cur, entry, category), metric)
                    self.assertEqual(upsert_source(cur, entry), source)
            for table in ('category', 'metric', 'source'):
                self.assertEqual(conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0], 1)
            self.assertEqual(conn.execute('SELECT category_name FROM category').fetchone()[0], entry['category_name'])
            self.assertEqual(conn.execute('SELECT metric_name, category_id FROM metric').fetchone(), (entry['metric_name'], category))

    def test_repeated_ingestion_and_sql_null(self):
        self.install()
        self.seed_price()
        before = self.snapshot()
        with patch('src.ingest.get_connection', side_effect=self.connect), \
             patch('src.ingest.get_series_metadata', return_value=METADATA), \
             patch('src.ingest.get_series_observations', return_value=pd.DataFrame(RAW)), \
             redirect_stdout(io.StringIO()):
            ingest_series('CAPG2211S')
            ingest_series('CAPG2211S')
        with self.connect() as conn:
            self.assertEqual(conn.execute("SELECT date, value FROM observations WHERE series_id = 'CAPG2211S' ORDER BY date").fetchall(), [(date(2020, 1, 1), 12.5), (date(2020, 2, 1), None)])
            self.assertEqual(conn.execute('SELECT count(*) FROM series').fetchone()[0], 2)
            for table in ('category', 'metric', 'source'):
                self.assertEqual(conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0], 1)
            self.assertEqual(conn.execute("""SELECT m.metric_code, s.source_name, t.title, t.notes
                FROM series t JOIN metric m USING (metric_id) JOIN source s USING (source_id)
                WHERE t.series_id = 'CAPG2211S'""").fetchone(), ('utility_capacity', 'FRED', METADATA['title'], METADATA['notes']))
        after = self.snapshot()
        self.assertEqual([row for row in after[0] if row[0] == 'APU000072610'], before[0])
        self.assertEqual([row for row in after[1] if row[0] == 'APU000072610'], before[1])

    def test_failed_ingestion_rolls_back_research_rows(self):
        self.install()
        bad = dict(METADATA, title=None)
        with patch('src.ingest.get_connection', side_effect=self.connect), \
             patch('src.ingest.get_series_metadata', return_value=bad), \
             patch('src.ingest.get_series_observations', return_value=pd.DataFrame(RAW)):
            with self.assertRaises(psycopg.errors.NotNullViolation):
                ingest_series('CAPG2211S')
        with self.connect() as conn:
            for table in ('category', 'metric', 'source', 'series', 'observations'):
                self.assertEqual(conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0], 0)

    def test_multiple_configured_series_share_source_without_duplicates(self):
        self.install()
        with patch('src.ingest.get_connection', side_effect=self.connect), \
             patch('src.ingest.get_series_metadata',
                   side_effect=lambda series_id: dict(METADATA, id=series_id)), \
             patch('src.ingest.get_series_observations', return_value=pd.DataFrame(RAW)), \
             redirect_stdout(io.StringIO()):
            for _ in range(2):
                for series_id in self.mapping:
                    ingest_series(series_id, self.mapping)
        with self.connect() as conn:
            expected = {'category': 2, 'metric': 2, 'source': 1,
                        'series': 2, 'observations': 4}
            for table, count in expected.items():
                self.assertEqual(conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0], count)
            self.assertEqual(conn.execute("""SELECT t.series_id, c.category_code, m.metric_code
                FROM series t JOIN metric m USING (metric_id)
                JOIN category c USING (category_id) ORDER BY t.series_id""").fetchall(),
                [('APU000072610', 'price', 'electricity_price'),
                 ('CAPG2211S', 'capacity', 'utility_capacity')])

    def test_reingestion_updates_metadata_and_values(self):
        self.install()
        metadata = dict(METADATA)
        rows = [dict(row) for row in RAW]
        with patch('src.ingest.get_connection', side_effect=self.connect), \
             patch('src.ingest.get_series_metadata', side_effect=lambda _: metadata), \
             patch('src.ingest.get_series_observations',
                   side_effect=lambda _: pd.DataFrame(rows)), \
             redirect_stdout(io.StringIO()):
            ingest_series('CAPG2211S')
            metadata['title'] = 'Revised capacity'
            rows[0]['value'] = '13.5'
            rows[1]['value'] = '14.5'
            ingest_series('CAPG2211S')
        with self.connect() as conn:
            self.assertEqual(conn.execute('SELECT title FROM series').fetchall(),
                             [('Revised capacity',)])
            self.assertEqual(conn.execute('SELECT value FROM observations ORDER BY date').fetchall(),
                             [(13.5,), (14.5,)])


if __name__ == '__main__':
    unittest.main()
