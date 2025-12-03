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

enchants_data = load_json("data/enchants.json")
categories_data = load_json("data/enchant_categories.json")
bestiary_data = load_json("data/bestiary.json")

def find_fish(key: str):
    return bestiary_data.get(key.lower().strip())

# --- /bestiary ---
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

    # Preferred Bait
    if entry.get("bait"):
        embed.add_field(name="Preferred Bait", value=entry["bait"], inline=False)

    # Conditions
    cond_lines = []
    if entry.get("time"):
        cond_lines.append(f"**Time:** {entry['time']}")
    if entry.get("weather"):
        cond_lines.append(f"**Weather:** {entry['weather']}")
    if entry.get("season"):
        cond_lines.append(f"**Season:** {entry['season']}")
    if cond_lines:
        embed.add_field(name="Conditions", value="\n".join(cond_lines), inline=False)

    # Weight (kg)
    min_w = entry.get("min_weight")
    avg_w = entry.get("avg_weight")
    max_w = entry.get("max_weight")
    weight_lines = []
    if min_w:
        weight_lines.append(f"Min: {min_w} kg")
    if avg_w:
        weight_lines.append(f"Avg: {avg_w} kg")
    if max_w:
        weight_lines.append(f"Max: {max_w} kg")
    if weight_lines:
        embed.add_field(name="Weight (kg, base)", value="\n".join(weight_lines), inline=False)

    # Value
    value_lines = []
    if entry.get("value_per_kg_base"):
        value_lines.append(f"C$/kg (base): {entry['value_per_kg_base']}")
    if entry.get("base_value_c"):
        value_lines.append(f"Average C$ (base): {entry['base_value_c']}")
    if value_lines:
        embed.add_field(name="Value", value="\n".join(value_lines), inline=False)

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
