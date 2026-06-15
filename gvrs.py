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


class TicketView(discord.ui.View):
    def __init__(self, ticket_type: str, opener_id: int, open_timestamp: int):
        super().__init__(timeout=None)
        self.ticket_type = ticket_type
        self.opener_id = opener_id
        self.open_timestamp = open_timestamp
        self.claimed_by = None

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success)
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

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
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
            view=TicketView(
                self.ticket_type,
                opener.id,
                int(discord.utils.utcnow().timestamp())
            )
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
# .warn / .warnings
# =====================================

WARNINGS_FILE = "warnings.json"
WARNING_CHANNELS = ["staff-input", "hc-input"]
WARNING_DELETE_ROLES = ["High Command", "Senior High Command"]

def load_warnings():
    try:
        with open(WARNINGS_FILE, "r", encoding="utf-8") as file:
            content = file.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_warnings(data):
    with open(WARNINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

def can_delete_warnings(member):
    return any(role.name in WARNING_DELETE_ROLES for role in member.roles)

class WarningDeleteSelect(discord.ui.Select):
    def __init__(self, target_id: str, warnings: list):
        self.target_id = target_id

        options = [
            discord.SelectOption(
                label=f"Warning {index + 1}",
                description=warning["text"][:90],
                value=str(index)
            )
            for index, warning in enumerate(warnings)
        ]

        super().__init__(
            placeholder="Select a warning to delete",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if not can_delete_warnings(interaction.user):
            await interaction.response.defer(ephemeral=True)
            return

        data = load_warnings()
        warnings = data.get(self.target_id, [])
        index = int(self.values[0])

        if index >= len(warnings):
            await interaction.response.send_message(
                "This warning no longer exists.",
                ephemeral=True
            )
            return

        warnings.pop(index)

        if warnings:
            data[self.target_id] = warnings
        else:
            data.pop(self.target_id, None)

        save_warnings(data)

        await send_log(
            interaction.guild,
            interaction.user,
            "Warning Deleted",
            f"Target ID: {self.target_id}\nWarning Number: {index + 1}"
        )

        await interaction.response.send_message(
            "Warning deleted.",
            ephemeral=True
        )

class WarningDeleteDropdownView(discord.ui.View):
    def __init__(self, target_id: str, warnings: list):
        super().__init__(timeout=120)
        self.add_item(WarningDeleteSelect(target_id, warnings))

class WarningDeleteButtonView(discord.ui.View):
    def __init__(self, target_user: discord.User, warnings: list):
        super().__init__(timeout=120)
        self.target_user = target_user
        self.warnings = warnings

    @discord.ui.button(
        label="Delete a Warning",
        style=discord.ButtonStyle.danger
    )
    async def delete_warning_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_delete_warnings(interaction.user):
            await interaction.response.defer(ephemeral=True)
            return

        embed = discord.Embed(
            title="Delete a Warning",
            description=f"**{self.target_user.name}** has **{len(self.warnings)}** warning(s). Select one to delete.",
            color=discord.Color.red()
        )

        await interaction.response.send_message(
            embed=embed,
            view=WarningDeleteDropdownView(str(self.target_user.id), self.warnings),
            ephemeral=True
        )

@bot.command()
async def warn(ctx, user: discord.User, *, warning_text: str):
    if ctx.channel.name not in WARNING_CHANNELS:
        return

    if not is_staff(ctx.author):
        return

    data = load_warnings()
    user_id_str = str(user.id)

    if user_id_str not in data:
        data[user_id_str] = []

    warning = {
        "text": warning_text,
        "moderator": ctx.author.id,
        "time": int(discord.utils.utcnow().timestamp())
    }

    data[user_id_str].append(warning)
    save_warnings(data)

    try:
        dm_embed = discord.Embed(
            description=warning_text,
            color=discord.Color.from_str("#fef1b3")
        )

        dm_embed.set_footer(
            text="Greenville Roleplay Society™",
            icon_url=bot.user.display_avatar.url
        )

        await user.send(embed=dm_embed)

    except:
        pass

    confirm_embed = discord.Embed(
        description=f"✅ **{user.name}** has been warned.",
        color=discord.Color.from_str("#fef1b3")
    )

    await ctx.send(embed=confirm_embed)

    await send_log(
    ctx.guild,
    ctx.author,
    ";warn",
    f"Warned User: {user.mention}\nReason: {warning_text}"
)

@bot.command()
async def warnings(ctx, user: discord.User):
    if ctx.channel.name not in WARNING_CHANNELS:
        return

    if not is_staff(ctx.author):
        return

    data = load_warnings()
    user_id_str = str(user.id)
    warnings = data.get(user_id_str, [])

    if not warnings:
        await ctx.send("This user has no warnings.")
        return

    text = ""

    for index, warning in enumerate(warnings, start=1):
        text += (
            f"**{index}.** {warning['text']}\n\n"
            f"Moderator: <@{warning['moderator']}>\n"
            f"Date: <t:{warning['time']}:D>\n\n"
        )

    embed = discord.Embed(
        title=f"{user.name} has {len(warnings)} warning(s).",
        description=text[:4000],
        color=discord.Color.from_str("#fef1b3")
    )

    view = None

    if can_delete_warnings(ctx.author):
        view = WarningDeleteButtonView(user, warnings)

    await ctx.send(
        embed=embed,
        view=view
    )

    await send_log(
    ctx.guild,
    ctx.author,
    ";warnings",
    f"Viewed warnings for: {user.mention}"
)

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