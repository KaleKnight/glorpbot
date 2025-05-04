import asyncio
import logging
import random
import discord
from discord.ext import commands
from discord import HTTPException
from collections import deque
import os
import time
from utils.config import get_config

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)

# Load config
try:
    cfg = get_config()
except Exception as e:
    logging.error("Failed to load configuration. Exiting.")
    exit(1)

# Log bot invite URL
if client_id := cfg.get("client_id"):
    logging.info(
        f"\n\nBOT INVITE URL:\nhttps://discord.com/api/oauth2/authorize?client_id={client_id}&permissions=412317273088&scope=bot\n"
    )
else:
    logging.warning("client_id not found in config. Bot invite URL unavailable.")

# Setup Discord client with commands.Bot
intents = discord.Intents.default()
intents.message_content = True

status_rotation = [
    discord.Game("Glorping around"),
    discord.Activity(type=discord.ActivityType.listening, name="Sabrina Carpenter"),
    discord.Activity(type=discord.ActivityType.watching, name="Stranger Things"),
    discord.Activity(type=discord.ActivityType.playing, name="Fortnite with Elon Musk"),
    discord.Activity(type=discord.ActivityType.listening, name="Dance Gavin Dance"),
]

discord_client = commands.Bot(
    command_prefix="!",
    intents=intents,
    activity=random.choice(status_rotation),
    max_messages=5000,
    heartbeat_timeout=120.0
)
discord_client.remove_command("help")  # Remove the default help command
discord_client.cfg = cfg  # Attach cfg to the bot instance

# Reaction queue for processing reactions
reaction_queue = deque()
MAX_CONCURRENT_REACTIONS = 5
reaction_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REACTIONS)

# Background task for processing reaction queue
async def process_reaction_queue():
    while True:
        if not reaction_queue:
            await asyncio.sleep(0.1)
            continue
        message, emoji = reaction_queue.popleft()
        async with reaction_semaphore:
            try:
                await message.add_reaction(emoji)
                logging.info(f"Reacted with {emoji} to message ID {message.id}")
                await asyncio.sleep(0.5)
            except HTTPException as e:
                if e.code == 429:
                    retry_after = e.retry_after or 1.0
                    logging.warning(f"Rate limit hit, retrying after {retry_after}s")
                    reaction_queue.appendleft((message, emoji))
                    await asyncio.sleep(retry_after)
                else:
                    logging.error(f"Error reacting to message: {e}")
            except Exception as e:
                logging.error(f"Unexpected error reacting to message: {e}")

# Background task for rotating status
async def rotate_status():
    await discord_client.wait_until_ready()
    while not discord_client.is_closed():
        try:
            new_status = random.choice(status_rotation)
            await discord_client.change_presence(activity=new_status)
            logging.info(f"Changed status to: {new_status}")
        except Exception as e:
            logging.error(f"Error changing status: {e}")
        await asyncio.sleep(1800)

# Background task for cleaning up conversation history
async def cleanup_conversation_history():
    from cogs.ai_chat import conversation_history, MAX_HISTORY
    while True:
        try:
            current_time = time.time()
            expired_channels = []
            for channel_id, history in conversation_history.items():
                if len(history) > MAX_HISTORY:
                    conversation_history[channel_id] = history[-MAX_HISTORY:]
                last_message_time = history[-1][1]["timestamp"] if history else 0
                if current_time - last_message_time > 3600:
                    expired_channels.append(channel_id)
            for channel_id in expired_channels:
                del conversation_history[channel_id]
                logging.info(f"Cleaned up conversation history for channel {channel_id}")
        except Exception as e:
            logging.error(f"Error cleaning up conversation history: {e}")
        await asyncio.sleep(3600)

# Load command files
def load_commands():
    for filename in os.listdir("./commands"):
        if filename.endswith(".py"):
            module_name = filename[:-3]
            logging.info(f"Loading command module: {module_name}")
            module = __import__(f"commands.{module_name}", fromlist=["setup"])
            if hasattr(module, 'setup'):
                module.setup(discord_client, cfg)
            else:
                logging.warning(f"Module {module_name} has no setup function, skipping.")

# Load cogs
def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            module_name = filename[:-3]
            logging.info(f"Loading cog: {module_name}")
            discord_client.load_extension(f"cogs.{module_name}")

@discord_client.event
async def on_connect():
    logging.info("Bot connected to Discord gateway.")

@discord_client.event
async def on_disconnect():
    logging.warning("Bot disconnected from Discord gateway. Attempting to reconnect...")

@discord_client.event
async def on_ready():
    logging.info(f'Logged in as {discord_client.user} (ID: {discord_client.user.id})')
    logging.info('------')
    await discord_client.change_presence(activity=random.choice(status_rotation))
    load_commands()
    load_cogs()
    asyncio.create_task(rotate_status())
    asyncio.create_task(process_reaction_queue())
    asyncio.create_task(cleanup_conversation_history())

@discord_client.event
async def on_resumed():
    logging.info('Connection resumed')

@discord_client.event
async def on_error(event, *args, **kwargs):
    logging.error(f'Unhandled error in {event}:', exc_info=True)

# Custom reconnection logic with backoff
async def reconnect_with_backoff():
    max_attempts = 5
    base_delay = 1.0
    for attempt in range(max_attempts):
        try:
            await discord_client.start(cfg["bot_token"])
            return
        except Exception as e:
            delay = base_delay * (2 ** attempt)
            logging.error(f"Reconnect attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
            await asyncio.sleep(delay)
    logging.error("Max reconnect attempts reached. Exiting.")
    exit(1)

# Start the bot
async def main():
    try:
        logging.info("Starting bot...")
        await reconnect_with_backoff()
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt. Shutting down...")
    except Exception as e:
        logging.error(f"Error starting bot: {e}")
    finally:
        if not discord_client.is_closed():
            await discord_client.close()
        logging.info("Bot has shut down.")

if __name__ == "__main__":
    asyncio.run(main())