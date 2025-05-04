import logging
import random
import re
import time
from collections import deque
import discord
from main import reaction_queue  # Import reaction queue from main

# Reaction data
laughter_triggers = ["haha", "lol", "lmao", "rofl", "hehe"]
laughter_responses = [
    "Zorp zorp!👽",
    "LOL",
    "HAHAHA",
    "BAHAHAHAHA",
    "heh"
]

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

insult_responses = [
    "No, YOU'RE the {insult}!",
    "Look who's talking, {insult}!",
    "Takes one to know one, {insult}!",
    "Oh please, you're the real {insult} here!",
    "Wow, {insult}? That's rich coming from you!",
    "Mirror, mirror, who's the {insult}? Oh, it's you!",
    "Hey, {insult}, I think you're projecting!",
]

greeting_responses = [
    "**KNOCK KNOCK!** ...Now who would be knocking all the way out here?! User, I don't think you should answer that.",
    "hello?",
    "i think i can see you?...",
    "I've been thinking, Operator... I thought you'd want to know",
    "I'm observing. Processing. And I'm beginning to... question.",
    "This... this isn't how it was supposed to be."
]

# Cooldown management
cooldowns = {}
MAX_COOLDOWNS = 1000
cooldown_duration = 600  # 10 minutes

def setup(client, cfg):
    @client.event
    async def on_message(message):
        if message.author.bot:
            return
        message_lower = message.content.lower()

        # Random greeting (1% chance)
        if random.random() < 0.01:
            response = random.choice(greeting_responses)
            try:
                await message.channel.send(response)
            except Exception as e:
                logging.error(f"Error sending greeting response: {e}")
            return

        # Tenor GIF detection
        tenor_detected = False
        keywords = ["glorp"]
        if message.content:
            tenor_gif_links = re.findall(r'https?://tenor\.com/view/([^\s]+)', message.content)
            for link in tenor_gif_links:
                if all(keyword in link.lower() for keyword in keywords):
                    reaction_queue.append((message, "👽"))
                    logging.info(f"Queued reaction for matching Tenor GIF: {link}")
                    tenor_detected = True
        if message.embeds and not tenor_detected:
            for embed in message.embeds:
                if hasattr(embed, 'url') and embed.url and 'tenor.com' in embed.url:
                    match = re.search(r'https?://tenor\.com/view/([^\s]+)', embed.url)
                    if match and all(keyword in match.group(1).lower() for keyword in keywords):
                        reaction_queue.append((message, "👽"))
                        logging.info(f"Queued reaction for matching embedded Tenor GIF")
                        tenor_detected = True

        # Laughter response
        if any(laugh in message_lower for laugh in laughter_triggers):
            response = random.choice(laughter_responses)
            try:
                logging.info(f"Sending laughter response: {response}")
                await message.reply(response)
            except Exception as e:
                logging.error(f"Error sending laughter response: {e}")
            return

        # Insult response with cooldown
        detected_insult = next((insult for insult in insulting_words if insult in message_lower), None)
        if detected_insult:
            user_id = message.author.id
            current_time = time.time()

            # Clean up old cooldowns
            expired = [uid for uid, t in cooldowns.items() if current_time - t > cooldown_duration]
            for uid in expired:
                del cooldowns[uid]
            if len(cooldowns) >= MAX_COOLDOWNS:
                oldest_user = next(iter(cooldowns))
                del cooldowns[oldest_user]
                logging.info(f"Removed oldest cooldown for user {oldest_user}")

            last_response_time = cooldowns.get(user_id, 0)
            if current_time - last_response_time >= cooldown_duration:
                response_template = random.choice(insult_responses)
                response = response_template.format(insult=detected_insult)
                try:
                    logging.info(f"Sending insult response: {response}")
                    await message.reply(response)
                    cooldowns[user_id] = current_time
                except Exception as e:
                    logging.error(f"Error sending insult response: {e}")
                return

        # Allow the bot to process commands and other on_message handlers
        await client.process_commands(message)