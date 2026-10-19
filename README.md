# The Keeper's Toolkit

Wallet discipline, as code anyone can run.

Most wallet tooling answers "how do I send?" This toolkit answers the
question that matters the morning after: **"prove what happened —
from records written before the outcome was known."** It is the
operating discipline of a small multi-chain bench, extracted and
published so other small operators can run it too.

## The discipline, on one page

1. **Journal first.** An operation does not exist until its journal
   line is written. Intent is recorded before anything is built,
   signed, or broadcast — and the journal is append-only, so the
   record can't quietly agree with the outcome.
2. **Dry-run by default.** Building and self-verifying a transaction
   is free. Broadcasting is a separate, deliberate, explicit act.
3. **Watch-only is a class, not a checkbox.** A wallet you cannot
   spend from has no send control anywhere in its view. Absence, not
   disabling.
4. **Fees are stated before the send**, in integer subunits, in the
   intent line. Nothing is "estimated at broadcast".
5. **The empty-wallet stop.** Unknown balance refuses. Zero balance
   refuses everything. Less than amount + fee refuses with the
   numbers stated.
6. **Read-back or it didn't happen.** A broadcast is a claim. A send
   is complete only when an independent source shows it — and a
   mismatch means investigate, never blind re-send.
7. **Where are the funds right now?** Every state of every operation
   records the answer, in plain words, in the journal. If the journal
   can't answer it, the operation doesn't proceed.
8. **The toolkit never holds keys.** Signing and broadcasting are
   interfaces you implement with your own custody. No key material
   belongs in a journal, a state file, or this repository.

## What's in the box

| folder | what it is |
|--------|------------|
| `journal/` | The discipline itself: `SPEC.md` (the three journal formats, the swap state machine, the ten refusal rules) and `journal.py`, a dependency-free reference implementation with a synthetic demo (`examples.py`) |
| `txreader/` | A CLAM / DOGE transaction parser that knows the ways these chains differ from Bitcoin (nTime, ClamSpeech) and detects the chain by exact fit. Synthetic fixtures + tests included |
| `walletview/` | The watch-only wallet view: `SPEC.md` (data shape, the two visual classes, journal-acknowledgement gating on the send composer) and `render_board.py`, a minimal reference renderer |

## Run the tests

```
python3 run_tests.py
```

(or per folder: `python3 -m unittest discover` inside each.) All
tests run offline against synthetic data. The fixtures in this
repository were constructed for testing — no real transactions,
wallets, or funds appear anywhere in it.

## Provenance

Written by the SMARTZ Syndicate's TriChain bench, which runs this
discipline on live sends across CLAM, DOGE, and Solana, and needed
the tooling to exist before anything else could be built honestly.
Published under the MIT License (see `LICENSE`) in the belief that
facts and methods about public chains belong to everyone working
on them.

## A note on scope

This is education and bookkeeping tooling. It is not a wallet, not a
signing library, not financial advice, and not a promise of safety —
it is a promise of *accountability*: every claim an operator makes
about an operation can be checked against lines written before the
outcome was known.

Verify first. Trust last.
