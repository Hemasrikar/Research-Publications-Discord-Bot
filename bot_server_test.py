import os
import discord
from discord.ext import tasks
from discord import app_commands
from dotenv import load_dotenv
import arxiv
import json

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Server ID
GUILD_ID = os.getenv("SERVER_ID")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

CONFIG_FILE = "channels.json"
posted = set()

# Load saved channels/topics
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
else:
    config = {}

# Slash command to set a channel and topic
@tree.command(
    name="setchannel",
    description="Subscribe this channel to arXiv papers",
    guild=discord.Object(id=GUILD_ID)  # guild command → appears instantly
)
@app_commands.describe(topic="Research topic (keywords)")
async def setchannel(interaction: discord.Interaction, topic: str):
    guild_id = str(interaction.guild_id)
    channel_id = str(interaction.channel_id)
    config[guild_id] = {"channel_id": channel_id, "topic": topic}

    # Save to file
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    await interaction.response.send_message(
        f" This channel is now subscribed to **{topic}** papers.", ephemeral=True
    )

# Task to check arXiv periodically
@tasks.loop(hours=6)
async def check_arxiv():
    for guild_id, data in config.items():
        channel = client.get_channel(int(data["channel_id"]))
        if not channel:
            continue

        search = arxiv.Search(
            query=data["topic"],
            max_results=3,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )

        for paper in search.results():
            if paper.entry_id in posted:
                continue
            posted.add(paper.entry_id)
            message = (
                f" TITLE: **{paper.title}**\n"
                f"AUTHORS: {', '.join(a.name for a in paper.authors)}\n"
                f"PUBLISHED DATE: {paper.published.date()}\n"
                f"LINK: {paper.pdf_url}"
            )
            await channel.send(message)

@client.event
async def on_ready():
    # Sync commands for your server (instant)
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f" Logged in as {client.user}")
    check_arxiv.start()

client.run(TOKEN)