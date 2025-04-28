import asyncio
import logging
import random
import re
import time
import discord
import yaml
from openai import AsyncOpenAI
from collections import deque
from discord import HTTPException

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)

# Load config with robust error handling
def get_config(filename="config.yaml"):
    try:
        with open(filename, "r") as file:
            config = yaml.safe_load(file)
            if config is None:
                logging.error(f"Config file {filename} is empty or invalid.")
                raise ValueError("Config file is empty or invalid")
            if not isinstance(config, dict):
                logging.error(f"Config file {filename} did not load as a dictionary.")
                raise ValueError("Config file did not load as a dictionary")
            return config
    except FileNotFoundError:
        logging.error(f"Config file {filename} not found.")
        raise
    except yaml.YAMLError as e:
        logging.error(f"Error parsing config file {filename}: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error loading config file {filename}: {e}")
        raise

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

# Setup discord client with enhanced configuration
intents = discord.Intents.default()
intents.message_content = True

# Status rotation list
status_rotation = [
    discord.Game("Glorping around"),
    discord.Activity(type=discord.ActivityType.listening, name="Sabrina Carpenter"),
    discord.Activity(type=discord.ActivityType.watching, name="Stranger Things"),
    discord.Activity(type=discord.ActivityType.playing, name="Fortnite with Elon Musk"),
    discord.Activity(type=discord.ActivityType.listening, name="Dance Gavin Dance"),
    discord.Activity(type=discord.ActivityType.watching, name="Game of Thrones"),
    discord.Activity(type=discord.ActivityType.playing, name="Stardew Valley"),
    discord.Activity(type=discord.ActivityType.listening, name="kendrick lamar"),
    discord.Activity(type=discord.ActivityType.watching, name="Severance"),
    discord.Activity(type=discord.ActivityType.playing, name="Minecraft"),
    discord.Activity(type=discord.ActivityType.listening, name="Peach Pit"),
    discord.Activity(type=discord.ActivityType.watching, name="You"),
    discord.Activity(type=discord.ActivityType.playing, name="Tetris"),
    discord.Activity(type=discord.ActivityType.listening, name="AC/DC"),
    discord.Activity(type=discord.ActivityType.watching, name="Invincible"),
    discord.Activity(type=discord.ActivityType.playing, name="Dead by Daylight"),
    discord.Activity(type=discord.ActivityType.listening, name="Gorillaz"),
    discord.Activity(type=discord.ActivityType.watching, name="Daredevil: Born Again"),
    discord.Activity(type=discord.ActivityType.playing, name="Grand Theft Auto VI"),
]

discord_client = discord.Client(
    intents=intents,
    activity=random.choice(status_rotation),
    max_messages=5000,  # Reduced to save memory
    heartbeat_timeout=120.0  # Increased to handle network hiccups
)

# Setup OpenAI client
provider_slash_model = cfg["model"]
provider, model = provider_slash_model.split("/", 1)
base_url = cfg["providers"][provider]["base_url"]
api_key = cfg["providers"][provider].get("api_key", "sk-no-key-required")
openai_client = AsyncOpenAI(base_url=base_url, api_key=api_key)

# Store conversation history per channel with size limit
conversation_history = {}
MAX_HISTORY = 20  # Limit to 20 messages per channel

# Dictionary for reminders
reminders = {}

# Dictionary for insult response cooldowns with size limit
cooldowns = {}
MAX_COOLDOWNS = 1000  # Maximum number of users in cooldowns

# List of bad words (example)
bad_words = [
    "badword1",
    "badword2",
    "badword3",
    "offensiveword1",
    "offensiveword2",
]

# List of insulting words
insulting_words = [
    "loser",
    "idiot",
    "stupid",
    "jerk",
    "moron",
    "fool",
    "dummy",
    "lame",
    "pathetic",
    "weirdo",
    "retard"
]

# Playful insult responses
insult_responses = [
    "No, YOU'RE the {insult}!",
    "Look who's talking, {insult}!",
    "Takes one to know one, {insult}!",
    "Oh please, you're the real {insult} here!",
    "Wow, {insult}? That's rich coming from you!",
    "Mirror, mirror, who's the {insult}? Oh, it's you!",
    "Hey, {insult}, I think you're projecting!",
]

# Alien-themed jokes
jokes = [
    "Why did the alien visit Earth? To abduct some new friends!",
    "What do aliens use to communicate? Their *cell-fones*!",
    "Why don't aliens play chess? They're afraid of any move with a bishop!",
    "How do aliens throw parties? They beam up the guests!",
    "What's an alien's favorite sport? Spaceball!"
]

# Random greeting responses
greeting_responses = [
    "**KNOCK KNOCK!** ...Now who would be knocking all the way out here?! User, I don't think you should answer that.",
    "hello?",
    "i think i can see you?...",
    "I've been thinking, Operator... I thought you'd want to know",
    "I'm observing. Processing. And I'm beginning to... question.",
    "This... this isn't how it was supposed to be."
]

# Laughter triggers and responses
laughter_triggers = ["haha", "lol", "lmao", "rofl", "hehe"]
laughter_responses = [
    "Zorp zorp!👽",
    "LOL",
    "HAHAHA",
    "BAHAHAHAHA",
    "heh"
]

# Queue for processing reactions to avoid rate limits
reaction_queue = deque()
MAX_CONCURRENT_REACTIONS = 5  # Limit concurrent reactions
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
                await asyncio.sleep(0.5)  # Small delay to avoid rate limits
            except HTTPException as e:
                if e.code == 429:  # Rate limit
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
        await asyncio.sleep(600)  # 10 minutes

# Background task to clean up conversation history
async def cleanup_conversation_history():
    while True:
        try:
            current_time = time.time()
            expired_channels = []
            for channel_id, history in conversation_history.items():
                if len(history) > MAX_HISTORY:
                    conversation_history[channel_id] = history[-MAX_HISTORY:]
                # Remove histories older than 1 hour
                last_message_time = history[-1][1]["timestamp"] if history else 0
                if current_time - last_message_time > 3600:
                    expired_channels.append(channel_id)
            for channel_id in expired_channels:
                del conversation_history[channel_id]
                logging.info(f"Cleaned up conversation history for channel {channel_id}")
        except Exception as e:
            logging.error(f"Error cleaning up conversation history: {e}")
        await asyncio.sleep(3600)  # Run every hour

# Background task for AI chat
async def handle_ai_chat(message, channel_id, user_message, past_history):
    messages = [{"role": "system", "content": cfg.get("system_prompt", "You are a helpful assistant.")}]
    for role, content in past_history:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    try:
        async with message.channel.typing():
            response = await asyncio.wait_for(
                openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=False
                ),
                timeout=8.0  # Reduced timeout to 8 seconds
            )
            bot_reply = response.choices[0].message.content.strip()
            await message.channel.send(bot_reply)
            past_history.append(("user", user_message))
            past_history.append(("assistant", bot_reply))
            if len(past_history) > MAX_HISTORY:
                past_history = past_history[-MAX_HISTORY:]
            conversation_history[channel_id] = past_history
    except asyncio.TimeoutError:
        logging.error("OpenAI request timed out after 8 seconds.")
        await message.reply("⚠️ AI response timed out. Please try again.")
    except Exception as e:
        logging.error(f"Error generating AI response: {e}")
        try:
            await message.reply("⚠️ Error generating a response. Please try again.")
        except Exception as e:
            logging.error(f"Error sending AI error message: {e}")

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
    asyncio.create_task(rotate_status())
    asyncio.create_task(process_reaction_queue())  # Start reaction queue processor
    asyncio.create_task(cleanup_conversation_history())  # Start history cleanup

@discord_client.event
async def on_resumed():
    logging.info('Connection resumed')

@discord_client.event
async def on_error(event, *args, **kwargs):
    logging.error(f'Unhandled error in {event}:', exc_info=True)

@discord_client.event
async def on_message(message):
    try:
        if message.author.bot:
            return

        # Improved Tenor GIF detection with queuing
        if message.content or message.embeds:
            tenor_detected = False
            if message.content:
                tenor_gif_links = re.findall(r'https?://tenor\.com/view/[^\s]+', message.content)
                for link in tenor_gif_links:
                    reaction_queue.append((message, "👽"))
                    logging.info(f"Queued reaction for Tenor GIF: {link}")
                    tenor_detected = True
            if message.embeds and not tenor_detected:
                for embed in message.embeds:
                    if hasattr(embed, 'url') and embed.url and 'tenor.com' in embed.url:
                        reaction_queue.append((message, "👽"))
                        logging.info(f"Queued reaction for embedded Tenor GIF")
                        tenor_detected = True

        # 1% chance random greeting response
        if random.random() < 0.01:
            response = random.choice(greeting_responses)
            await message.channel.send(response)
            return

        # Log the incoming message with more context
        logging.info(f"Message from {message.author} in {message.channel}: {message.content}")

        message_lower = message.content.lower()

        # Insult response with cooldown
        detected_insult = next((insult for insult in insulting_words if insult in message_lower), None)
        if detected_insult:
            user_id = message.author.id
            current_time = time.time()
            cooldown_duration = 600  # 10 minutes

            # Clean up old cooldowns and enforce size limit
            expired = [uid for uid, t in cooldowns.items() if current_time - t > cooldown_duration]
            for uid in expired:
                del cooldowns[uid]
            if len(cooldowns) >= MAX_COOLDOWNS:
                oldest_user = next(iter(cooldowns))
                del cooldowns[oldest_user]
                logging.info(f"Removed oldest cooldown for user {oldest_user} to enforce size limit")

            last_response_time = cooldowns.get(user_id, 0)
            time_since_last_response = current_time - last_response_time

            if time_since_last_response >= cooldown_duration:
                response_template = random.choice(insult_responses)
                response = response_template.format(insult=detected_insult)
                try:
                    logging.info(f"Sending insult response: {response}")
                    await message.reply(response)
                    cooldowns[user_id] = current_time
                except Exception as e:
                    logging.error(f"Error sending insult response: {e}")
                return

        # React to laughter
        if any(laugh in message_lower for laugh in laughter_triggers):
            response = random.choice(laughter_responses)
            try:
                logging.info(f"Sending laughter response: {response}")
                await message.reply(response)
            except Exception as e:
                logging.error(f"Error sending laughter response: {e}")
            return

        # Handle commands
        if message_lower == "!ping":
            try:
                logging.info("Sending ping response")
                await message.reply("glorp is alive and watching...")
            except Exception as e:
                logging.error(f"Error sending ping response: {e}")
            return

        if message_lower == "!help":
            help_text = (
                "**Available Commands:**\n"
                "!ping - Check if glorp is alive.\n"
                "!8ball - Ask a question.\n"
                "!coinflip - Flip a coin.\n"
                "!joke - Hear an alien joke.\n"
                "@glorp <message> - Chat with glorp.\n"
            )
            try:
                logging.info("Sending help response")
                await message.reply(help_text)
            except Exception as e:
                logging.error(f"Error sending help response: {e}")
            return

        if message_lower == "!joke":
            try:
                joke = random.choice(jokes)
                logging.info(f"Sending joke: {joke}")
                await message.reply(joke)
            except Exception as e:
                logging.error(f"Error sending joke response: {e}")
            return

        if message_lower == "!coinflip":
            result = random.choice(["Heads", "Tails"])
            try:
                logging.info(f"Sending coinflip result: {result}")
                await message.reply(f"The coin lands on **{result}**!")
            except Exception as e:
                logging.error(f"Error sending coinflip response: {e}")
            return

        # AI Chat Handling
        if discord_client.user in message.mentions:
            channel_id = message.channel.id
            user_message = message.content.replace(discord_client.user.mention, "").strip()
            past_history = conversation_history.get(channel_id, [])
            asyncio.create_task(handle_ai_chat(message, channel_id, user_message, past_history))

    except Exception as e:
        logging.error(f"Unexpected error in on_message handler: {e}")

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

# Start the bot with proper shutdown handling
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