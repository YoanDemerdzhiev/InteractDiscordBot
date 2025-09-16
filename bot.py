import os
import re 
import asyncio
from dotenv import load_dotenv

import discord
from discord.ext import commands, tasks
from discord.ui import Button, View

import gspread
from oauth2client.service_account import ServiceAccountCredentials  

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
SHEET_KEY = os.getenv('SHEET_KEY')
CREDENTIALS_FILE = 'credentials.json'
GUILD_ID = 1417139813617893399
VERIFY_CHANNEL_ID = 1417139814465273975

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

def get_sheet():
    """Свързва се с Google Sheets и връща обект на таблица."""
    scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_KEY).sheet1
    return sheet

def find_in_sheet(phone):
    """Проверява дали даден телефон съществува в таблицата."""
    sheet = get_sheet()
    records = sheet.get_all_records()
    def normalize_phone(p):
        digits = re.sub(r"\D", '',str(p or ''))


        if digits.startswith("359") and len(digits) > 3:
            digits = "0" + digits[3:]

        elif digits.startswith("00") and len(digits) > 5:
            digits = "0" + digits[5:]

        elif len(digits) == 9 and digits.startswith("8"):
            digits = "0" + digits

        return digits
    
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

@bot.event
async def on_ready():
    print(f'Влязох като {bot.user}')
    guild = bot.get_guild(GUILD_ID)
    channel = guild.get_channel(VERIFY_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="Верификация на нови членове",
            description="Натисни бутона по-долу, за да започнеш процеса на верификация и получиш достъп до сървъра.",
            color=discord.Color.green()
        )
        embed.set_footer(text="Ботът автоматично ще създаде частен канал за теб.")
        
        await channel.send(embed=embed, view=VerificationView())

    update_roles_task.start()

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        if interaction.data.get("custom_id") == "verify_button":
            user = interaction.user
            guild = interaction.guild

            await interaction.response.send_message(
            "✅ Създадох частен канал за верификацията ти!", 
            ephemeral=True
            )

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
                
            private_channel = await guild.create_text_channel(
                f"verification-{user.name}", overwrites=overwrites
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
                await private_channel.send("❌ Телефонът не е намерен в таблицата.")
                await asyncio.sleep(5)
                await private_channel.send("⏳ Каналът ще се затвори след 30 секунди.")
                await asyncio.sleep(30)
                await private_channel.delete()
                return
            
            value = str(row.get("Официален член") or "").strip().upper()
            verified = value == "TRUE"
            member_role = discord.utils.get(guild.roles, name="Член")
            candidate_role = discord.utils.get(guild.roles, name="Кандидат-член")

            if verified:  
                await user.add_roles(member_role)
                await user.remove_roles(candidate_role)
                await private_channel.send("✅ Вече сте **член**!")
            else:
                await user.add_roles(candidate_role)
                await private_channel.send("✅ Вече сте **кандидат-член**!")

            await asyncio.sleep(5)
            await private_channel.send("⏳ Каналът ще се затвори след 30 секунди.")
            await asyncio.sleep(30)
            await private_channel.delete()

@tasks.loop(minutes=1)
async def update_roles_task():
    print("🔄 Update roles task executed")
    await bot.wait_until_ready()
    sheet = get_sheet()
    records = sheet.get_all_records()
    guild = bot.get_guild(GUILD_ID)

    for row in records:
        discord_id = row.get("DiscordID")  # трябва да имаш колона с Discord ID, ако искаш автоматично да се обновяват роли
        if not discord_id:
            continue
        member = guild.get_member(int(discord_id))
        if not member:
            continue

        verified = row.get("Официален член")
        member_role = discord.utils.get(guild.roles, name="Член")
        candidate_role = discord.utils.get(guild.roles, name="Кандидат-член")

        if verified:
            if candidate_role in member.roles:
                await member.remove_roles(candidate_role)
            if member_role not in member.roles:
                await member.add_roles(member_role)
        else:
            if member_role in member.roles:
                await member.remove_roles(member_role)
            if candidate_role not in member.roles:
                await member.add_roles(candidate_role)

bot.run(DISCORD_TOKEN)