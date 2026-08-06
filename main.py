import asyncio
import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # Required to read text responses

bot = commands.Bot(command_prefix=".", intents=intents)


@bot.event
async def on_ready():
  print(f"Logged in as {bot.user.name} ({bot.user.id})")
  print("Embed Bot is ready and online!")


@bot.command(name="embed")
@commands.has_permissions(manage_messages=True)
async def create_embed(ctx: commands.Context):
  # 1. Delete the initial .embed command message
  try:
    await ctx.message.delete()
  except Exception:
    pass

  # 2. Send prompt giving a 10-minute window
  prompt = await ctx.send(
      f"📝 {ctx.author.mention}, you have **10 minutes** to send the message for"
      " your embed below.\n*(Your response will be automatically deleted and"
      " turned into the embed)*"
  )

  # Check that the next message comes from the same user in the same channel
  def check(m: discord.Message):
    return m.author == ctx.author and m.channel == ctx.channel

  try:
    # 3. Wait up to 600 seconds (10 minutes) for user response
    user_msg = await bot.wait_for("message", check=check, timeout=600.0)

    # Store user content
    content = user_msg.content

    # 4. Delete user's message and the prompt message to clean the chat
    try:
      await user_msg.delete()
      await prompt.delete()
    except Exception:
      pass

    # 5. Create and send the final clean embed
    embed = discord.Embed(
        description=content,
        color=discord.Color.from_rgb(59, 130, 246),  # Clean modern blue
    )

    await ctx.send(embed=embed)

  except asyncio.TimeoutError:
    # Handle timeout if no message is sent within 10 minutes
    try:
      await prompt.edit(
          content=(
              "⏰ **Time expired!** Embed creation timed out after 10 minutes."
          ),
          delete_after=10,
      )
    except Exception:
      pass


@create_embed.error
async def embed_error(ctx: commands.Context, error):
  if isinstance(error, commands.MissingPermissions):
    await ctx.send(
        "❌ You need `Manage Messages` permissions to use `.embed`!",
        delete_after=5,
    )


bot.run(os.getenv("DISCORD_TOKEN"))
