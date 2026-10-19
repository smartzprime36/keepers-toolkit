"""Keeper's Toolkit — transaction reader (parser).

Decodes raw CLAM / DOGE transaction hex into structure: inputs, outputs
(addresses + amounts), CLAM's nTime + ClamSpeech, and locktime. The chain
is detected by exact-fit parsing (see :func:`detect_chain`): a byte
string is a CLAM transaction or a DOGE transaction only if it parses
with zero trailing bytes under that chain's rules.

A raw transaction does not carry its input amounts, so a fee can only
be reported when the caller supplies them — the parser reports
``total_out_sats`` and leaves fee arithmetic to the caller.

This is a *reader*. It cannot build, sign, or broadcast anything.

Adaptation note: the bench this was extracted from imports its
Base58Check encoder from a signing core. The toolkit ships its own
copy below so the reader never links signing code — reading and
signing stay separate programs, on purpose.
"""
import hashlib
import struct

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _dsha(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def b58check_encode(version: int, payload: bytes) -> str:
    """Standard Base58Check: version byte + payload + 4-byte checksum."""
    data = bytes([version]) + payload
    data += _dsha(data)[:4]
    n = int.from_bytes(data, "big")
    s = ""
    while n:
        n, r = divmod(n, 58)
        s = _B58[r] + s
    return "1" * (len(data) - len(data.lstrip(b"\0"))) + s


ADDR_VERSION = {"CLAM": 0x89, "DOGE": 0x1E}


class Reader:
    def __init__(self, raw):
        self.b = raw
        self.i = 0

    def take(self, n):
        out = self.b[self.i:self.i + n]
        assert len(out) == n, "short read"
        self.i += n
        return out

    def u32(self):
        return struct.unpack("<I", self.take(4))[0]

    def u64(self):
        return struct.unpack("<Q", self.take(8))[0]

    def varint(self):
        x = self.take(1)[0]
        if x < 0xFD:
            return x
        if x == 0xFD:
            return struct.unpack("<H", self.take(2))[0]
        if x == 0xFE:
            return self.u32()
        return self.u64()

    def varstr(self):
        n = self.varint()
        return self.take(n)

    @property
    def left(self):
        return len(self.b) - self.i


def script_address(chain, script):
    # P2PKH: OP_DUP OP_HASH160 <20> OP_EQUALVERIFY OP_CHECKSIG
    if (len(script) == 25 and script[:3] == b"\x76\xa9\x14"
            and script[23:] == b"\x88\xac"):
        return b58check_encode(ADDR_VERSION[chain], script[3:23]), "p2pkh"
    if len(script) == 23 and script[:2] == b"\xa9\x14" \
            and script[22:] == b"\x87":
        return None, "p2sh"
    if not script:
        return None, "empty"
    return None, "other"


def parse(raw: bytes, chain: str):
    r = Reader(raw)
    version = r.u32()
    ntime = r.u32() if chain == "CLAM" else None
    inputs = []
    for _ in range(r.varint()):
        prev = r.take(32)[::-1].hex()
        vout = r.u32()
        sig = r.varstr()
        seq = r.u32()
        inputs.append({"txid": prev, "vout": vout,
                       "script_sig_hex": sig.hex(), "sequence": seq})
    outputs = []
    for _ in range(r.varint()):
        sats = r.u64()
        script = r.varstr()
        addr, kind = script_address(chain, script)
        outputs.append({"amount_sats": sats, "amount": sats / 1e8,
                        "script_hex": script.hex(), "address": addr,
                        "script_type": kind})
    speech = ""
    if chain == "CLAM" and version > 1:
        speech = r.varstr().decode("utf-8", "replace")
    locktime = r.u32()
    assert r.left == 0, f"{chain} parse leaves {r.left} trailing bytes"
    txid = _dsha(raw)[::-1].hex()
    return {"chain": chain, "txid": txid, "version": version,
            "ntime": ntime, "inputs": inputs, "outputs": outputs,
            "total_out_sats": sum(o["amount_sats"] for o in outputs),
            "speech": speech, "locktime": locktime}


def detect_chain(raw: bytes):
    fits = []
    for chain in ("DOGE", "CLAM"):
        try:
            parse(raw, chain)
            fits.append(chain)
        except Exception:
            pass
    if len(fits) == 1:
        return fits[0]
    raise ValueError(f"chain detection ambiguous/failed: fits={fits}")


def decode_hex(hexstr: str):
    raw = bytes.fromhex(hexstr.strip())
    return parse(raw, detect_chain(raw))
