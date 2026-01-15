from aiogram import Router, types
from aiogram.filters import Command
from services.ai_handler import AIService
from services.google_sheets import GoogleSheetsService
import os

router = Router()
sheets = GoogleSheetsService()
ai_service = AIService()
MY_ID = int(os.getenv('MY_USER_ID'))

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id != MY_ID: return
    await message.answer(
        "💰 **TeleGrana Ativo!**\n\n"
        "📝 Envie suas despesas em linguagem natural:\n"
        "Ex: \"Gastei 400 reais no mercado hoje, paguei no pix\"\n"
        "Ex: \"Paguei 50 reais de uber com cartão de crédito\""
    )

@router.message()
async def handle_message(message: types.Message):
    if message.from_user.id != MY_ID: return

    text = message.text.strip()
    
    # Processa com IA (linguagem natural)
    ai_result = await ai_service.parse_expense(text)
    
    if ai_result and ai_result.get("valor"):
        # IA conseguiu extrair os dados
        valor = float(ai_result["valor"])
        descricao = ai_result.get("descricao", "Sem descrição")
        tags = ai_result.get("tags", "")
        metodo = ai_result.get("metodo_pagamento", "")
        
        # Normaliza o método de pagamento para o formato esperado
        metodo_map = {
            "pix": "Pix",
            "crédito": "Crédito", 
            "credito": "Crédito",
            "débito": "Débito",
            "debito": "Débito",
            "caju": "Caju"
        }
        metodo_pagamento = metodo_map.get(metodo.lower(), metodo.capitalize() if metodo else "")
        
        sheets.add_expense(valor, descricao, tags=tags, metodo_pagamento=metodo_pagamento)
        
        resposta = f"✅ R$ {valor:.2f} salvos na planilha!"
        if tags:
            resposta += f"\n🏷️ Tag: {tags}"
        if metodo_pagamento:
            resposta += f"\n💳 Método: {metodo_pagamento}"
        
        await message.answer(resposta)
    else:
        await message.answer(
            "⚠️ Não consegui entender a mensagem.\n\n"
            "📝 Tente enviar em linguagem natural, por exemplo:\n"
            "• \"Gastei 400 reais no mercado hoje, paguei no pix\"\n"
            "• \"Paguei 50 reais de uber com cartão de crédito\"\n"
            "• \"15 reais de café no restaurante, débito\""
        )