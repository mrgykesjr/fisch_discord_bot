#!/usr/bin/env python3
import json
import discord
from discord.ext import commands
from discord import app_commands
import os

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable not found.")
GUILD_ID = None  # or your guild ID if you want to limit commands to a specific guild

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

bestiary_data = load_json("data/bestiary.json")
rods_data = load_json("data/rods.json")

def find_fish(key: str):
    return bestiary_data.get(key.lower().strip())

def find_rod(key: str):
    return rods_data.get(key.lower().strip())

# --- /bestiary command ---
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
    rarity = entry.get("rarity")
    if rarity:
        embed.add_field(name="Rarity", value=rarity, inline=False)

    # Location
    location = entry.get("location")
    if location:
        embed.add_field(name="Location", value=location, inline=False)

    # Resilience
    resilience = entry.get("resilience")
    if resilience:
        embed.add_field(name="Resilience", value=resilience, inline=False)

    # Progress Speed
    ps = entry.get("progress_speed") or entry.get("progress speed")
    if ps:
        embed.add_field(name="Progress Speed", value=ps, inline=False)

    # Preferred Bait
    bait = entry.get("bait")
    if bait:
        embed.add_field(name="Preferred Bait", value=bait, inline=False)

    # Conditions (Time / Weather / Season)
    conds = []
    for key in ("time", "weather", "season"):
        if entry.get(key):
            conds.append(f"**{key.title()}:** {entry[key]}")
    if conds:
        embed.add_field(name="Conditions", value="\n".join(conds), inline=False)

    # Weight (kg) — support both naming conventions
    w_lines = []
    if entry.get("min_weight"):
        w_lines.append(f"Min: {entry['min_weight']} kg")
    if entry.get("avg_weight"):
        w_lines.append(f"Avg: {entry['avg_weight']} kg")
    if entry.get("max_weight"):
        w_lines.append(f"Max: {entry['max_weight']} kg")
    # also check alternative keys if present
    if entry.get("min. kg"):
        w_lines.append(f"Min: {entry['min. kg']} kg")
    if entry.get("avg. kg"):
        w_lines.append(f"Avg: {entry['avg. kg']} kg")
    if entry.get("base kg"):
        w_lines.append(f"Base: {entry['base kg']} kg")
    if entry.get("max. kg"):
        w_lines.append(f"Max: {entry['max. kg']} kg")

    if w_lines:
        embed.add_field(name="Weight (kg)", value="\n".join(w_lines), inline=False)

    # Value
    v_lines = []
    if entry.get("value_per_kg_base"):
        v_lines.append(f"C$/kg (base): {entry['value_per_kg_base']}")
    if entry.get("base c$"):
        v_lines.append(f"Base C$: {entry['base c$']}")
    if entry.get("avg. c$"):
        v_lines.append(f"Avg C$: {entry['avg. c$']}")
    if entry.get("max. c$"):
        v_lines.append(f"Max C$: {entry['max. c$']}")
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

# --- /rod command ---
@bot.tree.command(name="rod", description="Get info about a Fisch fishing rod.")
@app_commands.describe(name="Name of the rod (case-insensitive)")
async def rod(interaction: discord.Interaction, name: str):
    entry = find_rod(name)
    if not entry:
        await interaction.response.send_message(
            f"❌ Could not find a rod named **{name}**.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=entry.get("name", name),
        url=entry.get("url"),
        color=discord.Color.green()
    )

    # list of rod fields to show
    for field_key, display_name in [
        ("obtained_from", "Obtained From"),
        ("price", "Cost / Price"),
        ("lure", "Lure"),
        ("luck", "Luck"),
        ("control", "Control"),
        ("resilience", "Resilience"),
        ("max_weight", "Max Weight (kg)"),
        ("ability", "Ability / Passive"),
        ("recommended_enchants", "Recommended Enchants")
    ]:
        if field_key in entry:
            val = entry[field_key]
            if field_key == "recommended_enchants" and isinstance(val, list):
                val = "\n".join(f"• {e}" for e in val)
            embed.add_field(name=display_name, value=val, inline=False)

    await interaction.response.send_message(embed=embed)

@rod.autocomplete("name")
async def rod_autocomplete(interaction: discord.Interaction, current: str):
    lower = current.lower()
    choices = []
    for key, data in rods_data.items():
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
