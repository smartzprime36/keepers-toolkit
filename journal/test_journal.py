"""Tests for the journal discipline. Run: python3 -m unittest test_journal -v"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from journal import (Journal, SEND_FIELDS, SWAP_FIELDS, JournalRefusal,
                     SendSession, SwapSession, assert_spendable)


class FakeBroadcaster:
    def __init__(self, txid="f" * 64):
        self.txid = txid
        self.calls = []

    def broadcast(self, chain, signed_tx):
        self.calls.append((chain, signed_tx))
        return self.txid


class TestSpendable(unittest.TestCase):
    def test_empty_wallet_stop(self):
        with self.assertRaises(JournalRefusal):
            assert_spendable(0, 1, 1)

    def test_unknown_balance_refuses(self):
        with self.assertRaises(JournalRefusal):
            assert_spendable(None, 1, 1)

    def test_insufficient_includes_fee(self):
        with self.assertRaises(JournalRefusal):
            assert_spendable(100, 95, 10)

    def test_exact_fit_passes(self):
        assert_spendable(105, 95, 10)


class TestSendSession(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.j = Journal(os.path.join(self.tmp, "journal.csv"), SEND_FIELDS)

    def session(self, live=False):
        return SendSession(self.j, "DOGE", "house-example",
                           "counterparty-example", 1000, 10, live=live)

    def test_build_before_intent_refused(self):
        with self.assertRaises(JournalRefusal):
            self.session().built("0" * 64)

    def test_dry_session_cannot_broadcast(self):
        s = self.session()
        s.open().built("0" * 64)
        with self.assertRaises(JournalRefusal):
            s.broadcast(FakeBroadcaster(), b"tx")

    def test_live_happy_path_journals_every_step(self):
        s = self.session(live=True)
        s.open().built("a" * 64)
        txid = s.broadcast(FakeBroadcaster(), b"tx")
        s.verify_readback(txid)
        kinds = [r["kind"] for r in self.j.rows()]
        self.assertEqual(kinds, ["INTENT", "BROADCAST", "READBACK"])

    def test_readback_mismatch_refused(self):
        s = self.session(live=True)
        s.open().built("a" * 64)
        s.broadcast(FakeBroadcaster(), b"tx")
        with self.assertRaises(JournalRefusal):
            s.verify_readback("e" * 64)


class TestSwapSession(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.j = Journal(os.path.join(self.tmp, "swaps.csv"), SWAP_FIELDS)

    def test_first_transition_must_be_quoted(self):
        sw = SwapSession(self.j, "CLAM", "DOGE", 10)
        with self.assertRaises(JournalRefusal):
            sw.transition("LEG1_WORKING")

    def test_illegal_transition_refused(self):
        sw = SwapSession(self.j, "CLAM", "DOGE", 10)
        sw.transition("QUOTED")
        with self.assertRaises(JournalRefusal):
            sw.transition("CLOSED")

    def test_full_walk_and_funds_tracking(self):
        sw = SwapSession(self.j, "CLAM", "DOGE", 10)
        for st in ["QUOTED", "LEG1_WORKING", "LEG1_FILLED", "LEG2_WORKING",
                   "LEG2_FILLED", "PAYOUT_SENT", "READBACK_VERIFIED",
                   "CLOSED"]:
            sw.transition(st, funds_at=f"at {st}")
        rows = self.j.rows()
        self.assertEqual([r["state"] for r in rows],
                         ["QUOTED", "LEG1_WORKING", "LEG1_FILLED",
                          "LEG2_WORKING", "LEG2_FILLED", "PAYOUT_SENT",
                          "READBACK_VERIFIED", "CLOSED"])
        self.assertEqual(rows[-1]["funds_at"], "at CLOSED")

    def test_cap_refusal(self):
        sw = SwapSession(self.j, "CLAM", "DOGE", 10, cap=0.0002)
        sw.transition("QUOTED")
        with self.assertRaises(JournalRefusal):
            sw.transition("LEG1_WORKING", mid_notional=0.001)

    def test_cap_refusal_on_hub_shortcut(self):
        # Issue #3 regression: when the source IS the hub asset there is
        # no leg 1 — QUOTED -> LEG2_WORKING is legal — and the cap must
        # still refuse an over-cap swap entering that working leg.
        sw = SwapSession(self.j, "BTC", "DOGE", 10, cap=0.0002)
        sw.transition("QUOTED")
        with self.assertRaises(JournalRefusal):
            sw.transition("LEG2_WORKING", mid_notional=0.001)
        self.assertEqual(sw.state, "QUOTED")
        self.assertEqual([r["state"] for r in self.j.rows()], ["QUOTED"])

    def test_cap_refusal_on_leg2_after_leg1_filled(self):
        # The other legal entry into LEG2_WORKING is capped too: the cap
        # is enforced on every transition into a working leg.
        sw = SwapSession(self.j, "CLAM", "DOGE", 10, cap=0.0002)
        sw.transition("QUOTED")
        sw.transition("LEG1_WORKING", mid_notional=0.0001)
        sw.transition("LEG1_FILLED")
        with self.assertRaises(JournalRefusal):
            sw.transition("LEG2_WORKING", mid_notional=0.001)
        self.assertEqual(sw.state, "LEG1_FILLED")

    def test_hub_shortcut_under_cap_passes(self):
        sw = SwapSession(self.j, "BTC", "DOGE", 10, cap=0.0002)
        sw.transition("QUOTED")
        sw.transition("LEG2_WORKING", mid_notional=0.0001)
        self.assertEqual(sw.state, "LEG2_WORKING")

    def test_abort_from_any_state(self):
        sw = SwapSession(self.j, "CLAM", "DOGE", 10)
        sw.transition("QUOTED")
        sw.abort("book moved")
        self.assertEqual(sw.state, "ABORTED")
        self.assertEqual(self.j.rows()[-1]["note"], "book moved")


if __name__ == "__main__":
    unittest.main()
