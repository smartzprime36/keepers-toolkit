"""Keeper's Toolkit — wallet view, minimal reference implementation.

Renders a board snapshot (SPEC.md §1) as a single static HTML page
and enforces the two rules that define the view:

* watch-only rows render in their own visual class and contain NO
  send control anywhere — absence, not disabling;
* the send composer for a spending-capable wallet keeps its action
  button disabled until a journal line has been composed AND
  acknowledged (SPEC.md §3), with dry-run as the visible default.

Pure standard library; the output is one self-contained HTML string.

    python3 render_board.py example_board.json > board.html
"""
import html
import json
import sys

SPENDING_KINDS = {"house-key", "hd"}

CSS = """
body { font-family: system-ui, sans-serif; background:#0b0e13;
       color:#e6e9ee; margin:2rem; }
.wallet { border-radius:10px; padding:1rem 1.25rem; margin:0 0 1rem;
          max-width:42rem; }
.wallet-house { border:2px solid #4fc9ff; background:#10151d; }
.wallet-watch { border:2px dashed #8a93a5; background:#0e1013;
                color:#aeb6c2; }
.tag { font-size:.72rem; letter-spacing:.12em; padding:.15rem .5rem;
       border-radius:99px; border:1px solid currentColor; }
.tag-watch { color:#ffb454; }
.tag-house { color:#4fc9ff; }
.addr { font-family:ui-monospace, monospace; font-size:.85rem;
        word-break:break-all; }
.bal { font-size:1.35rem; font-weight:600; }
.err { color:#ff7a7a; font-weight:600; }
.composer { border-top:1px solid #2a3242; margin-top:.75rem;
           padding-top:.75rem; }
.journal-line { font-family:ui-monospace, monospace; font-size:.8rem;
                background:#05070a; padding:.5rem; border-radius:6px;
                white-space:pre-wrap; }
button.send { font-size:1rem; padding:.5rem 1.25rem; border-radius:8px; }
button.send[disabled] { opacity:.45; }
.banner-dry { color:#ffb454; font-weight:700; letter-spacing:.08em; }
"""


def esc(x):
    return html.escape(str(x))


def render_wallet_row(row):
    """Render one wallet card. Watch-only cards contain no <button>."""
    kind = row.get("kind")
    watch = kind not in SPENDING_KINDS
    cls = "wallet-watch" if watch else "wallet-house"
    tag = ('<span class="tag tag-watch">👁 WATCH-ONLY</span>' if watch
           else '<span class="tag tag-house">SPENDING-CAPABLE</span>')
    if row.get("ok"):
        bal = f'<div class="bal">{esc(row.get("balance"))} ' \
              f'{esc(row.get("chain", ""))}</div>'
        src = f'<div>via {esc(row.get("source", "unknown source"))}</div>'
    else:
        bal = f'<div class="err">READ ERROR — balance unknown</div>'
        src = f'<div>{esc(row.get("error", "read failed"))}</div>'
    send = "" if watch else render_send_composer(row)
    return (f'<section class="wallet {cls}">'
            f'<h3>{esc(row.get("name", "unnamed"))} {tag}</h3>'
            f'<div class="addr">{esc(row.get("address", ""))}</div>'
            f'{bal}{src}{send}</section>')


def render_send_composer(row, journal_line=None, acknowledged=False):
    """The send composer with journal-acknowledgement gating.

    The action button is DISABLED unless a journal line has been
    composed and the operator has acknowledged it. Watch-only wallets
    never reach this function (see render_wallet_row).
    """
    if row.get("kind") not in SPENDING_KINDS:
        return ""
    if journal_line:
        line_html = f'<div class="journal-line">{esc(journal_line)}</div>'
        ack = "acknowledged" if acknowledged else "NOT acknowledged"
    else:
        line_html = ('<div class="journal-line">(no journal line '
                     'composed yet — the send does not exist)</div>')
        ack = "NOT acknowledged"
    disabled = "" if (journal_line and acknowledged) else " disabled"
    return ('<div class="composer">'
            '<div class="banner-dry">DRY RUN BY DEFAULT</div>'
            f'{line_html}'
            f'<div>journal line: {ack}</div>'
            f'<button class="send"{disabled}>Send</button>'
            '</div>')


def render_board(board):
    rows = "\n".join(render_wallet_row(r) for r in board.get("rows", []))
    return ('<!DOCTYPE html><html><head><meta charset="utf-8">'
            '<title>Wallet board</title>'
            f'<style>{CSS}</style></head><body>'
            f'<h2>Wallet board — as of {esc(board.get("as_of_utc", "?"))}'
            '</h2>'
            f'{rows}</body></html>')


def main(argv):
    with open(argv[1]) as f:
        board = json.load(f)
    print(render_board(board))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
