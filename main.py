from keep_alive import keep_alive
import discord
from discord.ext import commands, tasks
import asyncio
import random
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix=',', intents=intents)
bot.remove_command('help')

voice_times = {}
user_tickets = {}
milestone_checkpoints = {5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 70, 80, 90, 100}  # milestones to celebrate

@bot.event
async def on_ready():
    print(f'Bot is ready as {bot.user}')
    reset_leaderboard.start()

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and not before.channel:
        voice_times[member.id] = datetime.datetime.now()
        print(f"{member.name} joined VC")
    elif before.channel and not after.channel:
        if member.id in voice_times:
            joined_at = voice_times.pop(member.id)
            time_spent = (datetime.datetime.now() - joined_at).total_seconds()
            tickets_earned = int(time_spent // 60)  # 1 minute = 1 ticket
            if tickets_earned > 0:
                if member.id not in user_tickets:
                    user_tickets[member.id] = 0
                previous_tickets = user_tickets[member.id]
                user_tickets[member.id] += tickets_earned
                print(f"Allotted {tickets_earned} ticket(s) to {member.name}")

                # Check milestones
                for milestone in milestone_checkpoints:
                    if previous_tickets < milestone <= user_tickets[member.id]:
                        await send_milestone_message(member, milestone)
            else:
                print(f"No tickets allotted to {member.name} (not enough time)")
        print(f"{member.name} left VC")

async def send_milestone_message(member, milestone):
    channel_id = 1320698170837303367  # <<<< Replace this with your announcement channel ID
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(f"🎉 Congrats {member.mention}! You've collected **{milestone}** tickets! Keep it up!")

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

@bot.command(name='help')
async def help_command(ctx):
    embed = discord.Embed(title="📜 RaffleBot Commands", color=discord.Color.purple())
    embed.add_field(name=",help", value="Show this help menu", inline=False)
    embed.add_field(name=",tickets", value="Check your raffle tickets", inline=False)
    embed.add_field(name=",leaderboard", value="Show the leaderboard", inline=False)
    embed.add_field(name=",draw [number]", value="Admin only: Draw random winners", inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❓ Unknown command. Try `,help` to see all commands.")
    else:
        raise error

@tasks.loop(minutes=1)
async def reset_leaderboard():
    now = datetime.datetime.now()
    if now.weekday() == 6 and now.hour == 23 and now.minute == 59:
        user_tickets.clear()
        print("Leaderboard reset automatically.")
        channel_id = 1365343658076803194  # <<<< Replace this too
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send("Leaderboard has been reset for the new week!")

keep_alive()
bot.run(os.getenv("TOKEN"))