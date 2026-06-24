import os
import asyncio
import discord
import re
import io
import aiohttp
import colorsys
import sqlite3
from PIL import Image
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from datetime import datetime, timedelta
from urllib.parse import urlparse

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
WELCOME_IMAGE = "https://cdn.discordapp.com/attachments/1479130697800089622/1519100047961362463/image.png?ex=6a3c53aa&is=6a3b022a&hm=20dcd9ee3256031229c4245a4eb7ac879aa7f4dd56bc5adc9c948c8ccb4d3fb6&"
WELCOME_THUMBNAIL = "https://cdn.discordapp.com/attachments/1479130697800089622/1519101482203615323/image.png?ex=6a3c5500&is=6a3b0380&hm=efea340a34ed87dc6bec1a9e6c29cfdd545c6103712621e7046220045ade683e&"
STAFF_INFORMATION_IMAGE = "https://cdn.discordapp.com/attachments/1479130697800089622/1519309639471075468/Society_-_Embed_-_Staff_Information.webp?ex=6a3d16dd&is=6a3bc55d&hm=4dec9cec71bd426376ae543e24e310ca57595d585d114ec10f519e2e4d096fa8&"

EARLYACCESS_ROLE_ID = 1290705580046024725
CIVILIANS_ROLE_ID = 1290705580025184277
TICKET_CATEGORY_ID = 1506043336987906231
ROLEPLAY_RESTRICTED_ROLE_ID = 1290705580025184282
WELCOME_CHANNEL_ID = 1290705580905861223
BOOK_EMOJI = "<:GVRSbook:1515852761948749874>"
SUN_EMOJI = "☀️"

DB_FILE = "bot_data.db"

SESSION_START_TIMES = {}
ACTIVE_COHOSTS = {}
ACTIVE_SUPERVISIONS = {}
ACTIVE_STARTUPS = {}

ALLOWED_ROLEPLAY_CHANNELS = ["roleplay-1", "roleplay-2", "bot-testing-dont-remove"]
MAX_TIMEOUT_DURATION = timedelta(days=28)
MAX_EMOJI_DOWNLOAD_BYTES = 2 * 1024 * 1024
MAX_GIF_FRAMES = 80


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

    cur.execute("SELECT * FROM active_staff_timers")
    for row in cur.fetchall():
        key = (int(row["guild_id"]), int(row["channel_id"]), int(row["user_id"]))

        if row["timer_type"] == "cohost":
            ACTIVE_COHOSTS[key] = row["start_timestamp"]
        elif row["timer_type"] == "supervise":
            ACTIVE_SUPERVISIONS[key] = row["start_timestamp"]

    conn.close()


def save_active_session(active_key, message_id, start_timestamp):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO active_sessions
        (guild_id, channel_id, message_id, start_timestamp)
        VALUES (?, ?, ?, ?)
    """, (
        str(active_key[0]),
        str(active_key[1]),
        str(message_id),
        start_timestamp
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
        color=discord.Color.from_str("#fef1b3")
    )

    embed.add_field(
        name="Executed by",
        value=f"{user.mention}\n`{user}`",
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
                f"Date: <t:{session['end_timestamp']}:D>\n"
                f"Duration: {session['duration_minutes']} minutes\n"
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


class LOARequestView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def can_handle_loa(self, member):
        return any(role.name == "High Ranking Staff" for role in member.roles)

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
            name="⭐ discord.gg/gvsociety"
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
            "Welcome to **Greenville Roleplay Society** — a community built on professionalism, realism, and "
            "an engaging Greenville roleplay experience! We’re excited to have you here.\n\n"
            "Whether you're joining to patrol, roleplay as a civilian, participate in events, or connect with new people, "
            "GVRS is committed to providing a safe, organized, and enjoyable environment for everyone.\n\n"
            f"{BOOK_EMOJI} **Getting Started**\n"
            "• Make sure to read all server rules and in-game regulations\n"
            "• Claim your roles in the designated channels\n"
            "• Introduce yourself and meet the community\n"
            "• Watch for upcoming sessions, events, and announcements\n\n"
            "**Meet the Team**\n"
            "Our staff team is here to support you and maintain a smooth experience. If you need help, guidance, "
            "or have questions, feel free to contact any GVRS staff member."
        ),
        color=discord.Color.from_str("#fef1b3")
    )

    embed.set_thumbnail(url=WELCOME_THUMBNAIL)
    embed.set_image(url=WELCOME_IMAGE)
    embed.set_footer(
        text="Greenville Roleplay Society™",
        icon_url=bot.user.display_avatar.url
    )

    await channel.send(
        content=f"{SUN_EMOJI} Welcome to Greenville Roleplay Society {member.mention}!",
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
        role.name in ["Senior High Ranking Staff", "High Ranking Staff"]
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
        allowed_mentions=discord.AllowedMentions.none()
    )

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
        role.name in ["Staff Team", "High Ranking Staff"]
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

    start_timestamp = int(message.created_at.timestamp())
    SESSION_START_TIMES[active_key] = start_timestamp
    ACTIVE_STARTUPS[active_key] = message.id
    save_active_session(active_key, message.id, start_timestamp)

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

            if ACTIVE_STARTUPS.get(active_key) != message.id:
                return

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

    allowed_channels = ALLOWED_ROLEPLAY_CHANNELS

    if interaction.channel.name not in allowed_channels:
        await interaction.response.defer(ephemeral=True)
        return

    if not any(role.name in ["Ownership Team", "Bot Developer"] for role in interaction.user.roles):
        await interaction.response.defer(ephemeral=True)
        return

    active_key = session_key(interaction)
    ACTIVE_STARTUPS.pop(active_key, None)
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
    SESSION_START_TIMES.pop(active_key, None)
    clear_active_session(active_key)
    clear_staff_timers_for_session(active_key)

    await interaction.channel.send(embed=embed)

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
        color=discord.Color.from_str("#fef1b3")
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
        text="Greenville Roleplay Society™",
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
            "You have been **roleplay restricted** in **Greenville Roleplay Society** for the following reason(s):\n\n"
            f"- {reason}\n\n"
            f"This roleplay restriction is guilty for **{time}**. If you deem this restriction to be false "
            f"please open a ticket via {APPEAL_TICKET_LINK}.\n\n"
            f"Evidence: {evidence}"
        ),
        color=discord.Color.from_str("#fef1b3")
    )

    dm_embed.set_footer(
        text="Greenville Roleplay Society™",
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
            "You have been **roleplay unrestricted** in **Greenville Roleplay Society**.\n\n"
            "Feel free to join our sessions again as usually. You may get roleplay restricted in future "
            "if you break our guidelines again."
        ),
        color=discord.Color.from_str("#fef1b3")
    )

    dm_embed.set_footer(
        text="Greenville Roleplay Society™",
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

    active_key = user_session_key(interaction)
    start_timestamp = int(discord.utils.utcnow().timestamp())
    ACTIVE_SUPERVISIONS[active_key] = start_timestamp
    save_staff_timer(active_key, "supervise", start_timestamp)

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

STAFF_INFORMATION_TEXT = """
<a:blue_flower:1518783617160052909> **Welcome to the Greenville Roleplay Society Staff Team** <a:blue_flower:1518783617160052909>
Your commitment, professionalism, and leadership are essential to maintaining a safe, organized, and immersive roleplay environment for our community. As a member of the GVRS Staff Team, you represent the standard of conduct and structure that allows our server to operate at a high level. We sincerely appreciate the time and effort you dedicate to supporting GVRS and its members.

<:GVRSarrow2:1515852723713474611> **Notes**
Being a member of the GVRS Staff Team is both a responsibility and a privilege. Your dedication allows Greenville Roleplay Society to continue growing as a structured, professional, and enjoyable community for everyone involved.

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
**Session Formats** <a:GVRDdesolvingheart:1515852981205991627>

# Greenville Roleplay Society Session Format

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
                    color=discord.Color.from_str("#fef1b3")
                )
            ]
        elif self.values[0] == "Staff Quota Requirements":
            embeds = [
                discord.Embed(
                    description=STAFF_QUOTA_TEXT,
                    color=discord.Color.from_str("#fef1b3")
                )
            ]
        else:
            embeds = [
                discord.Embed(
                    description=SESSION_FORMATS_TEXT_1,
                    color=discord.Color.from_str("#fef1b3")
                ),
                discord.Embed(
                    description=SESSION_FORMATS_TEXT_2,
                    color=discord.Color.from_str("#fef1b3")
                )
            ]

        for embed in embeds:
            embed.set_footer(
                text="Greenville Roleplay Society™",
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

    banner_embed = discord.Embed(color=discord.Color.from_str("#fef1b3"))
    banner_embed.set_image(url=STAFF_INFORMATION_IMAGE)

    info_embed = discord.Embed(
        description=STAFF_INFORMATION_TEXT,
        color=discord.Color.from_str("#fef1b3")
    )

    info_embed.set_footer(
        text="Greenville Roleplay Society™",
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

    conn.close()

    embed = discord.Embed(
        title="Staff Profile",
        description=(
            f"**User:** {user.mention}\n\n"
            f"**Hosted Sessions:** {counts['hosted']}\n"
            f"**Co-Hosted Sessions:** {counts['cohosted']}\n"
            f"**Supervised Sessions:** {counts['supervised']}\n\n"
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
            f"You have received **One** Staff Strike in **Greenville Roleplay Society** for the following reason(s):\n\n"
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
HIGH_COMMAND_ROLE_NAMES = ["High Ranking Staff"]


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
                color=discord.Color.from_str("#fef1b3")
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
            color=discord.Color.from_str("#fef1b3")
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
            color=discord.Color.from_str("#fef1b3")
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

APPEAL_TICKET_LINK = "https://discord.com/channels/1290705579953754163/1503269938624856156"

STAFF_TEAM_ROLE = "Staff Team"
HIGH_COMMAND_ROLES = ["High Ranking Staff", "Senior High Ranking Staff"]

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
    "High Ranking Staff",
    "Senior High Ranking Staff",
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
        color=discord.Color.from_str("#fef1b3")
    )

    embed.set_footer(
        text="Greenville Roleplay Society",
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
            f"You have been **Infracted {next_number} Time** in **Greenville Roleplay Society** for the following reason(s):\n\n"
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
            f"You have been **Banned** from **Greenville Roleplay Society** for the following reason(s):\n\n"
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
            f"You have been **Suspended** from the **Greenville Roleplay Society** Staff Team for the following reason(s):\n\n"
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
            f"You have been **Terminated** from the **Greenville Roleplay Society** Staff Team for the following reason(s):\n\n"
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
                f"You have been **Infracted {number} Time** in **Greenville Roleplay Society** for the following reason(s):\n\n"
                f"- {warning['reason']}\n\n"
                f"This infraction is **{warning['appealable']}** in {warning['appeal_time']}, if you deem this infraction to be false "
                f"please open a ticket via {APPEAL_TICKET_LINK}.\n\n"
                f"Evidence: {warning['evidence']} - <t:{warning['timestamp']}:R>\n\n"
            )

        elif warning["type"].startswith("Staff Strike"):
            text += (
                f"**Moderator:** <@{warning['moderator_id']}>\n"
                f"You have received **One** Staff Strike in **Greenville Roleplay Society** for the following reason(s):\n\n"
                f"- {warning['reason']}\n\n"
                f"This Strike is **{warning['appealable']}** in {warning['appeal_time']}, if you deem this strike to be false "
                f"please open a ticket via {APPEAL_TICKET_LINK}.\n\n"
                f"Evidence: {warning['evidence']} - <t:{warning['timestamp']}:R>\n\n"
            )

        elif warning["type"] == "Suspension":
            text += (
                f"**Moderator:** <@{warning['moderator_id']}>\n"
                f"You have been **Suspended** from the **Greenville Roleplay Society** Staff Team for the following reason(s):\n\n"
                f"- {warning['reason']}\n\n"
                f"This Suspension is **{warning['appealable']}** in {warning['appeal_time']}, if you deem this suspension to be false "
                f"please open a ticket via {APPEAL_TICKET_LINK}.\n\n"
                f"Evidence: {warning['evidence']} - <t:{warning['timestamp']}:R>\n\n"
            )

        elif warning["type"] == "Termination":
            text += (
                f"**Moderator:** <@{warning['moderator_id']}>\n"
                f"You have been **Terminated** from the **Greenville Roleplay Society** Staff Team for the following reason(s):\n\n"
                f"- {warning['reason']}\n\n"
                f"This Termination is **{warning['appealable']}** in {warning['appeal_time']}.\n\n"
                f"Evidence: {warning['evidence']} - <t:{warning['timestamp']}:R>\n\n"
            )

        elif warning["type"] == "Ban":
            text += (
                f"**Moderator:** <@{warning['moderator_id']}>\n"
                f"You have been **Banned** from **Greenville Roleplay Society** for the following reason(s):\n\n"
                f"- {warning['reason']}\n\n"
                f"If you deem this ban to be false, feel free to appeal it with the appeal listed below.\n"
                f"Appeal: Soon.\n\n"
                f"Evidence: {warning['evidence']} - <t:{warning['timestamp']}:R>\n\n"
            )

        elif warning["type"] == "Roleplay Restriction":
            text += (
                f"**Moderator:** <@{warning['moderator_id']}>\n"
                f"You have been **roleplay restricted** in **Greenville Roleplay Society** for the following reason(s):\n\n"
                f"- {warning['reason']}\n\n"
                f"This roleplay restriction is guilty for **{warning['appeal_time']}**. If you deem this restriction to be false "
                f"please open a ticket via {APPEAL_TICKET_LINK}.\n\n"
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
        color=discord.Color.from_str("#fef1b3")
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

    # =====================================
# /serverinfo
# =====================================

SERVER_INFO_IMAGE = "https://cdn.discordapp.com/attachments/1479130697800089622/1513908128557695098/Society_-_Embed_-_Regulations.webp?ex=6a3d36d0&is=6a3be550&hm=2b34b49689c50a78db9ad5d5372699bec636df5f9b8dd8243cdfc5f8085646b4&"

ROBLOX_GROUP_LINK = "https://www.roblox.com/communities/650527738/Official-Greenville-Roleplay-Society#!/about"
RESTRICTED_VEHICLES_LINK = "https://docs.google.com/spreadsheets/d/1ahcV0bVi62XDg6rRYaEpGgFQV3_85_BPcwqXO-EVoVs/edit?gid=16420916#gid=16420916"

SERVER_GUIDELINES_TEXT = """
**1. <:GVRSarrow:1513646972106702919> Read the Regulations**
All Greenville Roleplay Society members must read and acknowledge the regulations listed in our information channels. Failure to comply may result in serious consequences.

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
Advertising of any kind is prohibited, including direct messages and public channels. Any server found recruiting Greenville Roleplay Society members or staff will be blacklisted, and involved members will be removed.

**8. <:GVRSarrow:1513646972106702919> No Resource Theft**
Stealing any Greenville Roleplay Society resources, such as announcements, documentation or any other assets will lead to an immediate ban from Greenville Roleplay Society and all affiliated servers.

**9. <:GVRSarrow:1513646972106702919> No Sharing of Personal Information**
Leaking, doxxing, or otherwise sharing personal information about any member will result in an immediate and permanent ban.

**10. <:GVRSarrow:1513646972106702919> No NSFW Content**
Posting or distributing not safe for work material, including pornography, gore, or violent imagery, is strictly prohibited. First offense results in a warning, although the second offense results in an immediate ban.

**11. <:GVRSarrow:1513646972106702919> Maintain Respect**
Greenville Roleplay Society will not tolerate any disrespect, defamatory comments or complaints about Greenville Roleplay Society or affiliated communities. Any user found being disrespectful will be moderated.

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
                    "> <a:GVRSbutterfly:1515852789266518056> **__Greenville Roleplay Society, Server Guidelines__** <a:GVRSbutterfly:1515852789266518056>\n\n"
                    f"{SERVER_GUIDELINES_TEXT}"
                ),
                color=discord.Color.from_str("#fef1b3")
            )

        elif choice == "Roblox Group":
            embed = discord.Embed(
                description=f"Klick [here]({ROBLOX_GROUP_LINK}) to join our roblox group.",
                color=discord.Color.from_str("#fef1b3")
            )

        else:
            embed = discord.Embed(
                description=f"Klick [here]({RESTRICTED_VEHICLES_LINK}) to view our Restricted Vehicles list.",
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

    if not any(role.name == "Ownership Team" for role in interaction.user.roles):
        await interaction.response.defer(ephemeral=True)
        return

    banner_embed = discord.Embed(color=discord.Color.from_str("#fef1b3"))
    banner_embed.set_image(url=SERVER_INFO_IMAGE)

    info_embed = discord.Embed(
        description=(
            "> <a:GVRSbutterfly:1515852789266518056> **__Welcome to Greenville Roleplay Society__** <a:GVRSbutterfly:1515852789266518056>\n\n"
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
    emoji="Paste the custom emoji here",
    hex_color="New HEX color, example: #ffb7c5"
)
async def repaint(interaction: discord.Interaction, emoji: str, hex_color: str):

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
        try:
            await interaction.followup.send(message, ephemeral=True)
        except:
            try:
                await interaction.user.send(message)
            except:
                pass

    if not re.fullmatch(r"#[0-9a-fA-F]{6}", hex_color):
        await safe_reply("Please use a valid HEX color, example: `#ffb7c5`.")
        return

    match = re.match(r"<(a?):(\w+):(\d+)>", emoji)

    if not match:
        await safe_reply("Please paste a valid custom emoji.")
        return

    is_animated = match.group(1) == "a"
    emoji_name = match.group(2)
    emoji_id = int(match.group(3))

    target_r = int(hex_color[1:3], 16)
    target_g = int(hex_color[3:5], 16)
    target_b = int(hex_color[5:7], 16)

    target_h, _, _ = colorsys.rgb_to_hls(
        target_r / 255,
        target_g / 255,
        target_b / 255
    )

    def repaint_pixel(old_r, old_g, old_b, alpha):
        if alpha == 0:
            return old_r, old_g, old_b, alpha

        _, old_l, old_s = colorsys.rgb_to_hls(
            old_r / 255,
            old_g / 255,
            old_b / 255
        )

        nr, ng, nb = colorsys.hls_to_rgb(
            target_h,
            old_l,
            max(old_s, 0.20)
        )

        return (
            int(nr * 255),
            int(ng * 255),
            int(nb * 255),
            alpha
        )

    file_extension = "gif" if is_animated else "png"
    emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{file_extension}?quality=lossless"

    def process_emoji_image(image_bytes):
        output = io.BytesIO()

        if is_animated:
            image = Image.open(io.BytesIO(image_bytes))
            frame_count = getattr(image, "n_frames", 1)

            if frame_count > MAX_GIF_FRAMES:
                raise ValueError(f"Animated emojis are limited to {MAX_GIF_FRAMES} frames.")

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
            image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

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

    try:
        timeout = aiohttp.ClientTimeout(total=15)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(emoji_url) as response:
                if response.status != 200:
                    await safe_reply("Could not download this emoji.")
                    return

                content_length = response.headers.get("Content-Length")

                if content_length and int(content_length) > MAX_EMOJI_DOWNLOAD_BYTES:
                    await safe_reply("This emoji is too large to repaint.")
                    return

                image_bytes = await response.read()

        if len(image_bytes) > MAX_EMOJI_DOWNLOAD_BYTES:
            await safe_reply("This emoji is too large to repaint.")
            return

        new_image_bytes = await asyncio.to_thread(process_emoji_image, image_bytes)

        if len(new_image_bytes) > 256000:
            await safe_reply(
                "The repainted emoji is too large for Discord. Try a smaller emoji/GIF."
            )
            return

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

        await safe_reply(f"Emoji repainted successfully: {new_emoji}")

        await send_log(
            interaction.guild,
            interaction.user,
            "/repaint",
            f"Emoji: {emoji}\nColor: {hex_color}"
        )

    except Exception as e:
        await safe_reply(f"Something went wrong: `{e}`")

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
