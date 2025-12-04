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
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Load ALL data sets
bestiary_data = load_json("data/bestiary.json")
rods_data = load_json("data/rods.json")
enchants_data = load_json("data/enchants.json")
categories_data = load_json("data/enchant_categories.json")

# ---------------------------------------------------------
# FISH
# ---------------------------------------------------------
def find_fish(key: str):
    return bestiary_data.get(key.lower().strip())

@bot.tree.command(name="bestiary", description="Get info about a Fisch fish.")
@app_commands.describe(name="Name of the fish (case-insensitive)")
async def bestiary(interaction: discord.Interaction, name: str):
    entry = find_fish(name)
    if not entry:
        await interaction.response.send_message(
            f"❌ Could not find a fish named **{name}**.", ephemeral=True
        )
        return

    wiki_name = entry.get("name", name).replace(" ", "_")
    wiki_url = f"https://fischipedia.org/wiki/{wiki_name}"

    embed = discord.Embed(
        title=entry.get("name", name.title()),
        url=wiki_url,
        color=discord.Color.teal()
    )

    for key, label in [
        ("rarity", "Rarity"),
        ("location", "Location"),
        ("resilience", "Resilience"),
        ("progress_speed", "Progress Speed"),
        ("progress speed", "Progress Speed"),
        ("bait", "Preferred Bait"),
    ]:
        if entry.get(key):
            embed.add_field(name=label, value=entry[key], inline=False)

    conds = []
    for key in ("time", "weather", "season"):
        if entry.get(key):
            conds.append(f"**{key.title()}:** {entry[key]}")
    if conds:
        embed.add_field(name="Conditions", value="\n".join(conds), inline=False)

    w_lines = []
    for key, label in [
        ("min_weight", "Min"),
        ("avg_weight", "Avg"),
        ("max_weight", "Max"),
        ("min. kg", "Min"),
        ("avg. kg", "Avg"),
        ("base kg", "Base"),
        ("max. kg", "Max")
    ]:
        if entry.get(key):
            w_lines.append(f"{label}: {entry[key]} kg")
    if w_lines:
        embed.add_field(name="Weight (kg)", value="\n".join(w_lines), inline=False)

    v_lines = []
    for key, label in [
        ("value_per_kg_base", "C$/kg (base)"),
        ("base c$", "Base C$"),
        ("avg. c$", "Avg C$"),
        ("max. c$", "Max C$")
    ]:
        if entry.get(key):
            v_lines.append(f"{label}: {entry[key]}")
    if v_lines:
        embed.add_field(name="Value", value="\n".join(v_lines), inline=False)

    await interaction.response.send_message(embed=embed)

@bestiary.autocomplete("name")
async def bestiary_autocomplete(interaction, current: str):
    lower = current.lower()
    return [
        app_commands.Choice(name=data.get("name", key), value=key)
        for key, data in bestiary_data.items()
        if lower in key.lower() or lower in data.get("name", "").lower()
    ][:25]

# ---------------------------------------------------------
# RODS
# ---------------------------------------------------------
def find_rod(key: str):
    return rods_data.get(key.lower().strip())

@bot.tree.command(name="rod", description="Get info about a Fisch fishing rod.")
@app_commands.describe(name="Name of the rod (case-insensitive)")
async def rod(interaction: discord.Interaction, name: str):
    entry = find_rod(name)
    if not entry:
        await interaction.response.send_message(
            f"❌ Could not find a rod named **{name}**.", ephemeral=True
        )
        return

    embed = discord.Embed(
        title=entry.get("name", name),
        url=entry.get("url"),
        color=discord.Color.green()
    )

    for key, label in [
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
        if key in entry:
            val = entry[key]
            if isinstance(val, list):
                val = "\n".join(f"• {v}" for v in val)
            embed.add_field(name=label, value=val, inline=False)

    await interaction.response.send_message(embed=embed)

@rod.autocomplete("name")
async def rod_autocomplete(interaction, current: str):
    lower = current.lower()
    return [
        app_commands.Choice(name=data.get("name", key), value=key)
        for key, data in rods_data.items()
        if lower in key.lower() or lower in data.get("name", "").lower()
    ][:25]

# ---------------------------------------------------------
# ENCHANTS
# ---------------------------------------------------------
@bot.tree.command(name="enchants", description="Get info about a Fisch enchantment.")
@app_commands.describe(name="Name of the enchantment")
async def enchants(interaction: discord.Interaction, name: str):
    entry = enchants_data.get(name.lower().strip())
    if not entry:
        await interaction.response.send_message(
            f"❌ Could not find an enchant named **{name}**.", ephemeral=True
        )
        return

    embed = discord.Embed(
        title=entry.get("name", name.title()),
        color=discord.Color.blue()
    )

    for key, label in [
        ("description", "Description"),
        ("max_level", "Max Level"),
        ("applies_to", "Applies To"),
        ("conflicts", "Conflicts With"),
        ("rarity", "Rarity"),
        ("category", "Category")
    ]:
        if key in entry:
            val = entry[key]
            if isinstance(val, list):
                val = "\n".join(f"• {v}" for v in val)
            embed.add_field(name=label, value=val, inline=False)

    await interaction.response.send_message(embed=embed)

@enchants.autocomplete("name")
async def enchants_autocomplete(interaction, current: str):
    lower = current.lower()
    return [
        app_commands.Choice(name=entry.get("name", key), value=key)
        for key, entry in enchants_data.items()
        if lower in key.lower() or lower in entry.get("name", "").lower()
    ][:25]

# ---------------------------------------------------------
# ENCHANT CATEGORY
# ---------------------------------------------------------
@bot.tree.command(name="enchantcategory", description="Look up an enchantment category.")
@app_commands.describe(category="Name of the enchantment category")
async def enchantcategory(interaction: discord.Interaction, category: str):
    entry = categories_data.get(category.lower().strip())
    if not entry:
        await interaction.response.send_message(
            f"❌ No category found named **{category}**.", ephemeral=True
        )
        return

    embed = discord.Embed(
        title=entry.get("name", category.title()),
        color=discord.Color.orange()
    )

    if "enchants" in entry:
        ench_list = "\n".join(f"• {e}" for e in entry["enchants"])
        embed.add_field(name="Enchantments", value=ench_list, inline=False)

    await interaction.response.send_message(embed=embed)

@enchantcategory.autocomplete("category")
async def enchantcategory_autocomplete(interaction, current: str):
    lower = current.lower()
    return [
        app_commands.Choice(name=entry.get("name", key), value=key)
        for key, entry in categories_data.items()
        if lower in key.lower() or lower in entry.get("name", "").lower()
    ][:25]

# ---------------------------------------------------------
# READY EVENT
# ---------------------------------------------------------
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
