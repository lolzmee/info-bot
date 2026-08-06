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
intents.members = True  # Required for welcome/leave messages

bot = commands.Bot(command_prefix=".", intents=intents)

# Database file for welcome/leave channels
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
# TICKET SYSTEM COMPONENTS
# ---------------------------------------------------------
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔒 Close Ticket",
        style=discord.ButtonStyle.red,
        custom_id="close_ticket_btn",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Closing this ticket in 5 seconds...")
        await asyncio.sleep(5)
        await interaction.channel.delete(reason="Ticket closed")

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="General Support",
                description="Questions about Gulp, stock, or general help.",
                emoji="💬",
                value="General Support",
            ),
            discord.SelectOption(
                label="Purchase Inquiry",
                description="Help with buying wallets, accounts, or payment issues.",
                emoji="💳",
                value="Purchase Inquiry",
            ),
        ]
        super().__init__(
            placeholder="Select a support category...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_category_select",
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        selected_category = self.values[0]

        clean_username = "".join(c for c in user.name.lower() if c.isalnum() or c in "-_")
        channel_name = f"ticket-{clean_username}"

        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel:
            await interaction.response.send_message(
                f"❌ You already have an open ticket in {existing_channel.mention}!",
                ephemeral=True,
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }

        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            reason=f"Ticket opened by {user.name}",
        )

        await interaction.response.send_message(
            f"✅ Ticket created! Head over to {ticket_channel.mention}",
            ephemeral=True,
        )

        embed = discord.Embed(
            title=f"🎫 Gulp Support — {selected_category}",
            description=f"Welcome {user.mention}!\n\nPlease explain what you need help with below, and our staff will be with you shortly.",
            color=discord.Color.from_rgb(148, 48, 255),
        )
        embed.set_footer(text="Click the button below to close this ticket.")

        await ticket_channel.send(content=f"{user.mention}", embed=embed, view=CloseTicketView())

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# ---------------------------------------------------------
# BOT EVENTS
# ---------------------------------------------------------
@bot.event
async def on_ready():
    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())
    print(f"Logged in as {bot.user.name}")
    print("Gulp Bot is ready and online!")

@bot.event
async def on_member_join(member):
    settings = load_settings()
    if "welcome_channel" in settings:
        channel = bot.get_channel(settings["welcome_channel"])
        if channel:
            embed = discord.Embed(
                title="👋 Welcome to Gulp!",
                description=f"Welcome to the server, {member.mention}! Make sure to read the rules and check out our stock.",
                color=discord.Color.from_rgb(148, 48, 255)
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    settings = load_settings()
    if "leave_channel" in settings:
        channel = bot.get_channel(settings["leave_channel"])
        if channel:
            embed = discord.Embed(
                description=f"🛫 **{member.name}** just left the server.",
                color=discord.Color.red()
            )
            await channel.send(embed=embed)

# ---------------------------------------------------------
# SETUP COMMANDS
# ---------------------------------------------------------
@bot.command(name="ticketsetup")
@commands.has_permissions(administrator=True)
async def ticket_setup(ctx: commands.Context):
    try:
        await ctx.message.delete()
    except: pass

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    # Prompt for Title
    prompt1 = await ctx.send("📝 **Step 1:** Type the TITLE for your ticket panel (You have 2 minutes):")
    try:
        title_msg = await bot.wait_for("message", check=check, timeout=120.0)
        panel_title = title_msg.content
        await title_msg.delete()
    except asyncio.TimeoutError:
        return await prompt1.edit(content="⏰ Setup timed out.", delete_after=5)

    # Prompt for Description
    prompt2 = await ctx.send("📝 **Step 2:** Type the DESCRIPTION for your ticket panel (You have 5 minutes):")
    try:
        desc_msg = await bot.wait_for("message", check=check, timeout=300.0)
        panel_desc = desc_msg.content
        await desc_msg.delete()
    except asyncio.TimeoutError:
        return await prompt2.edit(content="⏰ Setup timed out.", delete_after=5)

    # Cleanup prompts and post the panel
    await prompt1.delete()
    await prompt2.delete()

    embed = discord.Embed(
        title=panel_title,
        description=panel_desc,
        color=discord.Color.from_rgb(148, 48, 255)
    )
    await ctx.send(embed=embed, view=TicketView())

@bot.command(name="setupwelcome")
@commands.has_permissions(administrator=True)
async def setup_welcome(ctx: commands.Context):
    settings = load_settings()
    settings["welcome_channel"] = ctx.channel.id
    save_settings(settings)
    await ctx.send(f"✅ Welcome messages will now be sent in {ctx.channel.mention}")

@bot.command(name="setupleft")
@commands.has_permissions(administrator=True)
async def setup_left(ctx: commands.Context):
    settings = load_settings()
    settings["leave_channel"] = ctx.channel.id
    save_settings(settings)
    await ctx.send(f"✅ Leave messages will now be sent in {ctx.channel.mention}")

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
        await ctx.send("❌ I couldn't ban that user. Check my role permissions.")

@bot.command(name="role")
@commands.has_permissions(manage_roles=True)
async def add_role(ctx, member: discord.Member, *, role_name: str):
    """Usage: .role @user RoleName"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        return await ctx.send(f"❌ Could not find a role named `{role_name}`.")
    
    try:
        if role in member.roles:
            await member.remove_roles(role)
            await ctx.send(f"➖ Removed **{role.name}** from {member.mention}.")
        else:
            await member.add_roles(role)
            await ctx.send(f"➕ Granted **{role.name}** to {member.mention}.")
    except:
        await ctx.send("❌ I don't have permission to manage this role. Ensure my bot role is higher in the server settings.")

# (Keep your existing .embed and .nuke commands here)

bot.run(os.getenv("DISCORD_TOKEN"))
