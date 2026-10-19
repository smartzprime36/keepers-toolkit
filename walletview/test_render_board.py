"""Tests for the wallet view rules. Run: python3 -m unittest test_render_board -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_board as rb

WATCH = {"name": "cold", "chain": "DOGE", "address": "Dexample",
         "kind": "watch-only", "balance": 5.0, "source": "test",
         "ok": True}
HOUSE = {"name": "hot", "chain": "CLAM", "address": "xexample",
         "kind": "house-key", "balance": 5.0, "source": "test",
         "ok": True}


class TestVisualClasses(unittest.TestCase):
    def test_watch_only_has_no_send_control_anywhere(self):
        out = rb.render_wallet_row(WATCH)
        self.assertNotIn("<button", out)
        self.assertIn("wallet-watch", out)
        self.assertIn("WATCH-ONLY", out)

    def test_house_row_is_spending_class(self):
        out = rb.render_wallet_row(HOUSE)
        self.assertIn("wallet-house", out)

    def test_composer_refuses_watch_only(self):
        self.assertEqual(rb.render_send_composer(WATCH, "line", True), "")


class TestComposerGating(unittest.TestCase):
    def test_button_disabled_without_journal_line(self):
        out = rb.render_send_composer(HOUSE)
        self.assertIn("disabled", out)
        self.assertIn("does not exist", out)

    def test_button_disabled_until_acknowledged(self):
        out = rb.render_send_composer(HOUSE, "INTENT ...", False)
        self.assertIn("disabled", out)

    def test_button_enabled_after_line_and_ack(self):
        out = rb.render_send_composer(HOUSE, "INTENT ...", True)
        self.assertNotIn("disabled", out)

    def test_dry_run_banner_is_visible(self):
        out = rb.render_send_composer(HOUSE)
        self.assertIn("DRY RUN BY DEFAULT", out)


class TestErrorRows(unittest.TestCase):
    def test_failed_read_is_error_never_zero(self):
        row = dict(WATCH, ok=False, balance=None, source=None,
                   error="boom")
        out = rb.render_wallet_row(row)
        self.assertIn("READ ERROR", out)
        self.assertNotIn("0.0", out)


if __name__ == "__main__":
    unittest.main()
