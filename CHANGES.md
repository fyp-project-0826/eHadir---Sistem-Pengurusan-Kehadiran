# eHadir (MySQL / InfinityFree) — Security & Robustness Patch Set

Dijana: 2026-11-20. Struktur projek TIDAK diubah — hanya patch dalam fail sedia ada.
Setiap perubahan ditanda dengan komen `// FIX (...)` (PHP) atau `// FIX (XSS)` (JS) di
atas baris yang berubah. Tiada Composer, tiada CLI, tiada perpustakaan baharu —
mesin hosting shared InfinityFree cukup (PHP 8.x + MySQL/MariaDB).

---

## 1. Fail yang diubah

### app/config.php
- `RECEIPT_KEY` kini `getenv('EH_RECEIPT_KEY') ?: ''` — **kunci demo `demo-receipt-key-v1` dibuang** daripada fallback.
- tambah `EH_ALLOW_DEMO_SEED` (dari `getenv('EH_ALLOW_DEMO_SEED')` atau konfigurasi).

### app/config.local.php  *(lokal sahaja — TIDAK dibungkus dalam zip)*
- `EH_ALLOW_DEMO_SEED => true` supaya ujian sandbox terus berjalan.

### app/bootstrap.php
| Kumpulan | Perubahan |
|---|---|
| Default secrets | `EH_ALLOW_DEMO_SEED` didefinisikan; seed demo (admin/admin123, siti/siti123, pelajar123) **hanya** berjalan bila flag true. Kalau jadual `users` kosong dan flag mati → respons JSON `503 {"error":"sistem belum dikonfigurasi"}`. |
| Default secrets | `RECEIPT_KEY` kosong → JSON `500 {"error":"konfigurasi diperlukan"}` (aplikasi **berhenti**, tidak diam-diam memakai kunci yang diketahui orang ramai). |
| Default secrets | pembantu baharu `gen_pw(10)` — kata laluan rawak daripada set aksara tanpa aksara mengelirukan (`l/I/1/O/0`), menggunakan `random_int`. |
| IDOR / audit race | `log_act()` kini balut *baca hash terakhir + INSERT* dalam `GET_LOCK('eh_activity_log', 5)` / `RELEASE_LOCK` di dalam `finally` — imbasan serentak tidak lagi boleh mencabangkan rantaian hash. |
| Audit race | `verify_chain($all = false)` — lalai semak **2000 baris terakhir** sahaja (benang mula diambil dari hash baris sebelum tetingkap, bukan dari sifar); `$all = true` untuk semakan penuh. |
| Brute force | `locked_out()` kini mengembalikan `'user'` (5 percubaan gagal / 15 minit) **atau** `'ip'` (20 / 15 minit); `note_attempt()` simpan lajur `ip`. |
| Skema | `login_attempts` dapat lajur `ip VARCHAR(45) NULL` + indeks `idx_la_user (username,ok,ts)` & `idx_la_ip (ip,ok,ts)`; `SCHEMA_VERSION` → **`mysql-3`**. |
| Skema | fail penanda `.schema_ok` kini simpan `mysql-3:<DB_NAME>` — tukar `DB_NAME` = migrate & gerbang seed berjalan semula (sebelum ini penanda global menyebabkannya dilangkau). |
| Robustness | `set_exception_handler` global → `error_log(...)` + JSON `500 {"error":"server_error"}`; halaman **tidak pernah** blank dan tidak pernah bocor jejak Laluan/stack. |
| Sesi | `gc_maxlifetime` & lifetime kuki = 8 jam, `httponly`, `samesite=Lax`, `secure` aktif bila `HTTPS` **atau** `X-Forwarded-Proto: https` (InfinityFree di belakang ngrok/proxy). |
| MySQL | `PDO::MYSQL_ATTR_USE_BUFFERED_QUERY => true` + `closeCursor()` selepas `fetchColumn()` dalam `log_act` (Ralat 2014 pada build PHP tertentu). |
| Import/template | teks templat muat turun & nota UI tidak lagi menyebut `pelajar123` / `guru123`. |

### api/login.php
- Mesej 429 berasingan untuk kunci **per-akaun** dan kunci **per-IP**.

### api/manage.php
- `save_user`: tiada lagi kata laluan lalai — kosong → `gen_pw(10)`, dipulang **sekali** sebagai `generated_pw`. Kata laluan manual < 8 aksara → `400`.
- `import_students` / `import_teachers`: `pelajar123` / `guru123` dibuang; setiap baris dapat kata laluan rawak, disenaraikan dalam `generated_passwords`. Semak min 8 aksara per baris (`baris N: ...`).
- `enroll`: mesti `role="student" AND active=1` (guru/admin tidak lagi boleh didaftarkan ke kelas).
- `save_class` / `import_classes`: `lat`/`lng` **NULL** secara lalai (tiada titik KL 3.139/101.687 dipaksa ke kelas baharu).

### api/events.php  *(IDOR)*
- Simpan peristiwa **ber ID**: kelas **semasa** peristiwa juga mesti lulus `can_touch_class` — guru lain tidak lagi boleh "menghantar semula" peristiwa kelas orang (pindah kelas / tulis atas rekod orang).

### api/leave_apply.php
- Tarikh (mod bukan-sesi): regex `^\d{4}-\d{2}-\d{2}$` **dan** pusing-semak `DateTime::createFromFormat` → `2026-13-99`, `2026-02-30`, `not-a-date` ditolak 400.
- Muat naik MC: `finfo(FILEINFO_MIME_TYPE)` mesti `application/pdf` / `image/jpeg` / `image/png` — sambungan sah tidak cukup.
- DB simpan **nama fail sahaja** (bukan laluan penuh pelayan).

### api/mc.php
- Laluan dibina dari `APP_ROOT . '/uploads/mc/' . basename($mc_path)` + `realpath` mesti bermula dalam `uploads/mc` (sebelum ini laluan mutlak dari DB terus dibaca; `basename()` masih menyokong rekod lama).

### api/scan.php
- `INSERT` kehadiran dalam `try/catch (PDOException)`; ralat kunci berulang (`23000`) → respons `dupe` yang sama (bukan 500 / bukan duplikat baris).

### api/org.php
- Logo: **PNG/JPG sahaja** — SVG dibuang sepenuhnya (GET mime + POST + validasi `getimagesize`), termasuk semakan pada halaman admin.
- GET tambah `demo_seed` (boolean) supaya halaman login boleh sembunyikan kread demo.

### api/export_csv.php
- `csv_safe()` — sel yang bermula dengan `=`, `+`, `-`, `@`, TAB atau CR didahului `'` (halang formula-injection Excel); nilai `H`/`C`/`-`/nombor tidak disentuh.

### api/student_data.php
- Peratus kehadiran: pengangka **dan** penyebut kini scoped kepada kelas pelajar itu (`enrollments`); `min(100, ...)` — peratus tidak boleh >100 lagi untuk pelajar berbilang kelas.

### api/log_list.php
- `closeCursor()` selepas `fetchColumn()` (pembaikan ralat 2014 MySQL).

### js/admin2.js, js/teacher.js, js/admin.js, js/student.js
- **Stored XSS**: setiap sisipan data pelayan ke `innerHTML` kini dibalut `esc()` (didefinisikan dalam `js/csrf.js`, dimuatkan pada semua halaman) — nama kelas, mata pelajaran, nama pelajar, `@username`, jenis cuti, status, tarikh, `remark`, `detail` log, tajuk/isi pengumuman, mesej ralat API, senarai "belum hadir"/MC, roster & matriks laporan.
- `admin2.js` & `teacher.js`: paparkan `generated_pw` selepas pengguna/import dicipta (alert "salin sekarang — tidak dipaparkan lagi").
- `admin2.js`: semakan sambungan logo client-side kini PNG/JPG sahaja.
- `teacher.js`: amaran GPS (tiada lokasi kelas) kekal paparkan `triangle-alert` dalam kad kelas dan panel QR.

### admin.html
- `accept=".png,.jpg,.jpeg"` + teks panduan logo → "PNG / JPG".

### index.html
- Cip kread demo (`alang/pelajar123` dll.) **tersembunyi secara lalai**; hanya dipaparkan bila `org.php` melaporkan `demo_seed:true`.

### teacher.html
- Nota import pelajar tidak lagi mendedahkan `pelajar123`.

### js/templates.js
- Lajur `password` dalam templat Excel jadi kosong + arahan "kosongkan password = kata laluan rawak dijana & dipaparkan sekali".

**Tidak disentuh:** `import/data-real.sql`, `import/data-demo.sql`, logik perniagaan QR/GPS/HMAC, susun atur fail, teks Malay yang sedia ada.

---

## 2. Nota pasang (InfinityFree)

1. Gantikan semua fail dalam `htdocs/` (jangan overwrite `app/config.local.php` — ia tiada dalam zip).
2. **`RECEIPT_KEY` wajib diisi** dengan rentetan rawak anda (contoh: 32 aksara hex dari
   https://www.random.org/strings/ atau `bin2hex(random_bytes(16))`). Kalau kosong, aplikasi
   akan balas `{"error":"konfigurasi diperlukan"}` — ini disengajakan.
3. Kalau naik daripada versi lama: **padam `app/.schema_ok`** supaya migrasi `mysql-3`
   berjalan (tambah lajur `login_attempts.ip` + indeks). Atau jalankan SQL ini dalam phpMyAdmin:
   ```sql
   ALTER TABLE login_attempts ADD ip VARCHAR(45) NULL;
   CREATE INDEX idx_la_user ON login_attempts (username, ok, ts);
   CREATE INDEX idx_la_ip   ON login_attempts (ip, ok, ts);
   ```
   (Jika `ALTER` merungut "column exists", bermakna migrasi sudah pernah berjalan — abaikan.)
4. Jangan set `EH_ALLOW_DEMO_SEED` pada pelayan pengeluaran (production). Ia hanya untuk demo.
5. Selepas live: **tukar kata laluan SYSADMIN / T001 / T002** (kata laluan lama ada dalam fail SQL).
6. Data sedia ada: mana-mana `mc_path` lama yang tersimpan sebagai laluan penuh tetap boleh
   dibuka (`basename()`), tetapi fail MC lama memang tiada dalam hosting baharu — rekod sahaja dipindah.

---

## 3. Semakan yang telah dijalankan (lalu, pada :3003 MySQL/MariaDB)

| suite | hasil |
|---|---|
| `my_eh_admin_test.py` (logo/PDF/import/board/papan tanda/CSRF/rantaian) | **45/45** |
| `my_eh_teacher_test.py` (geofence, live count, laporan, import) | **35/35** |
| `my_eh_nf_test.py` ("Kelas Belum Penuh" + prestasi papan) | **11/11** |
| `my_eh_cls_test.py` (Jadual Kelas + roster) | **28/28** |
| `my_eh_cal_test.py` (Kalendar Kelas) | **29/29** |
| `my_eh_imp_test.py` (impersonation + log) | **53/53** |
| `my_eh_logpdf_test.py` (PDF log aktiviti) | **10/10** |
| `my_eh_sec_test.py` — **suite baharu untuk patch ini** | **46/46** |
| CDP p6smoke (semua halaman, klik setiap tab, 1280 & 390 px) | ralat konsol **[]** |
| CDP bukti XSS (`eh_xssproof2.js`) — kelas/pelajar/pengumuman/remark berpayload `<img src=x onerror=...>` | `pwned:false`, `liveImg:0`, `liveOnerr:0`, payload muncul sebagai teks ter-escape — semua 9 paparan |
| Rantaian audit penuh selepas semua ujian | `CHAIN_OK` (verify_chain all: ok, rows ≈ 3574) |

## 4. Senarai semak ujian manual (5 minit, selepas pasang)

1. **Login** — `admin`/kata laluan anda sendiri → dashboard terbuka; kata laluan salah 5× →
   mesej "Akaun dikunci 15 minit"; 20× dari IP sama (akaun berbeza) → mesej per-IP.
2. **Scan** — Buka QR (guru) → imbas dari telefon (pelajar, GPS betul) → "Hadir".
   Imbas dua kali berturut-turut → "Anda sudah hadir untuk sesi ini" (ralat hijau, bukan halaman rosak).
   *Serentak:* minta 30 tab `scan.php` dengan token sama (atau `ab -c 30 -n 30` bila ada SSH) →
   tepat **1 hadir**, selebihnya `dupe`, dan **Log Aktiviti → Rantaian Audit** masih "UTUH".
3. **Leave apply dengan tarikh buruk** — Cuba hantar cuti dengan tarikh `2026-13-99`
   (ubah input tarikh melalui DevTools, atau hantar terus ke `/api/leave_apply.php`) →
   `400 format tarikh salah` / `tarikh tidak wujud dalam kalendar`; senarai cuti tidak pecah.
4. **Event edit oleh guru salah** — Guru A cipta peristiwa kelasnya; log masuk sebagai Guru B
   dan cuba simpan semula dengan `id` peristiwa A (atau `class_id` kelas A) →
   `403 bukan peristiwa kelas anda` / `bukan kelas anda`.
5. **Tambah pengguna** — Tambah pelajar tanpa kata laluan → kata laluan rawak dipaparkan **sekali**;
   cuba log masuk dengannya → OK. Cuba kata laluan manual `abc` → ditolak (min 8).
6. **Logo** — Muat naik `.svg` → ditolak ("Guna PNG atau JPG"); PNG normal → muncul pada
   halaman login + kepala PDF.
7. **MC** — Muat naik fail `.pdf` palsu (sebenarnya teks) → ditolak oleh pemeriksaan kandungan;
   PDF/PNG sebenar → naik dan boleh dibuka oleh pelajar itu, guru kelas, dan admin sahaja.
8. **CSV** — Eksport laporan, buka dalam Excel → sebarang sel yang bermula `=`/`+`/`@`
   dipaparkan sebagai teks (tidak mengira formula).
9. **Peratus pelajar** — Daftar seorang pelajar ke dua kelas → peratus kekal ≤ 100%.
10. **Kesilapan pelayan** — Paksa ralat (mis. `RECEIPT_KEY` kosong) → JSON mesej, bukan halaman putih.

## 5. Baki risiko yang diketahui (tidak diubah dalam patch ini)

- `log_act` kini selamat di bawah php-fpm (GET_LOCK), **tetapi** import berbilang baris masih
  tiada satu transaksi — separa import mungkin tinggal jika pelayan mati di tengah jalan.
- Tiada HSTS / CSP header (boleh ditambah kemudian; InfinityFree sudah paksa HTTPS).
- Kata laluan lama dalam `data-real.sql` masih hash/plaintext asal daripada sistem lama — tukar (rotate) selepas live (langkah 5 di atas).

---

## 6. Kalendar Kelas — paparan JADUAL (table) baharu · 2026-11-20

Permintaan: ganti grid kalendar dengan **jadual bulanan** (satu baris per kelas dirancang).
API `events.php` (tambah/simpan/padam) dan jadual `class_events` **tidak berubah bentuk** —
data lama terus muncul.

### js/calendar.js  *( tulis-semula paparan )*
- **Navigasi bulan**: `‹ Bulan Sebelum` / `Bulan Ini` / `Bulan Seterusnya ›` + picker `type=month`; tajuk contoh "November 2026" (nama bulan BM).
- **Jadual bulanan** (lalai): lajur Tarikh · Hari · Masa (`08:00 – 10:00` dari `start_h`+`duration_h`) · Kelas · Subjek · Bilik · Guru (**admin sahaja**) · Catatan · Tindakan (Sunting/Padam seperti kebenaran sedia ada). Disusun ikut tarikh kemudian jam. Baris hari ini diserlahkan (`ktoday`); garis tebal memisahkan minggu (`wksep`). Kosong → "Tiada jadual untuk bulan ini".
- **Tapisan**: dropdown kelas (Semua kelas + setiap kelas) + carian teks pada subjek/bilik — kedua-duanya di sebelah klien (data bulan sudah dimuat).
- **Tiga paparan (togol `Kalendar · Jadual · Mingguan`)** — susulan permintaan pengguna 2026-11-21: **Kalendar bulanan kini LALAI** (kisi 7 lajur Isnin–Ahad, kotak tarikh, cip kelas berwarna am/petang, hari ini berbingkai, klik tarikh → tambah, klik cip → sunting/padam, "+N lagi" bila >3). Paparan **Jadual** (table) kekal sebagai pilihan kedua; **Mingguan** = Isnin–Ahad × 7:00–18:00 bacaan-sahaja dengan navigasi minggu. Tapisan & carian terpakai pada ketiga-tiga paparan; Cetak mencetak Kalendar (bukan grid mingguan).
- **Butang**: `+ Tambah Jadual` (buka form sedia ada + medan **Tarikh** baharu supaya tambah tidak memerlukan klik kalendar), `Cetak` (window.print + CSS cetak), `Muat Turun CSV` bulanan.
- **CSV**: BOM UTF-8 (`\ufeff`), CRLF, lajur ikut paparan (Guru ikut role); sel bermula `= + - @` didahului `'` (elak Excel jalankan formula).
- **XSS**: semua data pelayan (kelas, subjek, bilik, guru, catatan, nama bulan pilihan) melalui `esc()` sebelum `innerHTML`; `id`/`class_id` hanya masuk sebagai angka/attr terlindung.

### api/events.php
- `ORDER BY c.name` juga untuk senarai kelas guru (dropdown tapisan tersusun);
  pengesahan `month` (YYYY-MM), prepared statements & semakan kelas **semasa** peristiwa (IDOR) sudah ada dari set patch sebelum ini — dikekalkan & diuji semula.

### css/theme.css  *(blok "Kalendar Jadual Kelas" ditulis semula)*
- Gaya `.kbar/.ktbl/.kscroll` (had scroll sendiri, `thead th` **sticky** — penting untuk telefon & bulan panjang), `.gtbl` grid mingguan, kemas dialog form.
- **Mobile ≤820**: carian & butang jadi baris penuh; jadual kekal scroll mengufuk dalam `.kscroll` (tiada overflow pada halaman).
- **Cetak (`@media print`)**: toolbar/kawalan/butang Tindakan disembunyikan, header tidak lagi sticky, baris `break-inside:avoid` — keluaran bersih.

### app/bootstrap.php
- `SCHEMA_VERSION` `mysql-3` → `mysql-4`; **index gabungan** `idx_ev_date_class (event_date, class_id)` melalui `add_idx()` — sokong skop bulan + tapisan kelas.

### Ujian semula (port MySQL, :3003)
| Suite | Keputusan |
|---|---|
| `my_eh_cal_test.py` (API kalendar) | **29/29** |
| `my_eh_admin_test.py` | 45/45 |
| `my_eh_teacher_test.py` | 35/35 |
| `my_eh_p6smoke.js` (konsol, semua tab klik) | `excs:[]` |
| CDP DOM probe (admin & guru) | lajur betul, Guru tiada untuk guru, sticky=sticky, overflow=auto, wksep ktoday betul, CSV BOM benar + guard `'=1+2` benar |
| XSS (selirah `<img onerror>`, `onmouseover`, `<script>` dalam subjek/bilik/catatan) | teks literal, `pwned:false` |
| IDOR (guru class-1 cuba edit/padam peristiwa class-2) | **403** kedua-dua jalan |
| 390px | jadual scroll dalam container, `hscroll:false` |

### Checklist pantas (selepas pasang)
1. Buka tab **Kalendar Kelas** → jadual bulan ini; tukar bulan (butang + picker) → tajuk BM betul.
2. Tambah sebagai guru → baris muncul; sunting & padam baris sendiri OK; cuba edit peristiwa guru lain (hantar `id` melalui DevTools) → `403 bukan peristiwa kelas anda`.
3. Admin: lajur **Guru** ada; guru: lajur itu tiada.
4. Togol **Grid Mingguan** → petak Isnin–Ahad × jam, navigasi minggu jalan.
5. **Cetak** → toolbar & butang hilang, jadual penuh; **Muat Turun CSV** → Excel buka kemas, karekter BM betul.
6. Telefon (±390px) → jadual boleh geser ke kiri/kanan, header kekal di atas, page tidak "pecah".

### Butang tutup popup (2026-11-21) — js/calendar.js, css/theme.css
- Dialog Tambah/Sunting jadual kini ada butang **X Tutup** di kanan atas (sentiasa ada, bukan hanya mod sunting).

### Cache-buster (2026-11-21) — admin.html, teacher.html, index.html, scan.html, student.html
- Rujukan `/css/theme.css` dan `/js/calendar.js` kini `?v=2026-11-21` — elak browser/CDN InfinityFree hidangkan fail lama (punca layout kalendar pecah di live: calendar.js lama + theme.css baru).

## 7. Data demo penuh 3 bulan (2026-11-21)

Fail baharu: `import/data-demo-full.sql` (~180 KB) — satu import untuk semua data demo:

- 167 sesi QR tertutup + 1 sesi BUKA pada hari import (Kelas 5 Cemerlang, "Sains (Kuiz Topik 4)")
- 775 rekod kehadiran dengan resit (hadir / lewat / cuti / tiada rekod, ~86% hadir)
- 19 permohonan cuti (16 Approved, 2 Pending, 1 Rejected)
- 8 pengumuman Ogos-November (audience all/student/teacher, ada aktif & tamat tempoh)
- 75 jadual kalendar + 14 pengguna + 2 kelas + 11 slot masa + org_settings

Semua tarikh ditulis sebagai ekspresi `DATE_FORMAT(DATE_ADD(CURDATE(), INTERVAL -n DAY))`, jadi
sejarah 3 bulan sentiasa "mengikuti" hari sebenar — fail yang sama diimport bulan depan tetap
menunjukkan Ogos hingga "hari ini" dan papan pemuka/suapan tidak kosong.

Amaran: fail ini MEMADAM jadual data termasuk `users` (login demo: admin/admin123, siti/siti123,
ahmad/ahmad123, pelajar/pelajar123). Guna `data-real.sql` XOR `data-demo-full.sql`, jangan dua-dua.
`activity_log` & `login_attempts` dikosongkan supaya rantaian audit bermula bersih.
Cap-jari resit demo tidak disahkan semula oleh sistem, jadi RECEIPT_KEY tidak perlu diubah.
