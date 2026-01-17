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
    - metodo_pagamento: Escolha APENAS uma: [Pix, Crédito, Débito, Caju]. Se não mencionado, retorne null.
    - data: extraia a data mencionada no formato dd/mm/yyyy. Se não mencionado, retorne null. 
      Se o usuário disser "dia 13", assuma o mês e ano atuais de {current_date}.
    
    IMPORTANTE:
    - Se for GASTO: o valor deve ser NEGATIVO (ex: -400)
    - Se for ENTRADA: o valor deve ser POSITIVO (ex: 10000)
    - Se a tag não se encaixar perfeitamente ou não for mencionada, retorne null.
    - A descricao deve ser uma versão resumida e clara. Se não houver descrição clara, use null.
    
    Retorne APENAS um JSON:
    {{
        "valor": float (negativo para gastos, positivo para entradas),
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
        "is_reimbursement": boolean,
        "valor_reembolsado": float (null se não for reembolso),
        "data_compra": str no formato dd/mm/yyyy (null se não especificado),
        "descricao_compra": str (null se não especificado)
    }}
    
    EXEMPLO de reembolso:
    "Minha mae me deu 500 reais para reembolsar o mercado que eu fiz no dia 15"
    -> {{"is_reimbursement": true, "valor_reembolsado": 500.0, "data_compra": "15/XX/XXXX", "descricao_compra": "mercado"}} (use o ano e mês corretos)
    """

def get_edit_intent_prompt(text, all_tags, metodo_options):
    return f"""
    Você é um assistente financeiro. O usuário acabou de registrar uma transação e pode querer editá-la.
    Analise a frase do usuário: "{text}"

    A frase indica que o usuário quer ALTERAR ou CORRIGIR algum campo da transação anterior?
    Os campos editáveis são: 'valor', 'descricao', 'tags', 'metodo_pagamento'.

    REGRAS:
    - Se o usuário quer mudar a CATEGORIA/TAG, o campo é 'tags'. Opções conhecidas: {all_tags}.
    - Se o usuário quer mudar o MÉTODO, o campo é 'metodo_pagamento'. Opções: {metodo_options}.
    - Se o usuário quer mudar o VALOR, o campo é 'valor'.
    - Se o usuário quer mudar a DESCRIÇÃO, o campo é 'descricao'.

    IMPORTANTE: 
    - Se a frase for um REEMBOLSO de algo (ex: "Minha mãe reembolsou..."), "is_edit_request" DEVE ser false. Reembolsos NÃO são edições de transações anteriores.
    - Se a frase parecer o registro de uma NOVA transação, "is_edit_request" DEVE ser false.

    Retorne APENAS um JSON:
    {{
        "is_edit_request": boolean,
        "field": str (ou null),
        "value": any (ou null)
    }}

    EXEMPLOS:
    - "Altere o valor para 150" -> {{"is_edit_request": true, "field": "valor", "value": 150.0}}
    - "A categoria é Viagem" -> {{"is_edit_request": true, "field": "tags", "value": "Viagem"}}
    - "Minha mãe reembolsou 15000" -> {{"is_edit_request": false, "field": null, "value": null}}
    - "Gastei 50 no mercado" -> {{"is_edit_request": false, "field": null, "value": null}}
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
