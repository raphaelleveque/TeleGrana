import asyncio
import os
from dotenv import load_dotenv

load_dotenv() 

from aiogram import Bot, Dispatcher
from bot.handlers import router
from services.google_sheets import GoogleSheetsService 

async def main():    
    # Inicializa serviços
    bot = Bot(token=os.getenv('TELEGRAM_TOKEN'))
    dp = Dispatcher()
    dp.include_router(router)

    print("🚀 Bot TeleGrana rodando com sucesso!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())