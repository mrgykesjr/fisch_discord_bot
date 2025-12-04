#!/usr/bin/env python3
import json
import discord
from discord.ext import commands
from discord import app_commands
import os
import urllib.parse

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable not found.")

GUILD_ID = None

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


# ---------------------------------------------------------
# JSON LOADER
# ---------------------------------------------------------
def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# Load JSON files
bestiary_data = load_json("data/bestiary.json")
rods_data = load_json("data/rods.json")
enchants_data = load_json("data/enchants.json")
categories_data = load_json("data/enchant_categories.json")


# ---------------------------------------------------------
# NORMALIZATION UTILITIES
# ---------------------------------------------------------
def normalize(s: str) -> str:
    """Normalize for fuzzy matching."""
    if not isinstance(s, str):
        return ""
    s = urllib.parse.unquote(s)
    s = s.replace("’", "'")
    s = s.replace("`", "'")
    return s.lower().strip()


def match_entry(name: str, dataset: dict, name_field="name"):
    """Fuzzy match against both JSON keys and their 'name' field."""
    target = normalize(name)

    # direct key match
    for key, data in dataset.items():
        if normalize(key) == target:
            return data

    # direct name-field match
    for key, data in dataset.items():
        disp = data.get(name_field, "")
        if normalize(disp) == target:
            return data

    # single partial match fallback
    candidates = []
    for key, data in dataset.items():
        if target in normalize(key) or target in normalize(data.get(name_field, "")):
            candidates.append(data)

    if len(candidates) == 1:
        return candidates[0]

    return None


# Clean field label for embed titles
def clean_label(label: str) -> str:
    label = label.replace("_", " ")
    label = label.title()
    return label


# ---------------------------------------------------------
# BESTIARY
# ---------------------------------------------------------
@bot.tree.command(name="bestiary", description="Get info about a Fisch fish.")
@app_commands.describe(name="Name of the fish")
async def bestiary(interaction, name: str):

    entry = match_entry(name, bestiary_data)
    if not entry:
        await interaction.response.send_message(
            f"❌ Could not find a fish named **{name}**.",
            ephemeral=True
        )
        return

    wiki_name = entry.get("name", name).replace(" ", "_")
    embed = discord.Embed(
        title=entry.get("name", name.title()),
        url=f"https://fischipedia.org/wiki/{wiki_name}",
        color=discord.Color.teal()
    )

    # static fields
    for key, label in [
        ("rarity", "Rarity"),
        ("location", "Location"),
        ("resilience", "Resilience"),
        ("progress_speed", "Progress Speed"),
        ("progress speed", "Progress Speed"),
        ("bait", "Preferred Bait")
    ]:
        if entry.get(key):
            embed.add_field(name=label, value=entry[key], inline=False)

    # conditions
    conds = []
    for key in ("time", "weather", "season"):
        if entry.get(key):
            conds.append(f"**{key.title()}:** {entry[key]}")
    if conds:
        embed.add_field(name="Conditions", value="\n".join(conds), inline=False)

    # weights
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

    # value
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
async def bestiary_autocomplete(interaction, current):
    target = normalize(current)
    results = []
    for key, data in bestiary_data.items():
        disp = data.get("name", key)
        if target in normalize(key) or target in normalize(disp):
            results.append(app_commands.Choice(name=disp, value=key))
    return results[:25]


# ---------------------------------------------------------
# ROD — FULL DYNAMIC DISPLAY
# ---------------------------------------------------------
@bot.tree.command(name="rod", description="Get info about a Fisch fishing rod.")
@app_commands.describe(name="Name of the rod")
async def rod(interaction, name: str):

    entry = match_entry(name, rods_data)
    if not entry:
        await interaction.response.send_message(
            f"❌ Could not find a rod named **{name}**.",
            ephemeral=True
        )
        return

    title = entry.get("name", name.title())
    embed = discord.Embed(
        title=title,
        url=entry.get("url"),  # keep clickable title
        color=discord.Color.green()
    )

    # dynamic: iterate through JSON fields in the EXACT order they appear
    for key, value in entry.items():

        # skip internal display name
        if key == "name":
            continue

        # *** THIS IS THE ONLY CHANGE YOU ASKED FOR ***
        if key == "url":  
            continue  # do not add as its own field

        label = clean_label(key)

        if isinstance(value, list):
            formatted = "\n".join(f"• {v}" for v in value)
            embed.add_field(name=label, value=formatted, inline=False)
        else:
            embed.add_field(name=label, value=str(value), inline=False)

    await interaction.response.send_message(embed=embed)


@rod.autocomplete("name")
async def rod_autocomplete(interaction, current):
    target = normalize(current)
    results = []
    for key, data in rods_data.items():
        disp = data.get("name", key)
        if target in normalize(key) or target in normalize(disp):
            results.append(app_commands.Choice(name=disp, value=key))
    return results[:25]


# ---------------------------------------------------------
# ENCHANT
# ---------------------------------------------------------
@bot.tree.command(name="enchant", description="Get info about a Fisch enchantment.")
@app_commands.describe(name="Name of the enchantment")
async def enchant(interaction, name: str):

    entry = match_entry(name, enchants_data)
    if not entry:
        await interaction.response.send_message(
            f"❌ Could not find an enchant named **{name}**.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=entry.get("name", name.title()),
        color=discord.Color.blue()
    )

    if entry.get("category"):
        embed.add_field(name="Category", value=entry["category"].title(), inline=False)

    if entry.get("effect"):
        effects = "\n".join(f"• {line}" for line in entry["effect"])
        embed.add_field(name="Effect", value=effects, inline=False)

    if entry.get("tips"):
        tips = "\n".join(f"• {line}" for line in entry["tips"])
        embed.add_field(name="Tips", value=tips, inline=False)

    await interaction.response.send_message(embed=embed)


@enchant.autocomplete("name")
async def enchant_autocomplete(interaction, current):
    target = normalize(current)
    res = []
    for key, data in enchants_data.items():
        disp = data.get("name", key)
        if target in normalize(key) or target in normalize(disp):
            res.append(app_commands.Choice(name=disp, value=key))
    return res[:25]


# ---------------------------------------------------------
# ENCHANT CATEGORY
# ---------------------------------------------------------
@bot.tree.command(name="enchantcategory", description="Look up an enchantment category.")
@app_commands.describe(category="The category name")
async def enchantcategory(interaction, category: str):

    entry = match_entry(category, categories_data)
    if not entry:
        await interaction.response.send_message(
            f"❌ No category found named **{category}**.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=entry.get("name", category.title()),
        color=discord.Color.orange()
    )

    if entry.get("relic"):
        embed.add_field(name="Relic Type", value=entry["relic"], inline=False)

    if entry.get("enchants"):
        ench_list = "\n".join(f"• {e}" for e in entry["enchants"])
        embed.add_field(name="Enchantments", value=ench_list, inline=False)

    await interaction.response.send_message(embed=embed)


@enchantcategory.autocomplete("category")
async def enchantcategory_autocomplete(interaction, current):
    target = normalize(current)
    res = []
    for key, data in categories_data.items():
        disp = data.get("name", key)
        if target in normalize(key) or target in normalize(disp):
            res.append(app_commands.Choice(name=disp, value=key))
    return res[:25]


# ---------------------------------------------------------
# READY EVENT
# ---------------------------------------------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            commands_synced = await bot.tree.sync(guild=guild)
            print(f"✅ Synced {len(commands_synced)} commands to guild {GUILD_ID}.")
        else:
            commands_synced = await bot.tree.sync()
            print(f"✅ Synced {len(commands_synced)} global commands.")
    except Exception as e:
        print("Error syncing commands:", e)


bot.run(TOKEN)
