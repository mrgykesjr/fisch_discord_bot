#!/usr/bin/env python3
import json
import discord
from discord.ext import commands
from discord import app_commands
import os

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable not found.")
GUILD_ID = None

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

bestiary_data = load_json("data/bestiary.json")

def find_fish(key: str):
    return bestiary_data.get(key.lower().strip())

@bot.tree.command(name="bestiary", description="Get info about a Fisch fish.")
@app_commands.describe(name="Name of the fish (case-insensitive)")
async def bestiary(interaction: discord.Interaction, name: str):
    entry = find_fish(name)
    if not entry:
        await interaction.response.send_message(
            f"❌ Could not find a fish named **{name}**.",
            ephemeral=True
        )
        return

    wiki_name = entry.get("name", name).replace(" ", "_")
    wiki_url = f"https://fischipedia.org/wiki/{wiki_name}"

    embed = discord.Embed(
        title=entry.get("name", name.title()),
        url=wiki_url,
        color=discord.Color.teal()
    )

    # Rarity
    if entry.get("rarity"):
        embed.add_field(name="Rarity", value=entry["rarity"], inline=False)

    # Location
    if entry.get("location"):
        embed.add_field(name="Location", value=entry["location"], inline=False)

    # Resilience
    if entry.get("resilience"):
        embed.add_field(name="Resilience", value=entry["resilience"], inline=False)

    # Progress Speed
    ps = entry.get("progress_speed") or entry.get("progress speed")
    if ps:
        embed.add_field(name="Progress Speed", value=ps, inline=False)

    # Preferred Bait
    if entry.get("bait"):
        embed.add_field(name="Preferred Bait", value=entry["bait"], inline=False)

    # Conditions
    conds = []
    if entry.get("time"):
        conds.append(f"**Time:** {entry['time']}")
    if entry.get("weather"):
        conds.append(f"**Weather:** {entry['weather']}")
    if entry.get("season"):
        conds.append(f"**Season:** {entry['season']}")
    if conds:
        embed.add_field(name="Conditions", value="\n".join(conds), inline=False)

    # Weight (kg) — include min/avg/max if present
    w_lines = []
    if entry.get("min_weight"):
        w_lines.append(f"Min: {entry['min_weight']} kg")
    if entry.get("avg_weight"):
        w_lines.append(f"Avg: {entry['avg_weight']} kg")
    if entry.get("max_weight"):
        w_lines.append(f"Max: {entry['max_weight']} kg")
    if w_lines:
        embed.add_field(name="Weight (kg, base)", value="\n".join(w_lines), inline=False)

    # Value
    v_lines = []
    if entry.get("value_per_kg_base"):
        v_lines.append(f"C$/kg (base): {entry['value_per_kg_base']}")
    if entry.get("base_value_c"):
        v_lines.append(f"Average C$ (base): {entry['base_value_c']}")
    if v_lines:
        embed.add_field(name="Value", value="\n".join(v_lines), inline=False)

    await interaction.response.send_message(embed=embed)

@bestiary.autocomplete("name")
async def bestiary_autocomplete(interaction: discord.Interaction, current: str):
    lower = current.lower()
    choices = []
    for key, data in bestiary_data.items():
        display = data.get("name", key)
        if lower in key.lower() or lower in display.lower():
            choices.append(app_commands.Choice(name=display, value=key))
    return choices[:25]

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        if GUILD_ID:
            await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
            print("Slash commands synced to guild.")
        else:
            await bot.tree.sync()
            print("Slash commands synced globally.")
    except Exception as e:
        print("Error syncing commands:", e)

bot.run(TOKEN)
