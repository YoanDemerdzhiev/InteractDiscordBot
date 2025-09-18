import os
import re 
import asyncio
from dotenv import load_dotenv

import discord
from discord.ext import commands, tasks
from discord.ui import Button, View

import gspread
from oauth2client.service_account import ServiceAccountCredentials  

import json
import datetime

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
SHEET_KEY = os.getenv('SHEET_KEY')
CREDENTIALS_FILE = 'credentials.json'
GUILD_ID = 1417139813617893399
VERIFY_CHANNEL_ID = 1417139814465273975
UPDATE_CHANNEL_ID = 1417423373507498108
MESSAGE_ID_FILE = 'message_id.json'

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

def get_sheet():
    scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_KEY).sheet1
    return sheet


def normalize_phone(p: str) -> str:
    digits = re.sub(r"\D", '',str(p or ''))


    if digits.startswith("359") and len(digits) > 3:
            digits = "0" + digits[3:]

    elif digits.startswith("00359") and len(digits) > 5:
            digits = "0" + digits[5:]

    elif len(digits) == 9 and digits.startswith("8"):
            digits = "0" + digits

    return digits

def find_in_sheet(phone: str):
    sheet = get_sheet()
    records = sheet.get_all_records()
    phone_norm = normalize_phone(phone)

    for row in records:
        row_phone = normalize_phone(row.get('Телефон за контакт'))
        if row_phone == phone_norm:
            return True, row
    return False, None

class VerificationView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="Верифицирай ме", style=discord.ButtonStyle.green, custom_id="verify_button"))

class UpdateView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="Актуализирай ме", style=discord.ButtonStyle.red, custom_id="update_button"))

@bot.event
async def on_ready():
    print(f'Влязох като {bot.user}')
    guild = bot.get_guild(GUILD_ID)


    verify_channel = guild.get_channel(VERIFY_CHANNEL_ID)
    if verify_channel:
        old_msg_data = load_message_id("verify_message")
        old_msg = None
        delete_old = False

        if old_msg_data:
            msg_id = old_msg_data.get("id")
            timestamp_str = old_msg_data.get("timestamp")
            if msg_id and timestamp_str:
                try:
                    old_msg = await verify_channel.fetch_message(msg_id)
                    ts = datetime.datetime.fromisoformat(timestamp_str)
                    if (datetime.datetime.utcnow() - ts) > datetime.timedelta(days=365):
                        delete_old = True
                except discord.NotFound:
                    old_msg = None

        if delete_old and old_msg:
            await old_msg.delete()
            old_msg = None

        if old_msg:
            print("🔄 Старото съобщение за верификация е намерено.")
        else:
         embed = discord.Embed(
            title="Верификация на нови членове",
            description="Натисни бутона по-долу, за да започнеш процеса на верификация и получиш достъп до сървъра.",
            color=discord.Color.green()
         )
         embed.set_footer(text="Ботът автоматично ще създаде частен канал за теб.")
         new_msg = await verify_channel.send(embed=embed, view=VerificationView())
         save_message_id("verify_message", new_msg)
         print("📌 Изпратено е ново съобщение за верификация.")

    update_channel = guild.get_channel(UPDATE_CHANNEL_ID)
    if update_channel:
        old_msg_data = load_message_id("update_message")
        old_msg = None
        delete_old = False

        if old_msg_data:
            msg_id = old_msg_data.get("id")
            timestamp_str = old_msg_data.get("timestamp")
            if msg_id and timestamp_str:
                try:
                    old_msg = await update_channel.fetch_message(msg_id)
                    ts = datetime.datetime.fromisoformat(timestamp_str)
                    if (datetime.datetime.utcnow() - ts) > datetime.timedelta(days=365):
                        delete_old = True
                except discord.NotFound:
                    old_msg = None

        if delete_old and old_msg:
            await old_msg.delete()
            old_msg = None
        if old_msg:
            print("🔄 Старото съобщение за update е намерено.")
        else:
         embed = discord.Embed(
            title=" Актуализиране",
            description="Натисни бутона по-долу, за да актуализираш статуса си.",
            color=discord.Color.red()
         )
         new_msg = await update_channel.send(embed=embed, view=UpdateView())
         save_message_id("update_message", new_msg)
         print("📌 Изпратено е ново съобщение за update.")
    

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        user = interaction.user
        guild = interaction.guild

        if interaction.data.get("custom_id") == "verify_button":

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
                
            private_channel = await guild.create_text_channel(
                f"verification-{user.name}", overwrites=overwrites
            )

            await interaction.response.send_message(
            "✅ Създадох частен канал за верификацията ти!", 
            ephemeral=True
            )

            await private_channel.send(
                f"Здравей {user.mention}, моля въведи своя **телефонен номер**:"
            )

            def check(m):
                return m.author == user and m.channel == private_channel

            try:
                msg = await bot.wait_for('message', check=check, timeout=300) 
                phone = msg.content.strip()
            except asyncio.TimeoutError:
                try:
                    await private_channel.send("❌ Изтече времето. Моля опитайте отново.")
                    await asyncio.sleep(5)
                    await private_channel.send("⏳ Каналът ще се затвори след 30 секунди.")
                    await asyncio.sleep(30)
                    await private_channel.delete()
                except discord.errors.NotFound:
                    pass
                return
            
            found, row = find_in_sheet(phone)
            if not found:
                await private_channel.send(
                            f"❌ Телефонът не е намерен.\n"
                            f"Моля попълнете формуляр тук: <#{1417430628038737940}>"
                        )
                await asyncio.sleep(5)
                await private_channel.send("⏳ Каналът ще се затвори след 30 секунди.")
                await asyncio.sleep(30)
                await private_channel.delete()
                return
             
            await private_channel.send("✅ Телефонът е намерен. Верифициран сте!")
            guest_role = discord.utils.get(guild.roles, name="Гост")
            verified_role = discord.utils.get(guild.roles, name="Верифициран")
            await user.add_roles(verified_role)
            await user.remove_roles(guest_role)

            full_name = row.get("Име и фамилия")
            if full_name:
                try:
                    await user.edit(nick=full_name)
                except discord.Forbidden:
                    await private_channel.send("⚠️ Нямам права да променя никнейма ти.")
            
            value = str(row.get("Официален член") or "").strip().upper()
            verified = value == "TRUE"
            member_role = discord.utils.get(guild.roles, name="Член")
            candidate_role = discord.utils.get(guild.roles, name="Кандидат-член")

            if verified:  
                await user.add_roles(member_role)
                await user.remove_roles(candidate_role)
                await private_channel.send("🔵 Вече сте **член**!")
            else:
                await user.add_roles(candidate_role)
                await private_channel.send("🔴 Вече сте **кандидат-член**!")

            await asyncio.sleep(5)
            await private_channel.send("⏳ Каналът ще се затвори след 30 секунди.")
            await asyncio.sleep(30)
            await private_channel.delete()
        elif interaction.data.get("custom_id") == "update_button":
            await interaction.response.send_message(
                "🔄 Стартирам актуализация на ролите ти...", ephemeral=True
            )
            sheet = get_sheet()
            records = sheet.get_all_records()
            member = guild.get_member(user.id)

            found = False

            for row in records:
                if member.nick and  member.nick == row.get("Име и фамилия"):
                    found = True
                    value = str(row.get("Официален член") or "").strip().upper()
                    verified = value == "TRUE"
                    member_role = discord.utils.get(guild.roles, name="Член")
                    candidate_role = discord.utils.get(guild.roles, name="Кандидат-член")

                    if verified:  
                        await user.add_roles(member_role)
                        await user.remove_roles(candidate_role)
                        await interaction.followup.send("🔵 Ролите ти бяха актуализирани. Вече си **член**!",
                        ephemeral=True                                
                        )
                    else:
                        await user.add_roles(candidate_role)
                        await user.remove_roles(member_role)
                        await interaction.followup.send("🔴 Ролите ти бяха актуализирани. Вече си **кандидат-член**!",
                        ephemeral=True                                
                        )
                    return
            if not found:
                await asyncio.sleep(60)
                await interaction.followup.send(
                    "❌ Не можах да намеря информация за теб и да те актуализирам. "
                    "Моля свържи се с администратор.",
                    ephemeral=True
                )

def save_message_id(key, message):
    data = {}
    try:
        with open(MESSAGE_ID_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    data[key] = {"id": message.id,
                 "timestamp": datetime.datetime.utcnow().isoformat()
     }

    with open(MESSAGE_ID_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f)         

def load_message_id(key):
    try:
        with open(MESSAGE_ID_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get(key)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
bot.run(DISCORD_TOKEN)