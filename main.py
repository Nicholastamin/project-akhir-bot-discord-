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

# ====== COMMAND TAMBAH FAKTA ======
@bot.command()
async def tambahfakta(ctx, *, fakta_text: str):
    c.execute("INSERT INTO fakta (fakta, rating) VALUES (?, 10)", (fakta_text,))
    conn.commit()
    await ctx.send(f"✅ Fakta ditambahkan dengan rating awal 10!")

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

# ====== START BOT ======
bot.run(config.TOKEN)
