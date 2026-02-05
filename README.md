🎶 rhakim Music Player
rhakim Music Player adalah aplikasi pemutar video musik (MV) premium berbasis Python. Didesain untuk para kolektor MV yang menginginkan pengalaman menonton sambil beraktivitas, lengkap dengan fitur jendela melayang yang canggih, sinkronisasi lirik, dan integrasi sosial.

🚀 Fitur Utama (v2.0)
📺 Floating Cinema: Jendela video melayang yang always-on-top, bisa di-resize, dan mendukung mode sembunyi (withdraw).

🎤 Pro Lyric Engine:

Dual Mode: Mendukung lirik lokal (.lrc) dan pencarian otomatis via internet.

Manual Offset: Kalibrasi waktu lirik (± 0.5 detik) secara langsung jika lirik tidak sinkron.

Auto-scaling: Font lirik otomatis mengecil atau membesar mengikuti ukuran jendela.

🕹️ Advanced Playback:

Volume Control: Slider volume mandiri yang tidak mengganggu volume sistem Windows.

Shuffle & Repeat: Mode putar acak dan pengulangan lagu (One/All).

👾 Discord Rich Presence: Menampilkan judul lagu yang sedang kamu dengarkan secara real-time di profil Discord kamu.

🛡️ Security Minded: Menggunakan sistem .env untuk mengamankan Discord Client ID kamu agar tidak bocor di publik.

📦 Persiapan & Instalasi
Instal VLC Media Player: Aplikasi ini membutuhkan VLC 64-bit terinstal di sistem kamu.

Clone Repo:

Bash
git clone https://github.com/Ranggahakim/rhakimMusicPlayer.git
cd rhakimMusicPlayer
Instal Library:

Bash
pip install customtkinter python-vlc syncedlyrics pypresence python-dotenv
Konfigurasi Keamanan: Buat file .env di folder utama dan masukkan ID Discord kamu:

Plaintext
DISCORD_CLIENT_ID=GANTI_DENGAN_ID_KAMU
🛠️ Cara Build Menjadi Aplikasi (.exe)
Gunakan perintah berikut untuk membungkus kode menjadi file executable mandiri dengan nama resmi dan ikon kustom:

PowerShell
python -m PyInstaller --noconsole --onefile --name "rhakim Music Player" --icon=app.ico --add-data "ui_components.py;." main.py
📂 Struktur Proyek
main.py: Otak utama aplikasi, manajemen playlist, dan Discord RPC.

ui_components.py: Komponen GUI untuk jendela lirik melayang.

app.ico: Ikon aplikasi 🎶🔊.

.env: Penyimpanan rahasia Client ID (Jangan di-push ke GitHub!).

Tips Pro: Auto-Sync Lirik
Pastikan nama file lagu dan file lirik kamu sama persis (misal: MvLagu.mp4 dan MvLagu.lrc) agar aplikasi bisa langsung memutar lirik secara offline tanpa perlu internet.
