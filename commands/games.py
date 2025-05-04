import logging
import random

# Game data
jokes = [
    "Why did the alien visit Earth? To abduct some new friends!",
    "What do aliens use to communicate? Their *cell-fones*!",
    "Why don't aliens play chess? They're afraid of any move with a bishop!",
    "How do aliens throw parties? They beam up the guests!",
    "What's an alien's favorite sport? Spaceball!"
]

eight_ball_responses = [
    "It is certain.",
    "Without a doubt.",
    "Yes, definitely.",
    "You may rely on it.",
    "As I see it, yes.",
    "Most likely.",
    "Outlook good.",
    "Yes.",
    "Signs point to yes.",
    "Reply hazy, try again.",
    "Ask again later.",
    "Better not tell you now.",
    "Cannot predict now.",
    "Concentrate and ask again.",
    "Don't count on it.",
    "My reply is no.",
    "My sources say no.",
    "Outlook not so good.",
    "Very doubtful.",
    "No way, Jose!"
]

def setup(client, cfg):
    @client.command(name="joke")
    async def joke(ctx):
        try:
            joke = random.choice(jokes)
            logging.info(f"Sending joke: {joke}")
            await ctx.reply(joke)
        except Exception as e:
            logging.error(f"Error sending joke response: {e}")

    @client.command(name="coinflip")
    async def coinflip(ctx):
        result = random.choice(["Heads", "Tails"])
        try:
            logging.info(f"Sending coinflip result: {result}")
            await ctx.reply(f"The coin lands on **{result}**!")
        except Exception as e:
            logging.error(f"Error sending coinflip response: {e}")

    @client.command(name="8ball")
    async def eight_ball(ctx, *, question=None):
        if not question:
            try:
                logging.info("User sent !8ball without a question")
                await ctx.reply("Please ask a question after !8ball, like `!8ball Will I win the lottery?`")
            except Exception as e:
                logging.error(f"Error sending 8ball error response: {e}")
            return
        try:
            response = random.choice(eight_ball_responses)
            logging.info(f"Sending 8ball response: {response}")
            await ctx.reply(f"🎱 {response}")
        except Exception as e:
            logging.error(f"Error sending 8ball response: {e}")