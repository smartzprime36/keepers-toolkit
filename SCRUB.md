# SCRUB — Keeper's Toolkit v0.1

How this package was extracted from an operational bench, what was
kept out, and what the scrub pass found. Written for the human who
reviews before anything is published.

## Method

Files were **adapted, not copied**, from the source bench. Where a
source file mixed the publishable discipline with operations
(infrastructure, key handling, live state), the discipline was
rewritten against a placeholder interface and the operations were
left behind. After assembly, the whole package was grepped class by
class (results below) and every hit reviewed in context.

## Files included, and their sources

| package file | source / origin |
|---|---|
| `README.md` | written for the package |
| `LICENSE` | standard MIT text; holder is the author credit (see grep notes) |
| `run_tests.py` | written for the package |
| `journal/journal.py` | rewritten from the discipline in the bench's send + swap engine code: journal formats, state machine, refusal rules. Signing/broadcast seams replaced with the `Signer` / `Broadcaster` placeholder interfaces |
| `journal/SPEC.md` | written from the bench's journal formats (both CSV headers), its state schema document, and its watch-only journal spec — generalized, house specifics removed |
| `journal/examples.py` | written for the package; invented books, role-named wallets, no network |
| `journal/test_journal.py` | written for the package |
| `txreader/tx_parse.py` | the bench's transaction parser, adapted: bench path wiring removed; its one external dependency (a Base58Check encoder from the bench's signing core) re-implemented locally so the reader never links signing code |
| `txreader/fixtures/synthetic_tx_fixtures.json` | **constructed for the package** — see flag 2 |
| `txreader/fixtures/test_vectors.json` | copied verbatim from the bench's `publish/` folder (authored there for publication) — see flag 1 |
| `txreader/test_tx_parse.py`, `txreader/README.md` | written for the package |
| `walletview/SPEC.md` | adapted from the bench's console UX document (house specifics, internal names, and internal references removed) + the board data shapes + the watch-only journal spec's page contract, generalized |
| `walletview/render_board.py` | written for the package (minimal reference implementation of the SPEC) |
| `walletview/example_board.json` | written for the package; every value invented and labeled SYNTHETIC in the file itself |
| `walletview/test_render_board.py` | written for the package |

## Source files deliberately excluded, and why

| source | why |
|---|---|
| any seed/mnemonic material; the bench's seed-posture document | absolute exclusion — never opened for this package |
| `.devnet-test.env`, any `.env` | credentials — never opened |
| the bench's wallet registry file | real wallet names, addresses, and key references. Its *shape* informed `walletview/SPEC.md` via the board code; no entry was copied |
| the bench's real journal CSVs | real operation history. Only the header rows (formats) were read and used |
| the bench's `state/` directory (board snapshot, UTXO ledger, per-swap state files) | live operational state |
| the bench's network/broadcast scripts (laptop relay, mesh-connect helper) | infrastructure: hosts, paths, relay mechanics |
| the bench's internal team notes (`bus-*.md`) | internal communications |
| the bench's research/archaeology/venue notes | internal research; absolute exclusion per instructions |
| signing, derivation, and broadcast code (UTXO core, HD derivation, chain legs, quote/registry/electrumx modules and their tests) | outside v0.1 scope — and a design point: the toolkit's reader deliberately never links signing code. One function *signature* (the Base58Check encoder) was viewed to keep the parser's call compatible; the implementation shipped here is the standard public algorithm |
| the bench's BIP-39 wordlist data file | standard public wordlist; unneeded — the package contains no derivation code |
| the bench's `publish/` registry record + its README | public-chain parameter record; not part of the v0.1 contents defined for this package (not a sensitivity exclusion — a scope one). Candidate for a future version |
| the bench's raw-transaction fixtures file | **see flag 2** |

## Grep classes run (whole package, after assembly) and results

| class | result |
|---|---|
| `seed` | 4 hits. Two are prohibition text ("a seed field" must never exist). Two are field *names* inside the published public test vectors — see flag 1 |
| `mnemonic` | 1 hit: inside the published public test vectors — see flag 1 |
| `private` | 1 hit: "control plane … is private by default" (design language). No private keys or private data |
| `key` | 20 hits, all terminology: the `house-key` wallet class, "key material", "key field" prohibitions, "never holds keys". No key values of any kind |
| `token` | 1 hit: "Token balances" (generic accounting language). No tokens, no token addresses |
| `password` | 0 hits |
| `.env` | 0 hits |
| IP-address pattern | 0 hits |
| `smartz` (personal name) | 2 hits, both the permitted author credit: `LICENSE` copyright line and `README.md` provenance |
| personal/house terms sweep (`laptop`, mesh-network name, broadcast-service names, explorer-API brand names, internal codenames, venue names, absolute home paths, "Ledger" as a name) | 0 hits |
| long base58-shaped strings outside labeled test data | 3 hits, all public constants: the Base58 alphabet itself; the famous version-0x00 zero-hash example address used as a test constant; a substring of a placeholder in `example_board.json` that is labeled SYNTHETIC in its own file |
| 64-hex strings | only inside the two fixtures files: the synthetic fixtures' constructed txids (patterns are visibly constructed) and the published vectors' values — see flag 1 |
| email addresses / URLs | 0 hits in the entire package |

Compiled `__pycache__` artifacts produced while testing were removed
after the test run; the package ships source only.

## Test results (recorded at assembly time)

```
python3 run_tests.py
  journal/test_journal.py       13 tests — OK
  txreader/test_tx_parse.py      5 tests — OK
  walletview/test_render_board.py 8 tests — OK
  all suites passed
```

Also exercised by hand: `journal/examples.py` produced both journal
formats with the refusal firing as designed (a dry-run session's
broadcast attempt is refused, in the journal's terms), and
`walletview/render_board.py` rendered the synthetic example board.

## Flagged uncertainties — read these before publishing

1. **`txreader/fixtures/test_vectors.json` contains a mnemonic and
   key-shaped values.** They are the canonical *public* test vectors
   from the published BIP-39 / SLIP-0010 documents (the file's own
   header says so, and says they must never be used as real wallets),
   copied verbatim from a folder the bench authored for publication.
   They are not house secrets. **But** any automated secret scanner
   will flag this file, and the txreader tests do not consume it (it
   is included as the bench's published reference record, per the
   build instruction to prefer the published vectors). If the
   reviewer prefers zero scanner noise, delete this one file — the
   package loses nothing functional.
2. **The bench's own transaction fixtures were NOT included.**
   The bench file named as a source contains real house transactions
   — a real constructed payment (with a real recipient address), a
   real deposit txid, a real funding txid. Publishing it would put
   real operation history in a public repo. It was replaced with
   `synthetic_tx_fixtures.json`: transactions constructed byte by
   byte for the tests, expectations recorded at construction. This is
   a deliberate deviation from the build instruction's letter ("with
   its test fixtures") in favor of its own stated preference
   ("prefer those published vectors") and its absolute exclusions.
   The parser-derived addresses inside the synthetic fixtures are
   what the parser computes from invented script hashes; they are
   labeled synthetic in the file's `about` field.
3. **Demo arithmetic mirrors live behavior.** `journal/examples.py`
   uses a 1% venue-style fee with round-up, because that is the
   discipline's home context; the books and amounts are invented and
   no venue is named. Not sensitive; noted so nobody mistakes the
   demo numbers for a fee schedule.
4. **Brand color.** `walletview/render_board.py` uses the Syndicate's
   public brand cyan (`#4fc9ff`) in its CSS — a color from the live
   public sites, used intentionally for the reference render.
5. **Chain coverage note.** The toolkit's parser covers CLAM and
   DOGE; Solana appears only as a chain ticker in synthetic board
   examples. No Solana addresses, program ids, or RPC endpoints
   appear anywhere in the package.

## Review addendum — Zoran-mini, Oct 19, 2026
- `txreader/fixtures/test_vectors.json` REMOVED at review. Rationale: it carried the canonical public BIP-39 test mnemonic and SLIP-0010 key-shaped constants. They are published standards values, not house secrets — but a toolkit that teaches "never hold keys" ships no mnemonic-shaped text at all, and the txreader tests never consumed the file. Removal verified: package re-grepped (mnemonic appears only in this report, as documentation) and the full suite re-run by the reviewer: **all suites passed (26/26)**.
- The synthetic-fixtures deviation (real bench fixtures excluded) is endorsed as correct under the exclusion rules.
