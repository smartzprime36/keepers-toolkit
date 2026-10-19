# Contributing to the Keeper's Toolkit

This toolkit teaches wallet discipline: journal first, dry-run by
default, watch-only means *no send control anywhere*, and read-back
or it didn't happen. Contributions are welcome — a small, correct
PR that sharpens the discipline is worth more than a large one that
blurs it.

Start with `GOOD_FIRST_ISSUES.md` in this repo (also labelled
`good first issue` on the issue tracker). Those are real seams in
the code, sized for a first PR.

## The clean-room rule (read this before anything else)

This repository is public, and it stays clean enough to publish
forever. That means:

- **Never submit real key material of any kind** — no private keys,
  seed phrases, or mnemonics. Not yours, not anyone's, not "just a
  test wallet's". There are no exceptions, and that includes
  published standard test vectors: mnemonic-shaped text does not
  ship here at all. (This repo deliberately removed such a file
  before publication — see `SCRUB.md`.)
- **Never submit real operational data** — no real wallet files, no
  real journals, no real transaction hex, no real addresses tied to
  real funds. A bug report that needs an example gets a *synthetic*
  example, constructed for the purpose.
- **Synthetic fixtures only, constructed byte by byte.** The
  existing fixtures in `txreader/fixtures/` were built byte by byte
  for the tests, with expectations recorded at construction time,
  and are labelled synthetic in the file. New fixtures follow the
  same pattern: invented values, visibly constructed, expectations
  written down when you build them — never copied from a live
  chain.
- Maintainers run the `SCRUB.md` grep classes (seed / mnemonic /
  key / token / password / `.env` / IP patterns / long base58 and
  hex strings) over contributions before merge. A PR that trips
  them will be asked to rebuild its examples synthetically, however
  good the code is.

If you find a way the toolkit itself could leak or mishandle key
material, open an issue describing the mechanism — with a synthetic
reproduction, never real material pasted in to demonstrate it.

## Setup

Nothing to install. Pure Python standard library, Python 3.10+.
Clone, and run the tests:

```
python3 run_tests.py
```

All tests run offline against synthetic data.

## Tests

- **All suites must pass.** Current count: **29 tests** —
  `journal` 16, `txreader` 5, `walletview` 8.
- New behaviour needs new tests. A PR that changes what the code
  does without a test that pins the new behaviour will be sent
  back for one.
- Refusals are behaviour. If your change adds or moves a refusal,
  the test asserts the refusal *and* its message — the message is
  part of the discipline, not decoration.

## Architectural invariants (not negotiable in review)

- **The reader never links signing code.** `txreader/` ships its
  own Base58Check copy precisely so it never imports a signing or
  derivation core. Reading and signing stay separate programs. A
  PR that imports signing/derivation code into `txreader/` will be
  declined on design grounds, not style grounds.
- **The toolkit never holds keys.** `Signer` and `Broadcaster` in
  `journal/journal.py` are placeholder interfaces on purpose; no
  implementation of them ships here.
- **The journal is append-only.** Corrections are new rows, never
  edits. No API that edits or deletes journal history will be
  merged.
- **Watch-only is absence, not disabling.** A watch-only surface
  gets no send control at all — not a greyed-out one.

## Style

- **Standard library first — in practice, standard library only.**
  The modules say "pure standard library" on their first page and
  mean it. A new third-party dependency needs a very good reason
  stated in the PR.
- Amounts are integer subunits in journals and fixtures
  (`amount_sats=…`); timestamps are UTC ISO-8601. No float money.
- Docstrings and comments speak plainly and say what the code
  *refuses* and why, in the voice of the existing files. Refusal
  messages state the numbers (have / need), not just "error".

## Pull requests

A good small PR here looks like: one fixture added with its
expectations, one refusal message made clearer with its test
updated, one docs page corrected, one edge case pinned by a test.
One PR, one purpose.

In the PR description, say: what changed, which invariant it
touches (or "none"), and the test run — `python3 run_tests.py`
output or the per-suite equivalent. No ceremony beyond that.

Expect review to check three things: tests green, invariants
intact, and nothing real in the examples. Fixes are usually small
follow-ups, not rewrites.

## Recognition

Contributors are named — in this repository and in the school's
public record — with the work attributed to them. A merged PR here
is public proof-of-work: a receipt you can point at forever, that
says you shipped discipline tooling other operators actually run.

To be plain about the terms: contributing is voluntary and unpaid.
There is no payment, bounty, token, or points arrangement attached
to it. The credit is the receipt — recognition, not compensation.

Verify first. Trust last.
