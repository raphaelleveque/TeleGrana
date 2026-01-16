import asyncio
import os
from dotenv import load_dotenv

load_dotenv() 

from aiogram import Bot, Dispatcher
from bot.handlers import router
from services.transaction_service import TransactionService 

async def main():    
    service = TransactionService()
    
    # ---------------------------------------------------------
    # Inicialização Inteligente: Verifica se a planilha está vazia
    # Se estiver vazia, cria headers e validações.
    # Se não, mantém como está.
    # ---------------------------------------------------------
    print(f"--- {service.initialize_sheet()} ---") 
    
    # Inicializa serviços
    bot = Bot(token=os.getenv('TELEGRAM_TOKEN'))
    dp = Dispatcher()
    dp.include_router(router)

    print("🚀 Bot TeleGrana rodando com sucesso!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())