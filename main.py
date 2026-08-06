import asyncio
import os
import discord
from discord.ext import commands
import datetime
import json

# Initialize bot with all required intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)

SETTINGS_FILE = "settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ---------------------------------------------------------
# 1. LIVE TICKET SYSTEM (What users see)
# ---------------------------------------------------------
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Closing this ticket in 5 seconds...")
        await asyncio.sleep(5)
        await interaction.channel.delete(reason="Ticket closed")

class DynamicTicketSelect(discord.ui.Select):
    def __init__(self, options_data):
        # Build the discord SelectOptions from the custom data you create in the setup
        select_options = []
        for opt in options_data:
            select_options.append(discord.SelectOption(
                label=opt['label'],
                description=opt['description'],
                emoji=opt['emoji'],
                value=opt['label']
            ))
            
        super().__init__(
            placeholder="Select a support category...",
            min_values=1,
            max_values=1,
            options=select_options,
            custom_id="dynamic_ticket_select"
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        selected_category = self.values[0]

        clean_username = "".join(c for c in user.name.lower() if c.isalnum() or c in "-_")
        channel_name = f"ticket-{clean_username}"

        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel:
            return await interaction.response.send_message(
                f"❌ You already have an open ticket in {existing_channel.mention}!", ephemeral=True
            )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }

        ticket_channel = await guild.create_text_channel(
            name=channel_name, overwrites=overwrites, reason=f"Ticket opened by {user.name}"
        )

        await interaction.response.send_message(f"✅ Ticket created! Head over to {ticket_channel.mention}", ephemeral=True)

        embed = discord.Embed(
            title=f"🎫 Gulp Support — {selected_category}",
            description=f"Welcome {user.mention}!\n\nPlease explain what you need help with below, and our staff will be with you shortly.",
            color=discord.Color.from_rgb(148, 48, 255),
        )
        await ticket_channel.send(content=f"{user.mention}", embed=embed, view=CloseTicketView())

class LiveTicketView(discord.ui.View):
    def __init__(self, options_data):
        super().__init__(timeout=None)
        self.add_item(DynamicTicketSelect(options_data))

# ---------------------------------------------------------
# 2. INTERACTIVE BUILDER SYSTEM (What admins use)
# ---------------------------------------------------------
# ---------------------------------------------------------
# MODAL INPUTS (UPDATING TEXT & DROPDOWN OPTIONS)
# ---------------------------------------------------------
class TextEditModal(discord.ui.Modal, title='Edit Panel Text'):
    emb_title = discord.ui.TextInput(
        label='Title', 
        default='Gulp Support Center', 
        max_length=256
    )
    emb_desc = discord.ui.TextInput(
        label='Description', 
        style=discord.TextStyle.paragraph, 
        max_length=4000
    )

    def __init__(self, builder_view):
        super().__init__()
        self.builder_view = builder_view
        self.emb_title.default = builder_view.embed.title
        self.emb_desc.default = builder_view.embed.description

    async def on_submit(self, interaction: discord.Interaction):
        self.builder_view.embed.title = self.emb_title.value
        self.builder_view.embed.description = self.emb_desc.value
        await interaction.response.edit_message(embed=self.builder_view.embed, view=self.builder_view)


class AddCategoryModal(discord.ui.Modal, title='Add Dropdown Category'):
    cat_label = discord.ui.TextInput(
        label='Category Name (e.g., Support)', 
        max_length=100
    )
    cat_desc = discord.ui.TextInput(
        label='Description (e.g., General help)', 
        max_length=100
    )
    cat_emoji = discord.ui.TextInput(
        label='Emoji (Paste standard or custom emoji string)', 
        max_length=100, 
        required=False
    )

    def __init__(self, builder_view):
        super().__init__()
        self.builder_view = builder_view

    async def on_submit(self, interaction: discord.Interaction):
        emoji_val = self.cat_emoji.value.strip() if self.cat_emoji.value.strip() else "📁"
        self.builder_view.custom_options.append({
            "label": self.cat_label.value,
            "description": self.cat_desc.value,
            "emoji": emoji_val
        })
        
        self.builder_view.embed.add_field(
            name=f"Added Option: {emoji_val} {self.cat_label.value}", 
            value=self.cat_desc.value, 
            inline=False
        )
        await interaction.response.edit_message(embed=self.builder_view.embed, view=self.builder_view)

class TicketBuilderView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=600) # 10 minute timeout to build
        self.ctx = ctx
        self.embed = discord.Embed(
            title="Gulp Support Center", 
            description="Welcome to support! Use the builder buttons below to customize this embed.",
            color=discord.Color.from_rgb(148, 48, 255)
        )
        self.custom_options = []

    @discord.ui.button(label="📝 Edit Title & Desc", style=discord.ButtonStyle.blurple)
    async def edit_text(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TextEditModal(self))

    @discord.ui.button(label="➕ Add Dropdown Option", style=discord.ButtonStyle.secondary)
    async def add_option(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.custom_options) >= 10:
            return await interaction.response.send_message("❌ You can only have up to 10 options!", ephemeral=True)
        await interaction.response.send_modal(AddCategoryModal(self))

    @discord.ui.button(label="✅ Publish Panel", style=discord.ButtonStyle.green)
    async def publish_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.custom_options) == 0:
            return await interaction.response.send_message("❌ You must add at least 1 dropdown option before publishing!", ephemeral=True)
        
        # Clean up the "Added Option" fields from the preview embed
        self.embed.clear_fields()
        
        # Send the final panel
        await interaction.channel.send(embed=self.embed, view=LiveTicketView(self.custom_options))
        
        # Delete the builder message
        await interaction.message.delete()

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
    async def cancel_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()

# ---------------------------------------------------------
# BOT EVENTS & COMMANDS
# ---------------------------------------------------------
@bot.event
async def on_ready():
    bot.add_view(CloseTicketView())
    # Note: Because we are dynamically generating dropdowns, persistent views across total bot restarts 
    # require a database. For now, the panel will work flawlessly while the bot is online!
    print(f"Logged in as {bot.user.name}")

@bot.command(name="ticketsetup")
@commands.has_permissions(administrator=True)
async def ticket_setup(ctx: commands.Context):
    try:
        await ctx.message.delete()
    except: pass
    
    builder_view = TicketBuilderView(ctx)
    await ctx.send(
        content="**🛠️ Interactive Ticket Builder**\n*Only admins can see these buttons. Click them to customize your panel, then hit Publish.*", 
        embed=builder_view.embed, 
        view=builder_view
    )


# ---------------------------------------------------------
# MODERATION & UTILITY COMMANDS
# ---------------------------------------------------------
@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
async def mute_user(ctx, member: discord.Member, duration: str):
    """Usage: .mute @user 5m | 1h | 1d"""
    unit = duration[-1].lower()
    amount = int(duration[:-1])
    
    if unit == 'm':
        delta = datetime.timedelta(minutes=amount)
    elif unit == 'h':
        delta = datetime.timedelta(hours=amount)
    elif unit == 'd':
        delta = datetime.timedelta(days=amount)
    else:
        return await ctx.send("❌ Invalid time format! Use `m` (minutes), `h` (hours), or `d` (days). Example: `.mute @user 5m`")

    try:
        await member.timeout(discord.utils.utcnow() + delta, reason=f"Muted by {ctx.author.name}")
        await ctx.send(f"🔇 **{member.name}** has been muted for {duration}.")
    except Exception as e:
        await ctx.send("❌ I don't have permission to mute this user. Make sure my role is higher than theirs.")

@bot.command(name="unmute")
@commands.has_permissions(moderate_members=True)
async def unmute_user(ctx, member: discord.Member):
    """Usage: .unmute @user"""
    try:
        # Setting the timeout to None instantly lifts the mute
        await member.timeout(None, reason=f"Unmuted by {ctx.author.name}")
        await ctx.send(f"🔊 **{member.name}** has been unmuted.")
    except Exception as e:
        await ctx.send("❌")



@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_user(ctx, member: discord.Member, *, reason="No reason provided."):
    """Usage: .ban @user [reason]"""
    try:
        await member.ban(reason=reason)
        embed = discord.Embed(title="🔨 User Banned", color=discord.Color.red())
        embed.add_field(name="User", value=f"{member.name}")
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Banned By", value=ctx.author.mention)
        await ctx.send(embed=embed)
    except:
        await ctx.send("❌")

@bot.command(name="role")
@commands.has_permissions(manage_roles=True)
async def add_role(ctx, member: discord.Member, *, role_name: str):
    """Usage: .role @user RoleName"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        return await ctx.send(f"❌ `{role_name}`.")
    
    try:
        if role in member.roles:
            await member.remove_roles(role)
            await ctx.send(f"➖ Removed **{role.name}** from {member.mention}.")
        else:
            await member.add_roles(role)
            await ctx.send(f"➕ Granted **{role.name}** to {member.mention}.")
    except:
        await ctx.send("❌.")



# ---------------------------------------------------------
# Keep your existing .embed and .nuke commands here
# ---------------------------------------------------------

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
      title="wiped",
      description="w opsec",
      color=discord.Color.from_rgb(148, 48, 255),
  )
  embed.set_footer(text=f"Nuked by {ctx.author.name}")
  embed.set_image(
      url="https://klipy.com/gifs/mullvad-opsec"
  )

  await new_channel.send(embed=embed)


bot.run(os.getenv("DISCORD_TOKEN"))
