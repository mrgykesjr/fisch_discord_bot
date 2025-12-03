#!/usr/bin/env python3
import json
import discord
from discord.ext import commands
from discord import app_commands
import os

# CONFIG — keep your token secret in real use
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable not found.")
GUILD_ID = None  # or your guild ID for quick sync

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Load JSON data
def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
        # except: pass
    except FileNotFoundError:
        return {}

try:
    enchants_data = load_json("data/enchants.json")
except Exception as e:
    print("ERROR loading enchants.json:", e)
    enchants_data = {}

try:
    categories_data = load_json("data/enchant_categories.json")
except Exception as e:
    print("WARNING: could not load enchant_categories.json:", e)
    categories_data = {}

try:
    bestiary_data = load_json("data/bestiary.json")
except Exception as e:
    print("WARNING: could not load bestiary.json:", e)
    bestiary_data = {}

def find_enchant(name: str):
    return enchants_data.get(name.lower().strip())

def find_category(key: str):
    return categories_data.get(key.lower().strip())

def find_fish(key: str):
    return bestiary_data.get(key.lower().strip())

# --- /enchant command ---
@bot.tree.command(name="enchant", description="Get info about a Fisch enchant.")
@app_commands.describe(name="Name of the enchant (e.g. 'Abyssal')")
async def enchant(interaction: discord.Interaction, name: str):
    entry = find_enchant(name)
    if not entry:
        await interaction.response.send_message(
            f"❌ Could not find an enchant named **{name}**.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"Enchant: {entry.get('name', name.title())}",
        color=discord.Color.blue()
    )
    embed.add_field(name="Category",
                    value=entry.get("category", "Unknown").title(),
                    inline=False)

    effect_list = entry.get("effect", [])
    if isinstance(effect_list, list) and effect_list:
        effects_str = "\n".join(f"• {e}" for e in effect_list)
    else:
        effects_str = entry.get("effect", "No effect listed.")
    embed.add_field(name="Effects", value=effects_str, inline=False)

    tips_list = entry.get("tips", [])
    if isinstance(tips_list, list) and tips_list:
        tips_str = "\n".join(f"• {t}" for t in tips_list)
    else:
        tips_str = "No tips available."
    embed.add_field(name="Tips", value=tips_str, inline=False)

    await interaction.response.send_message(embed=embed)

@enchant.autocomplete("name")
async def enchant_autocomplete(interaction: discord.Interaction, current: str):
    current_lower = current.lower()
    choices = []
    for key, data in enchants_data.items():
        display_name = data.get("name", key)
        if current_lower in key.lower() or current_lower in display_name.lower():
            choices.append(app_commands.Choice(name=display_name, value=key))
    return choices[:25]

# --- /enchantmentcategory command ---
@bot.tree.command(
    name="enchantmentcategory",
    description="Get the relic + list of enchantments for a category."
)
@app_commands.describe(category="Choose an enchantment category")
async def enchantmentcategory(interaction: discord.Interaction, category: str):
    entry = find_category(category)
    if not entry:
        await interaction.response.send_message(
            f"❌ Could not find an enchant category called **{category}**.",
            ephemeral=True
        )
        return

    name = entry.get("name", category.title())
    relic = entry.get("relic", "Unknown relic")
    description = entry.get("description", "")
    enchants = entry.get("enchants", [])

    embed = discord.Embed(
        title=f"Enchant Category: {name}",
        description=description or None,
        color=discord.Color.dark_gold()
    )
    embed.add_field(name="Relic Used", value=relic, inline=False)

    if enchants:
        enchants_text = "\n".join(f"• {e}" for e in enchants)
        embed.add_field(name="Enchantments", value=enchants_text, inline=False)
    else:
        embed.add_field(name="Enchantments", value="(none listed)", inline=False)

    await interaction.response.send_message(embed=embed)

@enchantmentcategory.autocomplete("category")
async def category_autocomplete(interaction: discord.Interaction, current: str):
    current_lower = current.lower()
    choices = []
    for key, data in categories_data.items():
        display_name = data.get("name", key)
        if current_lower in key.lower() or current_lower in display_name.lower():
            choices.append(app_commands.Choice(name=display_name, value=key))
    return choices[:25]

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

    # Build link to Fischipedia
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

    # Location & Resilience
    location = entry.get("location")
    if location:
        embed.add_field(name="Location", value=location, inline=False)

    resilience = entry.get("resilience")
    if resilience:
        embed.add_field(name="Resilience", value=resilience, inline=False)

    # Preferred Bait
    bait = entry.get("bait")
    if bait:
        embed.add_field(name="Preferred Bait", value=bait, inline=False)

    # Time / Weather / Season
    time_str = entry.get("time")
    weather_str = entry.get("weather")
    season_str = entry.get("season")
    cond_lines = []
    if time_str:
        cond_lines.append(f"**Time:** {time_str}")
    if weather_str:
        cond_lines.append(f"**Weather:** {weather_str}")
    if season_str:
        cond_lines.append(f"**Season:** {season_str}")
    if cond_lines:
        embed.add_field(
            name="Conditions",
            value="\n".join(cond_lines),
            inline=False
        )

    # Weight fields
    min_w = entry.get("min_weight") or entry.get("lowest_kg")
    avg_w = entry.get("avg_weight") or entry.get("average_kg")
    max_w = entry.get("max_weight") or entry.get("highest_kg")
    if min_w or avg_w or max_w:
        weight_lines = []
        if min_w:
            weight_lines.append(f"Min: {min_w} kg")
        if avg_w:
            weight_lines.append(f"Avg: {avg_w} kg")
        if max_w:
            weight_lines.append(f"Max: {max_w} kg")
        embed.add_field(
            name="Weight (kg, base)",
            value="\n".join(weight_lines),
            inline=False
        )

    # Value fields
    value_per_kg = entry.get("value_per_kg_base") or entry.get("C_kg")
    base_value_c = entry.get("base_value_c") or entry.get("average_C")
    value_lines = []
    if value_per_kg:
        value_lines.append(f"C$/kg (base): {value_per_kg}")
    if base_value_c:
        value_lines.append(f"Average C$ (base): {base_value_c}")
    if value_lines:
        embed.add_field(
            name="Value",
            value="\n".join(value_lines),
            inline=False
        )

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

# --- Bot ready & sync ---
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
