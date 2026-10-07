# Inferway Suite

Factory akun **Inferway** + panen **API key** otomatis.
Signup → verify email → API key `inferway_live_...` → **free tier 1.000 req/hari**.

## Cara kerja

```
1. buat inbox tempik (session SAMA untuk create + read — penting!)
2. buka https://inferway.ai/sign-up (Clerk)
3. isi email + password + accept terms → Continue
4. baca kode verifikasi dari inbox → submit
5. masuk /console → auto "Default key" dibuat
6. Create key → klik "Reveal secret" → ambil secret inferway_live_...
7. simpan ke accounts.txt
```

## Free tier

| Item | Nilai |
|---|---|
| Model gratis | **MiMo-V2.6 Flash** (`inferway/mimo-v2.6-flash`) |
| Kuota | **1.000 request/hari** |
| Context | 384K |
| Harga (kalau bayar) | $0.14/1M in, $0.28/1M out |

## Instalasi

```bash
python3 -m venv .venv
.venv/bin/pip install rich requests patchright
.venv/bin/patchright install chromium
cp config.example.toml config.toml   # isi endpoint tempmail Anda
```

## Command

```bash
./run.sh harvest 1     # buat 1 akun + panen API key
./run.sh harvest 5     # 5 akun
./run.sh test          # uji semua key (chat ke MiMo)
./run.sh report        # ringkasan akun
./run.sh usage         # cek kuota tiap key
./run.sh sync          # inject key ke 9router
./run.sh probe         # cek API hidup
```

Batch:

```bash
.venv/bin/python batch.py 10 --delay 10
```

## Gateway

OpenAI-compatible: `https://api.inferway.ai/v1`

```bash
curl https://api.inferway.ai/v1/chat/completions \
  -H "Authorization: Bearer inferway_live_..." \
  -H "Content-Type: application/json" \
  -d '{"model":"inferway/mimo-v2.6-flash","messages":[{"role":"user","content":"hi"}]}'
```

## 🔧 Catatan teknis (penting)

1. **Tempik session HARUS sama** untuk create inbox + baca pesan —
   `TempikClient()` baru tidak bisa baca inbox lama (HTTP 400 "Missing x-session-id").
2. **Secret key hanya tampil sekali** — ada tombol "Reveal secret"; engine
   mengkliknya lalu ambil dari `[data-testid=secret-value]`.
3. **Endpoint API key**: `POST /api/gateway/v1/keys` (via session cookie Clerk).
4. Auth pakai **Clerk** (`clerk.inferway.ai`) — signup email+password tanpa captcha.

## Format akun (`accounts.txt`)

```
email:password:apikey
```

## Atribusi

Sumber kode temp-mail: **[hirotomasato/tempik](https://github.com/hirotomasato/tempik)**
(lihat `src/tempmail.py`).

## Struktur

```
main.py            # CLI
batch.py           # batch runner
src/inferway.py    # engine: signup + verify + panen API key
src/tempmail.py    # client temp-mail (tempik)
src/inboxstore.py  # riwayat inbox
src/router9.py     # sync ke 9router
config.example.toml
```

## Disclaimer

Untuk penggunaan pribadi/edukasi. Hormati Terms of Service Inferway.
