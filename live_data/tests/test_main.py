import unittest

from rtd_collector.main import build_parser


class CollectorCliTests(unittest.TestCase):
    def test_parser_accepts_cron_run_mode(self):
        args = build_parser().parse_args(["--run-mode", "cron", "--log-level", "DEBUG"])

        self.assertEqual(args.run_mode, "cron")
        self.assertEqual(args.log_level, "DEBUG")
        self.assertIsNone(args.once)
        self.assertFalse(args.init_db)

    def test_parser_accepts_single_feed_collection(self):
        args = build_parser().parse_args(["--once", "vehicle_positions"])

        self.assertEqual(args.once, "vehicle_positions")
        self.assertIsNone(args.run_mode)
