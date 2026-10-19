# Journal-before-order — the spec

The discipline in one sentence: **an operation does not exist until its
journal line is written.** Intent is recorded before action, every step
appends its own line, and the journal is append-only — corrections are
new rows, never edits. If "where are the funds right now" cannot be
answered from the journal alone, the operation does not proceed.

This spec defines three journal formats and the rules that bind them.
`journal.py` in this folder is the reference implementation.

---

## 1. Formats

### 1.1 Send journal (CSV)

One file per operation desk. Columns, in order:

| column   | meaning |
|----------|---------|
| `at_utc` | ISO-8601 UTC timestamp of the row, `YYYY-MM-DDTHH:MM:SSZ` |
| `kind`   | row kind, from the lifecycle below |
| `chain`  | chain ticker, e.g. `CLAM`, `DOGE`, `SOL` |
| `detail` | free text carrying the facts: parties, integer amounts, txids |

Row kinds, in lifecycle order:

- `INTENT` — a live send is declared, before anything is built.
- `INTENT-DRY` — a dry-run send is declared. A dry run builds and
  self-verifies a transaction but never broadcasts it.
- `DRY-BUILT` — the dry-run transaction was built; its txid is recorded
  with the words "not broadcast".
- `BROADCAST` — the transaction was broadcast; txid recorded.
- `BROADCAST-FAILED` — the broadcast path failed. The row must state
  that nothing was sent, so the inputs remain unspent and accounted.
- `READBACK` — an independent source (not the broadcast path) shows
  the transaction. Only now is the send "sent".
- `CORRECTION` — a later row that amends an earlier one by reference.
  The earlier row is never edited or deleted.

Amounts in `detail` are integer subunits (`amount_sats=… fee_sats=…`)
so a journal can be re-added by a reader with no float ambiguity.

### 1.2 Swap journal (CSV)

One row per state transition of one swap:

| column    | meaning |
|-----------|---------|
| `at`      | ISO-8601 UTC timestamp of the transition |
| `swap_id` | `YYYYMMDD-<8 hex>` — one id for the life of the swap |
| `state`   | the state entered (§2) |
| `from`    | source asset ticker |
| `to`      | target asset ticker |
| `amount`  | amount of the source asset |
| `mode`    | execution mode, e.g. `PATIENT` (resting limit orders) |
| `funds_at`| **where the funds are at this moment**, in plain words |
| `note`    | the facts of the transition: ticket, fills, fees, txids |

The `funds_at` column is not decoration. It is the column that makes
the journal a complete answer to "where are the coins right now" at
every point in the swap's life — including mid-flight, including
aborted.

### 1.3 Watch-only journal (CSV)

For addresses you observe but cannot spend from:

| column         | meaning |
|----------------|---------|
| `timestamp_utc`| ISO-8601 UTC timestamp of the observation |
| `chain`        | chain ticker |
| `address`      | the watched address |
| `balance`      | balance as read, in native coin units |
| `note`         | observer's note |

See §4 for the rules that make watch-only a hard boundary, not a
preference.

---

## 2. The swap state machine

```
QUOTED ──► LEG1_WORKING ──► LEG1_FILLED ──► LEG2_WORKING ──► LEG2_FILLED
  │                                                    │
  │                                                    ▼
  │                                              PAYOUT_SENT
  │                                                    │
  │                                                    ▼
  │                                          READBACK_VERIFIED ──► CLOSED
  │
  └── (any non-terminal state) ──► ABORTED
```

- The first transition is always `QUOTED`, journaled with the full
  ticket (route, gross amounts, every fee, estimated receive labeled
  as an estimate) **before any leg is placed** — in dry-run and in
  live mode alike.
- Legs are the two halves of a routed swap: leg 1 moves the source
  asset into the hub asset; leg 2 moves the hub asset into the
  target. When the source *is* the hub asset, `QUOTED` proceeds
  directly to the leg-2 states; when the target *is* the hub asset,
  `LEG1_FILLED` proceeds directly to `LEG2_FILLED`.
- `PAYOUT_SENT` is not completion. Completion is
  `READBACK_VERIFIED`: an independent source shows the payout at its
  destination. Only then `CLOSED`.
- `ABORTED` is reachable from every non-terminal state and always
  carries its reason in `note`. An aborted swap's journal must still
  answer where the funds are.
- A per-swap notional cap is checked when leg 1 starts: a swap whose
  mid-leg notional exceeds the cap is refused at the cap, in the
  journal, before it can work.

---

## 3. The refusal rules

These are the rules the reference implementation enforces in code.
They are the product. Everything else is plumbing.

1. **Journal first.** No build, no signature, no broadcast before the
   intent line exists. Code paths that act without a prior intent row
   raise a refusal, not a warning.
2. **Dry-run by default.** A session is dry unless constructed
   explicitly live. A dry session may build and journal; it can never
   broadcast, and its broadcast method refuses out loud.
3. **Watch-only can never send.** A wallet classified watch-only has
   no send path — not a disabled button, an absent one. Classification
   is a property of the wallet record, checked before any send flow
   begins.
4. **Fees are stated before the send.** Amount and fee, in integer
   subunits, are part of the intent line. There is no "fee to be
   estimated at broadcast".
5. **No invented change.** When a UTXO send creates change, it returns
   to the source address. The tool never derives or invents a fresh
   change address.
6. **The empty-wallet stop.** Before intent, spendability is asserted:
   unknown balance refuses; zero balance refuses everything; balance
   below amount + fee refuses with the numbers stated.
7. **Read-back or it didn't happen.** A broadcast is a claim, not a
   fact. The send completes only when an independent source shows it.
   If read-back disagrees with the broadcast claim, the journal says
   so and the next step is investigation — **never a blind re-send**.
8. **Explicit input selection.** UTXO inputs are selected by a stated
   rule (the reference bench: a single UTXO, or an explicit
   largest-first set), and inputs that come from a local ledger are
   used only if that ledger verified them at funding time. Inputs are
   never inferred from an explorer at send time when a verified ledger
   exists.
9. **Corrections are new rows.** History is never rewritten. If a row
   was wrong, a `CORRECTION` row says what was wrong and what is true.
10. **The toolkit never holds keys.** Signing and broadcasting are
    interfaces the operator implements with their own custody
    (see `journal.py`: `Signer`, `Broadcaster`). No key material, of
    any chain, in any form, belongs in a journal, a state file, or
    this toolkit.

---

## 4. Watch-only journals

A watch-only journal observes addresses — your own cold wallets, a
counterparty's published address, a project's treasury — without any
spending capability anywhere in the loop:

- Reads come from public chain APIs, called directly by the observer.
  No intermediary server needs to see the address.
- The journal stores observations (balance + note + time) and exports
  the §1.3 CSV.
- There is **never** a key field, a seed field, or a send function in
  a watch-only surface. If a design sketch adds one, it is no longer
  watch-only and must be reclassified before it is built.

---

## 5. What this spec is not

Not a wallet. Not a signing library. Not financial advice, and not a
promise that following it makes any operation safe — it makes
operations *accountable*: every claim an operator makes about a send
can be checked against lines that were written before the outcome was
known. That, and nothing more, is what a journal buys you.
