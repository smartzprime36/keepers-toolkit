# Good first issues — Keeper's Toolkit

Real seams in the code, sized for a stranger's first PR. Each issue
says why it matters, what the scope is, which files it touches, and
the test that proves it done. Read `CONTRIBUTING.md` first — the
clean-room rule (synthetic data only, constructed byte by byte)
applies to every one of these.

Run the whole suite before and after: `python3 run_tests.py`
(current count: 29 tests, all passing).

---

## 1. txreader: the README describes a fixtures file that isn't in the repo

**Why it matters.** `txreader/README.md` has a "Fixtures" section
describing `fixtures/test_vectors.json` — a file that does not exist
in this repository (it was deliberately removed before publication;
`SCRUB.md`'s review addendum records the removal and the reason). A
new reader following the docs goes looking for a missing file and
finds the docs disagreeing with the repo — the exact failure this
toolkit exists to prevent.

**Scope.** Rewrite the Fixtures section of `txreader/README.md` so
it describes only what actually ships: the synthetic fixtures file,
how it was constructed, and how the tests use it. Do not re-add any
file, and do not describe contents that aren't there.

**Files touched.** `txreader/README.md` only.

**Acceptance test.** Every path named in `txreader/README.md`
exists in the repo; `python3 run_tests.py` still passes (29).

**Difficulty.** First-PR size — under an hour.

---

## 2. txreader: add a synthetic OP_RETURN fixture, constructed byte by byte

**Why it matters.** The fixture set covers P2PKH and P2SH outputs
only. `script_address()` in `tx_parse.py` also returns `other` and
`empty` script kinds — an OP_RETURN (data-carrying) output is the
common real-world case that lands in `other`, and no fixture pins
how the parser reports it. Unpinned behaviour drifts.

**Scope.** Construct one new synthetic DOGE transaction byte by
byte containing an OP_RETURN output (zero value is fine and
typical) alongside a normal P2PKH output, and add it to
`fixtures/synthetic_tx_fixtures.json` in the existing format:
invented values, `synthetic: true`, a note saying it was
constructed for the toolkit, and full `expect` values (txid,
per-output address / amount / script_type, totals) recorded at
construction time. Follow the two existing fixtures as the pattern.

**Files touched.** `txreader/fixtures/synthetic_tx_fixtures.json`
(the fixture-driven test in `txreader/test_tx_parse.py` picks new
fixtures up automatically — no test-code change should be needed).

**Acceptance test.** `python3 -m unittest test_tx_parse -v` in
`txreader/` passes with the new fixture included in
`test_all_fixtures_parse_to_expectations`; full suite passes (29
plus any assertions the new fixture adds).

**Difficulty.** Easy–medium. The work is the byte construction:
getting the script, the varints, and the length prefixes right by
hand, then recording what the parser derives.

---

## 3. journal: the per-swap cap is not checked on the hub-shortcut path

**Why it matters.** `SwapSession.transition()` checks the per-swap
notional cap only when entering `LEG1_WORKING`. But the state
machine deliberately allows shortcuts: when the source asset *is*
the hub asset there is no leg 1, and `QUOTED → LEG2_WORKING` is a
legal transition — one that never passes the cap check. A cap with
a hole in it is worse than no cap: the journal claims a discipline
the code doesn't enforce. (`journal/SPEC.md` §2 states the cap as a
rule of the machine, not of one leg.)

**Scope.** Make the cap check fire on whichever working transition
comes first (`LEG1_WORKING` or `LEG2_WORKING`), so both the full
route and the hub-shortcut route are checked, keeping the existing
refusal message format (numbers stated). Behaviour on the existing
paths must not change.

**Files touched.** `journal/journal.py`, `journal/test_journal.py`.

**Acceptance test.** A new test mirrors the existing
`test_cap_refusal`: a swap opened `QUOTED → LEG2_WORKING` with
`mid_notional` above the cap raises `JournalRefusal` and appends no
state row; the existing 13 journal tests still pass; full suite
passes.

**Difficulty.** Medium. Small diff, but you have to understand the
state machine and its shortcuts before touching it — that reading
is the real work.

---

## 4. txreader: replace bare asserts with parse errors that say what failed and where

**Why it matters.** The parser's job is to refuse confident
nonsense — but its own failures are bare `assert` statements
(`"short read"`, a trailing-bytes count) and `detect_chain()`
swallows every exception, then reports "ambiguous/failed" without
saying why either chain rejected the bytes. An operator debugging a
malformed transaction gets nothing to investigate. A reader built
on "read-back or it didn't happen" should report its reads
precisely.

**Scope.** Introduce a named parse error (e.g. `ParseError`, a
`ValueError` subclass) raised with a message that states what
failed and where: truncation at a byte offset, trailing-byte count,
the field being read. `detect_chain()` should include each chain's
rejection reason in its failure message. `decode_hex()` keeps its
public behaviour — raise on bad input — with the better messages.
No parsing behaviour changes: anything that parsed before parses
identically.

**Files touched.** `txreader/tx_parse.py`,
`txreader/test_tx_parse.py`.

**Acceptance test.** Tests assert message content for the three
failure shapes (truncated input, trailing bytes, wrong-chain /
undetectable input); all existing fixture expectations unchanged;
full suite passes (29, with updated assertions where they pinned
bare `Exception`).

**Difficulty.** Medium.

---

## 5. journal: a read-only timeline viewer for journal CSVs

**Why it matters.** The toolkit writes journals and demos that
produce them, but ships no way to *read* one back as a story: an
operator auditing a swap today opens raw CSV. The discipline's
core question — "where were the funds at each step?" — should be
answerable by a tool, not by squinting at columns.

**Scope.** Add a small read-only viewer (a `journal/view.py` module
or a `__main__` path in `journal.py` — pick one and say why) that
takes a send- or swap-journal CSV path and prints an ordered,
human-readable timeline: timestamps, row kind / state, and for
swaps the `funds_at` text on every line. Read-only is a hard
requirement: the viewer must never open the journal for writing.
Handle both formats by their headers, and refuse an unrecognised
file with a clear message.

**Files touched.** `journal/journal.py` or new `journal/view.py`;
`journal/test_journal.py`.

**Acceptance test.** A test builds the demo swap journal (as
`examples.py` does), renders it with the viewer, and asserts the
timeline contains every state in order with its `funds_at` text;
a second test asserts the journal file's bytes are unchanged after
viewing; full suite passes.

**Difficulty.** Medium.

---

## 6. docs: write the five-minute first-run walkthrough

**Why it matters.** The README explains the discipline on one page,
but a new operator's first five minutes are unguided: nothing walks
them from clone to *seeing a refusal fire* — and the refusal firing
is the moment the toolkit makes sense.

**Scope.** Write `WALKTHROUGH.md` (repo root) that takes a fresh
clone through, in order: running the tests; running
`journal/examples.py` and reading the two journals it writes, row
by row (what each row kind means, where the dry-run broadcast
refusal appears and why); rendering `walletview/example_board.json`
with `render_board.py` and finding the two visual classes and the
absent button on the watch-only card. Every command must work
exactly as written — the author runs them all, in order, from a
clean checkout before submitting.

**Files touched.** New `WALKTHROUGH.md`; a one-line link from
`README.md`'s test section is welcome but optional.

**Acceptance test.** Maintainer follows the walkthrough from a
fresh clone using nothing else and reaches: green tests, two demo
journals, the refusal visible in the demo output, and a rendered
board — with zero improvisation. Full suite still passes (29).

**Difficulty.** Easy to write, exacting to verify — the
verification *is* the task.

---

## 7. walletview: render_board.py CLI — friendly errors instead of tracebacks

**Why it matters.** `render_board.py` is the first thing a new user
runs after the tests, and its failure modes are raw tracebacks:
no argument gives an `IndexError`; a missing file or malformed
JSON dumps a stack trace. Small, but this is the toolkit's front
door, and a discipline tool should fail the way its journals do —
a clear statement of what didn't happen.

**Scope.** Give `main()` real argument handling: no argument, a
missing file, or unparseable JSON each print a one-line usage /
error message to stderr and exit non-zero, with no traceback.
Valid input renders byte-identical output to today.

**Files touched.** `walletview/render_board.py`,
`walletview/test_render_board.py`.

**Acceptance test.** Tests cover the three failure shapes (exit
code non-zero, message on stderr, no traceback text); the existing
8 walletview tests pass unchanged and the example board renders
identically; full suite passes.

**Difficulty.** Easy.

---

*Want to claim one? Comment on the issue so two people don't build
the same fixture. New seam you spotted that isn't listed? Open an
issue describing it — the list grows from the code, not from a
roadmap.*
