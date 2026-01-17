from aiogram import Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from services.ai_handler import AIService
from services.transaction_service import TransactionService
from bot.states import ExpenseState
from models.transaction import Transaction
import os

router = Router()
service = TransactionService() # Renamed from 'sheets' to 'service'
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
    
    # Proteção: Antes de tentar editar, verifica se a mensagem parece uma NOVA intenção clara 
    # (como um novo reembolso ou gasto), para evitar falsos positivos de edição.
    reemb_check = await ai_service.parse_reimbursement(text)
    if reemb_check and reemb_check.get("is_reimbursement"):
        await state.clear()
        await handle_message(message, state)
        return

    ai_result = await ai_service.parse_edit_intent(text, service.tag_options, service.metodo_options)

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
            is_new = service.add_category(new_category)
            service.update_expense_category(last_row, new_category)
            response = f"✅ Categoria atualizada para **{new_category}**!"
            if is_new:
                response += f"\n🎉 Nova categoria criada: '{new_category}'."
        
        elif field == "valor":
            try:
                new_value_float = float(new_value)
                service.update_expense_value(last_row, new_value_float)
                response = f"✅ Valor alterado para **R$ {new_value_float:.2f}**!"
            except (ValueError, TypeError):
                await message.answer("⚠️ O valor fornecido não parece ser um número válido.")
                return

        elif field == "descricao":
            new_desc = str(new_value)
            service.update_description(last_row, new_desc)
            response = f"✅ Descrição alterada para: \"{new_desc}\"."

        elif field == "metodo_pagamento":
            new_method = str(new_value).capitalize()
            if new_method not in service.metodo_options:
                await message.answer(f"⚠️ Método de pagamento '{new_method}' não é válido. Opções: {', '.join(service.metodo_options)}.")
                return
            service.update_payment_method(last_row, new_method)
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
    await process_reimbursement(message, matches, choice_idx, valor_reembolsado, service)
    await state.clear()

async def process_reimbursement(message, matches_data, choice_idx, valor_reembolsado, service):
    # matches_data é lista de dicts com 'row_index' e 'row_data' (serializado)
    selected_data = matches_data[choice_idx]
    
    # Reconstrói objeto Transaction
    transaction = Transaction.from_row(selected_data["row_data"], row_index=selected_data["row_index"])
    
    # Delega lógica para o serviço
    result = service.process_reimbursement(
        transaction=transaction, 
        valor_reembolsado=valor_reembolsado
    )
    
    # Formata resposta com base no resultado
    resposta = ""
    if result["is_surplus"]:
        resposta = (
            f"✅ Reembolso processado com excedente!\n"
            f"💰 A compra de R$ {result['valor_compra_abs']:.2f} foi **totalmente quitada**.\n"
            f"📈 O troco de R$ {result['surplus_amount']:.2f} foi salvo como uma nova **Entrada** (Tag: Reembolso)."
        )
    else:
        diferenca = result["diferenca"]
        resposta = f"✅ Reembolso processado!\n💰 Compra de R$ {result['valor_compra_abs']:.2f} - Reembolsado: R$ {result['valor_reembolsado']:.2f}\n"
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
        matches = service.find_expense_by_date_and_desc(data_compra, descricao_compra)
        
        if not matches:
            await message.answer(f"⚠️ Não encontrei despesa de '{descricao_compra}'" + (f" em {data_compra}." if data_compra else "."))
            return
        
        if len(matches) > 1:
            # Matches multiplos - pede para o usuário escolher
            response_msg = "⚠️ Encontrei mais de uma transação. Qual delas?\n\n"
            match_options = []
            
            # matches é lista de Transaction objects
            for idx, transaction in enumerate(matches, 1):
                response_msg += f"{idx}. {transaction.date} - {transaction.description} ({transaction.amount})\n"
                # Serializa para o estado
                match_options.append({"row_index": transaction.row_index, "row_data": transaction.to_row()})
            
            response_msg += "\nResponda com o número da opção (ex: 1)"
            
            await state.set_state(ExpenseState.AwaitingReimbursementChoice)
            await state.set_data({"reimbursement_matches": match_options, "valor_reembolsado": valor_reembolsado})
            await message.answer(response_msg)
            return

        # Único match - processa direto
        transaction = matches[0]
        # Serializa para manter consistência com a função process_reimbursement genérica
        matches_data = [{"row_index": transaction.row_index, "row_data": transaction.to_row()}]
        await process_reimbursement(message, matches_data, 0, valor_reembolsado, service)
        return

    # Passou direto se não for reembolso... (segue fluxo)


    tag_result = await ai_service.parse_tag_intent(text)
    if tag_result and tag_result.get("action"):
        action = tag_result.get("action")
        
        if action == "list":
            tags_str = ", ".join([f"`{t}`" for t in service.tag_options])
            await message.answer(f"📋 **Suas Tags:**\n{tags_str}")
            return
            
        if action == "create":
            new_tag = tag_result.get("tag_name")
            if new_tag:
                if service.add_category(new_tag):
                     await message.answer(f"✅ Tag **{new_tag}** criada com sucesso!")
                else:
                     await message.answer(f"⚠️ A tag **{new_tag}** já existe.")
            else:
                await message.answer("⚠️ Não entendi o nome da tag.")
            return

    # 3. Tenta processar como consulta (Get)
    query_result = await ai_service.parse_query_intent(text, service.metodo_options)
    if query_result and query_result.get("is_query"):
        totals = service.calculate_totals(
            start_date_str=query_result.get("start_date"),
            end_date_str=query_result.get("end_date"),
            query_type=query_result.get("query_type"),
            exclude_methods=query_result.get("exclude_methods"),
            include_methods=query_result.get("include_methods")
        )
        
        period_lab = query_result.get("label") or "período"
        qt = query_result.get("query_type")
        msg = f"📊 **Resumo de {period_lab}:**\n"
        
        if query_result.get("exclude_methods"):
            msg += f"🚫 (Excluindo: {', '.join(query_result['exclude_methods'])})\n"
        if query_result.get("include_methods"):
            msg += f"🎯 (Apenas: {', '.join(query_result['include_methods'])})\n"
            
        msg += "\n"
        
        # Mostra o Gasto Líquido
        if qt == "spent" or qt == "summary":
            msg += f"💸 **Gastos Líquidos:** R$ {totals['spent']:.2f}\n"
            
            # Adiciona breakdown se houver itens
            if totals["items"]:
                # Pega os 5 maiores gastos
                expenses = [i for i in totals["items"] if i["val"] < 0]
                expenses.sort(key=lambda x: x["val"]) # Mais negativos primeiro
                
                if expenses:
                    msg += "__Principais itens:__\n"
                    for item in expenses[:5]:
                        msg += f"• {item['desc']}: `R$ {abs(item['val']):.2f}`\n"
            msg += "\n"

        # Mostra Total Recebido
        if qt == "gain" or qt == "summary":
            msg += f"💰 **Total Recebido:** R$ {totals['gain']:.2f}\n"
            
            # Adiciona breakdown de ganhos se houver e for relevante
            if qt == "gain" or totals["gain"] > 0:
                gains = [i for i in totals["items"] if i["val"] > 0]
                gains.sort(key=lambda x: x["val"], reverse=True)
                if gains:
                    msg += "__Principais ganhos:__\n"
                    for item in gains[:5]:
                        msg += f"• {item['desc']}: `R$ {item['val']:.2f}`\n"
            msg += "\n"
            
        if qt == "summary":
            msg += f"⚖️ **Saldo Líquido:** R$ {(totals['gain'] - totals['spent']):.2f}"
            
        await message.answer(msg)
        return

    # 4. Tenta processar como despesa/entrada normal
    ai_result = await ai_service.parse_expense(text, service.expense_tags, service.income_tags)
    
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
            "data": ai_result.get("data"),
            "type": tipo_operacao
        }
        await state.update_data(temp_expense=current_data)
        await check_missing_info(message, state)
        return

    # 4. Tenta processar como edição de transação passada
    edit_result = await ai_service.parse_past_edit(text, service.tag_options, service.metodo_options)

    if edit_result and edit_result.get("is_past_edit"):
        criteria = edit_result.get("search_criteria", {})
        updates = edit_result.get("updates", {})
        
        matches = service.find_transaction(
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
        transaction = matches[0]
        row_index = transaction.row_index
        response_parts = ["✅ Transação atualizada!"]
        
        if updates.get("tag"):
            new_tag = str(updates["tag"]).capitalize()
            # Validação/Criação já tratada no service.add_category se fosse o caso, mas aqui usamos o service proxy
            service.add_category(new_tag) # Garante que existe na lista validada
            service.update_expense_category(row_index, new_tag)
            response_parts.append(f"🏷️ Tag: {new_tag}")
            
        if updates.get("payment_method"):
            new_method = str(updates["payment_method"]).capitalize()
            service.update_payment_method(row_index, new_method)
            response_parts.append(f"💳 Método: {new_method}")
            
        if updates.get("amount") is not None:
             # Mantém o sinal original da transação
            old_val = transaction.amount
            new_val_abs = abs(float(updates["amount"]))
            new_val_signed = -new_val_abs if old_val < 0 else new_val_abs
            service.update_expense_value(row_index, new_val_signed)
            response_parts.append(f"💰 Valor: R$ {new_val_abs:.2f}")

        if updates.get("description"):
            new_desc = str(updates["description"])
            service.update_description(row_index, new_desc)
            response_parts.append(f"📝 Descrição: {new_desc}")
            
        await message.answer("\n".join(response_parts))
        return

    # Se nada funcionou
    await message.answer(
        "🤔 Não entendi muito bem. Você pode dizer algo como:\n"
        "• 'Gastei 50 reais no mercado'\n"
        "• 'Altere o valor para 100'\n"
        "• 'Reembolsou 20 reais do Uber de ontem'"
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
        if clean_tag not in service.tag_options:
             service.add_category(clean_tag)
        temp_expense["tags"] = clean_tag
        
    elif missing_field == "metodo_pagamento":
        clean_method = text.title()
        # Validação simples
        if clean_method not in service.metodo_options and "Caju" not in clean_method: 
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
        opts = ", ".join(service.tag_options)
        await message.answer(f"🏷️ Qual a categoria (tag)?\nOpções: {opts}")
        return

    if not data.get("metodo_pagamento"):
        await state.update_data(missing_field="metodo_pagamento")
        await state.set_state(ExpenseState.AwaitingMissingInfo)
        opts = ", ".join(service.metodo_options)
        await message.answer(f"💳 Qual o método de pagamento?\nOpções: {opts}")
        return
        
    # Se chegou aqui, tem tudo! Salva.
    await final_save(message, state, data)

async def final_save(message, state, data):
    # Delega salvamento ao TransactionService
    result = service.create_transaction(
        valor=data["valor"],
        descricao=data["descricao"],
        tags=data["tags"],
        metodo=data["metodo_pagamento"],
        data=data.get("data")
    )
    
    data_formatada = data.get("data") or "hoje"
        
    valor_abs = result["valor_abs"]
    emoji = "💸" if result["is_expense"] else "💰"
    tipo_operacao = data["type"] # Poderia vir do result tbm se quisesse
    
    resposta = f"{emoji} {tipo_operacao}: R$ {valor_abs:.2f}\n📅 Data: {data_formatada}\n✅ Salvos na planilha!"
    resposta += f"\n🏷️ Tag: {result['tags']}"
    resposta += f"\n💳 Método: {result['metodo_clean']}"
        
    await message.answer(resposta)

    # Entra em modo de edição
    await state.set_state(ExpenseState.AwaitingEdit)
    await state.set_data({"last_transaction_row": result["row_index"]})
    await message.answer("👆 Transação salva. Se precisar alterar algo, é só me dizer.")