from aiogram import Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from services.ai_handler import AIService
from services.google_sheets import GoogleSheetsService
from bot.states import ExpenseState
import os

router = Router()
sheets = GoogleSheetsService()
ai_service = AIService()
MY_ID = int(os.getenv('MY_USER_ID'))

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    if message.from_user.id != MY_ID: return
    await state.clear()
    await message.answer(
        "💰 **TeleGrana Ativo!**\n\n"
        "📝 Envie suas despesas ou entradas em linguagem natural:\n"
        "💸 Gasto: \"Gastei 400 reais no mercado hoje, paguei no pix\"\n"
        "💰 Entrada: \"Recebi 10000 de salário hoje\"\n"
        "💸 Gasto: \"Paguei 50 reais de uber com cartão de crédito\""
    )

@router.message(ExpenseState.AwaitingEdit)
async def handle_edit(message: types.Message, state: FSMContext):
    """
    Handler para quando o bot está esperando uma possível edição da última transação.
    """
    if message.from_user.id != MY_ID: return
    
    text = message.text.strip()
    ai_result = await ai_service.parse_edit_intent(text, sheets.tag_options, sheets.metodo_options)

    # Verifica se a IA identificou uma tentativa de edição
    if ai_result and ai_result.get("is_edit_request"):
        field = ai_result.get("field")
        new_value = ai_result.get("value")

        if not field or new_value is None:
            await message.answer("⚠️ Não consegui entender o que você quer alterar. Tente ser mais específico, como 'altere o valor para 50' ou 'a categoria é Lazer'.")
            return

        user_data = await state.get_data()
        last_row = user_data.get("last_transaction_row")

        if not last_row:
            await message.answer("⚠️ Não encontrei a última transação para editar.")
            await state.clear()
            return
        
        response = ""
        # Mapeia o campo da IA para a função de atualização correspondente
        if field == "tags":
            new_category = str(new_value).capitalize()
            is_new = sheets.add_category(new_category)
            sheets.update_expense_category(last_row, new_category)
            response = f"✅ Categoria atualizada para **{new_category}**!"
            if is_new:
                response += f"\n🎉 Nova categoria criada: '{new_category}'."
        
        elif field == "valor":
            try:
                new_value_float = float(new_value)
                sheets.update_expense_value(last_row, new_value_float)
                response = f"✅ Valor alterado para **R$ {new_value_float:.2f}**!"
            except (ValueError, TypeError):
                await message.answer("⚠️ O valor fornecido não parece ser um número válido.")
                return

        elif field == "descricao":
            new_desc = str(new_value)
            sheets.update_description(last_row, new_desc)
            response = f"✅ Descrição alterada para: \"{new_desc}\"."

        elif field == "metodo_pagamento":
            new_method = str(new_value).capitalize()
            if new_method not in sheets.metodo_options:
                await message.answer(f"⚠️ Método de pagamento '{new_method}' não é válido. Opções: {', '.join(sheets.metodo_options)}.")
                return
            sheets.update_payment_method(last_row, new_method)
            response = f"✅ Método de pagamento alterado para **{new_method}**."

        else:
            await message.answer(f"⚠️ Não sei como alterar o campo '{field}'.")
            return

        await message.answer(response)
        await state.clear()

    else:
        # Se não for um comando de edição, limpa o estado e processa como uma nova mensagem
        await state.clear()
        await handle_message(message, state)


@router.message(ExpenseState.AwaitingReimbursementChoice)
async def handle_reimbursement_choice(message: types.Message, state: FSMContext):
    if message.from_user.id != MY_ID: return
    
    text = message.text.strip()
    user_data = await state.get_data()
    matches = user_data.get("reimbursement_matches", [])
    valor_reembolsado = user_data.get("valor_reembolsado")
    
    if not text.isdigit():
        await message.answer("⚠️ Por favor, envie o número da opção (ex: 1).")
        return
    
    choice_idx = int(text) - 1
    if choice_idx < 0 or choice_idx >= len(matches):
        await message.answer("⚠️ Opção inválida.")
        return
    
    # Processa o reembolso com o item escolhido
    await process_reimbursement(message, matches, choice_idx, valor_reembolsado, sheets)
    await state.clear()

async def process_reimbursement(message, matches, choice_idx, valor_reembolsado, sheets_service):
    selected = matches[choice_idx]
    row_index = selected["row_index"]
    row_data = selected["row_data"]
    
    valor_compra = sheets_service.get_expense_value(row_data)
    valor_compra_abs = abs(valor_compra)
    diferenca = valor_reembolsado - valor_compra_abs
    
    resposta = ""
    
    if diferenca > 0:
        # Reembolso maior que a despesa: Capa o reembolso e cria entrada
        sheets_service.update_reimbursement(row_index, valor_compra_abs)
        
        # Cria nova entrada para o excedente
        descricao_excedente = f"Reembolso Excedente: {row_data[3]}"
        # Verifica se tag Reembolso existe, senão cria
        if "Reembolso" not in sheets_service.tag_options:
            sheets_service.add_category("Reembolso")
            
        sheets_service.add_expense(diferenca, descricao_excedente, 0, "Reembolso", "Pix") # Assume Pix/Transferência para o troco?
        
        resposta = (
            f"✅ Reembolso processado com excedente!\n"
            f"💰 A compra de R$ {valor_compra_abs:.2f} foi **totalmente quitada**.\n"
            f"📈 O troco de R$ {diferenca:.2f} foi salvo como uma nova **Entrada** (Tag: Reembolso)."
        )
    else:
        # Reembolso normal ou parcial
        sheets_service.update_reimbursement(row_index, valor_reembolsado)
        resposta = f"✅ Reembolso processado!\n💰 Compra de R$ {valor_compra_abs:.2f} - Reembolsado: R$ {valor_reembolsado:.2f}\n"
        
        if diferenca < 0: 
            resposta += f"📉 Faltam R$ {abs(diferenca):.2f}"
        else: 
            resposta += "✨ Valor reembolsado cobre exatamente a compra!"
            
    await message.answer(resposta)

@router.message(StateFilter(None))
async def handle_message(message: types.Message, state: FSMContext):
    if message.from_user.id != MY_ID: return

    await state.clear()
    text = message.text.strip()
    
    # 1. Tenta processar como reembolso
    reembolso_result = await ai_service.parse_reimbursement(text)
    
    if reembolso_result and reembolso_result.get("is_reimbursement"):
        # Lógica de reembolso...
        valor_reembolsado = reembolso_result.get("valor_reembolsado")
        data_compra = reembolso_result.get("data_compra")
        descricao_compra = reembolso_result.get("descricao_compra", "")
        
        if not valor_reembolsado:
            await message.answer("⚠️ Não consegui identificar o valor do reembolso.")
            return
        
        # Tenta buscar (se data for None, a busca deve suportar isso)
        matches = sheets.find_expense_by_date_and_desc(data_compra, descricao_compra)
        
        if not matches:
            await message.answer(f"⚠️ Não encontrei despesa de '{descricao_compra}'" + (f" em {data_compra}." if data_compra else "."))
            return
        
        if len(matches) > 1:
            # Matches multiplos - pede para o usuário escolher
            response_msg = "⚠️ Encontrei mais de uma transação. Qual delas?\n\n"
            match_options = []
            for idx, (row_idx, row) in enumerate(matches, 1):
                # row[0] is date, row[1] is val, row[3] is desc
                response_msg += f"{idx}. {row[0]} - {row[3]} ({row[1]})\n"
                match_options.append({"row_index": row_idx, "row_data": row})
            
            response_msg += "\nResponda com o número da opção (ex: 1)"
            
            await state.set_state(ExpenseState.AwaitingReimbursementChoice)
            await state.set_data({"reimbursement_matches": match_options, "valor_reembolsado": valor_reembolsado})
            await message.answer(response_msg)
            return

        # Único match - processa direto
        row_index, row_data = matches[0]
        match_idx = 0
        matches_data = [{"row_index": row_index, "row_data": row_data}]
        await process_reimbursement(message, matches_data, 0, valor_reembolsado, sheets)
        return

    # Passou direto se não for reembolso... (segue fluxo)


    tag_result = await ai_service.parse_tag_intent(text)
    if tag_result and tag_result.get("action"):
        action = tag_result.get("action")
        
        if action == "list":
            tags_str = ", ".join([f"`{t}`" for t in sheets.tag_options])
            await message.answer(f"📋 **Suas Tags:**\n{tags_str}")
            return
            
        if action == "create":
            new_tag = tag_result.get("tag_name")
            if new_tag:
                if sheets.add_category(new_tag):
                     await message.answer(f"✅ Tag **{new_tag}** criada com sucesso!")
                else:
                     await message.answer(f"⚠️ A tag **{new_tag}** já existe.")
            else:
                await message.answer("⚠️ Não entendi o nome da tag.")
            return

    # 3. Tenta processar como edição de transação passada
    edit_result = await ai_service.parse_past_edit(text, sheets.tag_options, sheets.metodo_options)

    if edit_result and edit_result.get("is_past_edit"):
        criteria = edit_result.get("search_criteria", {})
        updates = edit_result.get("updates", {})
        
        matches = sheets.find_transaction(
            date_query=criteria.get("date"),
            amount_query=criteria.get("amount"),
            desc_query=criteria.get("description")
        )
        
        if not matches:
            await message.answer("⚠️ Não encontrei nenhuma transação correspondente para editar.")
            return
        
        if len(matches) > 1:
            await message.answer(f"⚠️ Encontrei {len(matches)} transações parecidas. Tente ser mais específico (data ou valor exato).")
            return
        
        # Encontrou uma única transação
        row_index, row_data = matches[0]
        response_parts = ["✅ Transação atualizada!"]
        
        if updates.get("tag"):
            new_tag = str(updates["tag"]).capitalize()
            sheets.add_category(new_tag) # Cria se não existir
            sheets.update_expense_category(row_index, new_tag)
            response_parts.append(f"🏷️ Tag: {new_tag}")
            
        if updates.get("payment_method"):
            new_method = str(updates["payment_method"]).capitalize()
            # Validação simples
            if new_method not in sheets.metodo_options and "Caju" not in new_method: # Caju as sometimes it's distinct
                 pass 
            sheets.update_payment_method(row_index, new_method)
            response_parts.append(f"💳 Método: {new_method}")
            
        if updates.get("amount") is not None:
             # Mantém o sinal original da transação
            old_val = sheets.get_expense_value(row_data)
            new_val_abs = abs(float(updates["amount"]))
            new_val_signed = -new_val_abs if old_val < 0 else new_val_abs
            sheets.update_expense_value(row_index, new_val_signed)
            response_parts.append(f"💰 Valor: R$ {new_val_abs:.2f}")

        if updates.get("description"):
            new_desc = str(updates["description"])
            sheets.update_description(row_index, new_desc)
            response_parts.append(f"📝 Descrição: {new_desc}")
            
        await message.answer("\n".join(response_parts))
        return

    # 3. Tenta processar como despesa/entrada normal
    ai_result = await ai_service.parse_expense(text, sheets.expense_tags, sheets.income_tags)
    
    if ai_result and ai_result.get("valor") is not None:
        valor = float(ai_result["valor"])
        descricao = ai_result.get("descricao", "Sem descrição")
        tags = ai_result.get("tags", "Outros")
        metodo = ai_result.get("metodo_pagamento", "")
        
        is_gasto = valor < 0
        tipo_operacao = "Gasto" if is_gasto else "Entrada"
        
        # Salva o estado inicial e verifica o que falta
        current_data = {
            "valor": ai_result["valor"],
            "descricao": ai_result.get("descricao"),
            "tags": ai_result.get("tags"),
            "metodo_pagamento": ai_result.get("metodo_pagamento"),
            "type": tipo_operacao
        }
        await state.update_data(temp_expense=current_data)
        await check_missing_info(message, state)
        return

    else:
        # Se a IA não conseguir processar
        await message.answer(
            "⚠️ Não consegui entender a mensagem.\n\n"
            "📝 Tente usar um formato como:\n"
            "• \"Gastei 50 no mercado\"\n"
            "• \"Recebi 1000 de salário\"\n"
            "• \"Reembolso de 50 da compra de ontem\""
        )

@router.message(ExpenseState.AwaitingMissingInfo)
async def handle_missing_info_response(message: types.Message, state: FSMContext):
    if message.from_user.id != MY_ID: return
    
    text = message.text.strip()
    user_data = await state.get_data()
    missing_field = user_data.get("missing_field")
    temp_expense = user_data.get("temp_expense")
    
    if text.lower() == "cancelar":
        await message.answer("❌ Operação cancelada.")
        await state.clear()
        return

    # Atualiza o campo que estava faltando
    if missing_field == "tags":
        clean_tag = text.title()
        # Se não existir, cria (ou avisa? MVP: Cria)
        if clean_tag not in sheets.tag_options:
             sheets.add_category(clean_tag)
        temp_expense["tags"] = clean_tag
        
    elif missing_field == "metodo_pagamento":
        clean_method = text.title()
        # Validação simples
        if clean_method not in sheets.metodo_options and "Caju" not in clean_method: 
             # Aceita mas avisa, ou mapeia? Vamos aceitar o texto do user se não for absurdo
             pass
        temp_expense["metodo_pagamento"] = clean_method
        
    elif missing_field == "descricao":
        temp_expense["descricao"] = text
        
    # Salva atualização e verifica se falta mais algo
    await state.update_data(temp_expense=temp_expense)
    await check_missing_info(message, state)

async def check_missing_info(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    data = user_data.get("temp_expense")
    
    # Ordem de prioridade para perguntar
    if not data.get("descricao"):
        await state.update_data(missing_field="descricao")
        await state.set_state(ExpenseState.AwaitingMissingInfo)
        await message.answer("📝 Qual a descrição dessa transação?")
        return

    if not data.get("tags"):
        await state.update_data(missing_field="tags")
        await state.set_state(ExpenseState.AwaitingMissingInfo)
        opts = ", ".join(sheets.tag_options)
        await message.answer(f"🏷️ Qual a categoria (tag)?\nOpções: {opts}")
        return

    if not data.get("metodo_pagamento"):
        await state.update_data(missing_field="metodo_pagamento")
        await state.set_state(ExpenseState.AwaitingMissingInfo)
        opts = ", ".join(sheets.metodo_options)
        await message.answer(f"💳 Qual o método de pagamento?\nOpções: {opts}")
        return
        
    # Se chegou aqui, tem tudo! Salva.
    await final_save(message, state, data)

async def final_save(message, state, data):
    valor = data["valor"]
    descricao = data["descricao"]
    tags = data["tags"]
    metodo = data["metodo_pagamento"]
    tipo_operacao = data["type"]
    
    # Mapeamento final de metodo se precisar
    metodo_map = {"pix": "Pix", "crédito": "Crédito", "credito": "Crédito", "débito": "Débito", "debito": "Débito", "caju": "Caju"}
    metodo_pagamento_clean = metodo_map.get(metodo.lower(), metodo.capitalize())
        
    row_index = sheets.add_expense(valor, descricao, reembolsado=0, tags=tags, metodo_pagamento=metodo_pagamento_clean)
        
    valor_abs = abs(valor)
    emoji = "💸" if valor < 0 else "💰"
    resposta = f"{emoji} {tipo_operacao}: R$ {valor_abs:.2f}\n✅ Salvos na planilha!"
    resposta += f"\n🏷️ Tag: {tags}"
    resposta += f"\n💳 Método: {metodo_pagamento_clean}"
        
    await message.answer(resposta)

    # Entra em modo de edição
    await state.set_state(ExpenseState.AwaitingEdit)
    await state.set_data({"last_transaction_row": row_index})
    await message.answer("👆 Transação salva. Se precisar alterar algo, é só me dizer.")