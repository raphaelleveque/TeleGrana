def get_expense_classification_prompt(text, expense_tags, income_tags):
    return f"""
    Você é um assistente financeiro pessoal. Analise a frase: "{text}"
    
    CLASSIFIQUE como:
    - GASTO: quando é saída de dinheiro (ex: "gastei", "paguei", "comprei")
    - ENTRADA: quando é recebimento de dinheiro (ex: "recebi", "ganhei", "salário")
    
    REGRAS DE CLASSIFICAÇÃO:
    - tags para GASTOS: {expense_tags}
    - tags para ENTRADAS: {income_tags}
    - metodo_pagamento: Escolha APENAS uma: [Pix, Crédito, Débito, Caju]. Se não mencionado, retorne null.
    
    IMPORTANTE:
    - Se for GASTO: o valor deve ser NEGATIVO (ex: -400)
    - Se for ENTRADA: o valor deve ser POSITIVO (ex: 10000)
    - Se a tag não se encaixar perfeitamente ou não for mencionada, retorne null (não use 'Outros' por padrão).
    - Se o método de pagamento não for mencionado, retorne null.
    - A descricao deve ser uma versão resumida e clara. Se não houver descrição clara, use null.
    
    Retorne APENAS um JSON:
    {{
        "valor": float (negativo para gastos, positivo para entradas),
        "descricao": str (ou null),
        "tags": str (ou null),
        "metodo_pagamento": str (ou null)
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

    - Se o usuário quer mudar a CATEGORIA, o campo é 'tags'. As opções de tags conhecidas são: {all_tags}. Se for uma nova, extraia o nome da nova tag.
    - Se o usuário quer mudar o MÉTODO DE PAGAMENTO, o campo é 'metodo_pagamento'. As opções são: {metodo_options}. Use a forma canônica (ex: "Cartão de Crédito" -> "Crédito").
    - Se o usuário quer mudar o VALOR, o campo é 'valor'. O valor deve ser um float.
    - Se o usuário quer mudar a DESCRIÇÃO, o campo é 'descricao'. O valor deve ser uma string.

    Retorne APENAS um JSON com o seguinte formato:
    {{
        "is_edit_request": boolean,
        "field": str, // 'valor', 'descricao', 'tags', ou 'metodo_pagamento'
        "value": any // O novo valor para o campo
    }}

    Se não for um pedido de edição, retorne "is_edit_request": false.

    EXEMPLOS:
    - "Altere o valor para 150 reais" -> {{"is_edit_request": true, "field": "valor", "value": 150.0}}
    - "O método de pagamento foi Cartão de Crédito" -> {{"is_edit_request": true, "field": "metodo_pagamento", "value": "Crédito"}}
    - "A categoria é Viagem" -> {{"is_edit_request": true, "field": "tags", "value": "Viagem"}}
    - "Na verdade, a descrição é 'Almoço com cliente'" -> {{"is_edit_request": true, "field": "descricao", "value": "Almoço com cliente"}}
    - "Pode colocar na categoria Gasolina" -> {{"is_edit_request": true, "field": "tags", "value": "Gasolina"}}
    - "ok obrigado" -> {{"is_edit_request": false, "field": null, "value": null}}
    - "Gastei 50 reais no mercado" -> {{"is_edit_request": false, "field": null, "value": null}}
    """

def get_past_edit_prompt(text, all_tags, metodo_options):
    return f"""
    Você é um assistente financeiro. Analise a frase: "{text}"

    O usuário quer alterar uma transação JÁ EXISTENTE (passada).
    Identifique:
    1. Critérios de busca (para encontrar QUAL transação editar):
       - data_busca: "hoje", "ontem" ou data dd/mm/yyyy.
       - valor_busca: valor original mencionado (float).
       - descricao_busca: palavras-chave para identificar a transação.
    
    2. O que alterar (novos valores):
       - novo_valor: se ele quiser mudar o valor.
       - nova_descricao: se quiser mudar a descrição.
       - nova_tag: se quiser mudar a categoria. (Opções: {all_tags})
       - novo_metodo: se quiser mudar o método de pagamento. (Opções: {metodo_options})

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
            "payment_method": str (null se não mudar)
        }}
    }}

    EXEMPLOS:
    "A entrada do dia de hoje de 400 reais, recebi no pix"
    -> {{ "is_past_edit": true, "search_criteria": {{ "date": "today", "amount": 400.0, "description": null }}, "updates": {{ "payment_method": "Pix" }} }}

    "A despesa de 500 reais de hoje, classifique-a como mercado"
    -> {{ "is_past_edit": true, "search_criteria": {{ "date": "today", "amount": 500.0, "description": null }}, "updates": {{ "tag": "Mercado" }} }}

    "O gasto com Uber de ontem mude para 45 reais"
    -> {{ "is_past_edit": true, "search_criteria": {{ "date": "yesterday", "description": "Uber" }}, "updates": {{ "amount": 45.0 }} }}
    
    "Gastei 50 rais"
    -> {{ "is_past_edit": false }}
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
