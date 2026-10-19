# txreader — read a transaction like a keeper

`tx_parse.py` decodes raw CLAM / DOGE transaction hex into structure:
inputs, outputs (addresses + amounts), CLAM's nTime and ClamSpeech,
and locktime. Chain detection is by exact fit — the bytes must parse
with zero trailing bytes under exactly one chain's rules.

These two chains are the interesting case. Bitcoin-derived tooling
almost fits them and quietly misreads them: CLAM adds an `nTime`
field after the version and a `ClamSpeech` string after the outputs.
A parser that doesn't know that produces confident nonsense. This one
knows.

## Use

```python
import tx_parse
tx = tx_parse.decode_hex(raw_hex_from_anywhere)
tx["outputs"]        # [{'address': ..., 'amount_sats': ..., ...}]
tx["total_out_sats"] # sum of outputs; a raw tx carries no input
                     # amounts, so fees are the caller's arithmetic
```

## Fixtures

- `fixtures/synthetic_tx_fixtures.json` — transactions constructed
  byte by byte for the tests. Never broadcast; no real funds,
  wallets, or addresses. Expectations were recorded at construction
  time.
- `fixtures/test_vectors.json` — the public BIP-39 / SLIP-0010 test
  vectors the originating bench proves its key-derivation code
  against. They are published constants from the BIP documents,
  included so downstream implementations can check themselves
  against the same public record. **They are not, and must never be
  used as, real wallets.**

## Tests

```
python3 -m unittest test_tx_parse -v
```

The suite also pins the Base58Check encoder against the well-known
version-0x00 zero-hash example, so address derivation is checked
against a public constant rather than against itself.

## Boundary

This module is a reader. It cannot build, sign, or broadcast a
transaction, and it ships its own Base58Check copy so it never needs
to link a signing core. Reading and signing stay separate programs.
