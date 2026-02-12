import discord
from discord.ext import commands
import sqlite3
import random
import config
# ====== SETUP BOT ======
TOKEN = "ISI_TOKEN_DISCORD_KAMU"
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

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

# ====== COMMAND TAMBAH FAKTA ======
@bot.command()
async def tambahfakta(ctx, *, fakta_text: str):
    c.execute("INSERT INTO fakta (fakta, rating) VALUES (?, 10)", (fakta_text,))
    conn.commit()
    await ctx.send(f"✅ Fakta ditambahkan dengan rating awal 10!")
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

# ====== LIHAT FEEDBACK (ADMIN ONLY) ======

@bot.command()
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

# ====== START BOT ======
bot.run(config.TOKEN)
