import discord
from discord.ext import commands
import sqlite3
import random
import config
import difflib

# ====== SETUP BOT ======
TOKEN = "ISI_TOKEN_DISCORD_KAMU"
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
def hanya_dm():
    async def predicate(ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            return True
        # await ctx.send("❌ Command ini hanya bisa digunakan lewat DM bot.")
        return False
    return commands.check(predicate)

# ====== DATABASE SETUP ======
conn = sqlite3.connect("fakta.db")
c = conn.cursor()

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
📌 **Daftar Command FaktaBot**

🧠 Fakta:
!tambahfakta <teks> → Tambah fakta baru  
!fakta → Fakta random  
!rate <id> <1-10> → Rating fakta  
!carifakta <kata> → Cari fakta dari kata  
!lihatfakta <id> → Lihat fakta detail  

ℹ️ Info:
!info → Info bot  
!help → Bantuan command  
!feedback → Masukkan saran atau kritik
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
    c.execute("SELECT id, fakta, rating FROM fakta")
    data = c.fetchall()

    if not data:
        await ctx.send("❌ Database kosong")
        return

    ids = [d[0] for d in data]
    fakta_list = [d[1] for d in data]
    weights = [d[2] for d in data]  # rating jadi bobot

    # weighted random
    chosen = random.choices(list(zip(ids, fakta_list)), weights=weights)[0]

    await ctx.send(f"🌍 Fakta Unik (ID {chosen[0]}):\n{chosen[1]}")

# ====== CARI FAKTA DENGAN KATA KUNCI ======
@bot.command()
async def carifakta(ctx, *, kata: str):
    c.execute("SELECT id, fakta FROM fakta WHERE fakta LIKE ?", (f"%{kata}%",))
    results = c.fetchall()

    if not results:
        return await ctx.send("❌ Tidak ada fakta yang cocok")

    # batasi 5 hasil biar tidak spam
    results = results[:5]

    msg = f"🔍 Hasil pencarian untuk **{kata}**:\n"
    for r in results:
        msg += f"**ID {r[0]}** → {r[1][:50]}...\n"

    msg += "\n📌 Ketik: `!lihatfakta ID` untuk melihat detail. Jika tidak ada silahkan  ketik kata yang lebih detail"
    await ctx.send(msg)

# ====== LIHAT FAKTA DETAIL DARI ID ======
@bot.command()
async def lihatfakta(ctx, fakta_id: int):
    c.execute("SELECT id, fakta, rating FROM fakta WHERE id=?", (fakta_id,))
    data = c.fetchone()

    if not data:
        return await ctx.send("❌ Fakta tidak ditemukan")

    await ctx.send(
        f"📚 Fakta ID {data[0]}\n"
        f"🧠 {data[1]}\n"
        f"⭐ Rating: {data[2]:.2f}"
    )

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
async def tambahupdate(ctx):

    await ctx.send("📩 Cek DM untuk menambahkan update.")

    try:
        await ctx.author.send("🔐 Masukkan password admin:")

        def check(m):
            return m.author == ctx.author and isinstance(m.channel, discord.DMChannel)

        msg = await bot.wait_for("message", check=check, timeout=60)

        if msg.content != FEEDBACK_PASS:
            await ctx.author.send("❌ Password salah.")
            return

        await ctx.author.send("✏️ Kirim isi update:")

        update_msg = await bot.wait_for("message", check=check, timeout=120)

        c.execute("INSERT INTO updates (isi) VALUES (?)", (update_msg.content,))
        conn.commit()

        await ctx.author.send("✅ Update berhasil ditambahkan!")

    except discord.Forbidden:
        await ctx.send("❌ Tidak bisa kirim DM.")

# ====== LIHAT FEEDBACK 

@bot.command()
@hanya_dm()
async def listfeedback(ctx):
    await ctx.send("📩 Cek DM kamu untuk memasukkan password!")

    # kirim pesan ke DM
    try:
        await ctx.author.send("🔐 Masukkan password untuk melihat feedback:")

        def check(m):
            return m.author == ctx.author and isinstance(m.channel, discord.DMChannel)

        msg = await bot.wait_for("message", check=check, timeout=60)

        if msg.content != FEEDBACK_PASS:
            await ctx.author.send("❌ Password salah! kembali ke server dan ketik perintah yang sama")
            return

        # ambil feedback
        c.execute("SELECT id, user, pesan FROM feedback")
        data = c.fetchall()

        if not data:
            await ctx.author.send("📭 Tidak ada feedback")
            return

        text = "📩 **Daftar Feedback:**\n"
        for d in data:
            text += f"ID {d[0]} | {d[1]}: {d[2]}\n"

        # kirim ke DM
        await ctx.author.send(text)

    except Exception as e:
        await ctx.send("❌ Saya tidak bisa DM kamu. Aktifkan DM dari server ini.")

@bot.command()
@hanya_dm()

async def listreport(ctx):
    await ctx.send("📩 Cek DM untuk password!")

    try:
        await ctx.author.send("🔐 Masukkan password admin:")

        def check(m):
            return m.author == ctx.author and isinstance(m.channel, discord.DMChannel)

        msg = await bot.wait_for("message", check=check, timeout=60)

        if msg.content != FEEDBACK_PASS:
            await ctx.author.send("❌ Password salah")
            return

        c.execute("SELECT id, fakta_id, user, alasan FROM reports")
        data = c.fetchall()

        if not data:
            await ctx.author.send("📭 Tidak ada report")
            return

        text = "🚩 **Daftar Report Fakta:**\n"
        for d in data:
            text += f"ID {d[0]} | Fakta {d[1]} | {d[2]} → {d[3]}\n"

        await ctx.author.send(text)

    except:
        await ctx.send("❌ Tidak bisa kirim DM")
@bot.command()
@hanya_dm()
async def hapusupdate(ctx):
    await ctx.send("📩 Cek DM untuk menghapus update.")

    try:
        await ctx.author.send("🔐 Masukkan password admin:")

        def check(m):
            return m.author == ctx.author and isinstance(m.channel, discord.DMChannel)

        msg = await bot.wait_for("message", check=check, timeout=60)

        if msg.content != FEEDBACK_PASS:
            await ctx.author.send("❌ Password salah")
            return

        await ctx.author.send("🗑️ Masukkan ID update yang ingin dihapus:")

        id_msg = await bot.wait_for("message", check=check, timeout=60)

        update_id = int(id_msg.content)

        c.execute("DELETE FROM updates WHERE id=?", (update_id,))
        conn.commit()

        await ctx.author.send("✅ Update berhasil dihapus")

    except:
        await ctx.send("❌ Gagal menghapus update (cek DM atau ID).")
@bot.command()
@hanya_dm()
async def hapusreport(ctx):
    await ctx.send("📩 Cek DM untuk menghapus report.")

    try:
        await ctx.author.send("🔐 Masukkan password admin:")

        def check(m):
            return m.author == ctx.author and isinstance(m.channel, discord.DMChannel)

        msg = await bot.wait_for("message", check=check, timeout=60)

        if msg.content != FEEDBACK_PASS:
            await ctx.author.send("❌ Password salah")
            return

        await ctx.author.send("🚩 Masukkan ID report yang ingin dihapus:")

        id_msg = await bot.wait_for("message", check=check, timeout=60)

        report_id = int(id_msg.content)

        c.execute("DELETE FROM reports WHERE id=?", (report_id,))
        conn.commit()

        await ctx.author.send("✅ Report berhasil dihapus")

    except:
        await ctx.send("❌ Gagal menghapus report.")
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ Command ini hanya bisa digunakan lewat DM bot.")
    else:
        raise error

# ====== START BOT ======
bot.run(config.TOKEN)
