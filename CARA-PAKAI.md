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

Claude bakal **tanya-tanya bentar**, terus **bikin + jalanin** sendiri. Hasilnya di
`projects/properti/`.

Contoh: "set up cowork buat klinik gigi", "aku akuntan, bikinin automation".

---

## CARA 2 — Pakai Wizard (klik, bukan chat)

1. Di folder repo, ketik:
   ```powershell
   node wizard/server.mjs
   ```
2. Buka `http://localhost:4321` → isi form → klik **Create**.
3. Folder jadi di `projects/<bidang>/`. Lalu buka di Cowork.

(Wizard butuh Node + Python, **tanpa** npm install.)

---

## HASILNYA APA?

Folder `projects/<bidang>/`:

- **skill Cowork** → langsung jalan di Cowork (tanpa setup).
- **CLI** (opsional) → buat jalan otomatis / terjadwal (butuh 1 API key).
- **website lokal** (opsional) → dashboard buat lihat/ubah datamu di browser.
  **Tanpa akun, tanpa Convex, tanpa key** — cuma file lokal.
- **MCP server** (opsional) → biar **Claude bisa CRUD data website** itu langsung
  dari Cowork (create/read/update/delete). Tanpa key.

Semua berbagi satu datastore lokal (`.data/` + `output/`) — jadi sinkron.

---

## MAU YANG LAIN? tinggal bilang ke Claude

- "jalanin otomatis tiap pagi" → versi **CLI** + jadwal.
- "bikin website biar bisa lihat/ubah data" → versi **web lokal** (tanpa akun).
- "biar kamu bisa atur data websitenya" → pasang **MCP server**; Claude jadi bisa
  tambah/ubah/hapus data langsung.

Kalau nggak diminta, web & MCP **nggak** dibuat — biar ringan.

---

## AMAN (penting)

- Robot cuma bikin **draft**. Kirim/publish/hapus penting = **kamu** yang pencet
  (Claude konfirmasi dulu sebelum `delete`).
- Claude minta akses **1 folder** aja.
- Semua data = **file lokal** di komputermu. Key (kalau pakai CLI) di `.env`, bukan di chat.

Udah. Kamu ngomong (atau klik), robot kerja.
