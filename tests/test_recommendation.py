"""Small adversarial fixtures for a frozen, chronological recommendation protocol.

These examples are synthetic. They verify evaluation contracts rather than
claiming anything about Retailrocket model performance.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import duckdb
from pipeline import bootstrap_ci, paired_bootstrap, run_sql


class RecommendationContracts(unittest.TestCase):
    def setUp(self):
        self.c = duckdb.connect(":memory:")
        self.c.execute("SET threads=1")
        self.c.execute("CREATE TABLE config(train_end_ms BIGINT, validation_end_ms BIGINT)")
        self.c.execute("INSERT INTO config VALUES (100000,200000)")
        self.c.execute("""CREATE TABLE session_events(
            event_id BIGINT, ts_ms BIGINT, visitor_id BIGINT,
            session_no BIGINT, item_id BIGINT, event_type VARCHAR)""")
        rows = []

        def session(visitor, entries):
            for time_ms, item, event in entries:
                rows.append((len(rows) + 1, time_ms, visitor, 1, item, event))

        # At least ten eligible candidates, and deterministic popularity ties.
        for item in range(1, 26):
            session(item, [(1000 + item, item, "view")])
        # Repeated views must not inflate the count of co-viewing sessions.
        for visitor in (101, 102, 103):
            session(visitor, [(2000, 1, "view"), (2001, 2, "view"),
                              (2002, 2, "view"), (2003, 1, "view")])
        for visitor in (104, 105):
            session(visitor, [(3000, 1, "view"), (3001, 3, "view")])
        # Pair expansion is capped, but the full training catalog is retained.
        session(150, [(4000 + i, 100 + i, "view") for i in range(55)])

        session(501, [(110000, 1, "view"), (110000, 2, "view"),
                      (110100, 1, "view"), (110200, 3, "view"),
                      (110300, 2, "view")])
        session(502, [(120000, 999, "view"), (120001, 2, "view")])
        session(503, [(130000, 1, "view"), (130001, 888, "view")])
        session(504, [(140000, 1, "view"), (140001, 1, "view")])
        # The first validation point must not consume a test-period label.
        session(505, [(199999, 1, "view"), (200000, 2, "view")])
        # The boundary itself belongs to test.
        session(506, [(200000, 1, "view"), (200001, 2, "view")])
        # A session begun during training is excluded from held-out queries.
        session(507, [(99999, 1, "addtocart"), (100010, 1, "view"),
                      (100020, 2, "view")])
        session(508, [(199999, 1, "view"), (199999, 2, "view")])
        self.c.executemany("INSERT INTO session_events VALUES (?,?,?,?,?,?)", rows)
        self.c.execute("""CREATE TABLE sessions AS
            SELECT visitor_id,session_no,min(ts_ms) AS start_ms,max(ts_ms) AS end_ms
            FROM session_events GROUP BY visitor_id,session_no""")
        for name in ("09_popular.sql", "10_coview.sql", "11_eval_queries.sql", "12_evaluation.sql"):
            run_sql(self.c, name)

    def tearDown(self):
        self.c.close()

    def model_snapshot(self):
        return (
            self.c.execute("SELECT * FROM popular ORDER BY item_id").fetchall(),
            self.c.execute("SELECT * FROM coview ORDER BY seed_item,candidate_item").fetchall(),
            self.c.execute("SELECT * FROM related_top ORDER BY seed_item,related_rank").fetchall(),
        )

    def test_future_events_cannot_change_fitted_model_or_catalog(self):
        before = self.model_snapshot()
        # Inject a future 'viral' item, including events exactly at train cutoff.
        injected = [(90000 + i, 100000 + i, 900, 1, 999, "view") for i in range(100)]
        injected += [(91000 + i, 250000 + i, 901, 1, 888, "view") for i in range(100)]
        self.c.executemany("INSERT INTO session_events VALUES (?,?,?,?,?,?)", injected)
        run_sql(self.c, "09_popular.sql")
        run_sql(self.c, "10_coview.sql")
        self.assertEqual(before, self.model_snapshot())
        self.assertEqual(self.c.execute("SELECT count(*) FROM popular WHERE item_id IN (888,999)").fetchone()[0], 0)
        self.assertLess(self.c.execute("SELECT max(ts_ms) FROM train_views").fetchone()[0], 100000)

    def test_coview_counts_sessions_and_caps_pair_expansion(self):
        self.assertEqual(self.c.execute("SELECT support FROM coview WHERE seed_item=1 AND candidate_item=2").fetchone()[0], 3)
        self.assertEqual(self.c.execute("SELECT count(*) FROM train_session_items WHERE visitor_id=150").fetchone()[0], 50)
        self.assertEqual(self.c.execute("SELECT count(*) FROM popular WHERE item_id BETWEEN 100 AND 154").fetchone()[0], 55)
        self.assertEqual(self.c.execute("SELECT count(*) FROM train_session_items WHERE visitor_id=150 AND item_id>=150").fetchone()[0], 0)

    def test_label_is_next_strictly_later_different_view(self):
        self.assertEqual(self.c.execute("SELECT seed_item,target_item,target_ms FROM eval_queries WHERE visitor_id=501").fetchone(), (1, 3, 110200))
        self.assertEqual(self.c.execute("SELECT count(*) FROM eval_queries WHERE visitor_id IN (504,508)").fetchone()[0], 0)
        self.assertEqual(self.c.execute("SELECT count(*) FROM prediction_points WHERE visitor_id=507").fetchone()[0], 0)

    def test_validation_labels_do_not_cross_into_test(self):
        self.assertEqual(self.c.execute("SELECT count(*) FROM eval_queries WHERE split='validation' AND target_ms>=200000").fetchone()[0], 0)
        self.assertEqual(self.c.execute("SELECT count(*) FROM eval_queries WHERE visitor_id=505").fetchone()[0], 0)
        self.assertEqual(self.c.execute("SELECT split,prediction_ms FROM eval_queries WHERE visitor_id=506").fetchone(), ("test", 200000))

    def test_unseen_targets_remain_in_both_method_denominators(self):
        self.assertEqual(self.c.execute("SELECT method,hit FROM evaluation_detail WHERE visitor_id=503 ORDER BY method").fetchall(), [("coview", 0), ("popular", 0)])
        metrics = self.c.execute("SELECT method,queries,hits,hit_rate_at_10 FROM evaluation_metrics WHERE split='validation' ORDER BY method").fetchall()
        self.assertEqual(len(metrics), 2)
        for _, queries, hits, rate in metrics:
            self.assertEqual((queries, hits), (3, 2))
            self.assertAlmostEqual(rate, 2 / 3)
        self.assertEqual(self.c.execute("SELECT count(*) FROM prediction_points WHERE split='validation'").fetchone()[0], 6)

    def test_ten_unique_training_candidates_exclude_seed(self):
        groups = self.c.execute("""SELECT query_id,method,count(*),count(DISTINCT item_id),
            min(rank),max(rank) FROM recommendations GROUP BY query_id,method""").fetchall()
        queries = self.c.execute("SELECT count(*) FROM eval_queries").fetchone()[0]
        self.assertEqual(len(groups), queries * 2)
        for _, _, size, unique, lo, hi in groups:
            self.assertEqual((size, unique, lo, hi), (10, 10, 1, 10))
        self.assertEqual(self.c.execute("""SELECT count(*) FROM recommendations r
            JOIN eval_queries q USING(query_id) WHERE r.item_id=q.seed_item""").fetchone()[0], 0)
        self.assertEqual(self.c.execute("""SELECT count(*) FROM recommendations r
            LEFT JOIN popular p USING(item_id) WHERE p.item_id IS NULL""").fetchone()[0], 0)
        # Candidate 2 is present in both sources but appears only once in output.
        self.assertEqual(self.c.execute("SELECT count(*) FROM recommendations WHERE query_id='501-1' AND method='coview' AND item_id=2").fetchone()[0], 1)

    def test_unknown_seed_falls_back_without_dropping_query(self):
        output = self.c.execute("SELECT method,item_id,rank FROM recommendations WHERE query_id='502-1' ORDER BY method,rank").fetchall()
        self.assertEqual([(item, rank) for method, item, rank in output if method == "coview"],
                         [(item, rank) for method, item, rank in output if method == "popular"])
        self.assertEqual(self.c.execute("SELECT full_popular_fallback FROM evaluation_detail WHERE visitor_id=502 AND method='coview'").fetchone()[0], 1)
        self.assertEqual(self.c.execute("SELECT full_popular_fallback FROM evaluation_detail WHERE visitor_id=501 AND method='coview'").fetchone()[0], 0)


class BootstrapContracts(unittest.TestCase):
    def setUp(self):
        self.c = duckdb.connect(":memory:")
        self.c.execute("SET threads=1")
        self.c.execute("CREATE TABLE evaluation_detail(query_id VARCHAR,visitor_id BIGINT,split VARCHAR,method VARCHAR,hit INTEGER)")
        # Unequal session counts ensure the reported effect is query-weighted,
        # while resampling keeps each visitor's sessions together.
        specs = [(10001, [(1, 0), (1, 0)]),
                 (90000001, [(0, 1)]),
                 (200000003, [(1, 1), (0, 0), (0, 0)])]
        self.rows = []
        for visitor, outcomes in specs:
            for i, (coview_hit, popular_hit) in enumerate(outcomes):
                for method, hit in (("coview", coview_hit), ("popular", popular_hit)):
                    self.rows.append((f"{visitor}-{i}", visitor, "test", method, hit))
        self.c.executemany("INSERT INTO evaluation_detail VALUES(?,?,?,?,?)", self.rows)

    def tearDown(self):
        self.c.close()

    def test_paired_effect_uses_the_shared_query_denominator(self):
        result = paired_bootstrap(self.c, "test")
        self.assertAlmostEqual(result["difference_pp"], 100 / 6)
        self.assertEqual(result["bootstrap_unit"], "visitor")
        self.assertLessEqual(result["ci_low_pp"], result["difference_pp"])
        self.assertGreaterEqual(result["ci_high_pp"], result["difference_pp"])

    def test_seeded_intervals_do_not_depend_on_insert_order(self):
        before = (bootstrap_ci(self.c, "test", "coview"), paired_bootstrap(self.c, "test"))
        self.c.execute("DELETE FROM evaluation_detail")
        self.c.executemany("INSERT INTO evaluation_detail VALUES(?,?,?,?,?)", list(reversed(self.rows)))
        after = (bootstrap_ci(self.c, "test", "coview"), paired_bootstrap(self.c, "test"))
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
