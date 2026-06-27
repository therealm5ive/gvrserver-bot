import os
import asyncio
import discord
import re
import io
import aiohttp
import sqlite3
import gc
from PIL import Image
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from datetime import datetime, timedelta
from urllib.parse import urlparse

load_dotenv()

TOKEN = os.getenv("TOKEN")

STARTUP_IMAGE = "https://media.discordapp.net/attachments/1479130697800089622/1513461961269182604/Server_-_Embed_-_Session_Startup.png?ex=6a27d0ca&is=6a267f4a&hm=18740e4a1d98af9cc8af01f6215e00389dec33b1369de0e09f4b55488224aed9&=&format=webp&quality=lossless"
SETTINGUP_IMAGE = "https://cdn.discordapp.com/attachments/1479130697800089622/1513567354863485029/Server_-_Embed_-_Setting_Up.png?ex=6a2832f2&is=6a26e172&hm=735140119f487af1ee9610a777452bf0a3dcec125e775b6e1ca9b726c290957e&"
EARLYACCESS_IMAGE = "https://media.discordapp.net/attachments/1479130697800089622/1513461961021587507/Server_-_Embed_-_Early_Access.png?ex=6a27d0ca&is=6a267f4a&hm=6a41537a1ce99096852afcd3353324e350aea59befaf12030ebadd89dff6685f&=&format=webp&quality=lossless"
RELEASE_IMAGE = "https://media.discordapp.net/attachments/1479130697800089622/1513461960761413702/Server_-_Embed_-_Session_Release.png?ex=6a27d0ca&is=6a267f4a&hm=1573b02e59a9bce5bb8427ceb419e5d201a39efaf8162b879671beae398f39dd&=&format=webp&quality=lossless"
OVER_IMAGE = "https://media.discordapp.net/attachments/1479130697800089622/1513461960165822626/Server_-_Embed_-_Session_Concluded.png?ex=6a27d0ca&is=6a267f4a&hm=25d4fdfdca98d0e7dbd789dc00c6a70f81115868bca6862a40bdfb28c7737817&=&format=webp&quality=lossless"
REINVITES_IMAGE = "https://media.discordapp.net/attachments/1479130697800089622/1513461960455356526/Server_-_Embed_-_Session_Reinvites.png?ex=6a27d0ca&is=6a267f4a&hm=eaeca4b95415c2dcd907222657cecd95b77b650619da1e2997eb29169ae1801d&=&format=webp&quality=lossless"
TICKET_PANEL_IMAGE = "https://media.discordapp.net/attachments/1520482344710967316/1520546684210249909/download_39.png?ex=6a4196f3&is=6a404573&hm=1fc370e212b294cc2443e2682c5d3c45c0520feff137fcfec3e2d29ce9c514d2&=&format=webp&quality=lossless"
TICKET_OPEN_IMAGE = "https://media.discordapp.net/attachments/1520482344710967316/1520546684210249909/download_39.png?ex=6a4196f3&is=6a404573&hm=1fc370e212b294cc2443e2682c5d3c45c0520feff137fcfec3e2d29ce9c514d2&=&format=webp&quality=lossless"
WELCOME_IMAGE = "https://media.discordapp.net/attachments/1520482344710967316/1520546686408196096/download_34.png?ex=6a4196f4&is=6a404574&hm=feb2ad8d8d40a157887fa75e6d09d431a3218ef9383221d381b490c8a41d3597&=&format=webp&quality=lossless"
WELCOME_THUMBNAIL = "https://cdn.discordapp.com/attachments/1479130697800089622/1519101482203615323/image.png?ex=6a3c5500&is=6a3b0380&hm=efea340a34ed87dc6bec1a9e6c29cfdd545c6103712621e7046220045ade683e&"
STAFF_INFORMATION_IMAGE = "https://cdn.discordapp.com/attachments/1479130697800089622/1519309639471075468/Server_-_Embed_-_Staff_Information.webp?ex=6a3d16dd&is=6a3bc55d&hm=4dec9cec71bd426376ae543e24e310ca57595d585d114ec10f519e2e4d096fa8&"

EARLYACCESS_ROLE_ID = 1520526497834860747
SERVER_BOOSTER_ROLE_ID = 1520149560750506208
STAFF_TEAM_ROLE_ID = 1520147470909313045
CIVILIANS_ROLE_ID = 1520147861747007528
TICKET_CATEGORY_ID = 1520192391301042287
ROLEPLAY_RESTRICTED_ROLE_ID = 1520556110581338122
WELCOME_CHANNEL_ID = 1519463214264352768
BOOK_EMOJI = "<:GVRSbook:1515852761948749874>"
SUN_EMOJI = "☀️"
PRIMARY_ARROW_EMOJI = "<:GVRSarrow:1513646972106702919>"
YELLOW_ARROW_EMOJI = "<:yellowarrow:1517392101678121040>"
STARTUP_REACTION_EMOJI_ID = 1513524676180054107
STARTUP_REACTION_EMOJI = f"<:GVRScheck:{STARTUP_REACTION_EMOJI_ID}>"

DB_FILE = "bot_data.db"

SESSION_START_TIMES = {}
ACTIVE_COHOSTS = {}
ACTIVE_SUPERVISIONS = {}
ACTIVE_STARTUPS = {}
ACTIVE_HOSTS = {}

ALLOWED_ROLEPLAY_CHANNELS = ["roleplay-1", "bot-testing-dont-remove"]
MAX_TIMEOUT_DURATION = timedelta(days=28)
MAX_EMOJI_DOWNLOAD_BYTES = 2 * 1024 * 1024


def session_key(interaction):
    guild_id = interaction.guild.id if interaction.guild else 0
    return guild_id, interaction.channel.id


def user_session_key(interaction):
    guild_id, channel_id = session_key(interaction)
    return guild_id, channel_id, interaction.user.id


def is_allowed_url(value: str, allowed_hosts=None):
    parsed = urlparse(value.strip())

    if parsed.scheme != "https" or not parsed.netloc:
        return False

    if allowed_hosts is None:
        return True

    hostname = parsed.hostname or ""
    return any(hostname == host or hostname.endswith(f".{host}") for host in allowed_hosts)


async def purge_channels_by_name(guild: discord.Guild, channel_names: set[str], limit: int = 500):
    if not guild:
        return

    for channel in guild.text_channels:
        if channel.name not in channel_names:
            continue

        try:
            await channel.purge(
                limit=limit,
                check=lambda message: not message.pinned
            )
        except (discord.Forbidden, discord.HTTPException):
            pass


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS staff_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            session_type TEXT NOT NULL,
            note TEXT,
            start_timestamp INTEGER NOT NULL,
            end_timestamp INTEGER NOT NULL,
            duration_minutes INTEGER NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            reason TEXT NOT NULL,
            moderator_id TEXT NOT NULL,
            appealable TEXT,
            appeal_time TEXT,
            evidence TEXT,
            timestamp INTEGER NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS active_sessions (
            guild_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            start_timestamp INTEGER NOT NULL,
            PRIMARY KEY (guild_id, channel_id)
        )
    """)

    cur.execute("PRAGMA table_info(active_sessions)")
    active_session_columns = [row["name"] for row in cur.fetchall()]

    if "host_id" not in active_session_columns:
        cur.execute("ALTER TABLE active_sessions ADD COLUMN host_id TEXT")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS active_staff_timers (
            guild_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            timer_type TEXT NOT NULL,
            start_timestamp INTEGER NOT NULL,
            PRIMARY KEY (guild_id, channel_id, user_id, timer_type)
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_staff_sessions_user
        ON staff_sessions(user_id)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_warnings_user_active
        ON warnings(user_id, active)
    """)

    conn.commit()
    conn.close()


def load_active_state():
    ACTIVE_STARTUPS.clear()
    ACTIVE_HOSTS.clear()
    SESSION_START_TIMES.clear()
    ACTIVE_COHOSTS.clear()
    ACTIVE_SUPERVISIONS.clear()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM active_sessions")
    for row in cur.fetchall():
        key = (int(row["guild_id"]), int(row["channel_id"]))
        ACTIVE_STARTUPS[key] = int(row["message_id"])
        SESSION_START_TIMES[key] = row["start_timestamp"]
        if row["host_id"] is not None:
            ACTIVE_HOSTS[key] = int(row["host_id"])

    cur.execute("SELECT * FROM active_staff_timers")
    for row in cur.fetchall():
        key = (int(row["guild_id"]), int(row["channel_id"]), int(row["user_id"]))

        if row["timer_type"] == "cohost":
            ACTIVE_COHOSTS[key] = row["start_timestamp"]
        elif row["timer_type"] == "supervise":
            ACTIVE_SUPERVISIONS[key] = row["start_timestamp"]

    conn.close()


def save_active_session(active_key, message_id, start_timestamp, host_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO active_sessions
        (guild_id, channel_id, message_id, start_timestamp, host_id)
        VALUES (?, ?, ?, ?, ?)
    """, (
        str(active_key[0]),
        str(active_key[1]),
        str(message_id),
        start_timestamp,
        str(host_id)
    ))

    conn.commit()
    conn.close()


def clear_active_session(active_key):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM active_sessions
        WHERE guild_id = ? AND channel_id = ?
    """, (str(active_key[0]), str(active_key[1])))

    conn.commit()
    conn.close()


def save_staff_timer(active_key, timer_type, start_timestamp):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO active_staff_timers
        (guild_id, channel_id, user_id, timer_type, start_timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (
        str(active_key[0]),
        str(active_key[1]),
        str(active_key[2]),
        timer_type,
        start_timestamp
    ))

    conn.commit()
    conn.close()


def clear_staff_timer(active_key, timer_type):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM active_staff_timers
        WHERE guild_id = ? AND channel_id = ? AND user_id = ? AND timer_type = ?
    """, (
        str(active_key[0]),
        str(active_key[1]),
        str(active_key[2]),
        timer_type
    ))

    conn.commit()
    conn.close()


def clear_staff_timers_for_session(active_key):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM active_staff_timers
        WHERE guild_id = ? AND channel_id = ?
    """, (str(active_key[0]), str(active_key[1])))

    conn.commit()
    conn.close()


def add_staff_session(user_id, session_type, note, start_timestamp, end_timestamp):
    duration_minutes = round((end_timestamp - start_timestamp) / 60)

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO staff_sessions
        (user_id, session_type, note, start_timestamp, end_timestamp, duration_minutes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        str(user_id),
        session_type,
        note,
        start_timestamp,
        end_timestamp,
        duration_minutes
    ))

    conn.commit()
    conn.close()

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
        title=command_name,
        color=discord.Color.from_str("#93ffa5")
    )

    embed.add_field(
        name="Executed by",
        value=f"{user.mention}\n`{user.id}`",
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
        text="Greenville Roleplay Server™",
        icon_url=bot.user.display_avatar.url
    )

    await log_channel.send(embed=embed)

class EarlyAccessView(discord.ui.View):
    def __init__(self, link: str):
        super().__init__(timeout=None)
        self.link = link

    @discord.ui.button(label="Early Access Link", style=discord.ButtonStyle.secondary)
    async def early_access_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        allowed_role_ids = {
            EARLYACCESS_ROLE_ID,
            SERVER_BOOSTER_ROLE_ID,
            STAFF_TEAM_ROLE_ID,
        }
        allowed_role_names = {"Early Access", "Server Booster", "Staff Team"}
        has_early_access = any(
            role.id in allowed_role_ids or role.name in allowed_role_names
            for role in interaction.user.roles
        )

        if not has_early_access:
            await interaction.response.send_message(
                "You do not have early access and therefore wait for the release.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(self.link, ephemeral=True)

class ReleaseView(discord.ui.View):
    def __init__(self, link: str, startup_message_id: int, host: str):
        super().__init__(timeout=None)
        self.link = link
        self.startup_message_id = startup_message_id
        self.host = host

    async def user_reacted_to_startup(self, interaction: discord.Interaction) -> bool:
        try:
            startup_message = await interaction.channel.fetch_message(self.startup_message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return False

        for reaction in startup_message.reactions:
            if getattr(reaction.emoji, "id", None) != STARTUP_REACTION_EMOJI_ID:
                continue

            async for user in reaction.users():
                if user.id == interaction.user.id:
                    return True

        return False

    @discord.ui.button(label="Roleplay Link", style=discord.ButtonStyle.secondary)
    async def roleplay_link_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.user_reacted_to_startup(interaction):
            startup_url = (
                f"https://discord.com/channels/"
                f"{interaction.guild.id}/{interaction.channel.id}/{self.startup_message_id}"
            )
            await interaction.response.send_message(
                f"Please react [here]({startup_url}) in order to join {self.host}'s session.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(self.link, ephemeral=True)

class StaffProfileView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = str(user_id)

    async def send_sessions(self, interaction: discord.Interaction, session_type: str, title: str):
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM staff_sessions
            WHERE user_id = ? AND session_type = ?
            ORDER BY end_timestamp DESC
        """, (self.user_id, session_type))

        sessions = cur.fetchall()
        conn.close()


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
                f"Date: <t:{session['end_timestamp']}:f>\n"
                f"Duration: {session['duration_minutes']} minutes\n"
                f"Note: {session['note']}\n\n"
            )

        embed = discord.Embed(
            title=title,
            description=text[:4000],
            color=discord.Color.from_str("#93ffa5")
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


class LOARequestView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def can_handle_loa(self, member):
        return any(role.name == "High Command" for role in member.roles)

    async def finish_loa_request(self, interaction: discord.Interaction, message: str, accepted: bool):
        for item in self.children:
            item.disabled = True
            item.style = discord.ButtonStyle.secondary

            if accepted and item.custom_id == "loa_accept_button":
                item.label = "Accepted"
            elif not accepted and item.custom_id == "loa_deny_button":
                item.label = "Denied"

        await interaction.response.edit_message(view=self)
        await interaction.channel.send(
            message,
            reference=interaction.message,
            allowed_mentions=discord.AllowedMentions(users=True)
        )

    @discord.ui.button(
        label="Accept",
        style=discord.ButtonStyle.success,
        custom_id="loa_accept_button"
    )
    async def accept_loa(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.can_handle_loa(interaction.user):
            await interaction.response.defer()
            return

        await self.finish_loa_request(
            interaction,
            f"{interaction.user.mention} accepted your LOA!",
            True
        )

    @discord.ui.button(
        label="Deny",
        style=discord.ButtonStyle.danger,
        custom_id="loa_deny_button"
    )
    async def deny_loa(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.can_handle_loa(interaction.user):
            await interaction.response.defer()
            return

        await self.finish_loa_request(
            interaction,
            f"{interaction.user.mention} denied your LOA!",
            False
        )


class AnnouncementModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Announcement Message")

        self.text = discord.ui.TextInput(
            label="Message",
            placeholder="Write your message here...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.text)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Command executed!",
            ephemeral=True
        )

        message_text = str(self.text.value)

        await send_log(interaction.guild, interaction.user, "/announcement", f"Text: {message_text}")

        await interaction.channel.send(
            message_text,
            allowed_mentions=discord.AllowedMentions(
                everyone=True,
                roles=True,
                users=True
            )
        )


class SendEmbedModal(discord.ui.Modal):
    def __init__(self, image_url: str = None):
        super().__init__(title="Send Embed")
        self.image_url = image_url

        self.text = discord.ui.TextInput(
            label="Embed message",
            placeholder="Write the embed text here...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000
        )

        self.add_item(self.text)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        message_text = str(self.text.value)

        try:
            if self.image_url:
                image_embed = discord.Embed(color=discord.Color.from_str("#93ffa5"))
                image_embed.set_image(url=self.image_url)
                await interaction.channel.send(embed=image_embed)

            text_embed = discord.Embed(
                description=message_text,
                color=discord.Color.from_str("#93ffa5")
            )

            await interaction.channel.send(embed=text_embed)

            await interaction.followup.send(
                "Embed sent!",
                ephemeral=True
            )

            details = f"Image: {self.image_url or 'None'}\nText: {message_text}"
            await send_log(interaction.guild, interaction.user, "/send embed", details)

        except Exception as e:
            await interaction.followup.send(
                f"Something went wrong while sending the embed: `{e}`",
                ephemeral=True
            )


@bot.event
async def on_ready():
    init_db()
    load_active_state()
    print(f"Logged in as {bot.user}")

    bot.add_view(TicketPanelView())
    bot.add_view(PersistentTicketView())
    bot.add_view(ServerInfoView())
    bot.add_view(LOARequestView())
    bot.add_view(StaffInformationView())

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="🍀 discord.gg/gvrpserver"
        )
    )

    for guild in bot.guilds:
        bot.tree.copy_global_to(guild=guild)
        guild_synced = await bot.tree.sync(guild=guild)
        print(f"{len(guild_synced)} guild commands synchronised for {guild.name}")

    bot.tree.clear_commands(guild=None)
    synced = await bot.tree.sync()
    print(f"{len(synced)} global commands synchronised")

    print(f"{bot.user} is online!")


@bot.event
async def on_member_join(member: discord.Member):
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        description=(
            "> ### <:download_20:1520444814703853666>  **__Welcome to Greenville Roleplay Server__**\n"
            "<:download_15:1520397591500816485>  Welcome to **Greenville Roleplay Server**! In order to become a civilian and gain access to the server, simply verify yourself with **__Bloxlink__** and ensure to read through our **__Regulations & Guidelines__** for necessary information.\n\n"
            "<:download_3:1520445268938461427>  **__Require Assistance?__** Simply reach out to a member of our **__High Command__** team and they will be able to support you!"
        ),
        color=discord.Color.from_str("#93ffa5")
    )

    embed.set_image(url=WELCOME_IMAGE)
    embed.set_footer(
        text="Greenville Roleplay Server™",
        icon_url=bot.user.display_avatar.url
    )

    await channel.send(
        content=f"{SUN_EMOJI} Welcome to Greenville Roleplay Server {member.mention}!",
        embed=embed,
        allowed_mentions=discord.AllowedMentions(users=True)
    )

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

    await interaction.channel.send(
        text,
        allowed_mentions=discord.AllowedMentions(
            everyone=True,
            roles=True,
            users=True
        )
    )


@bot.tree.command(
    name="announcement",
    description="The bot sends a multi-line announcement"
)
async def announcement(interaction: discord.Interaction):
    if not any(
        role.name in ["Senior High Command", "High Command"]
        for role in interaction.user.roles
    ):
        await interaction.response.defer(ephemeral=True)
        return

    await interaction.response.send_modal(AnnouncementModal())


# =====================================
# /send
# =====================================

send_group = app_commands.Group(
    name="send",
    description="Send message tools"
)


@send_group.command(name="embed", description="Send an embed message")
@app_commands.describe(image_url="Optional image URL to send above the text embed")
async def send_embed(interaction: discord.Interaction, image_url: str = None):
    if not any(role.name == "Ownership Team" for role in interaction.user.roles):
        await interaction.response.defer(ephemeral=True)
        return

    if image_url and not is_allowed_url(image_url):
        await interaction.response.send_message(
            "Please provide a valid HTTPS image URL.",
            ephemeral=True
        )
        return

    await interaction.response.send_modal(SendEmbedModal(image_url))


bot.tree.add_command(send_group)

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

    allowed_channels = ALLOWED_ROLEPLAY_CHANNELS
    active_key = session_key(interaction)

    if interaction.channel.name not in allowed_channels:
        await interaction.response.defer(ephemeral=True)
        return

    if reactions <= 0:
        await interaction.response.send_message(
            "Reaction amount must be at least 1.",
            ephemeral=True
        )
        return

    if active_key in ACTIVE_STARTUPS:
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

    await purge_channels_by_name(
        interaction.guild,
        {"roleplay-1", "bot-testing-dont-remove"}
    )

    host = interaction.user.mention

    embed = discord.Embed(
        description=(
            f"> ### <a:yellowmovingbow:1509751680651100230> __Greenville Roleplay Server, Roleplay Startup!__\n"
            f"{PRIMARY_ARROW_EMOJI} {host} is currently hosting a roleplay session.\n\n"
            f"Prior to joining, please ensure to review the server information "
            f"and all roleplay regulations displayed below to avoid potential moderation.\n\n"
            f"<:yellownotification:1509751686179061760> **Roleplay Regulations**\n"
            f"{YELLOW_ARROW_EMOJI} Read over our Restricted Vehicles List to avoid infractions.\n"
            f"{YELLOW_ARROW_EMOJI} Ensure you have registered all of your vehicles.\n"
            f"{YELLOW_ARROW_EMOJI} Ensure you've enabled ROBLOX joins so everyone can invite you.\n\n"
            f"{YELLOW_ARROW_EMOJI} For this roleplay session to commence, we must achieve "
            f"**{reactions}+ reactions** on this startup message."
        ),
        color=discord.Color.from_str("#93ffa5")
    )

    embed.set_image(url=STARTUP_IMAGE)

    embed.set_footer(
    text="Greenville Roleplay Server™",
    icon_url=bot.user.display_avatar.url
)

    message = await interaction.channel.send(
        f"<@&{CIVILIANS_ROLE_ID}>",
        embed=embed
    )

    start_timestamp = int(message.created_at.timestamp())
    SESSION_START_TIMES[active_key] = start_timestamp
    ACTIVE_STARTUPS[active_key] = message.id
    ACTIVE_HOSTS[active_key] = interaction.user.id
    save_active_session(active_key, message.id, start_timestamp, interaction.user.id)

    await message.add_reaction(STARTUP_REACTION_EMOJI)
    await interaction.response.send_message("Startup message executed!", ephemeral=True)
    await send_log(
    interaction.guild,
    interaction.user,
    "/startup"
)

    async def wait_for_reactions():
        while True:
            await asyncio.sleep(5)

            if ACTIVE_STARTUPS.get(active_key) != message.id:
                return

            try:
                updated_message = await interaction.channel.fetch_message(message.id)

                for reaction in updated_message.reactions:
                    if getattr(reaction.emoji, "id", None) == STARTUP_REACTION_EMOJI_ID:
                        count = reaction.count - 1

                        if count >= reactions:
                            setup_embed = discord.Embed(
                                description=(
                                    f"> ### <a:GVRSloading:1513623240004735116> __Roleplay Setting Up!__\n"
                                    f"{PRIMARY_ARROW_EMOJI} {host} is now **setting up** their roleplay session. Please note that it may take the host 5-10 Minutes to release the session. Due to technical issues, it may take even longer.\n\n"
                                ),
                                color=discord.Color.from_str("#93ffa5")
                            )

                            setup_embed.set_image(url=SETTINGUP_IMAGE)

                            setup_embed.set_footer(
                                text="Greenville Roleplay Server™",
                                icon_url=bot.user.display_avatar.url
                            )
                            await interaction.channel.send(embed=setup_embed)
                            
                            try:
                                dm_embed = discord.Embed(
                                    description=(
                                        "Your session startup in **Greenville Roleplay Server** "
                                        "has reached the required reactions and is ready to be released!"
                                    ),
                                    color=discord.Color.from_str("#93ffa5")
                                )

                                dm_embed.set_footer(
                                    text="Greenville Roleplay Server™",
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
    allowed_channels = ALLOWED_ROLEPLAY_CHANNELS
    active_key = session_key(interaction)

    if interaction.channel.name not in allowed_channels:
        await interaction.response.defer(ephemeral=True)
        return

    if active_key not in ACTIVE_STARTUPS:
        await interaction.response.send_message(
        "There is no active startup in this channel.",
        ephemeral=True
        )
        return

    if not is_staff(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    if not is_allowed_url(link):
        await interaction.response.send_message("This is not a valid URL.", ephemeral=True)
        return

    host = interaction.user.mention

    await interaction.channel.send(
        "<@&1290705580046024725> <@&1333516817431265392> <@&1290705579982979178>"
    )

    embed = discord.Embed(
        description=(
            f"> ### <a:yellowtada:1509751747248390175> __Greenville Roleplay Server, Early Access!__\n"
            f"{PRIMARY_ARROW_EMOJI} {host} has now released early access to their roleplay session.\n\n"
            "<:GVRSarrow2:1515852723713474611> Nitro Boosters, Early Access members, and Staff Team members may now join using the button below, "
            "but sharing this link will result in the permanent removal of your Early Access privileges."
        ),
        color=discord.Color.from_str("#93ffa5")
    )

    embed.set_image(url=EARLYACCESS_IMAGE)

    embed.set_footer(
    text="Greenville Roleplay Server™",
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


async def peacetime_status_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> list[app_commands.Choice[str]]:
    options = ["Normal", "Strict", "Off"]
    return [
        app_commands.Choice(name=option, value=option)
        for option in options
        if current.lower() in option.lower()
    ]


async def frp_speeds_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> list[app_commands.Choice[str]]:
    options = ["65", "80", "95"]
    return [
        app_commands.Choice(name=option, value=option)
        for option in options
        if current.lower() in option.lower()
    ]


async def leo_status_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> list[app_commands.Choice[str]]:
    options = ["Offline", "Online"]
    return [
        app_commands.Choice(name=option, value=option)
        for option in options
        if current.lower() in option.lower()
    ]


@bot.tree.command(name="release", description="Sends a roleplay release message")
@app_commands.describe(
    session_link="Enter the roleplay link here",
    peacetime_status="Peacetime status",
    frp_speeds="FRP speed limit",
    leo_status="LEO status"
)
@app_commands.autocomplete(
    peacetime_status=peacetime_status_autocomplete,
    frp_speeds=frp_speeds_autocomplete,
    leo_status=leo_status_autocomplete
)
async def release(
    interaction: discord.Interaction,
    session_link: str,
    peacetime_status: str,
    frp_speeds: str,
    leo_status: str
):
    allowed_channels = ALLOWED_ROLEPLAY_CHANNELS
    active_key = session_key(interaction)

    if interaction.channel.name not in allowed_channels:
        await interaction.response.defer(ephemeral=True)
        return

    if active_key not in ACTIVE_STARTUPS:
        await interaction.response.send_message(
        "There is no active startup in this channel.",
        ephemeral=True
        )
        return

    if not is_staff(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    if not is_allowed_url(session_link):
        await interaction.response.send_message("This is not a valid URL.", ephemeral=True)
        return

    host = interaction.user.mention
    startup_message_id = ACTIVE_STARTUPS[active_key]

    embed = discord.Embed(
        description=(
            f"> ### <a:yellowanimatedstar:1509793309713764432> __Greenville Roleplay Server, Roleplay Released!__\n"
            f"{PRIMARY_ARROW_EMOJI} {host} has now **released** their roleplay session.\n"
            f"Prior to joining, please ensure to review the server information and all the roleplay regulations displayed below.\n\n"

            f"<:yellowrightarrow:1509751702075740191> Session links will be regenerated within five minutes of release, so be sure to join quickly. "
            f"Reinvites will occur every 20-30 minutes, so please do not ask the host for the link.\n\n"

            f"{BOOK_EMOJI} **Roleplay Regulations:**\n"
            f"{YELLOW_ARROW_EMOJI} Session Host: {host}\n"
            f"{YELLOW_ARROW_EMOJI} Peacetime Status: {peacetime_status}\n"
            f"{YELLOW_ARROW_EMOJI} FRP Speedlimit: {frp_speeds}\n"
            f"{YELLOW_ARROW_EMOJI} LEO Status: {leo_status}\n\n"

            f"<:alertbell:1520085233876078803> **Any unauthorized sharing of the link will result in moderation action.**"
        ),
        color=discord.Color.from_str("#93ffa5")
    )

    embed.set_image(url=RELEASE_IMAGE)

    embed.set_footer(
    text="Greenville Roleplay Server™",
    icon_url=bot.user.display_avatar.url
)

    await interaction.channel.send(
        f"<@&{CIVILIANS_ROLE_ID}>",
        embed=embed,
        view=ReleaseView(session_link, startup_message_id, host)
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
    leo_status="LEO status",
    reactions="Required amount of reactions"
)
@app_commands.autocomplete(
    peacetime_status=peacetime_status_autocomplete,
    frp_speeds=frp_speeds_autocomplete,
    leo_status=leo_status_autocomplete
)
async def reinvites(
    interaction: discord.Interaction,
    session_link: str,
    peacetime_status: str,
    frp_speeds: str,
    leo_status: str,
    reactions: int
):

    allowed_channels = ALLOWED_ROLEPLAY_CHANNELS
    active_key = session_key(interaction)

    if interaction.channel.name not in allowed_channels:
        await interaction.response.defer(ephemeral=True)
        return

    if active_key not in ACTIVE_STARTUPS:
        await interaction.response.send_message(
        "There is no active startup in this channel.",
        ephemeral=True
        )
        return

    if not is_staff(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    if not is_allowed_url(session_link):
        await interaction.response.send_message(
            "This is not a valid URL.",
            ephemeral=True
        )
        return

    if reactions < 1:
        await interaction.response.send_message(
            "Reactions must be at least 1.",
            ephemeral=True
        )
        return

    host = interaction.user.mention
    startup_message_id = ACTIVE_STARTUPS[active_key]

    commencing_embed = discord.Embed(
        description=(
            f"> ### <a:GVRSbutterfly:1515852830668357732> __Greenville Roleplay Server, Reinvites Commencing!__\n"
            f"<:GVRSdot:1513624330045493309> {host} is releasing reinvites for their **Greenville Roleplay Server** soon. "
            f"In order to become the session link, the host needs **{reactions}** reactions."
        ),
        color=discord.Color.from_str("#93ffa5")
    )

    commencing_embed.set_image(url=REINVITES_IMAGE)

    commencing_embed.set_footer(
        text="Greenville Roleplay Server™",
        icon_url=bot.user.display_avatar.url
    )

    message = await interaction.channel.send("@here", embed=commencing_embed)
    await message.add_reaction(STARTUP_REACTION_EMOJI)

    async def send_reinvites_message():
        embed = discord.Embed(
            description=(
                f"> ### <a:yellowanimatedstar:1509793309713764432> __Greenville Roleplay Server, Reinvites Released!__\n"
                f"{PRIMARY_ARROW_EMOJI} {host} has released re-invites for their session!\n\n"
                f"<:yellowrightarrow:1509751702075740191> Session links will be regenerated within five minutes of release, so be sure to join quickly. "
                f"Reinvites will occur every 20-30 minutes, so please do not ask the host for the link.\n\n"

                f"{BOOK_EMOJI} **Session Information:**\n"
                f"{YELLOW_ARROW_EMOJI} FRP Speed Limit: **{frp_speeds}**\n"
                f"{YELLOW_ARROW_EMOJI} Peacetime Status: **{peacetime_status}**\n"
                f"{YELLOW_ARROW_EMOJI} LEO Status: **{leo_status}**\n\n"

                f"<:alertbell:1520085233876078803> **Any unauthorized sharing of the link will result in moderation action.**"
            ),
            color=discord.Color.from_str("#93ffa5")
        )

        embed.set_image(url=REINVITES_IMAGE)

        embed.set_footer(
            text="Greenville Roleplay Server™",
            icon_url=bot.user.display_avatar.url
        )

        await interaction.channel.send(
            "@everyone",
            embed=embed,
            view=ReleaseView(session_link, startup_message_id, host)
        )

    async def wait_for_reinvite_reactions():
        while True:
            await asyncio.sleep(5)

            try:
                updated_message = await interaction.channel.fetch_message(message.id)

                for reaction in updated_message.reactions:
                    if getattr(reaction.emoji, "id", None) != STARTUP_REACTION_EMOJI_ID:
                        continue

                    count = reaction.count - 1

                    if count >= reactions:
                        await updated_message.delete()
                        await send_reinvites_message()
                        return

            except Exception as e:
                print(e)
                return

    asyncio.create_task(wait_for_reinvite_reactions())

    await interaction.response.send_message(
        "Reinvites commencing message executed!",
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
    allowed_channels = ALLOWED_ROLEPLAY_CHANNELS
    active_key = session_key(interaction)

    if interaction.channel.name not in allowed_channels:
        await interaction.response.defer(ephemeral=True)
        return

    if active_key not in ACTIVE_STARTUPS:
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
        color=discord.Color.from_str("#93ffa5")
    )

    message = await interaction.channel.send("@here", embed=embed)
    await message.add_reaction(STARTUP_REACTION_EMOJI)

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

    allowed_channels = ALLOWED_ROLEPLAY_CHANNELS

    if interaction.channel.name not in allowed_channels:
        await interaction.response.defer(ephemeral=True)
        return

    if not any(role.name in ["Ownership Team", "Bot Developer"] for role in interaction.user.roles):
        await interaction.response.defer(ephemeral=True)
        return

    active_key = session_key(interaction)
    ACTIVE_STARTUPS.pop(active_key, None)
    ACTIVE_HOSTS.pop(active_key, None)
    SESSION_START_TIMES.pop(active_key, None)
    clear_active_session(active_key)

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
    allowed_channels = ALLOWED_ROLEPLAY_CHANNELS
    active_key = session_key(interaction)
    if interaction.channel.name not in allowed_channels:
        await interaction.response.defer(ephemeral=True)
        return

    if active_key not in ACTIVE_STARTUPS:
        await interaction.response.send_message(
            "There is no active startup in this channel.",
            ephemeral=True
        )
        return

    if not is_staff(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    if ACTIVE_HOSTS.get(active_key) != interaction.user.id:
        await interaction.response.send_message(
            "You are not the host!",
            ephemeral=True
        )
        return

    host = interaction.user.mention
    start_timestamp = SESSION_START_TIMES.get(active_key)

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
        description=(
            f"> ### <a:yellowmovingbow:1509751680651100230> __Greenville Roleplay Server, Roleplay Concluded!__\n"
            f"{PRIMARY_ARROW_EMOJI} {host} has concluded their roleplay session.\n\n"
            f"<:GVRSarrow2:1515852723713474611> Thank you to all civilians who attended. A new session will be hosted shortly by our staff team. "
            f"Please do not harass staff for sessions, or you may face moderation action.\n\n"
            f"<:yellownotification:1509751686179061760> **Roleplay Notes:**\n"
            f"{YELLOW_ARROW_EMOJI} Session Host: {host}\n"
            f"{YELLOW_ARROW_EMOJI} Session Duration: {session_duration}\n"
            f"{YELLOW_ARROW_EMOJI} Additional Notes: {additional_notes}\n\n"
            f"{YELLOW_ARROW_EMOJI} Need to report a user? Please head over to our #server-assistance channel and create a ticket."
        ),
        color=discord.Color.from_str("#93ffa5")
    )

    embed.set_image(url=OVER_IMAGE)

    embed.set_footer(
        text="Greenville Roleplay Server™",
        icon_url=bot.user.display_avatar.url
    )

    await interaction.response.send_message("Over message executed!", ephemeral=True)
    await send_log(
    interaction.guild,
    interaction.user,
    "/over"
)

    await purge_channels_by_name(
        interaction.guild,
        {interaction.channel.name, "checkpoint-1"}
    )

    for cohost_key, cohost_start_timestamp in list(ACTIVE_COHOSTS.items()):
        if cohost_key[:2] != active_key:
            continue

        user_id = cohost_key[2]
        add_staff_session(
            user_id,
            "cohosted",
            f"Automatically ended when session concluded by {interaction.user.display_name}",
            cohost_start_timestamp,
            end_timestamp
        )

        ACTIVE_COHOSTS.pop(cohost_key, None)

    for supervise_key, supervise_start_timestamp in list(ACTIVE_SUPERVISIONS.items()):
        if supervise_key[:2] != active_key:
            continue

        user_id = supervise_key[2]
        add_staff_session(
            user_id,
            "supervised",
            f"Automatically ended when session concluded by {interaction.user.display_name}",
            supervise_start_timestamp,
            end_timestamp
        )

        ACTIVE_SUPERVISIONS.pop(supervise_key, None)

    ACTIVE_STARTUPS.pop(active_key, None)
    ACTIVE_HOSTS.pop(active_key, None)
    SESSION_START_TIMES.pop(active_key, None)
    clear_active_session(active_key)
    clear_staff_timers_for_session(active_key)

    await interaction.channel.send(embed=embed)


force_group = app_commands.Group(
    name="force",
    description="Force session commands"
)


@force_group.command(name="end", description="Force-end the active roleplay session")
async def force_end(interaction: discord.Interaction):
    allowed_channels = ALLOWED_ROLEPLAY_CHANNELS
    active_key = session_key(interaction)

    if interaction.channel.name not in allowed_channels:
        await interaction.response.defer(ephemeral=True)
        return

    if active_key not in ACTIVE_STARTUPS:
        await interaction.response.send_message(
            "There is no active startup in this channel.",
            ephemeral=True
        )
        return

    if not is_high_command(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    host_id = ACTIVE_HOSTS.get(active_key)

    if host_id is None:
        await interaction.response.send_message(
            "Session host could not be found.",
            ephemeral=True
        )
        return

    if host_id == interaction.user.id:
        await interaction.response.send_message(
            "You cannot force-end your own session.",
            ephemeral=True
        )
        return

    host_member = interaction.guild.get_member(host_id)
    host = host_member.mention if host_member else f"<@{host_id}>"
    start_timestamp = SESSION_START_TIMES.get(active_key)

    if start_timestamp:
        end_timestamp = int(discord.utils.utcnow().timestamp())
        session_duration = f"<t:{start_timestamp}:t> - <t:{end_timestamp}:t>"

        add_staff_session(
            host_id,
            "hosted",
            f"Force-ended by {interaction.user.display_name}",
            start_timestamp,
            end_timestamp
        )
    else:
        end_timestamp = int(discord.utils.utcnow().timestamp())
        session_duration = "Unknown"

    embed = discord.Embed(
        description=(
            f"> ### <a:yellowmovingbow:1509751680651100230> __Greenville Roleplay Server, Roleplay Concluded!__\n"
            f"{PRIMARY_ARROW_EMOJI} {interaction.user.mention} has force-ended {host}'s roleplay session.\n\n"
            f"<:GVRSarrow2:1515852723713474611> Thank you to all civilians who attended. A new session will be hosted shortly by our staff team. "
            f"Please do not harass staff for sessions, or you may face moderation action.\n\n"
            f"<:yellownotification:1509751686179061760> **Roleplay Notes:**\n"
            f"{YELLOW_ARROW_EMOJI} Session Host: {host}\n"
            f"{YELLOW_ARROW_EMOJI} Session Duration: {session_duration}\n"
            f"{YELLOW_ARROW_EMOJI} Additional Notes: Force-ended by {interaction.user.mention}\n\n"
            f"{YELLOW_ARROW_EMOJI} Need to report a user? Please head over to our #server-assistance channel and create a ticket."
        ),
        color=discord.Color.from_str("#93ffa5")
    )

    embed.set_image(url=OVER_IMAGE)

    embed.set_footer(
        text="Greenville Roleplay Server™",
        icon_url=bot.user.display_avatar.url
    )

    await interaction.response.send_message("Force end message executed!", ephemeral=True)
    await send_log(
        interaction.guild,
        interaction.user,
        "/force end",
        f"Host: {host}"
    )

    await purge_channels_by_name(
        interaction.guild,
        {interaction.channel.name, "checkpoint-1"}
    )

    for cohost_key, cohost_start_timestamp in list(ACTIVE_COHOSTS.items()):
        if cohost_key[:2] != active_key:
            continue

        user_id = cohost_key[2]
        add_staff_session(
            user_id,
            "cohosted",
            f"Automatically ended when session force-ended by {interaction.user.display_name}",
            cohost_start_timestamp,
            end_timestamp
        )

        ACTIVE_COHOSTS.pop(cohost_key, None)

    for supervise_key, supervise_start_timestamp in list(ACTIVE_SUPERVISIONS.items()):
        if supervise_key[:2] != active_key:
            continue

        user_id = supervise_key[2]
        add_staff_session(
            user_id,
            "supervised",
            f"Automatically ended when session force-ended by {interaction.user.display_name}",
            supervise_start_timestamp,
            end_timestamp
        )

        ACTIVE_SUPERVISIONS.pop(supervise_key, None)

    ACTIVE_STARTUPS.pop(active_key, None)
    ACTIVE_HOSTS.pop(active_key, None)
    SESSION_START_TIMES.pop(active_key, None)
    clear_active_session(active_key)
    clear_staff_timers_for_session(active_key)

    await interaction.channel.send(embed=embed)


bot.tree.add_command(force_group)

# =====================================
# /loa
# =====================================

loa_group = app_commands.Group(
    name="loa",
    description="LOA commands"
)


@loa_group.command(name="request", description="Submit an LOA request")
@app_commands.describe(
    reason="Reason for your LOA",
    start_of_loa="Start of LOA",
    end_of_loa="End of LOA"
)
async def loa_request(
    interaction: discord.Interaction,
    reason: str,
    start_of_loa: str,
    end_of_loa: str
):
    embed = discord.Embed(
        title="__LOA Request__",
        color=discord.Color.from_str("#93ffa5")
    )

    embed.add_field(
        name="User:",
        value=interaction.user.mention,
        inline=False
    )

    embed.add_field(
        name="Reason:",
        value=reason,
        inline=False
    )

    embed.add_field(
        name="Start of LOA:",
        value=start_of_loa,
        inline=False
    )

    embed.add_field(
        name="End of LOA:",
        value=end_of_loa,
        inline=False
    )

    embed.set_footer(
        text="Greenville Roleplay Server™",
        icon_url=bot.user.display_avatar.url
    )

    await interaction.response.send_message(
        embed=embed,
        view=LOARequestView()
    )

    await send_log(
        interaction.guild,
        interaction.user,
        "/loa request",
        f"Reason: {reason}\nStart of LOA: {start_of_loa}\nEnd of LOA: {end_of_loa}"
    )


bot.tree.add_command(loa_group)

# =====================================
# /roleplay
# =====================================

roleplay_group = app_commands.Group(
    name="roleplay",
    description="Roleplay moderation commands"
)


@roleplay_group.command(name="restrict", description="Roleplay restrict a user")
@app_commands.describe(
    user="Select the user",
    time="Restriction duration",
    reason="Reason(s)",
    evidence="Evidence"
)
async def roleplay_restrict(
    interaction: discord.Interaction,
    user: discord.Member,
    time: str,
    reason: str,
    evidence: str
):
    if not is_high_command(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    restricted_role = interaction.guild.get_role(ROLEPLAY_RESTRICTED_ROLE_ID)

    if restricted_role is None:
        await interaction.response.send_message(
            "Roleplay Restricted role was not found.",
            ephemeral=True
        )
        return

    await user.add_roles(
        restricted_role,
        reason=f"Roleplay restricted by {interaction.user}"
    )

    entry = make_entry(
        "Roleplay Restriction",
        reason,
        interaction.user.id,
        "Appealable",
        time,
        evidence
    )

    add_mod_entry(user.id, entry)

    dm_embed = discord.Embed(
        description=(
            "You have been **roleplay restricted** in **Greenville Roleplay Server** for the following reason(s):\n\n"
            f"- {reason}\n\n"
            f"This roleplay restriction is guilty for **{time}**. If you deem this restriction to be false "
            f"please open a ticket via {APPEAL_TICKET_LINK}.\n\n"
            f"Evidence: {evidence}"
        ),
        color=discord.Color.from_str("#93ffa5")
    )

    dm_embed.set_footer(
        text="Greenville Roleplay Server™",
        icon_url=bot.user.display_avatar.url
    )

    try:
        await user.send(embed=dm_embed)
    except:
        pass

    await interaction.response.send_message(
        f"{user.mention} has been roleplay restricted.",
        ephemeral=True
    )

    await send_log(
        interaction.guild,
        interaction.user,
        "/roleplay restrict",
        f"User: {user.mention}\nTime: {time}\nReason: {reason}\nEvidence: {evidence}"
    )


@roleplay_group.command(name="unrestrict", description="Roleplay unrestrict a user")
@app_commands.describe(user="Select the user")
async def roleplay_unrestrict(interaction: discord.Interaction, user: discord.Member):
    if not is_high_command(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    restricted_role = interaction.guild.get_role(ROLEPLAY_RESTRICTED_ROLE_ID)

    if restricted_role is None:
        await interaction.response.send_message(
            "Roleplay Restricted role was not found.",
            ephemeral=True
        )
        return

    if restricted_role in user.roles:
        await user.remove_roles(
            restricted_role,
            reason=f"Roleplay unrestricted by {interaction.user}"
        )

    dm_embed = discord.Embed(
        description=(
            "You have been **roleplay unrestricted** in **Greenville Roleplay Server**.\n\n"
            "Feel free to join our sessions again as usually. You may get roleplay restricted in future "
            "if you break our guidelines again."
        ),
        color=discord.Color.from_str("#93ffa5")
    )

    dm_embed.set_footer(
        text="Greenville Roleplay Server™",
        icon_url=bot.user.display_avatar.url
    )

    try:
        await user.send(embed=dm_embed)
    except:
        pass

    await interaction.response.send_message(
        f"{user.mention} has been roleplay unrestricted.",
        ephemeral=True
    )

    await send_log(
        interaction.guild,
        interaction.user,
        "/roleplay unrestrict",
        f"User: {user.mention}"
    )


bot.tree.add_command(roleplay_group)

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

    active_key = user_session_key(interaction)
    start_timestamp = int(discord.utils.utcnow().timestamp())
    ACTIVE_COHOSTS[active_key] = start_timestamp
    save_staff_timer(active_key, "cohost", start_timestamp)

    embed = discord.Embed(
        description=f"{interaction.user.mention} is **co-hosting** the current session.",
        color=discord.Color.from_str("#93ffa5")
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

    active_key = user_session_key(interaction)

    if active_key not in ACTIVE_COHOSTS:
        await interaction.response.send_message(
            "You have not started a cohost session.",
            ephemeral=True
        )
        return

    start_timestamp = ACTIVE_COHOSTS.pop(active_key)
    clear_staff_timer(active_key, "cohost")
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
        color=discord.Color.from_str("#93ffa5")
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

    active_key = user_session_key(interaction)
    start_timestamp = int(discord.utils.utcnow().timestamp())
    ACTIVE_SUPERVISIONS[active_key] = start_timestamp
    save_staff_timer(active_key, "supervise", start_timestamp)

    embed = discord.Embed(
        description=f"{interaction.user.mention} is **supervising** the current session.",
        color=discord.Color.from_str("#93ffa5")
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

    active_key = user_session_key(interaction)

    if active_key not in ACTIVE_SUPERVISIONS:
        await interaction.response.send_message(
            "You have not started a supervision.",
            ephemeral=True
        )
        return

    start_timestamp = ACTIVE_SUPERVISIONS.pop(active_key)
    clear_staff_timer(active_key, "supervise")
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
        color=discord.Color.from_str("#93ffa5")
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

STAFF_INFORMATION_TEXT = """
> ### <a:blue_flower:1518783617160052909> __Welcome to the Greenville Roleplay Server Staff Team__ <a:blue_flower:1518783617160052909>
Your commitment, professionalism, and leadership are essential to maintaining a safe, organized, and immersive roleplay environment for our community. As a member of the GVRS Staff Team, you represent the standard of conduct and structure that allows our server to operate at a high level. We sincerely appreciate the time and effort you dedicate to supporting GVRS and its members.

<:GVRSarrow2:1515852723713474611> **Notes**
Being a member of the GVRS Staff Team is both a responsibility and a privilege. Your dedication allows Greenville Roleplay Server to continue growing as a structured, professional, and enjoyable community for everyone involved.

Thank you for your continued hard work, leadership, and commitment to excellence.
"""

STAFF_REGULATIONS_TEXT = """
<:GVRSarrow2:1515852723713474611> **Community Safety & Moderation**
Staff members are entrusted with maintaining order and fairness throughout the server. This includes:

<:yellowarrow:1517392101678121040> Enforcing all server and roleplay rules consistently and fairly.
<:yellowarrow:1517392101678121040> Monitoring Discord channels and in-game activity for compliance.
<:yellowarrow:1517392101678121040> Addressing reports, concerns, and rule violations promptly.
<:yellowarrow:1517392101678121040> Ensuring sessions operate smoothly, safely, and without disruption.


<:GVRSarrow2:1515852723713474611> **Support & Communication**
Staff presence plays a key role in preventing issues before they escalate and maintaining a welcoming environment for all members. A critical part of being staff is providing assistance and clear communication to the community. Staff are expected to:

<:yellowarrow:1517392101678121040> Assist members with questions, concerns, or technical issues.
<:yellowarrow:1517392101678121040> Respond to support tickets in a timely and professional manner.
<:yellowarrow:1517392101678121040> Foster a welcoming and respectful atmosphere for new and existing members.
<:yellowarrow:1517392101678121040> Communicate clearly and effectively during roleplay sessions and events.


<:GVRSarrow2:1515852723713474611> **Professional Conduct**
Professional communication reflects the overall quality and structure of GVRS. Staff members must uphold the highest standards of professionalism at all times. This includes:

<:yellowarrow:1517392101678121040> Using staff permissions responsibly and appropriately.
<:yellowarrow:1517392101678121040> Treating all members fairly, equally, and without bias.
<:yellowarrow:1517392101678121040> Following all staff policies, procedures, and internal guidelines.
<:yellowarrow:1517392101678121040> Serving as a positive role model within the community.
"""

STAFF_QUOTA_TEXT = """
<:GVRSarrow2:1515852723713474611> **Staff Quota Requirements**
Your behavior sets the example for how members should conduct themselves. To remain active and in good standing, staff members are required to meet weekly activity quotas based on their rank.

**Low Ranking Staff**
<:yellowarrow:1517392101678121040> 4 sessions per week OR 8 moderation/activity logs per week

**Middle Ranking Staff**
<:yellowarrow:1517392101678121040> 3 sessions per week OR 6 moderation/activity logs per week
<:yellowarrow:1517392101678121040> Assist and guide lower-ranking staff
<:yellowarrow:1517392101678121040> Participate in staff discussions and internal communication

**High-Ranking Staff <:GVRSarrow2:1515852723713474611> Senior High Ranking**
<:yellowarrow:1517392101678121040> 2 hosted sessions per week
<:yellowarrow:1517392101678121040> 4 moderation/activity logs per week
<:yellowarrow:1517392101678121040> Oversee staff performance and address escalated situations
<:yellowarrow:1517392101678121040> Provide support and coordination with Ownership

**Executive Team**
<:yellowarrow:1517392101678121040> Quota exempt
<:yellowarrow:1517392101678121040> Expected to lead by example and ensure overall server stability

<:GVRSarrow2:1515852723713474611> **Missed Quota Policy**
Meeting quota demonstrates reliability, activity, and commitment to the server. Failure to meet quota without an approved Leave of Absence (LOA) may result in:

<:yellowarrow:1517392101678121040> Verbal or written warnings
<:yellowarrow:1517392101678121040> Staff strikes
<:yellowarrow:1517392101678121040> Temporary suspension
<:yellowarrow:1517392101678121040> Demotion for repeated noncompliance

If real-life responsibilities arise, staff are encouraged to submit an LOA in advance. Communication is key, and we understand that availability can change.
"""

SESSION_FORMATS_TEXT_1 = """
> ### <a:GVRDdesolvingheart:1515852981205991627> __Greenville Roleplay Server Session Format__ <a:GVRDdesolvingheart:1515852981205991627>
**(Use in this order)**

**Early Entry:** <a:yellowanimatedstar:1509793309713764432>
```
:A Greetings Early Entry, If you require to be brought, Say !host and assistance will be provided shortly.
```
```
:HA Failure to park up will result in a removal from the session and you will be required to join through Main Release.
```
```
:A Allow me to release the session to all participants else.
```
--------------------------------------------------------------------------------
**Main Release:** <a:yellowretrohearts:1509751711387095172>
```
:A Greetings all, If you require to be brought, Say !host and assistance will be provided shortly.
```
```
:Ha Failure to park up will result in a removal from the session and you may face moderation.
```
```
:A Once Parked, Please wait patiently and attentive while session regulations are being explained.
```
--------------------------------------------------------------------------------
**Roleplay Regulations:** <:GVRSmegaphone:1509751663764705360>
```
:HA Peacetime: Strict/Normal/Peacetime Off. FRP is 65/80/100. HC is (On/Off) Brookmere, Horton and Highway are all closed until further notice.
```
```
:A Law enforcement will be (Active/Inactive) this session.
```
```
:A GVFD will be (Active/Inactive) This session.
```
```
:A DOT Will be (Active/Inactive) This session.
```
"""

SESSION_FORMATS_TEXT_2 = """
```
:HA Fail-Roleplay will NOT be tolerated into GVRS sessions, Watch rotations will commence at random, it is your responsibility as a civilian to stay informed of the session Regulations.
```
```
:M Ensure to refer to roleplay-1 to gather more information about the current session.
```
```
:HA To avoid moderation, Ensure to check the vehicle list to ensure your desired vehicle is permitted into the session.
```
```
:M Allow me to set up the checkpoint.
```
--------------------------------------------------------------------------------
**Checkpoint:** <a:GVRDdesolvingheart:1515852981205991627>
```
:A Staff (On-Duty And Off-Duty) May Come forward as well as Law enforcement and Public services.
```
```
:A Early Entry may come forward, Once approached, ensure to ping [USER].
```
```
:A All remaining participants may come forward, Once approached, ensure to ping [USER].
```
```
:A Checkpoint has been concluded, Enjoy the session. Roadmap/Brookmere autos/Ron's Rivers will be open shortly.
```
**Other** <a:GVRDdesolvingheart:1515852981205991627>
```
:HA Watch Rotations are now in effect, any fail-roleplay that is seen will be dealt with accordingly.
```
```
:HA Vehicle Role-checks are now in effect, If you are caught using a vehicle without the correct roles, you may expect moderation.
```
```
:A Open up some businesses to enhance the roleplay interaction and experience.
```
```
:A Shall we do Daytime, Nighttime or cycle, Input your vote into the roblox chat!
```
```
:A Shall we do Sunny, Overcast, Rainy, Cloudy Or weather lock, Cast your vote into the roblox chat!
```
"""


class StaffInformationSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Staff Regulations",
                description="View staff regulations.",
                emoji=discord.PartialEmoji(name="GVRSarrow", id=1513646972106702919)
            ),
            discord.SelectOption(
                label="Staff Quota Requirements",
                description="View staff quota requirements.",
                emoji=discord.PartialEmoji(name="GVRSarrow", id=1513646972106702919)
            ),
            discord.SelectOption(
                label="Session Formats",
                description="View session formats.",
                emoji=discord.PartialEmoji(name="GVRSarrow", id=1513646972106702919)
            )
        ]

        super().__init__(
            placeholder="Select a option",
            options=options,
            custom_id="staff_information_select"
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Staff Regulations":
            embeds = [
                discord.Embed(
                    description=STAFF_REGULATIONS_TEXT,
                    color=discord.Color.from_str("#93ffa5")
                )
            ]
        elif self.values[0] == "Staff Quota Requirements":
            embeds = [
                discord.Embed(
                    description=STAFF_QUOTA_TEXT,
                    color=discord.Color.from_str("#93ffa5")
                )
            ]
        else:
            embeds = [
                discord.Embed(
                    description=SESSION_FORMATS_TEXT_1,
                    color=discord.Color.from_str("#93ffa5")
                ),
                discord.Embed(
                    description=SESSION_FORMATS_TEXT_2,
                    color=discord.Color.from_str("#93ffa5")
                )
            ]

        for embed in embeds:
            embed.set_footer(
                text="Greenville Roleplay Server™",
                icon_url=bot.user.display_avatar.url
            )

        await interaction.response.send_message(embeds=embeds, ephemeral=True)


class StaffInformationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(StaffInformationSelect())


staff_information_group = app_commands.Group(
    name="information",
    description="Staff information commands"
)


@staff_information_group.command(name="panel", description="Sends the staff information panel")
async def staff_information_panel(interaction: discord.Interaction):
    if not any(role.name in ["Ownership Team", "Bot Developer"] for role in interaction.user.roles):
        await interaction.response.defer(ephemeral=True)
        return

    banner_embed = discord.Embed(color=discord.Color.from_str("#93ffa5"))
    banner_embed.set_image(url=STAFF_INFORMATION_IMAGE)

    info_embed = discord.Embed(
        description=STAFF_INFORMATION_TEXT,
        color=discord.Color.from_str("#93ffa5")
    )

    info_embed.set_footer(
        text="Greenville Roleplay Server™",
        icon_url=bot.user.display_avatar.url
    )

    await interaction.channel.send(embed=banner_embed)
    await interaction.channel.send(embed=info_embed, view=StaffInformationView())

    await interaction.response.send_message(
        "Staff information panel sent!",
        ephemeral=True
    )

    await send_log(interaction.guild, interaction.user, "/staff information panel")


staff_group.add_command(staff_information_group)

@staff_group.command(name="profile", description="Displays a staff profile")
@app_commands.describe(user="Select a staff member")
async def staff_profile(interaction: discord.Interaction, user: discord.Member = None):
    if not is_staff(interaction.user):
        await interaction.response.defer(ephemeral=True)
        return

    if user is None:
        user = interaction.user

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT session_type, COUNT(*) as count
        FROM staff_sessions
        WHERE user_id = ?
        GROUP BY session_type
    """, (str(user.id),))

    counts = {
    "hosted": 0,
    "cohosted": 0,
    "supervised": 0
    }

    for row in cur.fetchall():
        counts[row["session_type"]] = row["count"]

    cur.execute("""
        SELECT COUNT(*) as count
        FROM warnings
        WHERE user_id = ? AND active = 1 AND type LIKE 'Staff Strike%'
    """, (str(user.id),))
    strikes = cur.fetchone()["count"]

    conn.close()

    embed = discord.Embed(
        title="Staff Profile",
        description=(
            f"**User:** {user.mention}\n"
            f"**Strikes:** {strikes}"
        ),
        color=discord.Color.from_str("#93ffa5")
    )

    embed.add_field(
        name="Hosted Sessions:",
        value=f"{counts['hosted']} session(s)",
        inline=True
    )
    embed.add_field(
        name="Co-Hosted Sessions:",
        value=f"{counts['cohosted']} session(s)",
        inline=True
    )
    embed.add_field(
        name="Supervised Sessions:",
        value=f"{counts['supervised']} session(s)",
        inline=True
    )

    if user.avatar:
        embed.set_thumbnail(url=user.avatar.url)

    await interaction.response.send_message(
        embed=embed,
        view=StaffProfileView(user.id)
    )

    await send_log(interaction.guild, interaction.user, "/staff profile", f"Profile: {user.mention}")

@staff_group.command(name="clear", description="Clears all staff profiles")
async def staff_clear(interaction: discord.Interaction):

    if not any(role.name in ["Ownership Team", "Bot Developer"] for role in interaction.user.roles):
        await interaction.response.defer(ephemeral=True)
        return

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM staff_sessions")
    conn.commit()
    conn.close()

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
        await interaction.response.send_message(
            "You do not have permission to use this command.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    current = [
        role for role in user.roles
        if role.name in STAFF_INFRACTION_ROLES
    ]

    if len(current) >= 3:
        await interaction.followup.send(
            "This staff member already has 3 staff strikes.",
            ephemeral=True
        )
        return

    next_number = len(current) + 1

    next_role_name = f"Staff Strike {next_number}/3"
    next_role = discord.utils.get(interaction.guild.roles, name=next_role_name)

    if next_role is None:
        await interaction.followup.send(f"Role `{next_role_name}` was not found.", ephemeral=True)
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
            f"You have received **One** Staff Strike in **Greenville Roleplay Server** for the following reason(s):\n\n"
            f"- {reason}\n\n"
            f"This Strike is **{appealable.value}** in {time}, if you deem this strike to be false please open a ticket via {APPEAL_TICKET_LINK}.\n\n"
            f"Evidence: {evidence}"
        )
    )

    await interaction.followup.send(
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


def get_ticket_info(channel):
    ticket_type = "General Assistance"
    opener_id = None
    open_timestamp = int(discord.utils.utcnow().timestamp())
    claimed_by = None

    if channel.topic:
        for part in channel.topic.split("|"):
            if part.startswith("type="):
                ticket_type = part.replace("type=", "")
            elif part.startswith("opener="):
                try:
                    opener_id = int(part.replace("opener=", ""))
                except:
                    opener_id = None
            elif part.startswith("opened="):
                try:
                    open_timestamp = int(part.replace("opened=", ""))
                except:
                    pass
            elif part.startswith("claimed="):
                try:
                    claimed_by = int(part.replace("claimed=", ""))
                except:
                    claimed_by = None

    return ticket_type, opener_id, open_timestamp, claimed_by


async def update_ticket_topic(channel, ticket_type, opener_id, open_timestamp, claimed_by=None):
    claimed_text = claimed_by if claimed_by else "none"

    await channel.edit(
        topic=f"type={ticket_type}|opener={opener_id}|opened={open_timestamp}|claimed={claimed_text}"
    )


class TicketCloseConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Confirm Close", style=discord.ButtonStyle.danger)
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket_type, opener_id, open_timestamp, claimed_by = get_ticket_info(interaction.channel)
        close_timestamp = int(discord.utils.utcnow().timestamp())

        if opener_id:
            try:
                opener = await bot.fetch_user(opener_id)

                dm_embed = discord.Embed(
                    title="Ticket Closed",
                    description=(
                        f"Hello {opener.mention}, your ticket has been successfully closed by "
                        f"{interaction.user.mention}. We hope our team was able to resolve your issue.\n\n"
                        f"**Closed by**\n{interaction.user.mention}\n\n"
                        f"**Ticket ID**\n{interaction.channel.id}\n\n"
                        f"**Open Date**\n<t:{open_timestamp}:F>\n\n"
                        f"**Close Date**\n<t:{close_timestamp}:F>"
                    ),
                    color=discord.Color.from_str("#93ffa5")
                )

                dm_embed.set_footer(
                    text="Greenville Roleplay Server™",
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

    @discord.ui.button(
        label="Claim",
        style=discord.ButtonStyle.success,
        custom_id="ticket_claim_button"
    )
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket_type, opener_id, open_timestamp, claimed_by = get_ticket_info(interaction.channel)

        if ticket_type == "Staff Report":
            allowed = any(role.name in HIGH_COMMAND_ROLE_NAMES for role in interaction.user.roles)
        else:
            allowed = any(role.name == STAFF_ROLE_NAME for role in interaction.user.roles)

        if not allowed:
            await interaction.response.defer(ephemeral=True)
            return

        if claimed_by is None:
            await update_ticket_topic(
                interaction.channel,
                ticket_type,
                opener_id,
                open_timestamp,
                interaction.user.id
            )

            button.label = "Unclaim"
            button.style = discord.ButtonStyle.danger

            await interaction.response.edit_message(view=self)

            embed = discord.Embed(
                description=f"{interaction.user.mention} claimed this ticket.",
                color=discord.Color.from_str("#93ffa5")
            )

            await interaction.channel.send(embed=embed)
            return

        if claimed_by != interaction.user.id:
            await interaction.response.send_message(
                "Only the user who claimed this ticket can unclaim it.",
                ephemeral=True
            )
            return

        await update_ticket_topic(
            interaction.channel,
            ticket_type,
            opener_id,
            open_timestamp,
            None
        )

        button.label = "Claim"
        button.style = discord.ButtonStyle.success

        await interaction.response.edit_message(view=self)

        embed = discord.Embed(
            description=f"{interaction.user.mention} unclaimed this ticket.",
            color=discord.Color.from_str("#93ffa5")
        )

        await interaction.channel.send(embed=embed)

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_close_button"
    )
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
            color=discord.Color.from_str("#93ffa5")
        )

        await interaction.response.send_message(
            embed=embed,
            view=TicketCloseConfirmView(),
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
        open_timestamp = int(discord.utils.utcnow().timestamp())

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
            topic=f"type={self.ticket_type}|opener={opener.id}|opened={open_timestamp}|claimed=none",
            reason=f"{self.ticket_type} ticket opened by {opener}"
        )

        banner_embed = discord.Embed(color=discord.Color.from_str("#93ffa5"))
        banner_embed.set_image(url=TICKET_OPEN_IMAGE)

        embed = discord.Embed(
            description=(
                f"> ### __Greenville Roleplay Server, {self.ticket_type} Ticket__\n"
                f"Thank you for opening a **{self.ticket_type} Ticket**.\n\n"
                f"**Reason for Opening:** {self.reason.value}\n"
                f"**Additional Information:** {self.additional_info.value or 'None'}\n\n"
                f"Please provide any further details that may help our staff team assist you."
            ),
            color=discord.Color.from_str("#93ffa5")
        )

        embed.set_footer(
            text="Greenville Roleplay Server™",
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
                emoji=discord.PartialEmoji(name="arrow", id=1520566971777810463)
            ),
            discord.SelectOption(
                label="Civilian Report",
                description="Report a Civilian within GVRS.",
                emoji=discord.PartialEmoji(name="arrow", id=1520566971777810463)
            ),
            discord.SelectOption(
                label="Staff Report",
                description="Report a staff member in GVRS.",
                emoji=discord.PartialEmoji(name="arrow", id=1520566971777810463)
            ),
            discord.SelectOption(
                label="Partnership",
                description="Open a Partnership ticket.",
                emoji=discord.PartialEmoji(name="arrow", id=1520566971777810463)
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

    await interaction.response.defer(ephemeral=True)

    embed = discord.Embed(
        description=(
            "> ### <:download_19:1520399271776485516>  **__Greenville Roleplay Server™, Support Directory__**\n"
            "<:arrow:1520566971777810463> Welcome to the Greenville Roleplay Server™, Support Directory! This channel allows you to request assistance, such as General Support, Staff Report, or a Civilian Report. If you are facing any issues within the server, please do not hesitate to make a ticket below!\n\n"
            "**__General Assistance:__**\n"
            "<:download_15:1520397591500816485>  Use this support ticket to ask questions about rules or sessions. You may also use this ticket to Request Partnerships, Claim Perks, or for Application Requests. This is not to be used to report someone, as there are other tickets to use that for.\n\n"
            "**__Civilian Report:__**\n"
            "<:download_15:1520397591500816485> Use this to report a Civilian who might be breaking the rules. Make sure to gather proof as it is necessary so that the server High Command Team can take action, depending on the severity. If further support is needed, please request the Staff Member to assist you further.\n\n"
            "**__Staff Report:__**\n"
            "<:download_15:1520397591500816485>  Use this to report a Staff Member who might be breaking the rules. Make sure to gather proof as it is necessary so that the server High Command Team can take action, depending on the severity. If further support is needed, please request the High Command Member to assist you further.\n\n"
            "**__Partnership:__**\n"
            "<:download_15:1520397591500816485>  Use this ticket if you are looking to partner with Greenville Roleplay Server.\n\n"
            "<:download_3:1520445268938461427>  **Please Note:** If you do not respond to your ticket within 24 Hours, it will be automatically closed. Processing your support tickets may take between 2-3 Hours."
        ),
        color=discord.Color.from_str("#93ffa5")
    )

    embed.set_image(url=TICKET_PANEL_IMAGE)
    embed.set_footer(
        text="Greenville Roleplay Server™",
        icon_url=bot.user.display_avatar.url
    )

    await interaction.channel.send(
        embed=embed,
        view=TicketPanelView()
    )

    await interaction.followup.send(
        "Ticket panel sent!",
        ephemeral=True
    )

    # =====================================
# Moderation System
# /infract /mute /modlogs /warnings /ban /suspend /terminate
# =====================================

APPEAL_TICKET_LINK = "https://discord.com/channels/1290705579953754163/1503269938624856156"

STAFF_TEAM_ROLE = "Staff Team"
HIGH_COMMAND_ROLES = ["High Command", "Senior High Command", "Senior High Ranking"]

INFRACTION_ROLES = ["Infraction 1/4", "Infraction 2/4", "Infraction 3/4", "Infraction 4/4"]
STAFF_INFRACTION_ROLES = ["Staff Strike 1/3", "Staff Strike 2/3", "Staff Strike 3/3"]

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

def make_entry(entry_type, reason, moderator_id, appealable, appeal_time, evidence):
    return {
        "type": entry_type,
        "reason": reason,
        "moderator": str(moderator_id),
        "appealable": appealable,
        "appeal_time": appeal_time,
        "evidence": evidence,
        "timestamp": int(discord.utils.utcnow().timestamp())
    }


def add_mod_entry(user_id, entry):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO warnings
        (
            user_id,
            type,
            reason,
            moderator_id,
            appealable,
            appeal_time,
            evidence,
            timestamp,
            active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (
        str(user_id),
        entry["type"],
        entry["reason"],
        str(entry["moderator"]),
        entry["appealable"],
        entry["appeal_time"],
        entry["evidence"],
        entry["timestamp"]
    ))

    conn.commit()
    conn.close()

async def send_mod_dm(user, title, description):
    embed = discord.Embed(
        description=description,
        color=discord.Color.from_str("#93ffa5")
    )

    embed.set_footer(
        text="Greenville Roleplay Server",
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
        "Infraction 1": "Infraction 1/4",
        "Infraction 2": "Infraction 2/4",
        "Infraction 3": "Infraction 3/4",
        "Infraction 4": "Infraction 4/4",
    }

    staff_strike_roles = {
        "Staff Strike 1": "Staff Strike 1/3",
        "Staff Strike 2": "Staff Strike 2/3",
        "Staff Strike 3": "Staff Strike 3/3",
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
                    value=str(warning["id"])
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

        warning_id = int(self.values[0])

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM warnings
            WHERE id = ? AND user_id = ? AND active = 1
        """, (warning_id, str(self.target.id)))

        removed_warning = cur.fetchone()

        if removed_warning is None:
            conn.close()
            await interaction.response.send_message(
                "This warning no longer exists.",
                ephemeral=True
            )
            return

        cur.execute("""
            UPDATE warnings
            SET active = 0
            WHERE id = ?
        """, (warning_id,))

        conn.commit()
        conn.close()

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

    await interaction.response.defer(ephemeral=True)

    target = await get_target(interaction.guild, user)

    if target is None or not isinstance(target, discord.Member):
        await interaction.followup.send("User was not found in this server.", ephemeral=True)
        return

    if is_staff_team(target):
        await interaction.followup.send(
            "Staff Team members cannot be infracted. Use `/staff strike` instead.",
            ephemeral=True
        )
        return

    current = [role for role in target.roles if role.name in INFRACTION_ROLES]

    if len(current) >= 4:
        await interaction.followup.send(
            "User has 4 infractions, roleplay restrict the user.",
            ephemeral=True
        )
        return

    next_number = len(current) + 1
    next_role_name = f"Infraction {next_number}/4"
    next_role = discord.utils.get(interaction.guild.roles, name=next_role_name)

    if next_role is None:
        await interaction.followup.send(f"Role `{next_role_name}` was not found.", ephemeral=True)
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
            f"You have been **Infracted {next_number} Time** in **Greenville Roleplay Server** for the following reason(s):\n\n"
            f"- {reason}\n\n"
            f"This infraction is **{appealable.value}** in {time}, if you deem this infraction to be false please open a ticket via {APPEAL_TICKET_LINK}.\n\n"
            f"Evidence: {evidence}"
        )
    )

    msg = f"{target.mention} has received **Infraction {next_number}**."

    if next_number == 4:
        msg += "\nThis user has now reached 4 infractions. User needs to be roleplay restricted."

    await interaction.followup.send(msg, ephemeral=True)

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

    if minutes < 0 or hours < 0:
        await interaction.response.send_message("Duration cannot be negative.", ephemeral=True)
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

    if duration > MAX_TIMEOUT_DURATION:
        await interaction.response.send_message("Discord timeouts cannot be longer than 28 days.", ephemeral=True)
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
            f"You have been **Banned** from **Greenville Roleplay Server** for the following reason(s):\n\n"
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
            f"You have been **Suspended** from the **Greenville Roleplay Server** Staff Team for the following reason(s):\n\n"
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
            f"You have been **Terminated** from the **Greenville Roleplay Server** Staff Team for the following reason(s):\n\n"
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

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM warnings
        WHERE user_id = ? AND active = 1
        ORDER BY timestamp ASC
    """, (str(target.id),))

    warnings_list = cur.fetchall()
    conn.close()

    if not warnings_list:
        await interaction.response.send_message("This user has no warnings.", ephemeral=True)
        return

    text = ""

    for warning in warnings_list:
        if warning["type"].startswith("Infraction"):
            number = warning["type"].replace("Infraction ", "")
            text += (
                f"**Moderator:** <@{warning['moderator_id']}>\n"
                f"You have been **Infracted {number} Time** in **Greenville Roleplay Server** for the following reason(s):\n\n"
                f"- {warning['reason']}\n\n"
                f"This infraction is **{warning['appealable']}** in {warning['appeal_time']}, if you deem this infraction to be false "
                f"please open a ticket via {APPEAL_TICKET_LINK}.\n\n"
                f"Evidence: {warning['evidence']} - <t:{warning['timestamp']}:R>\n\n"
            )

        elif warning["type"].startswith("Staff Strike"):
            text += (
                f"**Moderator:** <@{warning['moderator_id']}>\n"
                f"You have received **One** Staff Strike in **Greenville Roleplay Server** for the following reason(s):\n\n"
                f"- {warning['reason']}\n\n"
                f"This Strike is **{warning['appealable']}** in {warning['appeal_time']}, if you deem this strike to be false "
                f"please open a ticket via {APPEAL_TICKET_LINK}.\n\n"
                f"Evidence: {warning['evidence']} - <t:{warning['timestamp']}:R>\n\n"
            )

        elif warning["type"] == "Suspension":
            text += (
                f"**Moderator:** <@{warning['moderator_id']}>\n"
                f"You have been **Suspended** from the **Greenville Roleplay Server** Staff Team for the following reason(s):\n\n"
                f"- {warning['reason']}\n\n"
                f"This Suspension is **{warning['appealable']}** in {warning['appeal_time']}, if you deem this suspension to be false "
                f"please open a ticket via {APPEAL_TICKET_LINK}.\n\n"
                f"Evidence: {warning['evidence']} - <t:{warning['timestamp']}:R>\n\n"
            )

        elif warning["type"] == "Termination":
            text += (
                f"**Moderator:** <@{warning['moderator_id']}>\n"
                f"You have been **Terminated** from the **Greenville Roleplay Server** Staff Team for the following reason(s):\n\n"
                f"- {warning['reason']}\n\n"
                f"This Termination is **{warning['appealable']}** in {warning['appeal_time']}.\n\n"
                f"Evidence: {warning['evidence']} - <t:{warning['timestamp']}:R>\n\n"
            )

        elif warning["type"] == "Ban":
            text += (
                f"**Moderator:** <@{warning['moderator_id']}>\n"
                f"You have been **Banned** from **Greenville Roleplay Server** for the following reason(s):\n\n"
                f"- {warning['reason']}\n\n"
                f"If you deem this ban to be false, feel free to appeal it with the appeal listed below.\n"
                f"Appeal: Soon.\n\n"
                f"Evidence: {warning['evidence']} - <t:{warning['timestamp']}:R>\n\n"
            )

        elif warning["type"] == "Roleplay Restriction":
            text += (
                f"**Moderator:** <@{warning['moderator_id']}>\n"
                f"You have been **roleplay restricted** in **Greenville Roleplay Server** for the following reason(s):\n\n"
                f"- {warning['reason']}\n\n"
                f"This roleplay restriction is guilty for **{warning['appeal_time']}**. If you deem this restriction to be false "
                f"please open a ticket via {APPEAL_TICKET_LINK}.\n\n"
                f"Evidence: {warning['evidence']} - <t:{warning['timestamp']}:R>\n\n"
            )

    embed = discord.Embed(
        title=f"{len(warnings_list)} Warning{'s' if len(warnings_list) != 1 else ''} for {target} ({target.id})",
        description=text[:4000],
        color=discord.Color.from_str("#93ffa5")
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

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM warnings
        WHERE user_id = ?
        ORDER BY timestamp ASC
    """, (str(target.id),))

    logs = cur.fetchall()
    conn.close()

    if not logs:
        await interaction.response.send_message("This user has no modlogs.", ephemeral=True)
        return

    text = ""

    for log in logs:
        text += (
            f"**{log['type']}**\n"
            f"Reason: {log['reason']}\n"
            f"Moderator: <@{log['moderator_id']}>\n"
            f"Date: <t:{log['timestamp']}:F>\n"
            f"Evidence: {log['evidence']}\n\n"
        )

    embed = discord.Embed(
        title=f"Modlogs for {target}",
        description=text[:4000],
        color=discord.Color.from_str("#93ffa5")
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

# =====================================
# /membercount
# =====================================

@bot.tree.command(name="membercount", description="Shows the current member count")
async def membercount(interaction: discord.Interaction):
    if not any(role.name == "Ownership Team" for role in interaction.user.roles):
        await interaction.response.defer(ephemeral=True)
        return

    timestamp = int(discord.utils.utcnow().timestamp())

    embed = discord.Embed(
        title=f"{interaction.guild.member_count} Members",
        description=f"<t:{timestamp}:f>",
        color=discord.Color.from_str("#93ffa5")
    )

    await interaction.response.send_message(embed=embed)

    await send_log(interaction.guild, interaction.user, "/membercount")

    # =====================================
# /serverinfo
# =====================================

SERVER_INFO_IMAGE = "https://cdn.discordapp.com/attachments/1479130697800089622/1513908128557695098/Server_-_Embed_-_Regulations.webp?ex=6a3d36d0&is=6a3be550&hm=2b34b49689c50a78db9ad5d5372699bec636df5f9b8dd8243cdfc5f8085646b4&"

ROBLOX_GROUP_LINK = "https://www.roblox.com/communities/650527738/Official-Greenville-Roleplay-Server#!/about"
RESTRICTED_VEHICLES_LINK = "https://docs.google.com/spreadsheets/d/1ahcV0bVi62XDg6rRYaEpGgFQV3_85_BPcwqXO-EVoVs/edit?gid=16420916#gid=16420916"

SERVER_GUIDELINES_TEXT = """
**1. <:GVRSarrow:1513646972106702919> Read the Regulations**
All Greenville Roleplay Server members must read and acknowledge the regulations listed in our information channels. Failure to comply may result in serious consequences.

**2. <:GVRSarrow:1513646972106702919> Follow All Staff Instructions**
Members are required to follow directions given by staff. For example, if instructed to leave a session, you must comply immediately.


**3. <:GVRSarrow:1513646972106702919> Exercise Common Sense**
Use sound judgment when determining whether actions violate the rules. If it would be unacceptable in another community, it is not acceptable here.

**4. <:GVRSarrow:1513646972106702919> Age Requirement (13+)**
In accordance with Discord's Terms of Service, all members must be at least 13 years old. Anyone found under this age will be removed until they meet the requirement.

**5. <:GVRSarrow:1513646972106702919> No Harassment or Personal Attacks**
Any form of harassment or targeting of other members is prohibited. Violations may result in timeouts, strikes, or removal from the community.

**6. <:GVRSarrow:1513646972106702919> No Slurs or Offensive Remarks**
Use of discriminatory language or offensive comments based on race, gender identity, weight, ethnicity, or similar factors is strictly forbidden.

**7. <:GVRSarrow:1513646972106702919> No Advertising**
Advertising of any kind is prohibited, including direct messages and public channels. Any server found recruiting Greenville Roleplay Server members or staff will be blacklisted, and involved members will be removed.

**8. <:GVRSarrow:1513646972106702919> No Resource Theft**
Stealing any Greenville Roleplay Server resources, such as announcements, documentation or any other assets will lead to an immediate ban from Greenville Roleplay Server and all affiliated servers.

**9. <:GVRSarrow:1513646972106702919> No Sharing of Personal Information**
Leaking, doxxing, or otherwise sharing personal information about any member will result in an immediate and permanent ban.

**10. <:GVRSarrow:1513646972106702919> No NSFW Content**
Posting or distributing not safe for work material, including pornography, gore, or violent imagery, is strictly prohibited. First offense results in a warning, although the second offense results in an immediate ban.

**11. <:GVRSarrow:1513646972106702919> Maintain Respect**
Greenville Roleplay Server will not tolerate any disrespect, defamatory comments or complaints about Greenville Roleplay Server or affiliated communities. Any user found being disrespectful will be moderated.

**12. <:GVRSarrow:1513646972106702919> Voice Channel Conduct**
All rules apply in voice channels. Excessive noise, disruptive sounds, or "ear-rape" audio is prohibited and will result in disciplinary action.
"""

class ServerInfoSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Server Guidelines",
                description="View the server guidelines.",
                emoji=discord.PartialEmoji(name="GVRSarrow", id=1513646972106702919)
            ),
            discord.SelectOption(
                label="Roblox Group",
                description="Get the official Roblox group link.",
                emoji=discord.PartialEmoji(name="GVRSarrow", id=1513646972106702919)
            ),
            discord.SelectOption(
                label="Restricted Vehicles List",
                description="View the restricted vehicles list.",
                emoji=discord.PartialEmoji(name="GVRSarrow", id=1513646972106702919)
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
                description=(
                    "> ### <a:GVRSbutterfly:1515852789266518056> __Greenville Roleplay Server, Server Guidelines__ <a:GVRSbutterfly:1515852789266518056>\n"
                    f"{SERVER_GUIDELINES_TEXT}"
                ),
                color=discord.Color.from_str("#93ffa5")
            )

        elif choice == "Roblox Group":
            embed = discord.Embed(
                description=f"Klick [here]({ROBLOX_GROUP_LINK}) to join our roblox group.",
                color=discord.Color.from_str("#93ffa5")
            )

        else:
            embed = discord.Embed(
                description=f"Klick [here]({RESTRICTED_VEHICLES_LINK}) to view our Restricted Vehicles list.",
                color=discord.Color.from_str("#93ffa5")
            )

        embed.set_footer(
            text="Greenville Roleplay Server™",
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

    if not any(role.name == "Ownership Team" for role in interaction.user.roles):
        await interaction.response.defer(ephemeral=True)
        return

    banner_embed = discord.Embed(color=discord.Color.from_str("#93ffa5"))
    banner_embed.set_image(url=SERVER_INFO_IMAGE)

    info_embed = discord.Embed(
        description=(
            "<:download_19:1520399271776485516>  **__Greenville Roleplay Server — Opening Remarks__**\n"
            " <:download_15:1520397591500816485> Welcome to Greenville Roleplay Server, a third-party **Greenville Roleplay Server** dedicated to delivering a smooth, realistic, and enjoyable civilian-based roleplay experience within Greenville, Wisconsin. Proudly bringing roleplay to over 20 members, we strive to create an engaging and welcoming community for everyone.\n\n"
            "  <:download_17:1520399162062016615> Established in 2026 and founded by <@1472547347383718105>  and @zion_streax , this community was created for players who enjoy immersive, high-quality roleplay and a welcoming environment. Through active sessions and community interaction, we aim to bring the world of Greenville Roleplay to life in an engaging and realistic way.\n\n"
            " <:download_17:1520399162062016615> Before getting started, please take a moment to review the information available in the dropdown menu below. It includes key details about our community and helpful resources to ensure a smooth and enjoyable experience.\n\n"
            "Greenville Roleplay Server™"
        ),
        color=discord.Color.from_str("#93ffa5")
    )

    info_embed.set_footer(
        text="Greenville Roleplay Server™",
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
    description="Gives Ownership Team to a Bot Developer"
)
async def role(interaction: discord.Interaction):

    if not any(r.name == "Bot Developer" for r in interaction.user.roles):
        await interaction.response.defer(ephemeral=True)
        return

    ownership_role = discord.utils.get(interaction.guild.roles, name="Ownership Team")

    if ownership_role is None:
        await interaction.response.send_message(
            "Ownership Team role was not found.",
            ephemeral=True
        )
        return

    if ownership_role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "I cannot manage the Ownership Team role because it is higher than or equal to my highest role.",
            ephemeral=True
        )
        return

    if ownership_role in interaction.user.roles:
        await interaction.response.send_message(
            f"You already have {ownership_role.mention}.",
            ephemeral=True
        )
        return

    await interaction.user.add_roles(
        ownership_role,
        reason=f"Ownership Team role granted by /role to {interaction.user}"
    )

    await interaction.response.send_message(
        f"{ownership_role.mention} has been added to you.",
        ephemeral=True
    )

    await send_log(
        interaction.guild,
        interaction.user,
        "/role",
        f"Added Ownership Team to {interaction.user.mention}"
    )

        # =====================================
# /repaint
# =====================================

@bot.tree.command(
    name="repaint",
    description="Repaints a static or animated emoji"
)
@app_commands.describe(
    emojis="Paste one or more custom emojis here",
    hex="New HEX color without #, example: ffb7c5",
    image="Optional image to turn into an emoji",
    image_2="Optional second image",
    image_3="Optional third image",
    image_4="Optional fourth image",
    image_5="Optional fifth image"
)
async def repaint(
    interaction: discord.Interaction,
    emojis: str = "",
    hex: str = "",
    image: discord.Attachment = None,
    image_2: discord.Attachment = None,
    image_3: discord.Attachment = None,
    image_4: discord.Attachment = None,
    image_5: discord.Attachment = None
):

    ALLOWED_REPAINT_ROLES = [
        "Bot Developer",
        "Ownership Team"
    ]

    if not any(role.name in ALLOWED_REPAINT_ROLES for role in interaction.user.roles):
        await interaction.response.send_message(
            "You do not have permission to use this command.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    try:
        await interaction.followup.send(
            "Repainting emoji, please wait...",
            ephemeral=True
        )
    except:
        pass

    async def safe_reply(message: str):
        message = message[:1900]

        try:
            await interaction.followup.send(message, ephemeral=True)
        except:
            try:
                await interaction.user.send(message)
            except:
                pass

    hex_color = hex.strip().lstrip("#")

    if not re.fullmatch(r"[0-9a-fA-F]{6}", hex_color):
        await safe_reply("Please use a valid HEX color without `#`, example: `ffb7c5`.")
        return

    attachments = [
        attachment for attachment in [image, image_2, image_3, image_4, image_5]
        if attachment is not None
    ]
    emoji_matches = []
    seen_emoji_ids = set()

    for match in re.finditer(r"<(a?):(\w+):(\d+)>", emojis or ""):
        emoji_id = int(match.group(3))

        if emoji_id in seen_emoji_ids:
            continue

        seen_emoji_ids.add(emoji_id)
        emoji_matches.append(match)

    if not emoji_matches and not attachments:
        await safe_reply("Please provide at least one custom emoji or image.")
        return

    target_r = int(hex_color[0:2], 16)
    target_g = int(hex_color[2:4], 16)
    target_b = int(hex_color[4:6], 16)

    def repaint_pixel(old_r, old_g, old_b, alpha):
        if alpha == 0:
            return old_r, old_g, old_b, alpha

        luminance = (0.299 * old_r + 0.587 * old_g + 0.114 * old_b) / 255

        if luminance < 0.5:
            shade = 0.35 + 0.65 * (luminance / 0.5)
            new_r = int(target_r * shade)
            new_g = int(target_g * shade)
            new_b = int(target_b * shade)
        else:
            highlight = ((luminance - 0.5) / 0.5) * 0.75
            new_r = int(target_r + (255 - target_r) * highlight)
            new_g = int(target_g + (255 - target_g) * highlight)
            new_b = int(target_b + (255 - target_b) * highlight)

        return new_r, new_g, new_b, alpha

    def sanitize_emoji_name(name: str, fallback: str):
        clean_name = re.sub(r"\W+", "_", name.rsplit(".", 1)[0]).strip("_")
        clean_name = clean_name[:32]

        if len(clean_name) < 2:
            clean_name = fallback

        return clean_name

    def process_emoji_image(image_bytes):
        output = io.BytesIO()
        image = Image.open(io.BytesIO(image_bytes))
        frame_count = getattr(image, "n_frames", 1)
        is_animated = frame_count > 1

        if is_animated:
            frames = []
            durations = []

            for frame_index in range(frame_count):
                image.seek(frame_index)

                frame = image.convert("RGBA")

                if frame.width > 128 or frame.height > 128:
                    frame.thumbnail((128, 128), Image.LANCZOS)

                pixels = frame.load()

                for y in range(frame.height):
                    for x in range(frame.width):
                        old_r, old_g, old_b, alpha = pixels[x, y]
                        pixels[x, y] = repaint_pixel(old_r, old_g, old_b, alpha)

                frames.append(frame.copy())
                durations.append(image.info.get("duration", 100))

            frames[0].save(
                output,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=0,
                disposal=2,
                optimize=True
            )

        else:
            image = image.convert("RGBA")

            if image.width > 128 or image.height > 128:
                image.thumbnail((128, 128), Image.LANCZOS)

            pixels = image.load()

            for y in range(image.height):
                for x in range(image.width):
                    old_r, old_g, old_b, alpha = pixels[x, y]
                    pixels[x, y] = repaint_pixel(old_r, old_g, old_b, alpha)

            image.save(output, format="PNG", optimize=True)

        output.seek(0)
        return output.read()

    def make_repaint_preview(before_bytes, after_bytes):
        def first_frame(image_bytes):
            image = Image.open(io.BytesIO(image_bytes))
            image.seek(0)
            frame = image.convert("RGBA")
            frame.thumbnail((128, 128), Image.LANCZOS)
            return frame

        before = first_frame(before_bytes)
        after = first_frame(after_bytes)
        preview = Image.new("RGBA", (380, 160), (35, 35, 40, 255))

        before_x = 95 - before.width // 2
        after_x = 265 - after.width // 2
        before_y = 80 - before.height // 2
        after_y = 80 - after.height // 2

        preview.alpha_composite(before, (before_x, before_y))
        preview.alpha_composite(after, (after_x, after_y))

        output = io.BytesIO()
        preview.save(output, format="PNG", optimize=True)
        output.seek(0)
        return output

    async def send_repaint_report(emoji_label, before_bytes, after_bytes, index):
        preview = await asyncio.wait_for(
            asyncio.to_thread(make_repaint_preview, before_bytes, after_bytes),
            timeout=60
        )
        filename = f"repaint_preview_{index}.png"
        embed = discord.Embed(
            title="Repainted Emoji",
            description=(
                f"Hex: `#{hex_color}`\n"
                f"Executed by {interaction.user.mention}\n\n"
                f"**Before -> After**\n{emoji_label}"
            ),
            color=discord.Color.from_str("#93ffa5")
        )
        embed.set_image(url=f"attachment://{filename}")
        embed.set_footer(
            text="Greenville Roleplay Server™",
            icon_url=bot.user.display_avatar.url
        )

        try:
            await interaction.channel.send(
                embed=embed,
                file=discord.File(preview, filename=filename)
            )
            return None
        except (discord.Forbidden, discord.HTTPException) as error:
            try:
                preview.seek(0)
                await interaction.followup.send(
                    embed=embed,
                    file=discord.File(preview, filename=filename),
                    ephemeral=True
                )
                return "Could not send the repaint report publicly, so it was sent privately."
            except (discord.Forbidden, discord.HTTPException):
                return f"Could not send the repaint report: {error}"

    async def repaint_existing_emoji(session, match):
        try:
            is_animated = match.group(1) == "a"
            emoji_name = match.group(2)
            emoji_id = int(match.group(3))
            file_extension = "gif" if is_animated else "png"
            emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{file_extension}?quality=lossless"

            async with session.get(emoji_url) as response:
                if response.status != 200:
                    return None, f"Could not download `{emoji_name}`."

                image_bytes = await response.read()

            new_image_bytes = await asyncio.wait_for(
                asyncio.to_thread(process_emoji_image, image_bytes),
                timeout=300
            )

            if len(new_image_bytes) > 256000:
                return None, f"`{emoji_name}` is too large for Discord after repainting."

            old_emoji = discord.utils.get(interaction.guild.emojis, id=emoji_id)

            if old_emoji is not None:
                try:
                    await old_emoji.delete(
                        reason=f"Emoji repainted by {interaction.user}"
                    )
                except:
                    pass

            new_emoji = await asyncio.wait_for(
                interaction.guild.create_custom_emoji(
                    name=emoji_name,
                    image=new_image_bytes,
                    reason=f"Emoji repainted by {interaction.user}"
                ),
                timeout=60
            )
        except asyncio.TimeoutError:
            return None, f"`{match.group(2)}` took too long to repaint."
        except Exception as error:
            return None, f"`{match.group(2)}` failed: {error}"

        return {
            "emoji": new_emoji,
            "before_bytes": image_bytes,
            "after_bytes": new_image_bytes,
        }, None

    async def repaint_attachment(attachment: discord.Attachment, index: int):
        try:
            image_bytes = await asyncio.wait_for(attachment.read(), timeout=60)
            new_image_bytes = await asyncio.wait_for(
                asyncio.to_thread(process_emoji_image, image_bytes),
                timeout=300
            )

            if len(new_image_bytes) > 256000:
                return None, f"`{attachment.filename}` is too large for Discord after repainting."

            emoji_name = sanitize_emoji_name(attachment.filename, f"repainted_{index}")

            if emoji_name in processed_attachment_names:
                return None, f"`{emoji_name}` was already provided and was skipped to avoid a duplicate."

            processed_attachment_names.add(emoji_name)

            old_emoji = discord.utils.get(interaction.guild.emojis, name=emoji_name)

            if old_emoji is not None:
                try:
                    await old_emoji.delete(
                        reason=f"Emoji replaced from image by {interaction.user}"
                    )
                except:
                    pass

            new_emoji = await asyncio.wait_for(
                interaction.guild.create_custom_emoji(
                    name=emoji_name,
                    image=new_image_bytes,
                    reason=f"Emoji created from image by {interaction.user}"
                ),
                timeout=60
            )
        except asyncio.TimeoutError:
            return None, f"`{attachment.filename}` took too long to repaint."
        except Exception as error:
            return None, f"`{attachment.filename}` failed: {error}"

        return {
            "emoji": new_emoji,
            "before_bytes": image_bytes,
            "after_bytes": new_image_bytes,
        }, None

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        created_emojis = []
        created_results = []
        failures = []
        processed_attachment_names = set()

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for match in emoji_matches:
                result, error = await repaint_existing_emoji(session, match)
                if error:
                    failures.append(error)
                else:
                    created_results.append(result)
                    created_emojis.append(str(result["emoji"]))

        for index, attachment in enumerate(attachments, start=1):
            result, error = await repaint_attachment(attachment, index)
            if error:
                failures.append(error)
            else:
                created_results.append(result)
                created_emojis.append(str(result["emoji"]))

        for index, result in enumerate(created_results, start=1):
            report_error = await send_repaint_report(
                str(result["emoji"]),
                result["before_bytes"],
                result["after_bytes"],
                index
            )
            if report_error:
                failures.append(report_error)

        response_lines = []

        if created_emojis:
            response_lines.append(f"Repainted/created emoji(s): {' '.join(created_emojis)}")

        if failures:
            response_lines.append("Failed:\n" + "\n".join(f"- {failure}" for failure in failures))

        await safe_reply("\n\n".join(response_lines) or "No emojis were repainted.")

        await send_log(
            interaction.guild,
            interaction.user,
            "/repaint",
            f"Emojis: {emojis or 'None'}\nImages: {len(attachments)}\nColor: #{hex_color}"
        )

    except Exception as e:
        await safe_reply(f"Something went wrong: `{e}`")


clear_group = app_commands.Group(
    name="clear",
    description="Clear bot-side data"
)

clear_emoji_group = app_commands.Group(
    name="emoji",
    description="Clear emoji data"
)


@clear_emoji_group.command(name="data", description="Clears temporary emoji data from the bot")
async def clear_emoji_data(interaction: discord.Interaction):
    if not any(role.name in ["Bot Developer", "Ownership Team"] for role in interaction.user.roles):
        await interaction.response.defer(ephemeral=True)
        return

    gc.collect()

    await interaction.response.send_message(
        "Temporary emoji data cleared. The bot does not store repainted emoji image data in the database, so Discord server emojis stay untouched.",
        ephemeral=True
    )

    await send_log(
        interaction.guild,
        interaction.user,
        "/clear emoji data"
    )


clear_group.add_command(clear_emoji_group)
bot.tree.add_command(clear_group)

# =====================================
# .purge
# =====================================

@bot.command()
async def purge(ctx, amount: int):
    if not is_staff(ctx.author):
        return

    def not_pinned(message):
        return not message.pinned

    deleted_messages = await ctx.channel.purge(
        limit=amount + 1,
        check=not_pinned
    )

    purged_count = max(len(deleted_messages) - 1, 0)
    message_word = "message" if purged_count == 1 else "messages"
    embed = discord.Embed(
        description=f"> Purged **{purged_count}** {message_word}.",
        color=discord.Color.from_str("#93ffa5")
    )
    embed.set_footer(
        text="Greenville Roleplay Server™",
        icon_url=bot.user.display_avatar.url
    )

    confirmation = await ctx.channel.send(embed=embed)
    await confirmation.delete(delay=5)

    await send_log(
    ctx.guild,
    ctx.author,
    ";purge",
    f"Amount: {amount}"
)

bot.run(TOKEN)
