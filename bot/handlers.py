from aiogram import Router, types
from aiogram.filters import Command
from services.google_sheets import GoogleSheetsService
import os

router = Router()
sheets = GoogleSheetsService()
MY_ID = int(os.getenv('MY_USER_ID'))

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id != MY_ID: return
    await message.answer("💰 **TeleGrana Ativo!**\nEnvie: `Valor Descrição` (Ex: 50.00 Mercado)")

@router.message()
async def handle_message(message: types.Message):
    if message.from_user.id != MY_ID: return

    try:
        parts = message.text.split(" ", 1)
        valor = float(parts[0].replace(',', '.'))
        descricao = parts[1] if len(parts) > 1 else "Sem descrição"
        
        # Por enquanto salvando direto. 
        # Futuramente aqui podemos chamar um teclado para perguntar 'Reembolsado?'
        sheets.add_expense(message.from_user.first_name, valor, descricao)
        
        await message.answer(f"✅ R$ {valor:.2f} salvos na planilha!")
    except ValueError:
        await message.answer("⚠️ Formato: `Valor Descrição` (Ex: 15.00 Uber)")