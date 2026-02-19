import discord
from discord.ext import commands
import sqlite3
import random
import config
import difflib
import asyncio
# ====== SETUP BOT ======

intents = discord.Intents.default()
intents.message_content = True
search_sessions = {}
async def kirim_panjang(ctx, text):
    for i in range(0, len(text), 1900):
        await ctx.send(text[i:i+1900])

async def kirim_lima(ctx):
    session = search_sessions.get(ctx.author.id)
    if not session:
        return

    results = session["results"]
    i = session["index"]

    batch = results[i:i+5]

    if not batch:
        await ctx.send("📭 Hasil sudah habis.")
        del search_sessions[ctx.author.id]
        return

    text = "🔍 Hasil pencarian:\n"
    for r in batch:
        text += f"**ID {r[0]}** → {r[1][:60]}...\n"

    text += "\n👉 Ketik `lagi` untuk melihat berikutnya."
    await ctx.send(text)

    session["index"] += 5

bot = commands.Bot(command_prefix="!", intents=intents)
def hanya_dm():
    async def predicate(ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            return True
        # await ctx.send("❌ Command ini hanya bisa digunakan lewat DM bot.")
        return False
    return commands.check(predicate)
admin_sessions = set()

def admin_only():
    async def predicate(ctx):
        if ctx.author.id in admin_sessions:
            return True
        await ctx.send("❌ Kamu belum login admin. Ketik !adminlogin di DM.")
        return False
    return commands.check(predicate)

# ====== DATABASE SETUP ======
conn = sqlite3.connect("fakta.db")
c = conn.cursor()

try:
    c.execute("ALTER TABLE fakta ADD COLUMN views INTEGER DEFAULT 0")
    conn.commit()
except:
    pass

c.execute("""
CREATE TABLE IF NOT EXISTS fakta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fakta TEXT,
    rating REAL DEFAULT 10
)
""")
conn.commit()
# ====== TABLE FEEDBACK ======
c.execute("""
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    pesan TEXT
)
""")
conn.commit()
# ====== TABLE REPORT ======
c.execute("""
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fakta_id INTEGER,
    user TEXT,
    alasan TEXT
)
""")
conn.commit()
# ====== TABLE UPDATE ======
c.execute("""
CREATE TABLE IF NOT EXISTS updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    isi TEXT,
    tanggal TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# ====== COMMAND TAMBAH FAKTA ======
@bot.command()
async def tambahfakta(ctx, *, fakta_text: str):

    c.execute("SELECT fakta FROM fakta")
    semua_fakta = [row[0] for row in c.fetchall()]

    for f in semua_fakta:
        similarity = difflib.SequenceMatcher(None, f.lower(), fakta_text.lower()).ratio()
        if similarity > 0.85:
            await ctx.send("⚠️ Fakta ini sangat mirip dengan fakta yang sudah ada!")
            return

    c.execute("INSERT INTO fakta (fakta, rating) VALUES (?, 10)", (fakta_text,))
    conn.commit()

    await ctx.send("✅ Fakta baru berhasil ditambahkan!")
@bot.command()
async def report(ctx, fakta_id: int, *, alasan: str):

    # cek apakah fakta ada
    c.execute("SELECT id FROM fakta WHERE id=?", (fakta_id,))
    data = c.fetchone()

    if not data:
        await ctx.send("❌ Fakta tidak ditemukan")
        return

    user = str(ctx.author)

    c.execute(
        "INSERT INTO reports (fakta_id, user, alasan) VALUES (?, ?, ?)",
        (fakta_id, user, alasan)
    )
    conn.commit()

    await ctx.send("🚩 Laporan berhasil dikirim. Terima kasih!")

# ====== INFO BOT ======
@bot.command()
async def info(ctx):
    await ctx.send("""
🤖 **FaktaBot**
Bot Discord untuk menyimpan dan mencari fakta unik 🌍  
Prefix: `!`

Dibuat oleh: Nicholas  
Fitur utama: Fakta random + rating + pencarian fakta
""")
# ====== HELP COMMAND ======
bot.remove_command("help")

@bot.command()
async def help(ctx):
    await ctx.send("""
📌 **FaktaBot**

🧠 Fakta:
• /fakta → Fakta random
• /tambahfakta <teks> → Tambah fakta
• /carifakta <kata> → Cari fakta
• /lihatfakta <id> → Detail fakta
• /rate <id> <1-10> → Rating fakta

🚩 Lainnya:
• /report <id> <alasan> → Laporkan fakta
• /feedback <pesan> → Kirim saran
• /listupdate → Lihat update bot

💡 Tips:
Ketik `lagi` setelah cari fakta untuk lihat hasil berikutnya.
""")

@bot.command()
@hanya_dm()
@admin_only()
async def adminhelp(ctx):
    await ctx.send("""
🛠️ **FaktaBot — Admin Panel**

📢 Update:
• /tambahupdate → Tambah update
• /hapusupdate → Hapus update
• /listupdate → Lihat update

📩 Moderasi:
• /listfeedback → Lihat feedback
• /listreport → Lihat laporan
• /hapusreport → Hapus laporan

🔐 Admin:
• /adminlogin → Login admin
• /adminlogout → Logout admin

⚙️ Catatan:
Semua command admin hanya di DM.
""")

# ====== COMMAND RATE FAKTA ======
@bot.command()
async def rate(ctx, fakta_id: int, nilai: int):
    if nilai < 1 or nilai > 10:
        await ctx.send("❌ Rating harus 1-10")
        return

    # ambil rating lama
    c.execute("SELECT rating FROM fakta WHERE id=?", (fakta_id,))
    data = c.fetchone()

    if not data:
        await ctx.send("❌ Fakta tidak ditemukan")
        return

    rating_lama = data[0]
    rating_baru = (rating_lama + nilai) / 2  # rata-rata sederhana

    c.execute("UPDATE fakta SET rating=? WHERE id=?", (rating_baru, fakta_id))
    conn.commit()

    await ctx.send(f"⭐ Rating fakta {fakta_id} sekarang = {rating_baru:.2f}")
FEEDBACK_PASS = config.password
# ====== COMMAND FAKTA RANDOM BERBOBOT ======
@bot.command()
async def fakta(ctx):
    c.execute("SELECT id, fakta, rating, views FROM fakta")
    data = c.fetchall()

    if not data:
        await ctx.send("❌ Database kosong")
        return

    ids = [d[0] for d in data]
    fakta_list = [d[1] for d in data]
    weights = [d[2] for d in data]

    chosen = random.choices(list(zip(ids, fakta_list)), weights=weights)[0]

    fakta_id = chosen[0]
    fakta_text = chosen[1]

    # tambah views
    c.execute("UPDATE fakta SET views = views + 1 WHERE id=?", (fakta_id,))
    conn.commit()

    # ambil views terbaru
    c.execute("SELECT views FROM fakta WHERE id=?", (fakta_id,))
    views = c.fetchone()[0]

    await ctx.send(
        f"🌍 Fakta Unik (ID {fakta_id}):\n"
        f"{fakta_text}\n\n"
        f"👀 Dilihat: {views} kali"
    )

    await ctx.send("⭐ Mau kasih rating? Ketik angka 1–10 atau ketik `skip`")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        msg = await bot.wait_for("message", check=check, timeout=30)

        if msg.content.lower() == "skip":
            await ctx.send("👍 Oke, dilewati.")
            return

        nilai = int(msg.content)

        if nilai < 1 or nilai > 10:
            await ctx.send("❌ Rating harus 1–10")
            return

        c.execute("SELECT rating FROM fakta WHERE id=?", (fakta_id,))
        rating_lama = c.fetchone()[0]

        rating_baru = (rating_lama + nilai) / 2

        c.execute("UPDATE fakta SET rating=? WHERE id=?", (rating_baru, fakta_id))
        conn.commit()

        await ctx.send(f"⭐ Terima kasih! Rating sekarang = {rating_baru:.2f}")

    except asyncio.TimeoutError:
        await ctx.send("⌛ Waktu habis, rating dibatalkan.")


# ====== CARI FAKTA DENGAN KATA KUNCI ======
@bot.command()
async def carifakta(ctx, *, kata: str):

    c.execute("SELECT id, fakta FROM fakta WHERE fakta LIKE ?", (f"%{kata}%",))
    results = c.fetchall()

    if not results:
        return await ctx.send("❌ Tidak ada fakta yang cocok")

    search_sessions[ctx.author.id] = {
        "results": results,
        "index": 0
    }

    await kirim_lima(ctx)


# ====== LIHAT FAKTA DETAIL DARI ID ======

@bot.command()
async def lihatfakta(ctx, fakta_id: int):
    c.execute("SELECT id, fakta, rating, views FROM fakta WHERE id=?", (fakta_id,))
    data = c.fetchone()

    if not data:
        return await ctx.send("❌ Fakta tidak ditemukan")

    # tambah views
    c.execute("UPDATE fakta SET views = views + 1 WHERE id=?", (fakta_id,))
    conn.commit()

    views = data[3] + 1

    await ctx.send(
        f"📚 Fakta ID {data[0]}\n"
        f"🧠 {data[1]}\n"
        f"⭐ Rating: {data[2]:.2f}\n"
        f"👀 Dilihat: {views} kali"
    )

    await ctx.send("⭐ Mau kasih rating? Ketik angka 1–10 atau ketik `skip`")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        msg = await bot.wait_for("message", check=check, timeout=30)

        if msg.content.lower() == "skip":
            await ctx.send("👍 Oke, dilewati.")
            return

        nilai = int(msg.content)

        if nilai < 1 or nilai > 10:
            await ctx.send("❌ Rating harus 1–10")
            return

        rating_lama = data[2]
        rating_baru = (rating_lama + nilai) / 2

        c.execute("UPDATE fakta SET rating=? WHERE id=?", (rating_baru, fakta_id))
        conn.commit()

        await ctx.send(f"⭐ Terima kasih! Rating sekarang = {rating_baru:.2f}")

    except asyncio.TimeoutError:
        await ctx.send("⌛ Waktu habis, rating dibatalkan.")
@bot.command()
async def trending(ctx):

    c.execute("""
        SELECT id, fakta, views
        FROM fakta
        ORDER BY views DESC
        LIMIT 5
    """)

    data = c.fetchall()

    if not data:
        return await ctx.send("📭 Belum ada data.")

    text = "🔥 Fakta Trending:\n\n"

    for d in data:
        text += f"👀 {d[2]}x — ID {d[0]}\n{d[1][:80]}\n\n"

    await ctx.send(text)

# ====== KIRIM FEEDBACK ======
@bot.command()
async def feedback(ctx, *, pesan: str):
    user = str(ctx.author)
    c.execute("INSERT INTO feedback (user, pesan) VALUES (?, ?)", (user, pesan))
    conn.commit()
    await ctx.send("✅ Terima kasih! Feedback kamu sudah disimpan.")
@bot.command()
async def listupdate(ctx):

    c.execute("SELECT id, isi, tanggal FROM updates ORDER BY id DESC LIMIT 10")
    data = c.fetchall()

    if not data:
        await ctx.send("📭 Belum ada update.")
        return

    text = "📢 **Update Terbaru Bot:**\n"

    for d in data:
        text += f"\n🔹 {d[1]} ({d[2]})"

    await ctx.send(text)
@bot.command()
@hanya_dm()
@admin_only()
async def tambahupdate(ctx):

    await ctx.send("✏️ Kirim isi update:")

    def check(m):
        return m.author == ctx.author and isinstance(m.channel, discord.DMChannel)

    try:
        update_msg = await bot.wait_for("message", check=check, timeout=120)

        c.execute("INSERT INTO updates (isi) VALUES (?)", (update_msg.content,))
        conn.commit()

        await ctx.send("✅ Update berhasil ditambahkan!")

    except asyncio.TimeoutError:
        await ctx.send("⌛ Waktu habis.")

# ====== LIHAT FEEDBACK 
@bot.command()
@hanya_dm()
@admin_only()
async def listfeedback(ctx):

    c.execute("SELECT id, user, pesan FROM feedback")
    data = c.fetchall()

    if not data:
        await ctx.send("📭 Tidak ada feedback")
        return

    text = "📩 **Daftar Feedback:**\n"
    for d in data:
        text += f"ID {d[0]} | {d[1]}: {d[2]}\n"

    await ctx.send(text)

@bot.command()
@hanya_dm()
@admin_only()
async def listreport(ctx):

    c.execute("SELECT id, fakta_id, user, alasan FROM reports")
    data = c.fetchall()

    if not data:
        await ctx.send("📭 Tidak ada report")
        return

    text = "🚩 **Daftar Report Fakta:**\n"
    for d in data:
        text += f"ID {d[0]} | Fakta {d[1]} | {d[2]} → {d[3]}\n"

    await ctx.send(text)
@bot.command()
@hanya_dm()
@admin_only()
async def hapusupdate(ctx):

    await ctx.send("🗑️ Masukkan ID update yang ingin dihapus:")

    def check(m):
        return m.author == ctx.author and isinstance(m.channel, discord.DMChannel)

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)

        update_id = int(msg.content)

        c.execute("DELETE FROM updates WHERE id=?", (update_id,))
        conn.commit()

        await ctx.send("✅ Update berhasil dihapus")

    except:
        await ctx.send("❌ ID tidak valid atau waktu habis.")
@bot.command()
@hanya_dm()
@admin_only()
async def hapusreport(ctx):

    await ctx.send("🚩 Masukkan ID report yang ingin dihapus:")

    def check(m):
        return m.author == ctx.author and isinstance(m.channel, discord.DMChannel)

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)

        report_id = int(msg.content)

        c.execute("DELETE FROM reports WHERE id=?", (report_id,))
        conn.commit()

        await ctx.send("✅ Report berhasil dihapus")

    except:
        await ctx.send("❌ ID tidak valid atau waktu habis.")

@bot.command()
@hanya_dm()
async def adminlogin(ctx):
    await ctx.send("🔐 Masukkan password admin:")

    def check(m):
        return m.author == ctx.author and isinstance(m.channel, discord.DMChannel)

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)

        if msg.content == FEEDBACK_PASS:
            admin_sessions.add(ctx.author.id)
            await ctx.send("✅ Mode admin aktif!")
        else:
            await ctx.send("❌ Password salah.")

    except asyncio.TimeoutError:
        await ctx.send("⌛ Waktu habis.")
        
@bot.command()
@hanya_dm()
@admin_only()
async def listfakta(ctx):

    c.execute("SELECT id, fakta, rating FROM fakta")
    data = c.fetchall()

    if not data:
        await ctx.send("📭 Database kosong.")
        return

    text = "📚 DAFTAR FAKTA:\n\n"

    for d in data:
        text += f"ID {d[0]} | ⭐ {d[2]:.1f}\n{d[1][:100]}\n\n"

    await kirim_panjang(ctx, text)

@bot.command()
@hanya_dm()
@admin_only()
async def hapusfakta(ctx):

    await ctx.send("🗑️ Masukkan ID fakta yang ingin dihapus:")

    def check(m):
        return m.author == ctx.author and isinstance(m.channel, discord.DMChannel)

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)
        fakta_id = int(msg.content)

        # cek fakta
        c.execute("SELECT fakta FROM fakta WHERE id=?", (fakta_id,))
        data = c.fetchone()

        if not data:
            await ctx.send("❌ Fakta tidak ditemukan.")
            return

        await ctx.send(
            f"⚠️ Yakin ingin menghapus?\n\n🧠 {data[0][:150]}\n\nKetik `ya` untuk konfirmasi."
        )

        confirm = await bot.wait_for("message", check=check, timeout=30)

        if confirm.content.lower() == "ya":
            c.execute("DELETE FROM fakta WHERE id=?", (fakta_id,))
            conn.commit()
            await ctx.send("✅ Fakta berhasil dihapus.")
        else:
            await ctx.send("❎ Dibatalkan.")

    except asyncio.TimeoutError:
        await ctx.send("⌛ Waktu habis.")
    except:
        await ctx.send("❌ ID tidak valid.")

@bot.command()
@hanya_dm()
async def adminlogout(ctx):
    admin_sessions.discard(ctx.author.id)
    await ctx.send("👋 Mode admin dimatikan.")
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    session = search_sessions.get(message.author.id)

    if session and message.content.lower() == "lagi":
        ctx = await bot.get_context(message)
        await kirim_lima(ctx)
        return

    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ Command ini hanya bisa digunakan lewat DM bot.")
    else:
        raise error

# ====== START BOT ======
bot.run(config.TOKEN)
