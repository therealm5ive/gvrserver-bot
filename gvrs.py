import os
import asyncio
import discord
import json
import re
import io
import aiohttp
from PIL import Image
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

TOKEN = os.getenv("TOKEN")

STARTUP_IMAGE = "https://media.discordapp.net/attachments/1479130697800089622/1513461961269182604/Society_-_Embed_-_Session_Startup.png?ex=6a27d0ca&is=6a267f4a&hm=18740e4a1d98af9cc8af01f6215e00389dec33b1369de0e09f4b55488224aed9&=&format=webp&quality=lossless"
SETTINGUP_IMAGE = "https://cdn.discordapp.com/attachments/1479130697800089622/1513567354863485029/Society_-_Embed_-_Setting_Up.png?ex=6a2832f2&is=6a26e172&hm=735140119f487af1ee9610a777452bf0a3dcec125e775b6e1ca9b726c290957e&"
EARLYACCESS_IMAGE = "https://media.discordapp.net/attachments/1479130697800089622/1513461961021587507/Society_-_Embed_-_Early_Access.png?ex=6a27d0ca&is=6a267f4a&hm=6a41537a1ce99096852afcd3353324e350aea59befaf12030ebadd89dff6685f&=&format=webp&quality=lossless"
RELEASE_IMAGE = "https://media.discordapp.net/attachments/1479130697800089622/1513461960761413702/Society_-_Embed_-_Session_Release.png?ex=6a27d0ca&is=6a267f4a&hm=1573b02e59a9bce5bb8427ceb419e5d201a39efaf8162b879671beae398f39dd&=&format=webp&quality=lossless"
OVER_IMAGE = "https://media.discordapp.net/attachments/1479130697800089622/1513461960165822626/Society_-_Embed_-_Session_Concluded.png?ex=6a27d0ca&is=6a267f4a&hm=25d4fdfdca98d0e7dbd789dc00c6a70f81115868bca6862a40bdfb28c7737817&=&format=webp&quality=lossless"
REINVITES_IMAGE = "https://media.discordapp.net/attachments/1479130697800089622/1513461960455356526/Society_-_Embed_-_Session_Reinvites.png?ex=6a27d0ca&is=6a267f4a&hm=eaeca4b95415c2dcd907222657cecd95b77b650619da1e2997eb29169ae1801d&=&format=webp&quality=lossless"
TICKET_PANEL_IMAGE = "https://cdn.discordapp.com/attachments/1479130697800089622/1513567380910116955/Society_-_Embed_-_Assistance.png?ex=6a2832f8&is=6a26e178&hm=9c577084fd141441a642443b308194b5cb91feda42c41e4bbb4cbb73d69698a2&"
TICKET_OPEN_IMAGE = "https://cdn.discordapp.com/attachments/1479130697800089622/1513567380910116955/Society_-_Embed_-_Assistance.png?ex=6a2832f8&is=6a26e178&hm=9c577084fd141441a642443b308194b5cb91feda42c41e4bbb4cbb73d69698a2&"

EARLYACCESS_ROLE_ID = 1290705580046024725
CIVILIANS_ROLE_ID = 1290705580025184277
TICKET_CATEGORY_ID = 1506043336987906231

STAFF_DATA_FILE = "staff_sessions.json"
SESSION_START_TIMES = {}
ACTIVE_COHOSTS = {}
ACTIVE_SUPERVISIONS = {}
ACTIVE_STARTUPS = {}

def load_staff_data():
    try:
        with open(STAFF_DATA_FILE, "r", encoding="utf-8") as file:
            content = file.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_staff_data(data):
    temp_file = STAFF_DATA_FILE + ".tmp"

    try:
        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

        os.replace(temp_file, STAFF_DATA_FILE)

    except OSError as e:
        print(f"Could not save staff data: {e}")

def ensure_user(data, user_id):
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {
            "hosted": [],
            "cohosted": [],
            "supervised": []
        }

def add_staff_session(user_id, session_type, note, start_timestamp, end_timestamp):
    data = load_staff_data()
    user_id = str(user_id)
    ensure_user(data, user_id)

    duration_minutes = round((end_timestamp - start_timestamp) / 60)

    data[user_id][session_type].append({
        "note": note,
        "start": start_timestamp,
        "end": end_timestamp,
        "duration": duration_minutes
    })

    save_staff_data(data)

def is_staff(member):
    return any(role.name == "Staff Team" for role in member.roles)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix=";",
    intents=intents
)

LOG_CHANNEL_NAME = "server-logs"

async def send_log(guild, user, command_name: str, extra: str = None):
    if guild is None:
        return

    log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)

    if log_channel is None:
        return

    timestamp = int(discord.utils.utcnow().timestamp())

    embed = discord.Embed(
        title="Command executed",
        color=discord.Color.from_str("#fef1b3")
    )

    embed.add_field(
        name="Executed by",
        value=f"{user.mention}\n`{user}`",
        inline=False
    )

    embed.add_field(
        name="Command",
        value=f"`{command_name}`",
        inline=False
    )

    embed.add_field(
        name="Time",
        value=f"<t:{timestamp}:F>",
        inline=False
    )

    if extra:
        embed.add_field(
            name="Details",
            value=extra[:1000],
            inline=False
        )

    embed.set_footer(
        text="Greenville Roleplay Society™",
        icon_url=bot.user.display_avatar.url
    )

    await log_channel.send(embed=embed)

class EarlyAccessView(discord.ui.View):
    def __init__(self, link: str):
        super().__init__(timeout=None)
        self.link = link

    @discord.ui.button(label="Early Access Link", style=discord.ButtonStyle.secondary)
    async def early_access_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id == EARLYACCESS_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message(
                "You do not have permission to use early access!",
                ephemeral=True
            )
            return

        await interaction.response.send_message(self.link, ephemeral=True)

class ReleaseView(discord.ui.View):
    def __init__(self, link: str):
        super().__init__(timeout=None)
        self.link = link

    @discord.ui.button(label="Roleplay Link", style=discord.ButtonStyle.secondary)
    async def roleplay_link_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(self.link, ephemeral=True)

class StaffProfileView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = str(user_id)

    async def send_sessions(self, interaction: discord.Interaction, session_type: str, title: str):
        data = load_staff_data()
        sessions = data.get(self.user_id, {}).get(session_type, [])

        if not sessions:
            await interaction.response.send_message(
                f"No {title.lower()} found.",
                ephemeral=True
            )
            return

        text = ""

        for index, session in enumerate(sessions, start=1):
            text += (
                f"**{index}.**\n"
                f"Date: <t:{session['end']}:D>\n"
                f"Duration: {session['duration']} minutes\n"
                f"Note: {session['note']}\n\n"
            )

        embed = discord.Embed(
            title=title,
            description=text[:4000],
            color=discord.Color.from_str("#fef1b3")
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Hosted Sessions", style=discord.ButtonStyle.secondary)
    async def hosted_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_sessions(interaction, "hosted", "Hosted Sessions")

    @discord.ui.button(label="Co-Hosted Sessions", style=discord.ButtonStyle.secondary)
    async def cohosted_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_sessions(interaction, "cohosted", "Co-Hosted Sessions")

    @discord.ui.button(label="Supervised Sessions", style=discord.ButtonStyle.secondary)
    async def supervised_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_sessions(interaction, "supervised", "Supervised Sessions")

@bot.event
async def on_ready():

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="🌸 discord.gg/gvsociety"
        )
    )

    bot.add_view(TicketPanelView())
    bot.add_view(ServerInfoView())

    # Ticket Buttons nach Neustarts aktiv halten
    bot.add_view(TicketPanelView())
    bot.add_view(PersistentTicketView())
    bot.add_view(ServerInfoView())

    synced = await bot.tree.sync()
    print(f"{len(synced)} Commands synchronised")
    print(f"{bot.user} is online!")

# =====================================
# /say
# =====================================

@bot.tree.command(
    name="say",
    description="The bot sends your text"
)
@app_commands.describe(
    text="Message to send"
)
async def say(interaction: discord.Interaction, text: str):

    if not any(
        role.name in ["Senior High Command", "High Command"]
        for role in interaction.user.roles
    ):
        await interaction.response.defer(ephemeral=True)
        return

    await interaction.response.send_message(
        "Command executed!",
        ephemeral=True
    )

    await send_log(interaction.guild, interaction.user, "/say", f"Text: {text}")

    await interaction.channel.send(text)

# =====================================
# /startup
# =====================================

@bot.tree.command(
    name="startup",
    description="Sends a roleplay startup message"
)
@app_commands.describe(
    reactions="Required amount of reactions"
)
async def startup(
    interaction: discord.Interaction,
    reactions: int
):

    allowed_channels = ["roleplay-1", "roleplay-2", "bot-testing-dont-remove"]

    if interaction.channel.name not in allowed_channels:
        await interaction.response.defer(ephemeral=True)
        return

    if interaction.channel.id in ACTIVE_STARTUPS:
        await interaction.response.send_message(
            "There is already an active startup message in this channel.",
            ephemeral=True
        )
        return

    if not any(
        role.name in ["Staff Team", "High Command"]
        for role in interaction.user.roles
    ):
        await interaction.response.defer(ephemeral=True)
        return

    host = interaction.user.mention

    embed = discord.Embed(
        title="<a:yellowmovingbow:1509751680651100230> Greenville Roleplay Society, Roleplay Startup! <a:yellowmovingbow:1509751680651100230>",
        color=discord.Color.from_str("#fef1b3")
    )

    embed.description = (
        f"<:yellowarrow1:1509767083041226862> {host} is currently hosting a roleplay session.\n\n"
        f"Prior to joining, please ensure to review the server information "
        f"and all roleplay regulations displayed below to avoid potential moderation.\n\n"
        f"<:yellownotification:1509751686179061760> **Roleplay Regulations**\n"
        f"<:yellowarrow:1509767080004681839> Read over our Restricted Vehicles List to avoid infractions.\n"
        f"<:yellowarrow:1509767080004681839> Ensure you have registered all of your vehicles.\n"
        f"<:yellowarrow:1509767080004681839> Ensure you've enabled ROBLOX joins so everyone can invite you.\n\n"
        f"<:yellowarrow:1509767080004681839> For this roleplay session to commence, we must achieve "
        f"**{reactions}+ reactions** on this startup message."
    )

    embed.set_image(url=STARTUP_IMAGE)

    embed.set_footer(
    text="Greenville Roleplay Society™",
    icon_url=bot.user.display_avatar.url
)

    message = await interaction.channel.send(
        f"<@&{CIVILIANS_ROLE_ID}>",
        embed=embed
    )

    SESSION_START_TIMES[interaction.channel.id] = int(message.created_at.timestamp())
    ACTIVE_STARTUPS[interaction.channel.id] = message.id

    await message.add_reaction("<:yellowcheck:1513524676180054107>")
    await interaction.response.send_message("Startup message executed!", ephemeral=True)
    await send_log(
    interaction.guild,
    interaction.user,
    "/startup"
)

    async def wait_for_reactions():
        while True:
            await asyncio.sleep(5)

            try:
                updated_message = await interaction.channel.fetch_message(message.id)

                for reaction in updated_message.reactions:
                    if str(reaction.emoji) == "<:yellowcheck:1513524676180054107>":
                        count = reaction.count - 1

                        if count >= reactions:
                            setup_embed = discord.Embed(
                                title="<a:GVRSloading:1513623240004735116> Roleplay Setting Up!",
                                description=(
                                    f"<:yellowarrow1:1509767083041226862> {host} is now **setting up** their roleplay session. Please note that it may take the host 5-10 Minutes to release the session. Due to technical issues, it may take even longer.\n\n"
                                ),
                                color=discord.Color.from_str("#fef1b3")
                            )

                            setup_embed.set_image(url=SETTINGUP_IMAGE)

                            setup_embed.set_footer(
                                text="Greenville Roleplay Society™",
                                icon_url=bot.user.display_avatar.url
                            )
                            await interaction.channel.send(embed=setup_embed)
                            
                            try:
                                dm_embed = discord.Embed(
                                    description=(
                                        "Your session startup in **Greenville Roleplay Society** "
                                        "has reached the required reactions and is ready to be released!"
                                    ),
                                    color=discord.Color.from_str("#fef1b3")
                                )

                                dm_embed.set_footer(
                                    text="Greenville Roleplay Society™",
                                    icon_url=bot.user.display_avatar.url
                                )

                                await interaction.user.send(embed=dm_embed)
                            
                            except:
                                pass
                            return
                        
            except Exception as e:
                print(e)
                return

    asyncio.create_task(wait_for_reactions())

# =====================================
# /earlyaccess
# =====================================

@bot.tree.command(name="earlyaccess", description="Sends an early access message")
@app_commands.describe(link="Enter the early access link here")
async def earlyaccess(interaction: discord.Interaction, link: str):
    allowed_channels = ["roleplay-1", "roleplay-2", "bot-testing-dont-remove"]

    if interaction.channel.name not in allowed_channels:
        await interaction.response.defer(ephemeral=True)
        return

    if interaction.channel.id not in ACTIVE_STARTUPS:
        await interaction.response.send_message(
        "There is no active startup in this channel.",
        ephemeral=True
        )
        return

    if not is_staff(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    if "https" not in link:
        await interaction.response.send_message("This is not a valid URL.", ephemeral=True)
        return

    host = interaction.user.mention

    await interaction.channel.send(
        "<@&1290705580046024725> <@&1333516817431265392> <@&1290705579982979178>"
    )

    embed = discord.Embed(
        title="<a:yellowtada:1509751747248390175> Greenville Roleplay Society, Early Access! <a:yellowtada:1509751747248390175>",
        description=(
            f"<:yellowarrow1:1509767083041226862> {host} has now released early access to their roleplay session.\n\n"
            "Nitro Boosters, Early Access members, and Staff Team members may now join using the button below, "
            "but sharing this link will result in the permanent removal of your Early Access privileges."
        ),
        color=discord.Color.from_str("#fef1b3")
    )

    embed.set_image(url=EARLYACCESS_IMAGE)

    embed.set_footer(
    text="Greenville Roleplay Society™",
    icon_url=bot.user.display_avatar.url
)

    await interaction.channel.send(
        embed=embed,
        view=EarlyAccessView(link)
    )

    await interaction.response.send_message("Early Access message executed!", ephemeral=True)
    await send_log(
    interaction.guild,
    interaction.user,
    "/earlyaccess"
)

# =====================================
# /release
# =====================================

@bot.tree.command(name="release", description="Sends a roleplay release message")
@app_commands.describe(
    session_link="Enter the roleplay link here",
    peacetime_status="Peacetime status",
    frp_speeds="FRP speed limit",
    leo_status="LEO status"
)
async def release(
    interaction: discord.Interaction,
    session_link: str,
    peacetime_status: str,
    frp_speeds: str,
    leo_status: str
):
    allowed_channels = ["roleplay-1", "roleplay-2", "bot-testing-dont-remove"]

    if interaction.channel.name not in allowed_channels:
        await interaction.response.defer(ephemeral=True)
        return

    if interaction.channel.id not in ACTIVE_STARTUPS:
        await interaction.response.send_message(
        "There is no active startup in this channel.",
        ephemeral=True
        )
        return

    if not is_staff(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    if "https" not in session_link:
        await interaction.response.send_message("This is not a valid URL.", ephemeral=True)
        return

    host = interaction.user.mention

    embed = discord.Embed(
        title="<a:yellowanimatedstar:1509767076838113371> Greenville Roleplay Society, Roleplay Released! <a:yellowanimatedstar:1509767076838113371>",
        description=(
            f"<:yellowarrow1:1509767083041226862> {host} has now **released** their roleplay session.\n"
            f"Prior to joining, please ensure to review the server information and all the roleplay regulations displayed below.\n\n"

            f"<:yellowrightarrow:1509751702075740191> Session links will be regenerated within five minutes of release, so be sure to join quickly. "
            f"Reinvites will occur every 20-30 minutes, so please do not ask the host for the link.\n\n"

            f"<:yellownotification:1509751686179061760> **Roleplay Regulations:**\n"
            f"<:yellowarrow:1509767080004681839> Session Host: {host}\n"
            f"<:yellowarrow:1509767080004681839> Peacetime Status: {peacetime_status}\n"
            f"<:yellowarrow:1509767080004681839> FRP Speedlimit: {frp_speeds}\n"
            f"<:yellowarrow:1509767080004681839> LEO Status: {leo_status}\n\n"

            f"<:yellowalarm:1509767056705327114> **Any unauthorized sharing of the link will result in moderation action.**"
        ),
        color=discord.Color.from_str("#fef1b3")
    )

    embed.set_image(url=RELEASE_IMAGE)

    embed.set_footer(
    text="Greenville Roleplay Society™",
    icon_url=bot.user.display_avatar.url
)

    await interaction.channel.send(
        f"<@&{CIVILIANS_ROLE_ID}>",
        embed=embed,
        view=ReleaseView(session_link)
    )

    await interaction.response.send_message("Release message executed!", ephemeral=True)
    await send_log(
    interaction.guild,
    interaction.user,
    "/release"
)

    # =====================================
# /reinvites
# =====================================

@bot.tree.command(
    name="reinvites",
    description="Sends a roleplay reinvites message"
)
@app_commands.describe(
    session_link="Session link",
    peacetime_status="Peacetime status",
    frp_speeds="FRP speed limit",
    leo_status="LEO status"
)
async def reinvites(
    interaction: discord.Interaction,
    session_link: str,
    peacetime_status: str,
    frp_speeds: str,
    leo_status: str
):

    allowed_channels = ["roleplay-1", "roleplay-2", "bot-testing-dont-remove"]

    if interaction.channel.name not in allowed_channels:
        await interaction.response.defer(ephemeral=True)
        return

    if interaction.channel.id not in ACTIVE_STARTUPS:
        await interaction.response.send_message(
        "There is no active startup in this channel.",
        ephemeral=True
        )
        return

    if not is_staff(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    if "https" not in session_link:
        await interaction.response.send_message(
            "This is not a valid URL.",
            ephemeral=True
        )
        return

    host = interaction.user.mention

    embed = discord.Embed(
        title="<a:yellowanimatedstar:1509767076838113371> Greenville Roleplay Society — Reinvites Released <a:yellowanimatedstar:1509767076838113371>",
        description=(
            f"<:yellowarrow1:1509767083041226862> {host} has released re-invites for their session!\n\n"
            f"Please be sure to follow all instructions given by the host and co-hosts prior to departing from spawn. "
            f"In addition, all Greenville Roleplay Society regulations must be followed throughout the session.\n\n"

            f"<:yellowrightarrow:1509751702075740191> Session links will be regenerated within five minutes of release, so be sure to join quickly. "
            f"Reinvites will occur every 20-30 minutes, so please do not ask the host for the link.\n\n"

            f"<:yellownotification:1509751686179061760> **Session Information:**\n"
            f"<:yellowarrow:1509767080004681839> FRP Speed Limit: **{frp_speeds}**\n"
            f"<:yellowarrow:1509767080004681839> Peacetime Status: **{peacetime_status}**\n"
            f"<:yellowarrow:1509767080004681839> LEO Status: **{leo_status}**\n\n"

            f"<:yellowalarm:1509767056705327114> **Any unauthorized sharing of the link will result in moderation action.**"
        ),
        color=discord.Color.from_str("#fef1b3")
    )

    # HIER DEIN REINVITES BILD EINFÜGEN
    embed.set_image(url=REINVITES_IMAGE)

    embed.set_footer(
    text="Greenville Roleplay Society™",
    icon_url=bot.user.display_avatar.url
)

    await interaction.channel.send(
        "@everyone",
        embed=embed,
        view=ReleaseView(session_link)
    )

    await interaction.response.send_message(
        "Reinvites message executed!",
        ephemeral=True
    )
    await send_log(
    interaction.guild,
    interaction.user,
    "/reinvites"
)

# =====================================
# /linkregen
# =====================================

@bot.tree.command(name="linkregen", description="Sends a link regeneration message")
async def linkregen(interaction: discord.Interaction):
    allowed_channels = ["roleplay-1", "roleplay-2", "bot-testing-dont-remove"]

    if interaction.channel.name not in allowed_channels:
        await interaction.response.defer(ephemeral=True)
        return

    if interaction.channel.id not in ACTIVE_STARTUPS:
        await interaction.response.send_message(
        "There is no active startup in this channel.",
        ephemeral=True
        )
        return

    if not is_staff(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    embed = discord.Embed(
        description="<:GVRSarrow:1513646972106702919> The session link has been regenerated. React below for Re-invites!",
        color=discord.Color.from_str("#fef1b3")
    )

    message = await interaction.channel.send("@here", embed=embed)
    await message.add_reaction("<:yellowcheck:1509767574752333904>")

    await interaction.response.send_message("Link regeneration message executed!", ephemeral=True)
    await send_log(
    interaction.guild,
    interaction.user,
    "/linkregen"
)

    # =====================================
    # /sessionclear
    # =====================================

@bot.tree.command(
    name="sessionclear",
    description="Clears the active startup session"
)
async def sessionclear(interaction: discord.Interaction):

    allowed_channels = ["roleplay-1", "roleplay-2", "bot-testing-dont-remove"]

    if interaction.channel.name not in allowed_channels:
        await interaction.response.defer(ephemeral=True)
        return

    if not any(role.name in ["Ownership Team", "Bot Developer"] for role in interaction.user.roles):
        await interaction.response.defer(ephemeral=True)
        return

    ACTIVE_STARTUPS.pop(interaction.channel.id, None)
    SESSION_START_TIMES.pop(interaction.channel.id, None)

    await interaction.response.send_message(
        "The active session has been cleared.",
        ephemeral=True
    )

    await send_log(interaction.guild, interaction.user, "/sessionclear")

# =====================================
# /over
# =====================================

@bot.tree.command(name="over", description="Sends a roleplay concluded message")
@app_commands.describe(additional_notes="Additional notes")
async def over(interaction: discord.Interaction, additional_notes: str):
    allowed_channels = ["roleplay-1", "roleplay-2", "bot-testing-dont-remove"]
    if interaction.channel.name not in allowed_channels:
        await interaction.response.defer(ephemeral=True)
        return

    if interaction.channel.id not in ACTIVE_STARTUPS:
        await interaction.response.send_message(
            "There is no active startup in this channel.",
            ephemeral=True
        )
        return

    if not is_staff(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    host = interaction.user.mention
    start_timestamp = SESSION_START_TIMES.get(interaction.channel.id)

    if start_timestamp:
        end_timestamp = int(discord.utils.utcnow().timestamp())
        session_duration = f"<t:{start_timestamp}:t> - <t:{end_timestamp}:t>"

        add_staff_session(
            interaction.user.id,
            "hosted",
            additional_notes,
            start_timestamp,
            end_timestamp
        )
    else:
        end_timestamp = int(discord.utils.utcnow().timestamp())
        session_duration = "Unknown"

    embed = discord.Embed(
        title="<a:yellowmovingbow:1509751680651100230> Greenville Roleplay Society, Roleplay Concluded! <a:yellowmovingbow:1509751680651100230>",
        description=(
            f"<:yellowarrow1:1509767083041226862> {host} has concluded their roleplay session.\n\n"
            f"Thank you to all civilians who attended. A new session will be hosted shortly by our staff team. "
            f"Please do not harass staff for sessions, or you may face moderation action.\n\n"
            f"<:yellownotification:1509751686179061760> **Roleplay Notes:**\n"
            f"<:yellowarrow:1509767080004681839> Session Host: {host}\n"
            f"<:yellowarrow:1509767080004681839> Session Duration: {session_duration}\n"
            f"<:yellowarrow:1509767080004681839> Additional Notes: {additional_notes}\n\n"
            f"<:yellowarrow:1509767080004681839> Need to report a user? Please head over to our #server-assistance channel and create a ticket."
        ),
        color=discord.Color.from_str("#fef1b3")
    )

    embed.set_image(url=OVER_IMAGE)

    embed.set_footer(
        text="Greenville Roleplay Society™",
        icon_url=bot.user.display_avatar.url
    )

    def not_pinned(message):
        return not message.pinned

    await interaction.response.send_message("Over message executed!", ephemeral=True)
    await send_log(
    interaction.guild,
    interaction.user,
    "/over"
)

    await interaction.channel.purge(
        limit=500,
        check=not_pinned
    )

    for user_id, cohost_start_timestamp in list(ACTIVE_COHOSTS.items()):
        add_staff_session(
            user_id,
            "cohosted",
            f"Automatically ended when session concluded by {interaction.user.display_name}",
            cohost_start_timestamp,
            end_timestamp
        )

    ACTIVE_COHOSTS.clear()

    for user_id, supervise_start_timestamp in list(ACTIVE_SUPERVISIONS.items()):
        add_staff_session(
            user_id,
            "supervised",
            f"Automatically ended when session concluded by {interaction.user.display_name}",
            supervise_start_timestamp,
            end_timestamp
        )

    ACTIVE_SUPERVISIONS.clear()

    ACTIVE_STARTUPS.pop(interaction.channel.id, None)
    SESSION_START_TIMES.pop(interaction.channel.id, None)

    await interaction.channel.send(embed=embed)

# =====================================
# /cohost
# =====================================

cohost_group = app_commands.Group(
    name="cohost",
    description="Co-host commands"
)

@cohost_group.command(name="start", description="Starts your co-host timer")
async def cohost_start(interaction: discord.Interaction):
    if not is_staff(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    ACTIVE_COHOSTS[interaction.user.id] = int(discord.utils.utcnow().timestamp())

    embed = discord.Embed(
        description=f"{interaction.user.mention} is **co-hosting** the current session.",
        color=discord.Color.from_str("#fef1b3")
    )

    await interaction.channel.send(
        embed=embed
    )

    await interaction.response.send_message("Cohost timer started!", ephemeral=True)
    await send_log(
    interaction.guild,
    interaction.user,
    "/cohost start"
)

@cohost_group.command(name="end", description="Ends your co-host timer")
@app_commands.describe(note="Note for this co-host session")
async def cohost_end(interaction: discord.Interaction, note: str):
    if not is_staff(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    if interaction.user.id not in ACTIVE_COHOSTS:
        await interaction.response.send_message(
            "You have not started a cohost session.",
            ephemeral=True
        )
        return

    start_timestamp = ACTIVE_COHOSTS.pop(interaction.user.id)
    end_timestamp = int(discord.utils.utcnow().timestamp())
    duration_minutes = round((end_timestamp - start_timestamp) / 60)

    add_staff_session(
        interaction.user.id,
        "cohosted",
        note,
        start_timestamp,
        end_timestamp
    )

    embed = discord.Embed(
        description=f"{interaction.user.mention} has **stopped co-hosting the current session**.",
        color=discord.Color.from_str("#fef1b3")
    )

    await interaction.channel.send(
        embed=embed
    )

    await interaction.response.send_message(
        f"Cohost session saved! Duration: {duration_minutes} minutes.",
        ephemeral=True
    )
    await send_log(
    interaction.guild,
    interaction.user,
    "/cohost end"
)

bot.tree.add_command(cohost_group)

# =====================================
# /supervise
# =====================================

supervise_group = app_commands.Group(
    name="supervise",
    description="Supervision commands"
)

@supervise_group.command(name="start", description="Starts your supervision timer")
async def supervise_start(interaction: discord.Interaction):
    if not is_staff(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    ACTIVE_SUPERVISIONS[interaction.user.id] = int(discord.utils.utcnow().timestamp())

    embed = discord.Embed(
        description=f"{interaction.user.mention} is **supervising** the current session.",
        color=discord.Color.from_str("#fef1b3")
    )

    await interaction.channel.send(
        embed=embed
    )

    await interaction.response.send_message("Supervision timer started!", ephemeral=True)
    await send_log(
    interaction.guild,
    interaction.user,
    "/supervise start"
)

@supervise_group.command(name="end", description="Ends your supervision timer")
@app_commands.describe(note="Note for this supervision session")
async def supervise_end(interaction: discord.Interaction, note: str):
    if not is_staff(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    if interaction.user.id not in ACTIVE_SUPERVISIONS:
        await interaction.response.send_message(
            "You have not started a supervision.",
            ephemeral=True
        )
        return

    start_timestamp = ACTIVE_SUPERVISIONS.pop(interaction.user.id)
    end_timestamp = int(discord.utils.utcnow().timestamp())
    duration_minutes = round((end_timestamp - start_timestamp) / 60)

    add_staff_session(
        interaction.user.id,
        "supervised",
        note,
        start_timestamp,
        end_timestamp
    )

    embed = discord.Embed(
        description=f"{interaction.user.mention} has **stopped supervising the current session**.",
        color=discord.Color.from_str("#fef1b3")
    )

    await interaction.channel.send(
        embed=embed
    )

    await interaction.response.send_message(
        f"Supervision saved! Duration: {duration_minutes} minutes.",
        ephemeral=True
    )
    await send_log(
    interaction.guild,
    interaction.user,
    "/supervise end"
)

bot.tree.add_command(supervise_group)

# =====================================
# /staff
# =====================================

staff_group = app_commands.Group(
    name="staff",
    description="Staff profile commands"
)

@staff_group.command(name="profile", description="Displays a staff profile")
@app_commands.describe(user="Select a staff member")
async def staff_profile(interaction: discord.Interaction, user: discord.Member = None):
    if not is_staff(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    if user is None:
        user = interaction.user

    data = load_staff_data()
    ensure_user(data, user.id)
    save_staff_data(data)

    user_data = data[str(user.id)]

    embed = discord.Embed(
        title="Staff Profile",
        description=(
            f"**User:** {user.mention}\n\n"
            f"**Hosted Sessions:** {len(user_data['hosted'])}\n"
            f"**Co-Hosted Sessions:** {len(user_data['cohosted'])}\n"
            f"**Supervised Sessions:** {len(user_data['supervised'])}\n\n"
            f"Use the buttons below to view saved sessions."
        ),
        color=discord.Color.from_str("#fef1b3")
    )

    if user.avatar:
        embed.set_thumbnail(url=user.avatar.url)

    await interaction.response.send_message(
        embed=embed,
        view=StaffProfileView(user.id),
        ephemeral=True
    )

    await send_log(interaction.guild, interaction.user, "/staff profile", f"Profile: {user.mention}")

@staff_group.command(name="clear", description="Clears all staff profiles")
async def staff_clear(interaction: discord.Interaction):

    if not any(role.name in ["Ownership Team", "Bot Developer"] for role in interaction.user.roles):
        await interaction.response.defer(ephemeral=True)
        return

    save_staff_data({})

    await interaction.response.send_message(
        "All staff profiles have been cleared.",
        ephemeral=True
    )

    await send_log(interaction.guild, interaction.user, "/staff clear")

@staff_group.command(name="strike", description="Strike a staff member")
@app_commands.describe(
    user="Select a staff member",
    reason="Reason",
    appealable="Appealable or Unappealable",
    time="Appeal time",
    evidence="Evidence link"
)
@app_commands.choices(
    appealable=[
        app_commands.Choice(name="Appealable", value="Appealable"),
        app_commands.Choice(name="Unappealable", value="Unappealable")
    ]
)
async def staff_strike(interaction: discord.Interaction, user: discord.Member, reason: str, appealable: app_commands.Choice[str], time: str, evidence: str):
    if not is_high_command(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    current = [
        role for role in user.roles
        if role.name in STAFF_INFRACTION_ROLES
    ]

    if len(current) >= 3:
        await interaction.response.send_message(
            "This staff member already has 3 staff strikes.",
            ephemeral=True
        )
        return

    next_number = len(current) + 1
    roman = {
        1: "I",
        2: "II",
        3: "III"
    }

    roman = {1: "I", 2: "II", 3: "III"}
    next_role_name = f"Staff Infraction {roman[next_number]}"
    next_role = discord.utils.get(interaction.guild.roles, name=next_role_name)

    if next_role is None:
        await interaction.response.send_message(f"Role `{next_role_name}` was not found.", ephemeral=True)
        return

    await user.add_roles(next_role)

    entry = make_entry(
        f"Staff Strike {next_number}",
        reason,
        interaction.user.id,
        appealable.value,
        time,
        evidence
    )

    add_mod_entry(user.id, entry)

    await send_mod_dm(
        user,
        "Staff Strike",
        (
            f"You have received **One** Staff Strike in **Greenville Roleplay Desire** for the following reason(s):\n\n"
            f"- {reason}\n\n"
            f"This Strike is **{appealable.value}** in {time}, if you deem this strike to be false please open a ticket via {APPEAL_TICKET_LINK}.\n\n"
            f"Evidence: {evidence}"
        )
    )

    await interaction.response.send_message(
        f"{user.mention} has received **Staff Strike {next_number}**.",
        ephemeral=True
    )

    await send_log(
        interaction.guild,
        interaction.user,
        "/staff strike",
        f"User: {user.mention}\nStaff Strike: {next_number}\nReason: {reason}"
    )

bot.tree.add_command(staff_group)

# =====================================
# /ticketpanel
# =====================================

SERVER_OVERSEER_ROLE_NAME = "Bot Developer"
STAFF_ROLE_NAME = "Staff Team"
HIGH_COMMAND_ROLE_NAMES = ["High Command"]

class TicketCloseConfirmView(discord.ui.View):
    def __init__(self, opener_id: int, open_timestamp: int):
        super().__init__(timeout=60)
        self.opener_id = opener_id
        self.open_timestamp = open_timestamp

    @discord.ui.button(label="Confirm Close", style=discord.ButtonStyle.danger)
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        close_timestamp = int(discord.utils.utcnow().timestamp())

        try:
            opener = await bot.fetch_user(self.opener_id)

            dm_embed = discord.Embed(
                title="Ticket Closed",
                description=(
                    f"Hello {opener.mention}, your ticket has been successfully closed by "
                    f"{interaction.user.mention}. We hope our team was able to resolve your issue.\n\n"
                    f"**Closed by**\n{interaction.user.mention}\n\n"
                    f"**Ticket ID**\n{interaction.channel.id}\n\n"
                    f"**Open Date**\n<t:{self.open_timestamp}:F>\n\n"
                    f"**Close Date**\n<t:{close_timestamp}:F>"
                ),
                color=discord.Color.from_str("#fef1b3")
            )

            dm_embed.set_footer(
                text="Greenville Roleplay Society™",
                icon_url=bot.user.display_avatar.url
            )

            await opener.send(embed=dm_embed)
        except:
            pass

        await interaction.response.send_message("Ticket closed.", ephemeral=True)
        await send_log(
    interaction.guild,
    interaction.user,
    "Ticket closed",
    f"Ticket channel: {interaction.channel.name}\nTicket ID: {interaction.channel.id}"
)
        await interaction.channel.delete()


class PersistentTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.claimed_by = None

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, custom_id="ticket_claim_button")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        if self.ticket_type == "Staff Report":
            allowed = any(role.name in HIGH_COMMAND_ROLE_NAMES for role in interaction.user.roles)
        else:
            allowed = any(role.name == STAFF_ROLE_NAME for role in interaction.user.roles)

        if not allowed:
            await interaction.response.defer(ephemeral=True)
            return

        if self.claimed_by is None:
            self.claimed_by = interaction.user.id
            button.label = "Unclaim"
            button.style = discord.ButtonStyle.danger

            await interaction.response.edit_message(view=self)

            embed = discord.Embed(
                description=f"{interaction.user.mention} claimed this ticket.",
                color=discord.Color.from_str("#fef1b3")
            )
            await interaction.channel.send(embed=embed)
            return

        if self.claimed_by != interaction.user.id:
            await interaction.response.send_message(
                "Only the user who claimed this ticket can unclaim it.",
                ephemeral=True
            )
            return

        self.claimed_by = None
        button.label = "Claim"
        button.style = discord.ButtonStyle.success

        await interaction.response.edit_message(view=self)

        embed = discord.Embed(
            description=f"{interaction.user.mention} unclaimed this ticket.",
            color=discord.Color.from_str("#fef1b3")
        )
        await interaction.channel.send(embed=embed)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="ticket_close_button")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        allowed = (
            any(role.name == STAFF_ROLE_NAME for role in interaction.user.roles)
            or any(role.name in HIGH_COMMAND_ROLE_NAMES for role in interaction.user.roles)
        )

        if not allowed:
            await interaction.response.defer(ephemeral=True)
            return

        embed = discord.Embed(
            title="Close Ticket",
            description="Are you sure you want to close this ticket?",
            color=discord.Color.from_str("#fef1b3")
        )

        await interaction.response.send_message(
            embed=embed,
            view=TicketCloseConfirmView(self.opener_id, self.open_timestamp),
            ephemeral=True
        )


class TicketModal(discord.ui.Modal):
    def __init__(self, ticket_type: str):
        super().__init__(title=f"{ticket_type} Ticket")
        self.ticket_type = ticket_type

        self.reason = discord.ui.TextInput(
            label="Reason for opening",
            placeholder="Write your reason here...",
            required=True,
            max_length=500
        )

        self.additional_info = discord.ui.TextInput(
            label="Additional information",
            placeholder="Write additional information here...",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=1000
        )

        self.add_item(self.reason)
        self.add_item(self.additional_info)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        opener = interaction.user

        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
        high_command_roles = [
            role for role in guild.roles
            if role.name in HIGH_COMMAND_ROLE_NAMES
        ]

        if self.ticket_type == "Staff Report":
            support_roles = high_command_roles
        else:
            support_roles = [staff_role]

        if not support_roles or any(role is None for role in support_roles):
            await interaction.response.send_message(
                "Support role was not found.",
                ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            opener: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                read_message_history=True
            )
        }

        for role in support_roles:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

        category = guild.get_channel(TICKET_CATEGORY_ID)

        ticket_channel = await guild.create_text_channel(
            name=f"support-{opener.name}".lower().replace(" ", "-"),
            category=category,
            overwrites=overwrites,
            reason=f"{self.ticket_type} ticket opened by {opener}"
        )

        banner_embed = discord.Embed(color=discord.Color.from_str("#fef1b3"))
        banner_embed.set_image(url=TICKET_OPEN_IMAGE)

        embed = discord.Embed(
            title=f"Greenville Roleplay Society, {self.ticket_type} Ticket",
            description=(
                f"Thank you for opening a **{self.ticket_type} Ticket**.\n\n"
                f"**Reason for Opening:** {self.reason.value}\n"
                f"**Additional Information:** {self.additional_info.value or 'None'}\n\n"
                f"Please provide any further details that may help our staff team assist you."
            ),
            color=discord.Color.from_str("#fef1b3")
        )

        embed.set_footer(
            text="Greenville Roleplay Society™",
            icon_url=bot.user.display_avatar.url
        )

        support_mentions = " ".join(role.mention for role in support_roles)

        await ticket_channel.send(
            content=f"{opener.mention} {support_mentions}",
            embeds=[banner_embed, embed],
            view=PersistentTicketView()
        )

        await send_log(
    interaction.guild,
    interaction.user,
    "Ticket opened",
    f"Ticket type: {self.ticket_type}\nTicket channel: {ticket_channel.mention}"
)

        await interaction.response.send_message(
            f"Your ticket has been created: {ticket_channel.mention}",
            ephemeral=True
        )


class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="General Assistance",
                description="Open a General Assistance ticket.",
                emoji=discord.PartialEmoji(name="yellowrightarrow", id=1509751702075740191)
            ),
            discord.SelectOption(
                label="Civilian Report",
                description="Report a Civilian within GVRS.",
                emoji=discord.PartialEmoji(name="yellowrightarrow", id=1509751702075740191)
            ),
            discord.SelectOption(
                label="Staff Report",
                description="Report a staff member in GVRS.",
                emoji=discord.PartialEmoji(name="yellowrightarrow", id=1509751702075740191)
            ),
            discord.SelectOption(
                label="Partnership",
                description="Open a Partnership ticket.",
                emoji=discord.PartialEmoji(name="yellowrightarrow", id=1509751702075740191)
            )
        ]

        super().__init__(
            placeholder="Select an option",
            options=options,
            custom_id="ticket_select"
        )

    async def callback(self, interaction: discord.Interaction):

        if not any(role.id == CIVILIANS_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message(
                "You do not have permission to open a ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(TicketModal(self.values[0]))


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


@bot.tree.command(
    name="ticketpanel",
    description="Sends the assistance ticket panel"
)
async def ticketpanel(interaction: discord.Interaction):

    if not any(role.name == SERVER_OVERSEER_ROLE_NAME for role in interaction.user.roles):
        await interaction.response.defer(ephemeral=True)
        return

    banner_embed = discord.Embed(color=discord.Color.from_str("#fef1b3"))
    banner_embed.set_image(url=TICKET_PANEL_IMAGE)

    embed = discord.Embed(
        title="❕ Greenville Roleplay Society, Assistance",
        description=(
            "Welcome to **Greenville Roleplay Society's** assistance channel. "
            "Within this channel, you may create a ticket for assistance if needed and one of our Staff Members will assist you.\n\n"
            "**<:GVRSarrow:1513646972106702919> `General Assistance`** — You may open this ticket if you have any questions or need assistance.\n\n"
            "**<:GVRSarrow:1513646972106702919> `Civilian Report`** — You may open this ticket if you are looking to report a Civilian.\n\n"
            "**<:GVRSarrow:1513646972106702919> `Staff Report`** — You may open this ticket if you are looking to report a Staff member.\n\n"
            "**<:GVRSarrow:1513646972106702919> `Partnership`** — You may open this ticket if you are looking to partner with Greenville Roleplay Society.\n\n"
        ),
        color=discord.Color.from_str("#fef1b3")
    )

    embed.set_footer(
        text="Greenville Roleplay Society™",
        icon_url=bot.user.display_avatar.url
    )

    await interaction.channel.send(embed=banner_embed)

    await interaction.channel.send(
        embed=embed,
        view=TicketPanelView()
    )

    await interaction.response.send_message(
        "Ticket panel sent!",
        ephemeral=True
    )

    # =====================================
# Moderation System
# /infract /mute /modlogs /warnings /ban /suspend /terminate
# =====================================

MODLOGS_FILE = "modlogs.json"
APPEAL_TICKET_LINK = "https://discord.com/channels/1290705579953754163/1503269938624856156"

STAFF_TEAM_ROLE = "Staff Team"
HIGH_COMMAND_ROLES = ["High Command", "Senior High Command"]

INFRACTION_ROLES = ["Infraction I", "Infraction II", "Infraction III", "Infraction IIII"]
STAFF_INFRACTION_ROLES = ["Staff Infraction I", "Staff Infraction II", "Staff Infraction III"]

STAFF_REMOVE_ROLES = [
    "Staff Team",
    "Trial Staff Team",
    "Intern Staff",
    "Low Command",
    "Junior Moderator",
    "Community Moderator",
    "Senior Moderator",
    "Middle Ranking Staff",
    "Junior Administration",
    "Community Administration",
    "Senior Administration",
    "High Ranking Intern",
    "Trial Management",
    "High Command",
    "Senior High Command",
    "Staffing Management",
    "Community Management",
    "Executive Management",
    "Assistant Director",
    "Associate Director",
    "Community Director",
    "Bot Developer"
]

def load_modlogs():
    try:
        with open(MODLOGS_FILE, "r", encoding="utf-8") as file:
            content = file.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_modlogs(data):
    temp_file = MODLOGS_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)
    os.replace(temp_file, MODLOGS_FILE)

def is_high_command(member):
    return any(role.name in HIGH_COMMAND_ROLES for role in member.roles)

def is_staff_team(member):
    return any(role.name == STAFF_TEAM_ROLE for role in member.roles)

async def get_target(guild, user_input: str):
    user_id = re.sub(r"\D", "", user_input)

    if not user_id:
        return None

    user_id = int(user_id)
    member = guild.get_member(user_id)

    if member:
        return member

    try:
        return await bot.fetch_user(user_id)
    except:
        return None

def ensure_mod_user(data, user_id):
    user_id = str(user_id)

    if user_id not in data or isinstance(data[user_id], list):
        old_logs = data[user_id] if user_id in data and isinstance(data[user_id], list) else []

        data[user_id] = {
            "warnings": [],
            "modlogs": old_logs
        }
    user_id = str(user_id)

    if user_id not in data:
        data[user_id] = {
            "warnings": [],
            "modlogs": []
        }

def add_mod_entry(user_id, entry):
    data = load_modlogs()
    user_id = str(user_id)

    ensure_mod_user(data, user_id)

    data[user_id]["warnings"].append(entry)
    data[user_id]["modlogs"].append(entry.copy())

    save_modlogs(data)

def make_entry(entry_type, reason, moderator_id, appealable, appeal_time, evidence):
    return {
        "type": entry_type,
        "reason": reason,
        "moderator": moderator_id,
        "appealable": appealable,
        "appeal_time": appeal_time,
        "evidence": evidence,
        "timestamp": int(discord.utils.utcnow().timestamp())
    }

async def send_mod_dm(user, title, description):
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.from_str("#fef1b3")
    )

    embed.set_footer(
        text="Greenville Roleplay Desire",
        icon_url=bot.user.display_avatar.url
    )

    try:
        await user.send(embed=embed)
    except:
        pass

async def remove_roles_by_name(member, role_names):
    roles = [role for role in member.roles if role.name in role_names]

    if roles:
        await member.remove_roles(*roles)

async def remove_warning_role(member, warning_type):
    role_name = None

    infraction_roles = {
        "Infraction 1": "Infraction I",
        "Infraction 2": "Infraction II",
        "Infraction 3": "Infraction III",
        "Infraction 4": "Infraction IIII",
    }

    staff_strike_roles = {
        "Staff Strike 1": "Staff Infraction I",
        "Staff Strike 2": "Staff Infraction II",
        "Staff Strike 3": "Staff Infraction III",
    }

    if warning_type in infraction_roles:
        role_name = infraction_roles[warning_type]

    elif warning_type in staff_strike_roles:
        role_name = staff_strike_roles[warning_type]

    if role_name:
        role = discord.utils.get(member.guild.roles, name=role_name)

        if role and role in member.roles:
            await member.remove_roles(role)

class DeleteWarningSelect(discord.ui.Select):
    def __init__(self, target: discord.Member, warnings: list):
        self.target = target

        options = []

        for index, warning in enumerate(warnings[:25]):
            date_text = datetime.fromtimestamp(
                warning["timestamp"]
            ).strftime("%d.%m.%Y")

            options.append(
                discord.SelectOption(
                    label=warning["type"],
                    description=f"{warning['reason'][:40]} • {date_text}",
                    value=str(index)
                )
            )

        super().__init__(
            placeholder="Select a warning to delete",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if not is_high_command(interaction.user):
            await interaction.response.defer(ephemeral=True)
            return

        data = load_modlogs()
        user_id = str(self.target.id)

        warnings = data.get(user_id, {}).get("warnings", [])
        index = int(self.values[0])

        if index >= len(warnings):
            await interaction.response.send_message(
                "This warning no longer exists.",
                ephemeral=True
            )
            return

        removed_warning = warnings.pop(index)

        data[user_id]["warnings"] = warnings
        save_modlogs(data)

        await remove_warning_role(self.target, removed_warning["type"])

        await interaction.response.send_message(
            f"`{removed_warning['type']}` has been deleted from warnings.",
            ephemeral=True
        )

        await send_log(
            interaction.guild,
            interaction.user,
            "Warning deleted",
            f"User: {self.target.mention}\nWarning: {removed_warning['type']}"
        )

class DeleteWarningDropdownView(discord.ui.View):
    def __init__(self, target: discord.Member, warnings: list):
        super().__init__(timeout=120)
        self.add_item(DeleteWarningSelect(target, warnings))

class DeleteWarningButtonView(discord.ui.View):
    def __init__(self, target: discord.Member, warnings: list):
        super().__init__(timeout=120)
        self.target = target
        self.warnings = warnings

    @discord.ui.button(
        label="Delete a Warning",
        style=discord.ButtonStyle.danger
    )
    async def delete_warning_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_high_command(interaction.user):
            await interaction.response.defer(ephemeral=True)
            return

        embed = discord.Embed(
            title="Delete a Warning",
            description=f"{self.target.mention} has **{len(self.warnings)}** warning(s). Select a warning to delete.",
            color=discord.Color.red()
        )

        await interaction.response.send_message(
            embed=embed,
            view=DeleteWarningDropdownView(self.target, self.warnings),
            ephemeral=True
        )

@bot.tree.command(name="infract", description="Infract a user")
@app_commands.describe(
    user="Mention or user ID",
    reason="Reason",
    appealable="Appealable or Unappealable",
    time="Appeal time",
    evidence="Evidence link"
)
@app_commands.choices(
    appealable=[
        app_commands.Choice(name="Appealable", value="Appealable"),
        app_commands.Choice(name="Unappealable", value="Unappealable")
    ]
)
async def infract(interaction: discord.Interaction, user: str, reason: str, appealable: app_commands.Choice[str], time: str, evidence: str):
    if not is_staff_team(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    target = await get_target(interaction.guild, user)

    if target is None or not isinstance(target, discord.Member):
        await interaction.response.send_message("User was not found in this server.", ephemeral=True)
        return

    if is_staff_team(target):
        await interaction.response.send_message(
            "Staff Team members cannot be infracted. Use `/staff strike` instead.",
            ephemeral=True
        )
        return

    current = [role for role in target.roles if role.name in INFRACTION_ROLES]

    if len(current) >= 4:
        await interaction.response.send_message(
            "User has 4 infractions, roleplay restrict the user.",
            ephemeral=True
        )
        return

    next_number = len(current) + 1
    roman = {
        1: "I",
        2: "II",
        3: "III",
        4: "IIII"
    }

    roman = {1: "I", 2: "II", 3: "III", 4: "IIII"}
    next_role_name = f"Infraction {roman[next_number]}"
    next_role = discord.utils.get(interaction.guild.roles, name=next_role_name)

    if next_role is None:
        await interaction.response.send_message(f"Role `{next_role_name}` was not found.", ephemeral=True)
        return

    await target.add_roles(next_role)

    entry = make_entry(
        f"Infraction {next_number}",
        reason,
        interaction.user.id,
        appealable.value,
        time,
        evidence
    )

    add_mod_entry(target.id, entry)

    await send_mod_dm(
        target,
        "Infraction",
        (
            f"You have been **Infracted {next_number} Time** in **Greenville Roleplay Desire** for the following reason(s):\n\n"
            f"- {reason}\n\n"
            f"This infraction is **{appealable.value}** in {time}, if you deem this infraction to be false please open a ticket via {APPEAL_TICKET_LINK}.\n\n"
            f"Evidence: {evidence}"
        )
    )

    msg = f"{target.mention} has received **Infraction {next_number}**."

    if next_number == 4:
        msg += "\nThis user has now reached 4 infractions. User needs to be roleplay restricted."

    await interaction.response.send_message(msg, ephemeral=True)

    await send_log(interaction.guild, interaction.user, "/infract", f"User: {target.mention}\nInfraction: {next_number}\nReason: {reason}")

@bot.tree.command(name="mute", description="Mute a user")
@app_commands.describe(
    user="Mention or user ID",
    minutes="Minutes",
    hours="Hours"
)
async def mute(interaction: discord.Interaction, user: str, minutes: int = 0, hours: int = 0):
    if not is_staff_team(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    target = await get_target(interaction.guild, user)

    if target is None or not isinstance(target, discord.Member):
        await interaction.response.send_message("User was not found in this server.", ephemeral=True)
        return

    if is_staff_team(target):
        await interaction.response.send_message("Staff Team members cannot be muted.", ephemeral=True)
        return

    duration = timedelta(hours=hours, minutes=minutes)

    if duration.total_seconds() <= 0:
        await interaction.response.send_message("Please provide minutes or hours.", ephemeral=True)
        return

    await target.timeout(duration, reason=f"Muted by {interaction.user}")

    await interaction.response.send_message(
        f"{target.mention} has been muted for `{hours}h {minutes}m`.",
        ephemeral=True
    )

    await send_log(interaction.guild, interaction.user, "/mute", f"User: {target.mention}\nDuration: {hours}h {minutes}m")

@bot.tree.command(name="ban", description="Ban a user")
@app_commands.describe(
    user="Mention or user ID",
    reason="Reason",
    evidence="Evidence link"
)
async def ban(interaction: discord.Interaction, user: str, reason: str, evidence: str):
    if not is_high_command(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    target = await get_target(interaction.guild, user)

    if target is None:
        await interaction.response.send_message("User was not found.", ephemeral=True)
        return

    await send_mod_dm(
        target,
        "Ban",
        (
            f"You have been **Banned** from **Greenville Roleplay Desire** for the following reason(s):\n\n"
            f"- {reason}\n\n"
            f"If you deem this ban to be false, feel free to appeal it with the appeal listed below.\n"
            f"Appeal: Soon.\n\n"
            f"Evidence: {evidence}"
        )
    )

    await interaction.guild.ban(target, reason=reason)

    entry = make_entry("Ban", reason, interaction.user.id, "Soon", "Soon", evidence)
    add_mod_entry(target.id, entry)

    await interaction.response.send_message(f"{target} has been banned.", ephemeral=True)
    await send_log(interaction.guild, interaction.user, "/ban", f"User ID: {target.id}\nReason: {reason}")

@bot.tree.command(name="suspend", description="Suspend a staff member")
@app_commands.describe(
    user="Mention or user ID",
    reason="Reason",
    appealable="Appealable or Unappealable",
    time="Appeal time",
    evidence="Evidence link"
)
@app_commands.choices(
    appealable=[
        app_commands.Choice(name="Appealable", value="Appealable"),
        app_commands.Choice(name="Unappealable", value="Unappealable")
    ]
)
async def suspend(interaction: discord.Interaction, user: str, reason: str, appealable: app_commands.Choice[str], time: str, evidence: str):
    if not is_high_command(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    target = await get_target(interaction.guild, user)

    if target is None or not isinstance(target, discord.Member):
        await interaction.response.send_message("User was not found in this server.", ephemeral=True)
        return

    await remove_roles_by_name(target, STAFF_REMOVE_ROLES)

    entry = make_entry("Suspension", reason, interaction.user.id, appealable.value, time, evidence)
    add_mod_entry(target.id, entry)

    await send_mod_dm(
        target,
        "Suspension",
        (
            f"You have been **Suspended** from the **Greenville Roleplay Desire** Staff Team for the following reason(s):\n\n"
            f"- {reason}\n\n"
            f"This Suspension is **{appealable.value}** in {time}, if you deem this suspension to be false please open a ticket via {APPEAL_TICKET_LINK}\n\n"
            f"Evidence: {evidence}"
        )
    )

    await interaction.response.send_message(f"{target.mention} has been suspended.", ephemeral=True)
    await send_log(interaction.guild, interaction.user, "/suspend", f"User: {target.mention}\nReason: {reason}")

@bot.tree.command(name="terminate", description="Terminate a staff member")
@app_commands.describe(
    user="Mention or user ID",
    reason="Reason",
    appealable="Appealable or Unappealable",
    time="Appeal time",
    evidence="Evidence link"
)
@app_commands.choices(
    appealable=[
        app_commands.Choice(name="Appealable", value="Appealable"),
        app_commands.Choice(name="Unappealable", value="Unappealable")
    ]
)
async def terminate(interaction: discord.Interaction, user: str, reason: str, appealable: app_commands.Choice[str], time: str, evidence: str):
    if not is_high_command(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    target = await get_target(interaction.guild, user)

    if target is None or not isinstance(target, discord.Member):
        await interaction.response.send_message("User was not found in this server.", ephemeral=True)
        return

    await remove_roles_by_name(target, STAFF_REMOVE_ROLES)

    entry = make_entry("Termination", reason, interaction.user.id, appealable.value, time, evidence)
    add_mod_entry(target.id, entry)

    await send_mod_dm(
        target,
        "Termination",
        (
            f"You have been **Terminated** from the **Greenville Roleplay Desire** Staff Team for the following reason(s):\n\n"
            f"- {reason}\n\n"
            f"This Termination is **{appealable.value}** in {time}.\n\n"
            f"Evidence: {evidence}"
        )
    )

    await interaction.response.send_message(f"{target.mention} has been terminated.", ephemeral=True)
    await send_log(interaction.guild, interaction.user, "/terminate", f"User: {target.mention}\nReason: {reason}")

@bot.tree.command(name="warnings", description="View active warnings for a user")
@app_commands.describe(user="Mention or user ID")
async def warnings(interaction: discord.Interaction, user: str):
    if not is_staff_team(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    target = await get_target(interaction.guild, user)

    if target is None or not isinstance(target, discord.Member):
        await interaction.response.send_message("User was not found in this server.", ephemeral=True)
        return

    data = load_modlogs()
    warnings_list = data.get(str(target.id), {}).get("warnings", [])

    if not warnings_list:
        await interaction.response.send_message("This user has no warnings.", ephemeral=True)
        return

    text = ""

    for warning in warnings_list:
        if warning["type"].startswith("Infraction"):
            number = warning["type"].replace("Infraction ", "")
            text += (
                f"**Moderator:** <@{warning['moderator']}>\n"
                f"You have been **Infracted {number} Time** in **Greenville Roleplay Society** for the following reason(s):\n\n"
                f"- {warning['reason']}\n\n"
                f"This infraction is **{warning['appealable']}** in {warning['appeal_time']}, if you deem this infraction to be false "
                f"please open a ticket via {APPEAL_TICKET_LINK}.\n\n"
                f"Evidence: {warning['evidence']} - <t:{warning['timestamp']}:R>\n\n"
            )

        elif warning["type"].startswith("Staff Strike"):
            text += (
                f"**Moderator:** <@{warning['moderator']}>\n"
                f"You have received **One** Staff Strike in **Greenville Roleplay Society** for the following reason(s):\n\n"
                f"- {warning['reason']}\n\n"
                f"This Strike is **{warning['appealable']}** in {warning['appeal_time']}, if you deem this strike to be false "
                f"please open a ticket via {APPEAL_TICKET_LINK}.\n\n"
                f"Evidence: {warning['evidence']} - <t:{warning['timestamp']}:R>\n\n"
            )

        elif warning["type"] == "Suspension":
            text += (
                f"**Moderator:** <@{warning['moderator']}>\n"
                f"You have been **Suspended** from the **Greenville Roleplay Society** Staff Team for the following reason(s):\n\n"
                f"- {warning['reason']}\n\n"
                f"This Suspension is **{warning['appealable']}** in {warning['appeal_time']}, if you deem this suspension to be false "
                f"please open a ticket via {APPEAL_TICKET_LINK}.\n\n"
                f"Evidence: {warning['evidence']} - <t:{warning['timestamp']}:R>\n\n"
            )

        elif warning["type"] == "Termination":
            text += (
                f"**Moderator:** <@{warning['moderator']}>\n"
                f"You have been **Terminated** from the **Greenville Roleplay Society** Staff Team for the following reason(s):\n\n"
                f"- {warning['reason']}\n\n"
                f"This Termination is **{warning['appealable']}** in {warning['appeal_time']}.\n\n"
                f"Evidence: {warning['evidence']} - <t:{warning['timestamp']}:R>\n\n"
            )

        elif warning["type"] == "Ban":
            text += (
                f"**Moderator:** <@{warning['moderator']}>\n"
                f"You have been **Banned** from **Greenville Roleplay Society** for the following reason(s):\n\n"
                f"- {warning['reason']}\n\n"
                f"If you deem this ban to be false, feel free to appeal it with the appeal listed below.\n"
                f"Appeal: Soon.\n\n"
                f"Evidence: {warning['evidence']} - <t:{warning['timestamp']}:R>\n\n"
            )

    embed = discord.Embed(
        title=f"{len(warnings_list)} Warning{'s' if len(warnings_list) != 1 else ''} for {target} ({target.id})",
        description=text[:4000],
        color=discord.Color.from_str("#fef1b3")
    )

    view = DeleteWarningButtonView(target, warnings_list) if is_high_command(interaction.user) else None

    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="modlogs", description="View all moderation logs for a user")
@app_commands.describe(user="Mention or user ID")
async def modlogs(interaction: discord.Interaction, user: str):
    if not is_staff_team(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    target = await get_target(interaction.guild, user)

    if target is None:
        await interaction.response.send_message("User was not found.", ephemeral=True)
        return

    data = load_modlogs()
    logs = data.get(str(target.id), {}).get("modlogs", [])

    if not logs:
        await interaction.response.send_message("This user has no modlogs.", ephemeral=True)
        return

    text = ""

    for log in logs:
        text += (
            f"**{log['type']}**\n"
            f"Reason: {log['reason']}\n"
            f"Moderator: <@{log['moderator']}>\n"
            f"Date: <t:{log['timestamp']}:F>\n"
            f"Evidence: {log['evidence']}\n\n"
        )

    embed = discord.Embed(
        title=f"Modlogs for {target}",
        description=text[:4000],
        color=discord.Color.from_str("#fef1b3")
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

    # =====================================
# /serverinfo
# =====================================

SERVER_INFO_IMAGE = "https://cdn.discordapp.com/attachments/1479130697800089622/1513908128557695098/Society_-_Embed_-_Regulations.webp?ex=6a297050&is=6a281ed0&hm=dd0de229f889c0563f37d4de6c27e82277c597431990d53879e63dfef9b7079d&"

ROBLOX_GROUP_LINK = "https://www.roblox.com/communities/650527738/Official-Greenville-Roleplay-Society#!/about"
RESTRICTED_VEHICLES_LINK = "https://docs.google.com/spreadsheets/d/1ahcV0bVi62XDg6rRYaEpGgFQV3_85_BPcwqXO-EVoVs/edit?gid=16420916#gid=16420916"

SERVER_GUIDELINES_TEXT = """
**▰ Discord Rules & Regulations**

**1. <:yellowarrow:1509767080004681839> Read the Regulations**
All Greenville Roleplay Society members must read and acknowledge the regulations listed in our information channels. Failure to comply may result in serious consequences.

**2. <:yellowarrow:1509767080004681839> Follow All Staff Instructions**
Members are required to follow directions given by staff. For example, if instructed to leave a session, you must comply immediately.


**3. <:yellowarrow:1509767080004681839> Exercise Common Sense**
Use sound judgment when determining whether actions violate the rules. If it would be unacceptable in another community, it is not acceptable here.

**4. <:yellowarrow:1509767080004681839> Age Requirement (13+)**
In accordance with Discord's Terms of Service, all members must be at least 13 years old. Anyone found under this age will be removed until they meet the requirement.

**5. <:yellowarrow:1509767080004681839> No Harassment or Personal Attacks**
Any form of harassment or targeting of other members is prohibited. Violations may result in timeouts, strikes, or removal from the community.

**6. <:yellowarrow:1509767080004681839> No Slurs or Offensive Remarks**
Use of discriminatory language or offensive comments based on race, gender identity, weight, ethnicity, or similar factors is strictly forbidden.

**7. <:yellowarrow:1509767080004681839> No Advertising**
Advertising of any kind is prohibited, including direct messages and public channels. Any server found recruiting Greenville Roleplay Society members or staff will be blacklisted, and involved members will be removed.

**8. <:yellowarrow:1509767080004681839> No Resource Theft**
Stealing any Greenville Roleplay Society resources, such as announcements, documentation or any other assets will lead to an immediate ban from Greenville Roleplay Society and all affiliated servers.

**9. <:yellowarrow:1509767080004681839> No Sharing of Personal Information**
Leaking, doxxing, or otherwise sharing personal information about any member will result in an immediate and permanent ban.

**10. <:yellowarrow:1509767080004681839> No NSFW Content**
Posting or distributing not safe for work material, including pornography, gore, or violent imagery, is strictly prohibited. First offense results in a warning, although the second offense results in an immediate ban.

**11. <:yellowarrow:1509767080004681839> Maintain Respect**
Greenville Roleplay Society will not tolerate any disrespect, defamatory comments or complaints about Greenville Roleplay Society or affiliated communities. Any user found being disrespectful will be moderated.

**12. <:yellowarrow:1509767080004681839> Voice Channel Conduct**
All rules apply in voice channels. Excessive noise, disruptive sounds, or "ear-rape" audio is prohibited and will result in disciplinary action.
"""

class ServerInfoSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Server Guidelines",
                description="View the server guidelines.",
                emoji=discord.PartialEmoji(name="yellowarrow", id=1509767080004681839)
            ),
            discord.SelectOption(
                label="Roblox Group",
                description="Get the official Roblox group link.",
                emoji=discord.PartialEmoji(name="yellowarrow", id=1509767080004681839)
            ),
            discord.SelectOption(
                label="Restricted Vehicles List",
                description="View the restricted vehicles list.",
                emoji=discord.PartialEmoji(name="yellowarrow", id=1509767080004681839)
            )
        ]

        super().__init__(
            placeholder="Select an option",
            options=options,
            custom_id="server_info_select"
        )

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]

        if choice == "Server Guidelines":
            embed = discord.Embed(
                title="Greenville Roleplay Society, Server Guidelines",
                description=SERVER_GUIDELINES_TEXT,
                color=discord.Color.from_str("#fef1b3")
            )

        elif choice == "Roblox Group":
            embed = discord.Embed(
                title="Greenville Roleplay Society, Roblox Group",
                description=f"<:yellowarrow:1509767080004681839> Join our Roblox group here:\n{ROBLOX_GROUP_LINK}",
                color=discord.Color.from_str("#fef1b3")
            )

        else:
            embed = discord.Embed(
                title="Greenville Roleplay Society, Restricted Vehicles List",
                description=f"<:yellowarrow:1509767080004681839> View the Restricted Vehicles List here:\n{RESTRICTED_VEHICLES_LINK}",
                color=discord.Color.from_str("#fef1b3")
            )

        embed.set_footer(
            text="Greenville Roleplay Society™",
            icon_url=bot.user.display_avatar.url
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class ServerInfoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ServerInfoSelect())


@bot.tree.command(
    name="serverinfo",
    description="Sends the server information panel"
)
async def serverinfo(interaction: discord.Interaction):

    if not any(role.name == "Community Overseer" for role in interaction.user.roles):
        await interaction.response.defer(ephemeral=True)
        return

    banner_embed = discord.Embed(color=discord.Color.from_str("#fef1b3"))
    banner_embed.set_image(url=SERVER_INFO_IMAGE)

    info_embed = discord.Embed(
        description=(
            "<:yellowwave:1509751772154171563> Welcome to **Greenville Roleplay Society**\n\n"
            "On behalf of the entire team, we are delighted to welcome you to Greenville Roleplay Society. "
            "Founded in April 2026 through the strategic acquisition of the Roblox Roleplay Server, our community has scaled significantly while maintaining the core values that define us.\n\n"
            "Our mission is to set the standard for immersive and authentic Greenville roleplay. "
            "We operate with a civilian-first philosophy, dedicated to fostering a professional yet welcoming environment where community feedback directly shapes our evolution.\n\n"
            "Our administrative staff remains at your disposal for any inquiries. "
            "For escalated matters, our community owner is highly accessible and committed to ensuring an exceptional experience for every member.\n\n"
            "Please review the comprehensive resources detailed below, which outline our operational regulations, vehicle policies, and premium booster benefits."
        ),
        color=discord.Color.from_str("#fef1b3")
    )

    info_embed.set_footer(
        text="Greenville Roleplay Society™",
        icon_url=bot.user.display_avatar.url
    )

    await interaction.channel.send(embed=banner_embed)

    await interaction.channel.send(
        embed=info_embed,
        view=ServerInfoView()
    )

    await interaction.response.send_message(
        "Server information panel sent!",
        ephemeral=True
    )
    
    # =====================================
# /role
# =====================================

@bot.tree.command(
    name="role",
    description="Adds or removes a role from a user"
)
@app_commands.describe(
    user="Select the user",
    role="Select the role"
)
async def role(interaction: discord.Interaction, user: discord.Member, role: discord.Role):

    if not any(r.name == "Bot Developer" for r in interaction.user.roles):
        await interaction.response.defer(ephemeral=True)
        return

    if role in user.roles:
        await user.remove_roles(role)
        await interaction.response.send_message(
            f"{role.mention} has been removed from {user.mention}.",
            ephemeral=True
        )
    else:
        await user.add_roles(role)
        await interaction.response.send_message(
            f"{role.mention} has been added to {user.mention}.",
            ephemeral=True
        )

        await send_log(interaction.guild, interaction.user, "/role", f"User: {user.mention}\nRole: {role.mention}")

        # =====================================
# /repaint
# =====================================

@bot.tree.command(
    name="repaint",
    description="Repaints a static or animated emoji"
)
@app_commands.describe(
    emoji="Paste the custom emoji here",
    hex_color="New HEX color, example: #ffb7c5"
)
async def repaint(interaction: discord.Interaction, emoji: str, hex_color: str):

    if not any(role.name == "Bot Developer" for role in interaction.user.roles):
        await interaction.response.defer(ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    if not hex_color.startswith("#") or len(hex_color) != 7:
        await interaction.followup.send(
            "Please use a valid HEX color, example: `#ffb7c5`.",
            ephemeral=True
        )
        return

    match = re.match(r"<(a?):(\w+):(\d+)>", emoji)

    if not match:
        await interaction.followup.send(
            "Please paste a valid custom emoji.",
            ephemeral=True
        )
        return

    is_animated = match.group(1) == "a"
    emoji_name = match.group(2)
    emoji_id = int(match.group(3))

    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)

    file_extension = "gif" if is_animated else "png"
    emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{file_extension}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(emoji_url) as response:
                if response.status != 200:
                    await interaction.followup.send(
                        "Could not download this emoji.",
                        ephemeral=True
                    )
                    return

                image_bytes = await response.read()

        output = io.BytesIO()

        if is_animated:
            image = Image.open(io.BytesIO(image_bytes))

            frames = []
            durations = []

            for frame_index in range(getattr(image, "n_frames", 1)):
                image.seek(frame_index)

                frame = image.convert("RGBA")
                pixels = frame.load()

                for y in range(frame.height):
                    for x in range(frame.width):
                        old_r, old_g, old_b, alpha = pixels[x, y]

                        if alpha > 0:
                            pixels[x, y] = (r, g, b, alpha)

                frames.append(frame.copy())
                durations.append(image.info.get("duration", 100))

            frames[0].save(
                output,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=0,
                disposal=2
            )

        else:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
            pixels = image.load()

            for y in range(image.height):
                for x in range(image.width):
                    old_r, old_g, old_b, alpha = pixels[x, y]

                    if alpha > 0:
                        pixels[x, y] = (r, g, b, alpha)

            image.save(output, format="PNG")

        output.seek(0)
        new_image_bytes = output.read()

        old_emoji = discord.utils.get(interaction.guild.emojis, id=emoji_id)

        if old_emoji is not None:
            try:
                await old_emoji.delete(
                    reason=f"Emoji repainted by {interaction.user}"
                )
            except:
                pass

        new_emoji = await interaction.guild.create_custom_emoji(
            name=emoji_name,
            image=new_image_bytes,
            reason=f"Emoji repainted by {interaction.user}"
        )

        await interaction.followup.send(
            f"Emoji repainted successfully: {new_emoji}",
            ephemeral=True
        )

        await send_log(interaction.guild, interaction.user, "/repaint", f"Emoji: {emoji}\nColor: {hex_color}")

    except Exception as e:
        await interaction.followup.send(
            f"Something went wrong: `{e}`",
            ephemeral=True
        )

# =====================================
# .purge
# =====================================

@bot.command()
async def purge(ctx, amount: int):
    if not is_staff(ctx.author):
        return

    def not_pinned(message):
        return not message.pinned

    await ctx.channel.purge(
        limit=amount + 1,
        check=not_pinned
    )

    await send_log(
    ctx.guild,
    ctx.author,
    ";purge",
    f"Amount: {amount}"
)

bot.run(TOKEN)