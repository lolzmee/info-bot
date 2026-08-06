import asyncio
import os
import discord
from discord.ext import commands

# Initialize bot with required intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix=".", intents=intents)


# 1. Close Ticket Button Component
class CloseTicketView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(
      label="🔒 Close Ticket",
      style=discord.ButtonStyle.red,
      custom_id="close_ticket_btn",
  )
  async def close_ticket(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.send_message(
        "🔒 Closing this ticket in 5 seconds..."
    )
    await asyncio.sleep(5)
    await interaction.channel.delete(reason="Ticket closed by user")


# 2. Dropdown Select Menu Component
class TicketSelect(discord.ui.Select):

  def __init__(self):
    options = [
        discord.SelectOption(
            label="Product Not Received",
            description="Use this if your order was not delivered correctly.",
            emoji="📁",
            value="Product Not Received",
        ),
        discord.SelectOption(
            label="Replace Item",
            description="Request a replacement for an item that is not working.",
            emoji="➕",
            value="Replace Item",
        ),
        discord.SelectOption(
            label="General Support",
            description="Ask general questions or request help from staff.",
            emoji="⚙️",
            value="General Support",
        ),
        discord.SelectOption(
            label="Purchase / Order",
            description="Inquire about purchases or payment methods.",
            emoji="🛒",
            value="Purchase / Order",
        ),
    ]
    super().__init__(
        placeholder="Select a ticket category...",
        min_values=1,
        max_values=1,
        options=options,
        custom_id="ticket_category_select",
    )

  async def callback(self, interaction: discord.Interaction):
    guild = interaction.guild
    user = interaction.user
    selected_category = self.values[0]

    # Clean channel name format (e.g. ticket-username)
    clean_username = "".join(
        c for c in user.name.lower() if c.isalnum() or c in "-_"
    )
    channel_name = f"ticket-{clean_username}"

    # Check if user already has an open ticket channel
    existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
    if existing_channel:
      await interaction.response.send_message(
          f"❌ You already have an open ticket in {existing_channel.mention}!",
          ephemeral=True,
      )
      return

    # Set channel permissions: only visible to the user and the bot/staff
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(
            read_messages=True, send_messages=True, attach_files=True
        ),
        guild.me: discord.PermissionOverwrite(
            read_messages=True, send_messages=True, manage_channels=True
        ),
    }

    # Create private text channel
    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        overwrites=overwrites,
        reason=f"Ticket opened by {user.name}",
    )

    # Private ephemeral reply to the user clicking the menu
    await interaction.response.send_message(
        f"✅ Ticket created! Head over to {ticket_channel.mention}",
        ephemeral=True,
    )

    # Send welcome embed inside the newly created private channel
    embed = discord.Embed(
        title=f"🎫 Support Ticket — {selected_category}",
        description=(
            f"Welcome {user.mention}!\n\n"
            "Thank you for reaching out. Please describe your request or issue"
            " in detail so staff can assist you."
        ),
        color=discord.Color.from_rgb(148, 48, 255),  # Sleek purple accent
    )
    embed.set_footer(text="Click the button below when you wish to close this ticket.")

    await ticket_channel.send(
        content=f"{user.mention}", embed=embed, view=CloseTicketView()
    )


# 3. Main Ticket Panel View
class TicketView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)
    self.add_item(TicketSelect())


@bot.event
async def on_ready():
  # Register persistent views so buttons work after restarts
  bot.add_view(TicketView())
  bot.add_view(CloseTicketView())
  print(f"Logged in as {bot.user.name} ({bot.user.id})")
  print("Embed & Ticket Bot is ready and online!")


# 4. Command to spawn the Ticket Panel
@bot.command(name="ticketsetup")
@commands.has_permissions(administrator=True)
async def ticket_setup(ctx: commands.Context):
  try:
    await ctx.message.delete()
  except Exception:
    pass

  embed = discord.Embed(
      title="🎫 CosmicBoosts Assistant",
      description=(
          "ℹ️ **Support Center**\n\n"
          "> **Welcome to Support.**\n"
          "> Choose the department that best matches your request so the"
          " correct team can review it quickly.\n\n"
          "• 📁 **Product Not Received** — use this if your order was not"
          " delivered correctly.\n"
          "• ➕ **Replace** — request a replacement for a delivered item that"
          " is not working.\n"
          "• ⚙️ **Support** — ask general questions or request help from"
          " staff.\n\n"
          "⏰ *Please keep your order details ready before opening a case.*\n"
          "❯ **Open the menu below and select the category that fits your"
          " situation.**"
      ),
      color=discord.Color.from_rgb(148, 48, 255),  # Sleek purple border
  )

  # Banner Image at the bottom of the embed
  embed.set_image(
      url="https://i.ibb.co/3ykX4vJ/support-ticket-banner.png"
  )  # You can swap this image URL with your own banner link!

  await ctx.send(embed=embed, view=TicketView())


# Existing commands (.embed and .nuke)
@bot.command(name="embed")
@commands.has_permissions(manage_messages=True)
async def create_embed(ctx: commands.Context):
  try:
    await ctx.message.delete()
  except Exception:
    pass

  prompt = await ctx.send(
      f"📝 {ctx.author.mention}, you have **10 minutes** to send the message for"
      " your embed below."
  )

  def check(m: discord.Message):
    return m.author == ctx.author and m.channel == ctx.channel

  try:
    user_msg = await bot.wait_for("message", check=check, timeout=600.0)
    content = user_msg.content

    try:
      await user_msg.delete()
      await prompt.delete()
    except Exception:
      pass

    embed = discord.Embed(
        description=content, color=discord.Color.from_rgb(148, 48, 255)
    )
    await ctx.send(embed=embed)

  except asyncio.TimeoutError:
    try:
      await prompt.edit(
          content="⏰ **Time expired!** Embed creation timed out.",
          delete_after=10,
      )
    except Exception:
      pass


@bot.command(name="nuke")
@commands.has_permissions(manage_channels=True)
async def nuke_channel(ctx: commands.Context):
  position = ctx.channel.position
  category = ctx.channel.category

  new_channel = await ctx.channel.clone(reason=f"Nuked by {ctx.author.name}")
  await new_channel.edit(position=position, category=category)
  await ctx.channel.delete()

  embed = discord.Embed(
      title="💥 Channel Nuked",
      description="All chat history has been completely cleared.",
      color=discord.Color.from_rgb(148, 48, 255),
  )
  embed.set_footer(text=f"Nuked by {ctx.author.name}")
  embed.set_image(
      url="https://media.tenor.com/gi23E8Gg5bUAAAAC/explosion-boom.gif"
  )

  await new_channel.send(embed=embed)


bot.run(os.getenv("DISCORD_TOKEN"))
