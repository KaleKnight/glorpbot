import asyncio
import logging
import time
from discord.ext import commands
from openai import AsyncOpenAI

# Conversation history
conversation_history = {}
MAX_HISTORY = 20

class AIChat(commands.Cog):
    def __init__(self, client, cfg):
        self.client = client
        self.cfg = cfg
        self.openai_client = self._setup_openai_client()
        self.ai_chat_lock = asyncio.Lock()

    def _setup_openai_client(self):
        provider_slash_model = self.cfg["model"]
        provider, model = provider_slash_model.split("/", 1)
        base_url = self.cfg["providers"][provider]["base_url"]
        api_key = self.cfg["providers"][provider].get("api_key", "sk-no-key-required")
        return AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def handle_ai_chat(self, message, channel_id, user_message, past_history):
        if self.ai_chat_lock.locked():
            try:
                logging.info(f"Ignoring AI chat request from {message.author} due to active AI chat.")
                await message.reply("Sorry, I'm busy at the moment! Try again soon.")
            except Exception as e:
                logging.error(f"Error sending busy message: {e}")
            return

        async with self.ai_chat_lock:
            messages = [{"role": "system", "content": self.cfg.get("system_prompt", "You are a helpful assistant.")}]
            for role, content in past_history:
                messages.append({"role": role, "content": content})
            messages.append({"role": "user", "content": user_message})

            max_retries = 5
            base_delay = 1.0

            for attempt in range(max_retries):
                try:
                    async with message.channel.typing():
                        response = await asyncio.wait_for(
                            self.openai_client.chat.completions.create(
                                model=self.cfg["model"].split("/", 1)[1],
                                messages=messages,
                                stream=False
                            ),
                            timeout=120.0
                        )
                        bot_reply = response.choices[0].message.content.strip()
                        await message.channel.send(bot_reply)
                        past_history.append(("user", user_message))
                        past_history.append(("assistant", bot_reply))
                        if len(past_history) > MAX_HISTORY:
                            past_history = past_history[-MAX_HISTORY:]
                        conversation_history[channel_id] = past_history
                        return
                except asyncio.TimeoutError:
                    logging.warning(f"OpenAI request timed out after 120s (attempt {attempt + 1}/{max_retries}).")
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logging.info(f"Retrying after {delay}s...")
                        await asyncio.sleep(delay)
                        continue
                    logging.error("Max retries reached for OpenAI request.")
                    await message.reply("⚠️ AI response timed out after multiple attempts. Please try again later.")
                except Exception as e:
                    logging.error(f"Error generating AI response: {e}")
                    try:
                        await message.reply("⚠️ AI timed out :(")
                    except Exception as e:
                        logging.error(f"Error sending AI error message: {e}")
                    break

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if self.client.user in message.mentions:
            channel_id = message.channel.id
            user_message = message.content.replace(self.client.user.mention, "").strip()
            past_history = conversation_history.get(channel_id, [])
            await self.handle_ai_chat(message, channel_id, user_message, past_history)

def setup(client):
    client.add_cog(AIChat(client, client.cfg))