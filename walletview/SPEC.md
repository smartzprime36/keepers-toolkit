# Wallet view — the watch-only spec

A wallet view has one job: show what is true, in a way that cannot be
mistaken for control. This spec defines the data shape, the two
visual classes, and the interaction rules. `render_board.py` is a
minimal reference implementation.

## 1. Data shape (the board)

A board is a timestamped snapshot of wallet rows:

```json
{
  "as_of_utc": "2026-01-01T00:00:00Z",
  "rows": [
    {"name": "…", "chain": "CLAM", "address": "…",
     "kind": "house-key", "balance": 12.5, "source": "public-api",
     "ok": true}
  ]
}
```

| field     | meaning |
|-----------|---------|
| `name`    | operator-chosen label |
| `chain`   | chain ticker |
| `address` | the wallet's public address |
| `kind`    | `house-key`, `hd`, or `watch-only` (§2) |
| `balance` | native coin only. Token balances, if ever shown, are a separate array — never folded into the native figure |
| `source`  | where the balance was read from |
| `ok`      | whether the read succeeded |
| `error`   | present when `ok` is false; the row renders as an error, never as a zero |

Rules that travel with the shape:

- A failed read is an **error row**, not a 0.00000000. A board that
  renders outages as empty wallets teaches operators to panic — or
  worse, to re-send.
- Exchange deposit addresses are not wallets. They are venue
  property; venue balances belong to the venue's own accounting,
  never to this board.
- Every row carries its read source and the snapshot its timestamp.
  A balance without a source and a time is a rumor.

## 2. The two visual classes (a rule, not a theme)

`watch-only` is a **visual class**, not a permission dialog:

- **Spending-capable rows** (`house-key`, `hd`): solid treatment,
  may carry a send affordance.
- **Watch-only rows**: visually distinct at a glance (the reference
  implementation uses a dashed border, an eye marker, and a
  `WATCH-ONLY` tag) and **carry no send control anywhere** — not a
  disabled button, not a greyed menu item: nothing. A control that
  exists but is disabled invites the day someone enables it by
  accident. Absence is the feature.

Classification is a property of the wallet record, decided when the
wallet is registered — never inferred at render time from whether a
key happens to be loaded.

## 3. The send composer (journal-acknowledgement gating)

Where a spending-capable row does offer a send flow, the composer
enforces the journal discipline (see `../journal/SPEC.md`) in the
interaction itself:

1. The operator composes the exact journal line the send will write.
2. The line is rendered, in full, **before** the action control.
3. The action control stays disabled until the operator explicitly
   acknowledges the composed line.
4. **Dry-run is the default state of the screen** — a visible banner,
   not fine print. Switching to live is a deliberate act.
5. The flow ends at a **read-back panel**, not a success toast: the
   send shows as sent only when an independent source shows it.
6. The full fee stack is a first-class panel on the ticket — every
   fee itemized — and any estimated receive figure is labeled
   ESTIMATE wherever it appears. Quotes carry their read timestamp
   and go visibly stale.
7. Errors state what did **not** happen before what to do next:
   "nothing was sent" comes first.

## 4. Control plane vs evidence plane

A console that can act is a **control plane** and is private by
default: local-only or authenticated, never a public page with live
controls. Receipts, readers, and journals are the **evidence plane**
and may be public — they show what happened and can do nothing.
Keep the two planes separate in hosting, in code, and in your head.

## 5. Bring-your-own-address journaling

The public-facing sibling of this view: a visitor pastes *their own*
address and journals observations of it over time (format:
`../journal/SPEC.md` §1.3). The contract:

- Reads are made directly from the visitor's browser to public chain
  APIs. No server of the operator's ever sees the address — a claim
  the visitor can verify in their own network tab, which is stronger
  than any "we don't log" promise.
- The journal lives with the visitor (e.g. local storage) and
  exports CSV.
- Never on such a page: a key field, a seed field, a send function,
  analytics on the address. The watch-only rule is stated on the page
  in plain words.
