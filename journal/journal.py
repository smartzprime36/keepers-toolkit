"""Keeper's Toolkit — journal-before-order discipline (reference module).

The rule this module exists to enforce:

    NO SEND EXISTS UNTIL ITS JOURNAL LINE IS WRITTEN.

Every operation — a simple send or a multi-leg swap — begins as a journal
line declaring intent, written *before* anything is built, signed, or
broadcast. Every later step appends its own line. The journal is
append-only: corrections are new rows, never edits. If you cannot answer
"where are the funds right now" from the journal alone, the operation
does not proceed.

Two journal formats are supported (see SPEC.md for the full contract):

* the send journal  — columns: at_utc, kind, chain, detail
* the swap journal  — columns: at, swap_id, state, from, to, amount,
                      mode, funds_at, note

Dry-run is the default everywhere. A session only touches a broadcaster
when constructed with ``live=True`` — and even then, only through a
broadcaster object *you* supply.

The toolkit never holds keys. Signing is a placeholder interface
(:class:`Signer`) that you implement with whatever custody you trust —
a hardware wallet, an HSM, a separate signing host. No implementation
of it ships here, on purpose.

Pure standard library. Python 3.10+.
"""

import csv
import os
import time
import uuid

# --------------------------------------------------------------------------
# Formats (SPEC.md §1)
# --------------------------------------------------------------------------

SEND_FIELDS = ["at_utc", "kind", "chain", "detail"]
SWAP_FIELDS = ["at", "swap_id", "state", "from", "to", "amount", "mode",
               "funds_at", "note"]

# Send-journal row kinds, in lifecycle order.
SEND_KINDS = ["INTENT", "INTENT-DRY", "DRY-BUILT", "BROADCAST",
              "BROADCAST-FAILED", "READBACK", "CORRECTION"]

# --------------------------------------------------------------------------
# Swap state machine (SPEC.md §2)
#
#   QUOTED -> LEG1_WORKING -> LEG1_FILLED -> LEG2_WORKING -> LEG2_FILLED
#          -> PAYOUT_SENT -> READBACK_VERIFIED -> CLOSED
#   (any non-terminal state) -> ABORTED
#
# Shortcuts the reference bench uses, kept here: when the source asset IS
# the hub asset there is no leg 1 (QUOTED -> LEG2_*); when the target IS
# the hub asset there is no leg 2 (LEG1_FILLED -> LEG2_FILLED directly).
# --------------------------------------------------------------------------

SWAP_STATES = ["QUOTED", "LEG1_WORKING", "LEG1_FILLED", "LEG2_WORKING",
               "LEG2_FILLED", "PAYOUT_SENT", "READBACK_VERIFIED",
               "CLOSED", "ABORTED"]

_TRANSITIONS = {
    "QUOTED":            {"LEG1_WORKING", "LEG2_WORKING", "LEG2_FILLED",
                          "ABORTED"},
    "LEG1_WORKING":      {"LEG1_FILLED", "ABORTED"},
    "LEG1_FILLED":       {"LEG2_WORKING", "LEG2_FILLED", "ABORTED"},
    "LEG2_WORKING":      {"LEG2_FILLED", "ABORTED"},
    "LEG2_FILLED":       {"PAYOUT_SENT", "ABORTED"},
    "PAYOUT_SENT":       {"READBACK_VERIFIED", "ABORTED"},
    "READBACK_VERIFIED": {"CLOSED", "ABORTED"},
    "CLOSED":            set(),
    "ABORTED":           set(),
}

TERMINAL_STATES = {"CLOSED", "ABORTED"}

# Example per-swap notional cap, in hub-asset (BTC) terms, taken from the
# reference bench's v0 rules. A cap is part of the discipline: set your
# own, in writing, before you run anything live.
DEFAULT_PER_SWAP_CAP = 0.0002


def utcnow():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class JournalRefusal(Exception):
    """Raised when the discipline refuses an operation.

    A refusal is a designed outcome, not an error: the journal records
    what did NOT happen and why, and the operation stops.
    """


# --------------------------------------------------------------------------
# Placeholder interfaces — bring your own. The toolkit never holds keys.
# --------------------------------------------------------------------------

class Signer:
    """Signing interface. YOU implement this with your own custody.

    The toolkit ships no implementation: it never sees, stores, derives,
    or transmits key material of any kind. A typical implementation
    delegates to a hardware wallet or a separate signing host and
    returns the signed transaction bytes.
    """

    def sign(self, unsigned_tx: bytes) -> bytes:
        raise NotImplementedError(
            "bring your own signer — the toolkit never holds keys")


class Broadcaster:
    """Broadcast interface. YOU implement this for your chain/venue.

    Called only by a live session, only after the journal line for the
    step exists. Should return the transaction id as reported by the
    broadcast path; the caller must still verify by independent
    read-back (see SendSession.verify_readback).
    """

    def broadcast(self, chain: str, signed_tx: bytes) -> str:
        raise NotImplementedError("bring your own broadcaster")


# --------------------------------------------------------------------------
# The journal itself: append-only CSV, one writer, no edits.
# --------------------------------------------------------------------------

class Journal:
    """Append-only CSV journal. Create one per format (send or swap)."""

    def __init__(self, path, fields):
        self.path = path
        self.fields = fields

    def append(self, row):
        """Append one row. This is the only write operation that exists."""
        missing = [f for f in self.fields if f not in row]
        if missing:
            raise JournalRefusal(f"journal row missing fields: {missing}")
        new_file = not os.path.exists(self.path)
        with open(self.path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self.fields,
                               extrasaction="ignore")
            if new_file:
                w.writeheader()
            w.writerow({f: row[f] for f in self.fields})

    def rows(self):
        if not os.path.exists(self.path):
            return []
        with open(self.path, newline="") as f:
            return list(csv.DictReader(f))

    def has_row(self, **match):
        """True if a row exists whose fields equal all given values."""
        return any(all(r.get(k) == v for k, v in match.items())
                   for r in self.rows())


# --------------------------------------------------------------------------
# Spendability gate — the empty-wallet stop (SPEC.md §3, rule 6).
# --------------------------------------------------------------------------

def assert_spendable(balance_sats, amount_sats, fee_sats):
    """Refuse a send the wallet cannot fund. Called BEFORE intent.

    The empty-wallet stop is absolute: a wallet at zero refuses every
    send, and any wallet refuses a send whose amount + stated fee
    exceeds its spendable balance. Fees are stated, in integer
    subunits, before the send exists — never estimated after the fact.
    """
    if balance_sats is None:
        raise JournalRefusal("balance unknown — read it back first")
    if balance_sats <= 0:
        raise JournalRefusal("empty wallet — send refused")
    need = amount_sats + fee_sats
    if balance_sats < need:
        raise JournalRefusal(
            f"insufficient: have {balance_sats} sats, need {need} sats "
            f"(amount {amount_sats} + fee {fee_sats})")


# --------------------------------------------------------------------------
# Send session — one send, journal-first, dry-run by default.
# --------------------------------------------------------------------------

class SendSession:
    """A single send under the discipline.

    Lifecycle: open() writes INTENT (or INTENT-DRY) -> built() ->
    broadcast() [live only] -> verify_readback(). No step can run
    before the step before it has its journal line; attempting one
    raises JournalRefusal and nothing moves.
    """

    def __init__(self, journal, chain, from_wallet, to_address,
                 amount_sats, fee_sats, live=False):
        self.journal = journal
        self.chain = chain
        self.from_wallet = from_wallet
        self.to_address = to_address
        self.amount_sats = int(amount_sats)
        self.fee_sats = int(fee_sats)
        self.live = bool(live)
        self._opened = False
        self._built_txid = None
        self._broadcast_txid = None

    # -- internal ------------------------------------------------------
    def _line(self, kind, detail):
        self.journal.append({"at_utc": utcnow(), "kind": kind,
                             "chain": self.chain, "detail": detail})

    def _require_open(self, step):
        if not self._opened:
            raise JournalRefusal(
                f"{step} refused: no intent line exists for this send — "
                "the journal line is written first, always")

    # -- steps ---------------------------------------------------------
    def open(self):
        """Write the intent line. This is what makes the send exist."""
        kind = "INTENT" if self.live else "INTENT-DRY"
        self._line(kind,
                   f"{self.from_wallet} -> {self.to_address} "
                   f"amount_sats={self.amount_sats} "
                   f"fee_sats={self.fee_sats}")
        self._opened = True
        return self

    def built(self, txid):
        """Record that a signed transaction was built (not broadcast)."""
        self._require_open("build")
        self._built_txid = txid
        if not self.live:
            self._line("DRY-BUILT", f"txid {txid} (not broadcast)")
        return self

    def broadcast(self, broadcaster, signed_tx):
        """Broadcast via YOUR broadcaster. Live sessions only.

        In dry-run this refuses: a dry session can build and journal,
        but it can never put anything on a network.
        """
        self._require_open("broadcast")
        if not self.live:
            raise JournalRefusal(
                "broadcast refused: this is a dry-run session — "
                "nothing was sent")
        if self._built_txid is None:
            raise JournalRefusal(
                "broadcast refused: no built transaction is journaled")
        txid = broadcaster.broadcast(self.chain, signed_tx)
        self._broadcast_txid = txid
        self._line("BROADCAST", f"txid {txid}")
        return txid

    def verify_readback(self, seen_txid):
        """Close the loop with an INDEPENDENT read-back.

        ``seen_txid`` must come from a source other than the broadcast
        path (an explorer, a second node, your balance board). A send
        is not 'sent' until an independent source shows it.
        """
        self._require_open("read-back")
        if self.live and seen_txid != self._broadcast_txid:
            raise JournalRefusal(
                f"read-back mismatch: broadcast {self._broadcast_txid}, "
                f"independent source shows {seen_txid} — investigate "
                "before any re-send; never blind re-send")
        self._line("READBACK", f"txid {seen_txid} confirmed by read-back")
        return self


# --------------------------------------------------------------------------
# Swap session — the multi-leg state machine, journaled at every step.
# --------------------------------------------------------------------------

class SwapSession:
    """A swap under the discipline.

    The first transition MUST be QUOTED, and it is journaled with the
    full ticket before any leg is placed. Every transition records
    ``funds_at`` — where the funds are at that moment — so the journal
    alone always answers "where are the coins right now".
    """

    def __init__(self, journal, frm, to, amount, mode="PATIENT",
                 cap=DEFAULT_PER_SWAP_CAP):
        self.journal = journal
        self.id = (time.strftime("%Y%m%d") + "-" +
                   uuid.uuid4().hex[:8])
        self.frm, self.to = frm.upper(), to.upper()
        self.amount = float(amount)
        self.mode = mode
        self.cap = cap
        self.state = None
        self.funds_at = "operator wallet (not yet moved)"

    def transition(self, state, note="", funds_at=None, mid_notional=None):
        if state not in SWAP_STATES:
            raise JournalRefusal(f"unknown swap state: {state}")
        if self.state is None:
            if state != "QUOTED":
                raise JournalRefusal(
                    "first transition must be QUOTED — the ticket is "
                    "journaled before any leg exists")
        elif state not in _TRANSITIONS[self.state]:
            raise JournalRefusal(
                f"illegal transition {self.state} -> {state}")
        if (state == "LEG1_WORKING" and mid_notional is not None
                and mid_notional > self.cap):
            raise JournalRefusal(
                f"mid-leg notional {mid_notional:.8f} exceeds the "
                f"per-swap cap {self.cap:.8f} — swap refused at the cap")
        if funds_at:
            self.funds_at = funds_at
        self.state = state
        self.journal.append({
            "at": utcnow(), "swap_id": self.id, "state": state,
            "from": self.frm, "to": self.to, "amount": self.amount,
            "mode": self.mode, "funds_at": self.funds_at, "note": note})
        return self

    def abort(self, reason):
        """Abort from any non-terminal state, with the reason journaled."""
        if self.state in TERMINAL_STATES:
            raise JournalRefusal(f"cannot abort a {self.state} swap")
        return self.transition("ABORTED", note=reason)


# --------------------------------------------------------------------------
# Watch-only journal (SPEC.md §4) — bring-your-own-address observations.
# --------------------------------------------------------------------------

WATCH_FIELDS = ["timestamp_utc", "chain", "address", "balance", "note"]


def watch_journal(path):
    """A journal for watch-only address observations.

    Watch-only means exactly that: an address you observe but cannot
    spend from. This journal records balances and notes over time.
    There is no send path here, by design — see SPEC.md §4.
    """
    return Journal(path, WATCH_FIELDS)
