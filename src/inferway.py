"""Inferway engine - buat akun + panen API key (free tier 1000 req/hari).

Alur (terbukti):
  1. buat inbox tempik (session SAMA untuk create + read)
  2. buka https://inferway.ai/sign-up (Clerk) via patchright
  3. isi email + password + accept terms -> Continue
  4. baca kode verifikasi dari inbox -> submit
  5. masuk /console -> auto "Default key" dibuat
  6. Create key -> klik "Reveal secret" -> ambil secret
  7. simpan ke accounts.txt

Free tier: MiMo-V2.6 Flash, 1.000 req/hari.
Endpoint key: POST /api/gateway/v1/keys (via session cookie)
Sumber mail: https://github.com/hirotomasato/tempik
"""
import asyncio
import json
import random
import re
import string
from typing import Any, Dict, Optional

from rich.console import Console

from .tempmail import TempikClient
from .inboxstore import save as save_inbox

C = Console()

SIGNUP_URL = "https://inferway.ai/sign-up"
CONSOLE_KEYS = "https://inferway.ai/console/keys"
API = "https://api.inferway.ai/v1"
FREE_MODELS = ["inferway/mimo-v2.6-flash", "mimo-v2.6-flash"]

GIVEN = ["Arka", "Bima", "Cakra", "Dewa", "Eka", "Fajar", "Galih", "Hendra", "Indra",
         "Jaka", "Krisna", "Laras", "Mega", "Nanda", "Oka", "Putra"]
FAMILY = ["Wijaya", "Pratama", "Saputra", "Nugraha", "Hidayat", "Kusuma", "Permana"]


def _rand_password(n: int = 14) -> str:
    core = "".join(random.choices(string.ascii_letters + string.digits, k=n))
    return f"Iw!{core}7"


async def _read_code(tc: TempikClient, email: str, timeout: int = 180) -> Optional[str]:
    """Baca kode verifikasi dari inbox (session SAMA dengan pembuat inbox)."""
    t0 = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - t0 < timeout:
        try:
            msgs = tc.get_messages(email)
            for m in msgs or []:
                txt = (m.get("subject", "") + " " + (m.get("body") or "")
                       + " " + (m.get("html") or ""))
                codes = re.findall(r"\b(\d{4,8})\b", txt)
                if codes:
                    return codes[0]
        except Exception:
            pass
        await asyncio.sleep(4)
    return None


async def harvest_inferway(headless: bool = False, verbose: bool = True) -> Dict[str, Any]:
    """Buat 1 akun Inferway + panen API key."""
    from patchright.async_api import async_playwright

    out: Dict[str, Any] = {"site": "inferway", "ok": False}
    tc = TempikClient()
    email = tc.create_inbox()
    save_inbox("inferway", email, tc.session_id, "")
    pwd = _rand_password()
    out.update(email=email, password=pwd)
    if verbose:
        C.print(f"[cyan]inferway[/] inbox: {email}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        ctx = await browser.new_context()
        page = await ctx.new_page()
        try:
            await page.goto(SIGNUP_URL, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(4000)
            # dismiss cookie
            try:
                await page.click("text=Essential only", timeout=3000)
                await page.wait_for_timeout(800)
            except Exception:
                pass

            # isi form
            await page.fill("input[name=emailAddress]", email)
            await page.fill("input[name=password]", pwd)
            try:
                await page.check("input[name=legalAccepted]")
            except Exception:
                await page.evaluate("""() => { const c=document.querySelector('input[name=legalAccepted]'); if(c&&!c.checked) c.click(); }""")
            await page.wait_for_timeout(800)
            await page.evaluate("""() => { const b=[...document.querySelectorAll('button')].find(x=>/^continue$/i.test((x.innerText||'').trim())); if(b) b.click(); }""")
            await page.wait_for_timeout(8000)
            out["after_signup_url"] = page.url

            # tunggu halaman verify
            for _ in range(15):
                if "verify" in page.url:
                    break
                await page.wait_for_timeout(1000)

            # baca kode + submit
            code = await _read_code(tc, email, 180)
            out["code"] = code
            if not code:
                out["error"] = "no-code"
                return out
            if verbose:
                C.print(f"[dim]  code: {code}[/]")
            await page.evaluate("""() => { const i=document.querySelector('input[type=text]'); if(i) i.focus(); }""")
            await page.wait_for_timeout(300)
            await page.keyboard.type(code, delay=60)
            await page.wait_for_timeout(1500)
            await page.evaluate("""() => { const b=[...document.querySelectorAll('button')].find(x=>/^continue$/i.test((x.innerText||'').trim())); if(b) b.click(); }""")
            await page.wait_for_timeout(9000)
            out["final_url"] = page.url

            if "/console" not in page.url:
                out["error"] = "verify-failed"
                out["body"] = (await page.evaluate("document.body.innerText"))[:200]
                return out
            if verbose:
                C.print("[green]  akun jadi, masuk console[/]")

            # buat API key + reveal secret
            key = await _create_and_reveal_key(page, verbose)
            if key:
                out["ok"] = True
                out["apikey"] = key
                if verbose:
                    C.print(f"[green]  API key: {key[:26]}...[/]")
                _append_account(email, pwd, key)
            else:
                out["error"] = "no-apikey"
            return out
        except Exception as e:
            out["error"] = str(e)[:180]
            return out
        finally:
            try:
                await ctx.close()
                await browser.close()
            except Exception:
                pass


async def _create_and_reveal_key(page, verbose: bool = True) -> Optional[str]:
    """Buat API key baru + klik Reveal secret -> ambil secret."""
    try:
        await page.goto(CONSOLE_KEYS, wait_until="domcontentloaded", timeout=40000)
        await page.wait_for_timeout(5000)
        # klik Create key
        await page.evaluate("""() => { const b=[...document.querySelectorAll('button')].find(x=>/^create key$/i.test((x.innerText||'').trim())); if(b) b.click(); }""")
        await page.wait_for_timeout(2500)
        # isi nama
        await page.evaluate("""() => { const i=document.querySelector('input[placeholder*=production]'); if(i) i.focus(); }""")
        await page.wait_for_timeout(300)
        await page.keyboard.type("suite-key", delay=40)
        await page.wait_for_timeout(800)
        # klik Create key di dialog
        await page.evaluate("""() => { const btns=[...document.querySelectorAll('button')].filter(x=>/^create key$/i.test((x.innerText||'').trim())); if(btns.length) btns[btns.length-1].click(); }""")
        await page.wait_for_timeout(5000)
        # klik Reveal secret
        try:
            await page.click("button[aria-label='Reveal secret']", timeout=5000)
            await page.wait_for_timeout(1500)
        except Exception:
            pass
        # ambil secret
        secret = await page.evaluate("""() => { const e=document.querySelector('[data-testid=secret-value]'); return e?e.textContent:''; }""")
        if secret and secret.startswith("inferway_"):
            return secret.strip()
        # fallback: cari di seluruh DOM
        secret = await page.evaluate("""() => {
            const m = document.documentElement.innerHTML.match(/inferway_(live|test)_[A-Za-z0-9_-]{20,}/g);
            return m ? m[0] : '';
        }""")
        return secret.strip() if secret else None
    except Exception:
        return None


def _append_account(email: str, password: str, apikey: str):
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent / "accounts.txt"
    with open(p, "a") as f:
        f.write(f"{email}:{password}:{apikey}\n")


def api_chat(apikey: str, model: str = "inferway/mimo-v2.6-flash",
             prompt: str = "Say OK", timeout: int = 60) -> Dict[str, Any]:
    """Chat ke Inferway API (test key)."""
    import urllib.request
    body = json.dumps({"model": model, "max_tokens": 20,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(f"{API}/chat/completions", data=body, method="POST",
        headers={"Authorization": f"Bearer {apikey}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def api_usage(apikey: str, timeout: int = 20) -> Dict[str, Any]:
    """Cek usage (kuota harian)."""
    import urllib.request
    req = urllib.request.Request(f"{API}/usage?window=30d",
        headers={"Authorization": f"Bearer {apikey}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())
