from keep_alive import keep_alive
import discord
from discord.ext import commands, tasks
import asyncio
import random
import datetime
import os
from dotenv import load_dotenv

# Load token from .env file
load_dotenv()

# Set up Intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

# Create the bot
bot = commands.Bot(command_prefix=',', intents=intents)
bot.remove_command('help')  # Remove default help command

# Tracking voice channel join times
voice_times = {}

# Tickets storage
user_tickets = {}

# Event: when bot is ready
@bot.event
async def on_ready():
    print(f'Bot is ready as {bot.user}')
    reset_leaderboard.start()

# Event: when someone joins or leaves VC
@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and not before.channel:
        voice_times[member.id] = datetime.datetime.now()
        print(f"{member.name} joined VC")
    elif before.channel and not after.channel:
        if member.id in voice_times:
            joined_at = voice_times.pop(member.id)
            time_spent = (datetime.datetime.now() - joined_at).total_seconds()
            tickets_earned = int(time_spent // 600)  # 10 minutes = 1 ticket
            if tickets_earned > 0:
                if member.id not in user_tickets:
                    user_tickets[member.id] = 0
                user_tickets[member.id] += tickets_earned
                print(f"Allotted {tickets_earned} ticket(s) to {member.name}")
            else:
                print(f"No tickets allotted to {member.name} (not enough time)")
        print(f"{member.name} left VC")

# Command: check your tickets
@bot.command(name="tickets")
async def tickets(ctx):
    current_tickets = user_tickets.get(ctx.author.id, 0)
    embed = discord.Embed(
        title="🎟️ Your Tickets",
        description=f"You have {current_tickets} raffle tickets!",
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Requested by {ctx.author.name}")
    await ctx.send(embed=embed)

# Command: leaderboard
@bot.command(name="leaderboard")
async def leaderboard(ctx):
    if not user_tickets:
        await ctx.send("No one has earned any tickets yet!")
        return

    sorted_tickets = sorted(user_tickets.items(), key=lambda x: x[1], reverse=True)
    embed = discord.Embed(title="🏆 Weekly Leaderboard", color=discord.Color.gold())

    for i, (user_id, ticket_count) in enumerate(sorted_tickets, start=1):
        user = await bot.fetch_user(user_id)
        embed.add_field(name=f"{i}. {user.name}", value=f"{ticket_count} tickets", inline=False)

    await ctx.send(embed=embed)

# Command: draw winners
@bot.command(name="draw")
@commands.has_permissions(administrator=True)
async def draw(ctx, number_of_winners: int = 1):
    all_tickets = []
    for user_id, ticket_count in user_tickets.items():
        all_tickets.extend([user_id] * ticket_count)

    if not all_tickets:
        await ctx.send("No tickets have been earned yet!")
        return

    winners = set()
    while len(winners) < number_of_winners and all_tickets:
        winners.add(random.choice(all_tickets))

    if winners:
        winner_mentions = ", ".join(f"<@{winner_id}>" for winner_id in winners)
        embed = discord.Embed(
            title="🎉 Winners!",
            description=f"Congratulations to: {winner_mentions}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send("Not enough participants to draw winners.")

# Command: custom help menu
@bot.command(name='help')
async def help_command(ctx):
    embed = discord.Embed(title="📜 RaffleBot Commands", color=discord.Color.purple())
    embed.add_field(name=",help", value="Show this help menu", inline=False)
    embed.add_field(name=",tickets", value="Check your raffle tickets", inline=False)
    embed.add_field(name=",leaderboard", value="Show the leaderboard", inline=False)
    embed.add_field(name=",draw [number]", value="Admin only: Draw random winners", inline=False)
    await ctx.send(embed=embed)

# Handle unknown commands nicely
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❓ Unknown command. Try `,help` to see all commands.")
    else:
        raise error  # Let other errors raise normally

# Task: reset leaderboard every Sunday at 23:59
@tasks.loop(minutes=1)
async def reset_leaderboard():
    now = datetime.datetime.now()
    if now.weekday() == 6 and now.hour == 23 and now.minute == 59:
        user_tickets.clear()
        print("Leaderboard reset automatically.")
        channel_id = 1365343658076803194  # <<<< Replace with your channel ID
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send("Leaderboard has been reset for the new week!")

# Run the bot
keep_alive()
bot.run(os.getenv("TOKEN"))