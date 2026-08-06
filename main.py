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
        color=discord.Color.from_rgb(139, 92, 246),  # Clean modern purple
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



# NUKEE

@bot.command(name="nuke")
@commands.has_permissions(manage_channels=True)
async def nuke_channel(ctx: commands.Context):
    # Get the channel's original position and category so the new one goes in the exact same spot
    position = ctx.channel.position
    category = ctx.channel.category

    # Clone the channel
    new_channel = await ctx.channel.clone(reason=f"Nuked by {ctx.author.name}")
    
    # Move the new channel to the old channel's position
    await new_channel.edit(position=position, category=category)
    
    # Delete the old channel completely
    await ctx.channel.delete()

    # Send a confirmation message in the fresh new channel
    embed = discord.Embed(
        title="💥 Channel Nuked",
        description="All chat history has been completely cleared.",
        color=discord.Color.from_rgb(139, 92, 246)  # Clean modern purple (#8B5CF6)
    )
    embed.set_footer(text=f"Nuked by {ctx.author.name}")
    
    # Optional: Send a cool GIF or image
    embed.set_image(url="https://media.tenor.com/gi23E8Gg5bUAAAAC/explosion-boom.gif")
    
    await new_channel.send(embed=embed)

@nuke_channel.error
async def nuke_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need `Manage Channels` permissions to nuke a channel!", delete_after=5)



bot.run(os.getenv("DISCORD_TOKEN"))
