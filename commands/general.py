import logging
import discord
import asyncio

# Dictionary to track active vote kicks: {message_id: {"target_user": user, "votes": set of user IDs, "message": message}}
active_votes = {}

def setup(client, cfg):
    @client.command(name="ping")
    async def ping(ctx):
        try:
            logging.info("Sending ping response")
            await ctx.reply("glorp is alive and watching...")
        except Exception as e:
            logging.error(f"Error sending ping response: {e}")

    @client.command(name="help")
    async def help_command(ctx):
        help_text = (
            "**Available Commands:**\n"
            "!ping - Check if glorp is alive.\n"
            "!votekick <@user> - Start a vote to kick a user (needs 4 votes).\n"
            "!tldr - Summarize the last 15 messages in this channel.\n"
            "!8ball <question> - Ask the magic 8-ball a question.\n"
            "!coinflip - Flip a coin.\n"
            "!joke - Hear an alien joke.\n"
            "@glorp <message> - Chat with glorp.\n"
        )
        try:
            logging.info("Sending help response")
            await ctx.reply(help_text)
        except Exception as e:
            logging.error(f"Error sending help response: {e}")

    @client.command(name="votekick")
    async def votekick(ctx):
        # Check if a user is mentioned
        if not ctx.message.mentions:
            await ctx.reply("Please mention a user to vote kick! Usage: `!votekick @user`")
            return

        target_user = ctx.message.mentions[0]  # Get the first mentioned user

        # Prevent the bot from targeting itself
        if target_user == client.user:
            await ctx.reply("You can't vote to kick me! 👽")
            return

        # Send the initial vote kick message with a ✅ reaction
        vote_message = await ctx.send(f"{target_user.mention} needs 4 votes to get kicked!")
        await vote_message.add_reaction("✅")

        # Track the vote in active_votes
        active_votes[vote_message.id] = {
            "target_user": target_user,
            "votes": set(),  # Track user IDs who voted
            "message": vote_message
        }

        # Wait for 60 seconds, then check if the vote succeeded
        await asyncio.sleep(60)

        # Check the result
        vote_data = active_votes.get(vote_message.id)
        if vote_data:
            vote_count = len(vote_data["votes"])
            if vote_count >= 4:
                await ctx.send(f"{target_user.mention} is too powerful to be kicked! 💪")
            else:
                await ctx.send(f"Vote kick failed: not enough votes to kick {target_user.mention}! ({vote_count}/4 votes)")
            # Clean up
            del active_votes[vote_message.id]

    @client.command(name="tldr")
    async def tldr(ctx):
        try:
            # Fetch the last 15 messages in the channel (excluding the command message itself)
            messages = []
            async for message in ctx.channel.history(limit=16):  # 16 to account for the command message
                if message.id != ctx.message.id:  # Skip the !tldr command message
                    messages.append(message)
            messages = messages[:15]  # Ensure we only take the last 15 messages

            if not messages:
                await ctx.reply("There are no messages to summarize in this channel!")
                return

            # Format the messages into a string
            formatted_messages = []
            for msg in reversed(messages):  # Reverse to show oldest to newest
                content = msg.content if msg.content else "[No text content]"
                formatted_messages.append(f"{msg.author.name}: {content}")
            
            message_history = "\n".join(formatted_messages)

            # Create a prompt for the AI to summarize the messages
            prompt = (
                "Please provide a concise summary (TLDR) of the following conversation. "
                "Focus on the main topics discussed, ignoring minor details or off-topic comments:\n\n"
                f"{message_history}"
            )

            # Get the AIChat cog to generate the summary
            ai_chat_cog = client.get_cog("AIChat")
            if not ai_chat_cog:
                await ctx.reply("⚠ AI broken. Idk ask Jake.")
                return

            # Use the AIChat cog's handle_ai_chat method to generate the summary
            channel_id = ctx.channel.id
            past_history = []  # We don't need past history for a TLDR summary
            async with ctx.typing():
                await ai_chat_cog.handle_ai_chat(ctx.message, channel_id, prompt, past_history)

        except Exception as e:
            logging.error(f"Error in tldr command: {e}")
            await ctx.reply(" An error occurred womp womp.")

    @client.event
    async def on_reaction_add(reaction, user):
        # Check if the reaction is part of an active vote kick
        vote_data = active_votes.get(reaction.message.id)
        if not vote_data:
            return

        # Ensure the reaction is ✅, the user is not the bot, and not the target user
        if str(reaction.emoji) != "✅":
            return
        if user == client.user or user == vote_data["target_user"]:
            return

        # Add the user to the vote count (using a set to avoid duplicates)
        vote_data["votes"].add(user.id)