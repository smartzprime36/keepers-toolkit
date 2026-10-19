"""Tests for the transaction reader. Run: python3 -m unittest test_tx_parse -v

Fixtures are SYNTHETIC (fixtures/synthetic_tx_fixtures.json): transactions
constructed byte by byte for testing — never broadcast, no real funds or
wallets involved.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tx_parse

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "fixtures", "synthetic_tx_fixtures.json")


def load_fixtures():
    with open(FIXTURES) as f:
        return json.load(f)["fixtures"]


class TestBase58Check(unittest.TestCase):
    def test_known_vector(self):
        # The best-known Base58Check example: version 0x00 + 20 zero
        # bytes of hash160. Independent of chain versions used here.
        self.assertEqual(tx_parse.b58check_encode(0x00, bytes(20)),
                         "1111111111111111111114oLvT2")


class TestFixtures(unittest.TestCase):
    def test_all_fixtures_parse_to_expectations(self):
        for fx in load_fixtures():
            with self.subTest(fixture=fx["id"]):
                got = tx_parse.decode_hex(fx["raw_hex"])
                exp = fx["expect"]
                self.assertEqual(got["chain"], fx["chain"])
                self.assertEqual(got["txid"], exp["txid"])
                self.assertEqual(got["version"], exp["version"])
                self.assertEqual(got["ntime"], exp["ntime"])
                self.assertEqual(len(got["inputs"]), exp["vin"])
                self.assertEqual(len(got["outputs"]), exp["vout"])
                self.assertEqual(got["total_out_sats"],
                                 exp["total_out_sats"])
                self.assertEqual(got["speech"], exp["speech"])
                self.assertEqual(got["locktime"], exp["locktime"])
                for gin, ein in zip(got["inputs"], exp["inputs"]):
                    self.assertEqual(gin["txid"], ein["txid"])
                    self.assertEqual(gin["vout"], ein["vout"])
                for gout, eout in zip(got["outputs"], exp["outputs"]):
                    self.assertEqual(gout["address"], eout["address"])
                    self.assertEqual(gout["amount_sats"],
                                     eout["amount_sats"])
                    self.assertEqual(gout["script_type"],
                                     eout["script_type"])

    def test_chain_detection(self):
        for fx in load_fixtures():
            raw = bytes.fromhex(fx["raw_hex"])
            self.assertEqual(tx_parse.detect_chain(raw), fx["chain"])

    def test_trailing_bytes_rejected(self):
        fx = load_fixtures()[0]
        raw = bytes.fromhex(fx["raw_hex"]) + b"\x00"
        with self.assertRaises(Exception):
            tx_parse.parse(raw, fx["chain"])

    def test_wrong_chain_rejected(self):
        for fx in load_fixtures():
            other = "CLAM" if fx["chain"] == "DOGE" else "DOGE"
            raw = bytes.fromhex(fx["raw_hex"])
            with self.assertRaises(Exception):
                tx_parse.parse(raw, other)


if __name__ == "__main__":
    unittest.main()
