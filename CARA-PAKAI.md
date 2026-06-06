# CARA PAKAI (bahasa gampang)

Repo ini = **mesin bikin robot kerja**.
Kamu **ngomong** mau bikin apa → robot dibuat di folder **`projects/`**, terus
dipakai di Cowork. Kamu **nggak perlu** ngoding / buka terminal.

Ada **2 cara**. Pilih yang kamu suka.

---

## CARA 1 — Ngobrol sama Claude (paling gampang)

1. **Download** repo ini.
2. **Pasang skill**: Claude → **Settings → Skills** → pasang
   `cowork-automation-generator.skill`.
3. **Ngobrol** di Cowork:
   > "buatkan otomasi cowork untuk bidang properti"

Claude bakal **tanya-tanya bentar** (kamu kerja apa, yang paling makan waktu apa),
terus **bikin + jalanin** sendiri. Hasilnya muncul di `projects/properti/`.

Contoh kalimat:

- "set up cowork buat klinik gigi, fokus reminder pasien"
- "aku akuntan, bikinin automation"
- "buatkan otomasi cowork untuk bidang X"

---

## CARA 2 — Pakai Wizard (klik, bukan chat)

Buat yang lebih suka isi form daripada ngobrol.

1. Buka PowerShell di folder repo, ketik:
   ```powershell
   node wizard/server.mjs
   ```
2. Buka browser: `http://localhost:4321`
3. Isi form (bidang kamu, centang mau CLI / web), klik **Create**.
4. Folder dibuat di `projects/<bidang>/`.

Habis itu buka folder `projects/<bidang>/` di Cowork, jalanin skill-nya biar Claude
isiin tool khusus bidangmu. (Wizard cuma butuh Node + Python, **tanpa** npm install.)

---

## HASILNYA APA?

Folder `projects/<bidang>/` isinya:

- **skill Cowork** → langsung jalan di Cowork (tanpa setup).
- **CLI** (opsional) → buat jalan otomatis / terjadwal (butuh 1 API key).
- **web app** (opsional, kalau diminta) → biar tim bisa pakai bareng (BYOK).

---

## MAU YANG LAIN? tinggal bilang ke Claude

- "jalanin otomatis tiap pagi" → Claude pasang versi **CLI** + jadwal.
- "bikin web app biar tim bisa pakai" → Claude bikin versi **web** (butuh akun
  Convex gratis; Claude pandu 1 langkah login, sisanya dia).

Kalau nggak diminta, web app **nggak** dibuat — biar ringan.

---

## AMAN (penting)

- Robot cuma bikin **draft**. Kirim / publish = **kamu** yang pencet.
- Claude minta akses **1 folder** aja.
- Kunci (API key) **jangan** ditempel di chat — Claude simpan di tempat benar.

Udah. Kamu ngomong (atau klik), robot kerja.
