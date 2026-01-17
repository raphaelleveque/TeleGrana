def get_expense_classification_prompt(text, expense_tags, income_tags, current_date):
    return f"""
    Você é um assistente financeiro pessoal. Estamos em {current_date}.
    Analise a frase: "{text}"
    
    CLASSIFIQUE como:
    - GASTO: quando é saída de dinheiro (ex: "gastei", "paguei", "comprei")
    - ENTRADA: quando é recebimento de dinheiro (ex: "recebi", "ganhei", "salário")
    
    REGRAS DE CLASSIFICAÇÃO:
    - tags para GASTOS: {expense_tags}
    - tags para ENTRADAS: {income_tags}
    - METODOLOGIA ESPECIAL: Toda vez que houver uma **entrada/receita** relacionada a "vale alimentação", "alimentação" ou "VR" no método "Caju", a "tags" DEVE ser obrigatoriamente "Salário".
    - metodo_pagamento: Escolha APENAS uma: [Pix, Crédito, Débito, Caju]. Se não mencionado, retorne null.
    - data: extraia a data mencionada no formato dd/mm/yyyy. Se não mencionado, retorne null. 
    - Se o usuário disser "dia 13", assuma o mês e ano atuais de {current_date}.
    
    IMPORTANTE:
    - Se for GASTO: o valor deve ser NEGATIVO (ex: -400)
    - Se for ENTRADA: o valor deve ser POSITIVO (ex: 10000)
    
    PROIBIÇÕES TÓXICAS (NUNCA FAÇA):
    - É **PROIBIDO** inventar ou "alucinar" valores baseados em conhecimento externo (Ex: Não invente que um PS5 custa 3500 se o usuário não disse o preço).
    - Se o usuário não mencionar o valor gasto, mas sim apenas um valor de REEMBOLSO (ex: "comprei pão, me devolveram 5 reais"), o campo "valor" deve ser **null**. NÃO use o valor do reembolso como se fosse o valor da compra.
    
    Mais Regras:
    - Se a tag não se encaixar perfeitamente ou não for mencionada, retorne null.
    - A descricao deve ser uma versão resumida e clara. Se não houver descrição clara, use null.
    
    Retorne APENAS um JSON:
    {{
        "valor": float (negativo para gastos, positivo para entradas ou null),
        "descricao": str (ou null),
        "tags": str (ou null),
        "metodo_pagamento": str (ou null),
        "data": str (dd/mm/yyyy ou null)
    }}
    Se não houver valor, retorne null.
    """

def get_reimbursement_prompt(text, current_date):
    return f"""
    Você é um assistente financeiro pessoal. Estamos em {current_date}.
    Analise se a seguinte frase é sobre um REEMBOLSO: "{text}"
    
    Se for sobre reembolso, extraia:
    - valor_reembolsado: valor que foi reembolsado (float)
    - data_compra: data da compra original (formato dd/mm/yyyy). Se o usuário disser "dia 15" e não especificar mês/ano, assuma mês/ano atual ({current_date}).
    - descricao_compra: descrição da compra que foi reembolsada (ex: "mercado", "compra no mercado")
    
    Retorne APENAS um JSON:
    {{
        "is_reimbursement": true,
        "valor_reembolsado": float (null se não encontrado),
        "data_compra": str no formato dd/mm/yyyy (null se não especificado),
        "descricao_compra": str (null se não especificado)
    }}
    """


def get_past_edit_prompt(text, all_tags, metodo_options):
    return f"""
    Você é um assistente financeiro. Analise a frase: "{text}"

    O usuário quer alterar ou corrigir uma transação que já foi feita? 
    Isso deve ser verdade APENAS se houver verbos de correção (alterar, mudar, corrigir, trocar) ou se ele estiver fornecendo uma informação que falta para algo já citado (ex: "aquele gasto de ontem foi no crédito").

    REGRAS CRÍTICAS:
    - Se o usuário está simplesmente avisando de uma compra ("comprei X", "gastei Y", "recebi Z"), "is_past_edit" DEVE ser false. Isso é uma NOVA inserção.
    - Se não houver intenção clara de MUDANÇA, retorne false.

    Retorne APENAS um JSON:
    {{
        "is_past_edit": boolean,
        "search_criteria": {{
            "date": str (dd/mm/yyyy, "today", "yesterday" ou null),
            "amount": float (null se não descreveu o valor original),
            "description": str (null se não descreveu)
        }},
        "updates": {{
            "amount": float (null se não mudar),
            "description": str (null se não mudar),
            "tag": str (null se não mudar),
            "payment_method": str (null se null se não mudar)
        }}
    }}

    EXEMPLOS NEGATIVOS (is_past_edit: false):
    - "eu comprei um playstation 5 por 4000 reais" -> Isso é novo!
    - "gastei 50 no mercado" -> Isso é novo!
    - "recebi 200 de presente" -> Isso é novo!

    EXEMPLOS POSITIVOS (is_past_edit: true):
    - "mude o valor daquela compra de ontem para 100"
    - "a tag da passagem de aviao na verdade é viagem"
    - "o gasto de 400 reais de hoje foi no pix (corrigindo)"
    """

def get_tag_intent_prompt(text):
    return f"""
    Você é um assistente. O usuário quer gerenciar tags.
    Frase: "{text}"

    Identifique a intenção:
    - LISTAR: "quais são minhas tags?", "listar categorias", "ver tags".
    - CRIAR: "crie a tag Gasolina", "adicionar categoria Investimentos", "nova tag Lazer".

    Retorne APENAS um JSON:
    {{
        "action": "list" | "create" | null,
        "tag_name": str (apenas se action == create, Capitalizado, sem 'tag' ou 'categoria')
    }}
    
    Exemplos:
    "Crie a tag Viagem" -> {{"action": "create", "tag_name": "Viagem"}}
    "Adicionar categoria Carro" -> {{"action": "create", "tag_name": "Carro"}}
    "Quais tags existem?" -> {{"action": "list", "tag_name": null}}
    """

def get_query_intent_prompt(text, current_date, metodo_options):
    return f"""
    Você é um assistente financeiro. Estamos em {current_date}.
    Analise a pergunta do usuário sobre seus gastos/ganhos: "{text}"

    Identifique os parâmetros da consulta:
    1. DATE_RANGE:
       - "start_date": data de início no formato dd/mm/yyyy.
       - "end_date": data de fim no formato dd/mm/yyyy (exclusive, ou seja, até o início desse dia).
       - "label": como descrever esse período (ex: "hoje", "ontem", "anteontem", "esta semana", "semana passada", "dia 12").
    2. QUERY_TYPE:
       - "spent": quanto gastou.
       - "gain": quanto ganhou/recebeu.
       - "summary": resumo, saldo total (ganhos - gastos).
    3. FILTERS:
       - "exclude_methods": Lista de métodos de pagamento a EXCLUIR (ex: "sem caju").
       - "include_methods": Lista de métodos de pagamento a INCLUIR exclusivamente (ex: "no crédito").
    
    Opções de métodos conhecidos: {metodo_options}

    DICAS DE DATA:
    - Hoje: {current_date}
    - Ontem: dia anterior a {current_date}
    - Semana passada: intervalo de 7 dias terminando no último domingo.
    - Dia X: start_date=X/mes/ano, end_date=(X+1)/mes/ano.

    Retorne APENAS um JSON:
    {{
        "is_query": true,
        "start_date": str (dd/mm/yyyy) | null,
        "end_date": str (dd/mm/yyyy) | null,
        "label": str,
        "query_type": "spent" | "gain" | "summary",
        "exclude_methods": [str],
        "include_methods": [str]
    }}
    """

def get_intent_router_prompt(text):
    return f"""
    Você é o roteador de um assistente financeiro. 
    Sua missão é IDENTIFICAR a intenção do usuário na frase: "{text}"

    Escolha APENAS UM dos intents abaixo:
    1. "insert": O usuário está relatando um novo gasto ou ganho (ex: "comprei", "recebi", "paguei", "vendi", "almoço 50 reais").
    2. "reimburse": O usuário está falando sobre um REEMBOLSO de algo já comprado (ex: "reembolsou", "recebi estorno de").
    3. "query": O usuário quer ver um resumo, relatório ou saldo (ex: "quanto gastei", "meus gastos", "saldo", "total do mês").
    4. "edit": O usuário quer ALTERAR uma transação que ele acabou de registrar ou uma específica do passado (ex: "mude a tag", "corrija o valor", "não foi no pix").
    5. "tags": O usuário quer gerenciar categorias (ex: "quais minhas tags", "crie a tag X").
    6. "other": Se não se encaixar em nenhum acima.

    REGRAS CRÍTICAS:
    - Se a frase contiver um VALOR e um ITEM (ex: "picolé 11 reais"), o intent é "insert".
    - **PRIORIDADE**: Se a frase contiver palavras como "reembolsou", "reembolso", "estornou" ou "estorno", o intent é SEMPRE "reimburse", mesmo que o usuário mencione que comprou o item (ex: "comprei um jogo e ele foi reembolsado").
    - Se a frase for uma pergunta genérica sobre dinheiro gasto, é "query".

    Retorne APENAS um JSON:
    {{
        "intent": "insert" | "reimburse" | "query" | "edit" | "tags" | "other"
    }}
    """
