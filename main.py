import asyncio
from bot import bot
from server import app
import uvicorn
import os

async def start_bot():
    await bot.start(os.getenv("MTQxNzIwMjI4MTA5MDM4ODEzMg.Ge32g-.ds_Ws5_So8d1RpDyXajRorl9g1EFjoeOVOrb9E"))

async def start_server():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    await asyncio.gather(start_bot(), start_server())

asyncio.run(main())

