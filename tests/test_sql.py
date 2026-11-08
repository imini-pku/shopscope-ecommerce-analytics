"""Adversarial fixtures: duplicate vs repeat, strict ordering, NULLs and session boundaries."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import duckdb
from pipeline import run_sql

class SQLContracts(unittest.TestCase):
    def setUp(self):
        self.c=duckdb.connect(':memory:')
        self.c.execute('CREATE TABLE raw_events(source_row BIGINT,timestamp VARCHAR,visitorid VARCHAR,event VARCHAR,itemid VARCHAR,transactionid VARCHAR)')
        rows=[(1,'0','1','view','10',None),(2,'0','1','view','10',None),
              (3,'1000','1','addtocart','10',None),(4,'2000','1','transaction','10','7'),
              (5,'1802000','1','view','20',None),(6,'3602001','1','view','30',None),
              (7,'0','2','view','11',None),(8,'0','2','transaction','11','8'),
              (9,'500','3','transaction','12','9'),(10,'600','3','view','12',None),
              (11,'bad','4','view','10',None),(12,'700','4','transaction','10',None),
              (13,'0','5','view','13',None),(14,'100','5','transaction','13','10'),
              (15,'200','5','addtocart','13',None),(16,'300','5','view','13',None)]
        self.c.executemany('INSERT INTO raw_events VALUES(?,?,?,?,?,?)',rows)
        for f in ['01_data_quality.sql','02_clean_events.sql','03_users.sql','04_sessions.sql','05_daily_metrics.sql','06_funnel.sql','07_segment_metrics.sql','08_join_checks.sql']:run_sql(self.c,f)
    def tearDown(self):self.c.close()
    def test_exact_duplicate_only(self):
        self.assertEqual(self.c.execute('SELECT count(*) FROM events').fetchone()[0],13)
        self.assertEqual(self.c.execute('SELECT count(*) FROM events WHERE visitor_id=5 AND event_type=\'view\'').fetchone()[0],2)
    def test_session_boundary(self):
        self.assertEqual(self.c.execute('SELECT session_no FROM session_events WHERE event_id IN (5,6) ORDER BY event_id').fetchall(),[(1,),(2,)])
    def test_funnel_ordering(self):
        self.assertEqual(self.c.execute('SELECT count(purchase_ms),count(strict_purchase_ms) FROM funnel_pairs').fetchone(),(2,1))
        self.assertIsNone(self.c.execute('SELECT purchase_ms FROM funnel_pairs WHERE visitor_id=2').fetchone()[0])
        self.assertIsNone(self.c.execute('SELECT purchase_ms FROM funnel_pairs WHERE visitor_id=3').fetchone()[0])
    def test_nulls_and_join_grain(self):
        self.assertEqual(self.c.execute('SELECT invalid_rows FROM quality_summary').fetchone()[0],2)
        self.assertEqual(self.c.execute('SELECT before_rows=after_rows,duplicate_user_keys,unmatched_rows FROM join_checks').fetchone(),(True,0,0))

if __name__=='__main__':unittest.main()
