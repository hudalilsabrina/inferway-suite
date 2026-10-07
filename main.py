#!/usr/bin/env python3
"""Inferway Suite - CLI: factory akun + panen API key.

Command:
  harvest [n]   Buat n akun (default 1) + panen API key
  test          Uji semua API key (chat ke MiMo)
  report        Ringkasan akun
  usage         Cek kuota/usage tiap key
  sync          Inject API key ke 9router
  probe         Cek apakah API Inferway hidup
"""
import argparse
import asyncio
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rich.console import Console
from rich.table import Table
from rich import box

from src import inferway

C = Console()
ROOT = Path(__file__).resolve().parent
ACCOUNTS = ROOT / "accounts.txt"


def _load_accounts():
    if not ACCOUNTS.exists():
        return []
    out = []
    for line in ACCOUNTS.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split(":")
        if len(parts) >= 3:
            out.append({"email": parts[0], "password": parts[1], "apikey": parts[2]})
    return out


def cmd_harvest(n):
    ok = 0
    for i in range(1, n + 1):
        C.print(f"[cyan]=== Akun {i}/{n} ===[/]")
        r = asyncio.run(inferway.harvest_inferway())
        if r.get("ok"):
            ok += 1
        else:
            C.print(f"[yellow]  gagal: {r.get('error')}[/]")
    C.print(f"\n[bold]Selesai: {ok}/{n} sukses[/]")


def cmd_test():
    accts = _load_accounts()
    if not accts:
        C.print("[yellow]Belum ada akun.[/]")
        return
    C.print(f"[cyan]Uji {len(accts)} API key...[/]")
    t = Table(box=box.ROUNDED, title="Test API key")
    t.add_column("Email", style="cyan")
    t.add_column("Status")
    t.add_column("Balasan", style="dim")
    for a in accts:
        try:
            d = inferway.api_chat(a["apikey"])
            msg = d.get("choices", [{}])[0].get("message", {}).get("content", "")
            t.add_row(a["email"][:26], "[green]OK[/]", msg[:26])
        except Exception as e:
            t.add_row(a["email"][:26], "[red]FAIL[/]", str(e)[:34])
    C.print(t)


def cmd_report():
    accts = _load_accounts()
    C.print(f"[bold]Total akun: {len(accts)}[/]")
    if not accts:
        return
    t = Table(box=box.ROUNDED)
    t.add_column("#", justify="right")
    t.add_column("Email", style="cyan")
    t.add_column("API key")
    for i, a in enumerate(accts, 1):
        t.add_row(str(i), a["email"], a["apikey"][:28] + "...")
    C.print(t)


def cmd_usage():
    accts = _load_accounts()
    for a in accts:
        try:
            d = inferway.api_usage(a["apikey"])
            C.print(f"[cyan]{a['email']}[/]: {json.dumps(d)[:160]}")
        except Exception as e:
            C.print(f"[yellow]{a['email']}: {e}[/]")


def cmd_probe():
    try:
        req = urllib.request.Request(inferway.API + "/models")
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read())
            C.print(f"[green]API hidup — {len(d.get('data',[]))} model[/]")
    except Exception as e:
        C.print(f"[red]API bermasalah: {e}[/]")


def cmd_sync():
    from src import router9
    accts = _load_accounts()
    if not accts:
        C.print("[yellow]Belum ada akun.[/]")
        return
    accounts = [{"email": a["email"], "key": a["apikey"]} for a in accts]
    r = router9.ingest_gateway(name="inferway", prefix="inferway",
                               base_url=inferway.API, accounts=accounts)
    if r.get("ok"):
        C.print(f"[bold]{r['added']}/{r['total']} ditambahkan, {r['valid']} valid[/]")
    else:
        C.print(f"[red]gagal: {r.get('error')}[/]")


def main():
    ap = argparse.ArgumentParser(prog="inferway", description="Inferway Suite")
    sub = ap.add_subparsers(dest="cmd")
    h = sub.add_parser("harvest"); h.add_argument("n", nargs="?", type=int, default=1)
    sub.add_parser("test")
    sub.add_parser("report")
    sub.add_parser("usage")
    sub.add_parser("sync")
    sub.add_parser("probe")
    a = ap.parse_args()
    if a.cmd == "harvest":
        cmd_harvest(a.n)
    elif a.cmd == "test":
        cmd_test()
    elif a.cmd == "report":
        cmd_report()
    elif a.cmd == "usage":
        cmd_usage()
    elif a.cmd == "sync":
        cmd_sync()
    elif a.cmd == "probe":
        cmd_probe()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
