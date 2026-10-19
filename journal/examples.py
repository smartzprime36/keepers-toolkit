"""Synthetic examples for the journal discipline — no network, no keys.

Runs a dry-run send and a dry-run routed swap against SYNTHETIC data
(the books below are invented numbers; the wallets are named roles,
not real wallets) and writes the two journals so you can see the
formats working. Run:

    python3 examples.py [output-dir]

Everything here is a demonstration of bookkeeping. Nothing moves.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from journal import (Journal, SEND_FIELDS, SWAP_FIELDS, SendSession,
                     SwapSession, assert_spendable)

# Invented order books: {asset: (bids, asks)} with (price_in_hub, qty).
SYNTHETIC_BOOKS = {
    "CLAM": ([(0.00000086, 5000.0), (0.00000085, 20000.0)],
             [(0.00000088, 5000.0), (0.00000090, 20000.0)]),
    "DOGE": ([(0.00000150, 10000.0), (0.00000148, 50000.0)],
             [(0.00000155, 10000.0), (0.00000158, 50000.0)]),
}


def walk_sell(book, amount):
    bids, _ = book
    hub, left = 0.0, amount
    for price, qty in bids:
        take = min(qty, left)
        hub += take * price
        left -= take
        if left <= 0:
            break
    return hub, amount - left


def walk_buy(book, hub_budget):
    _, asks = book
    got, spent, left = 0.0, 0.0, hub_budget
    for price, qty in asks:
        take = min(qty * price, left)
        got += take / price
        spent += take
        left -= take
        if left <= 0:
            break
    return got, spent


def demo_send(outdir):
    print("— dry-run send —")
    j = Journal(os.path.join(outdir, "journal.csv"), SEND_FIELDS)
    # The empty-wallet stop runs before intent exists.
    assert_spendable(balance_sats=1_000_000, amount_sats=400_000,
                     fee_sats=10_000)
    s = SendSession(j, chain="DOGE", from_wallet="house-example",
                    to_address="counterparty-example",
                    amount_sats=400_000, fee_sats=10_000)  # dry default
    s.open()
    s.built(txid="0" * 64)  # synthetic txid; a dry run builds, never sends
    try:
        s.broadcast(broadcaster=None, signed_tx=b"")
    except Exception as e:
        print(f"  broadcast refused as designed: {e}")
    print(f"  journal: {j.path}")


def demo_swap(outdir):
    print("— dry-run swap: 100 CLAM -> DOGE (PATIENT) —")
    j = Journal(os.path.join(outdir, "swaps_journal.csv"), SWAP_FIELDS)
    sw = SwapSession(j, "CLAM", "DOGE", 100.0)
    gross, filled = walk_sell(SYNTHETIC_BOOKS["CLAM"], sw.amount)
    if filled < sw.amount:
        sw.transition("QUOTED", note="ticket: book too thin in this demo")
        sw.abort("insufficient book depth for leg 1")
        return
    import math
    fee = math.ceil(gross * 1e8 * 0.01) / 1e8  # 1% venue fee, rounded up
    mid = gross - fee
    sw.transition(
        "QUOTED",
        note=f"ticket: leg1 gross {gross:.8f} BTC, fee {fee:.8f}, "
             f"mid {mid:.8f} BTC",
        funds_at="operator wallet (not yet moved)")
    sw.transition("LEG1_WORKING", note="[dry] limit sell rests at the book",
                  funds_at="venue account (leg 1 working)",
                  mid_notional=mid)
    sw.transition("LEG1_FILLED", note=f"[dry] filled; {mid:.8f} BTC in hub",
                  funds_at="venue account (BTC hub)")
    sw.transition("LEG2_WORKING", note="[dry] limit buy rests at the book",
                  funds_at="venue account (leg 2 working)")
    got, _ = walk_buy(SYNTHETIC_BOOKS["DOGE"], mid)
    receive = got * 0.99  # leg-2 fee charged in the received asset
    sw.transition("LEG2_FILLED",
                  note=f"[dry] bought {got:.8f} DOGE gross; "
                       f"net ~{receive:.8f}",
                  funds_at="venue account (DOGE)")
    sw.transition("PAYOUT_SENT", note="[dry] payout send simulated",
                  funds_at="in transit (simulated)")
    sw.transition("READBACK_VERIFIED",
                  note="[dry] independent read-back simulated",
                  funds_at="operator DOGE wallet (simulated)")
    sw.transition("CLOSED",
                  note=f"[dry] swap complete; receive ~{receive:.8f} DOGE "
                       "before payout fees")
    print(f"  journal: {j.path}")


if __name__ == "__main__":
    outdir = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(
        prefix="keepers-journal-demo-")
    os.makedirs(outdir, exist_ok=True)
    demo_send(outdir)
    demo_swap(outdir)
    print(f"demo journals written to {outdir}")
