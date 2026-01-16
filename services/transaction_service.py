from services.google_sheets import GoogleSheetsService
from models.transaction import Transaction

class TransactionService:
    def __init__(self):
        self.sheets = GoogleSheetsService()

    def initialize_sheet(self):
        """Verifica se a planilha está vazia e cria os headers se necessário."""
        return self.sheets.setup_headers()

    @property
    def tag_options(self):
        return self.sheets.tag_options

    @property
    def metodo_options(self):
        return self.sheets.metodo_options
    
    @property
    def expense_tags(self):
        return self.sheets.expense_tags

    @property
    def income_tags(self):
        return self.sheets.income_tags

    def add_category(self, category):
        return self.sheets.add_category(category)

    def find_expense_by_date_and_desc(self, data_compra, descricao_compra):
        """Busca uma despesa por data (opcional) e descrição (fuzzy). Retorna lista de Transaction."""
        all_rows = self.sheets.get_all_rows()
        matches = []
        
        # Stopwords para ignorar na busca
        stopwords = {"de", "do", "da", "em", "no", "na", "com", "a", "o", "compra", "gasto", "despesa"}
        
        # Prepara termos de busca
        search_terms = [word.lower() for word in descricao_compra.split() if word.lower() not in stopwords]
        
        # Data de busca normalizada (se existir)
        data_busca_norm = None
        if data_compra:
             parts = data_compra.split('/')
             if len(parts) >= 2: 
                 data_busca_norm = data_compra
        
        # Itera de trás pra frente (mais recentes primeiro)
        # Offset start=2 because header is 1, and 0-indexed list implies row 2 is index 1. 
        # Wait, enumerate idx matches row number in sheet logic?
        # get_all_rows returns list of lists.
        # Row 1 is header. Row 2 is first 
        # enumerate(all_rows[1:], start=2) means idx is the actual 1-based row number in Sheets. Correct.
        data_rows = list(enumerate(all_rows[1:], start=2))
        data_rows.reverse() 
        
        for idx, row in data_rows:
            transaction = Transaction.from_row(row, row_index=idx)
            
            # 1. Verifica Reembolso e Se é Gasto
            # Ignorar Entradas (Valores positivos) - Lógica de Negócio!
            if transaction.is_income:
                continue
                
            if transaction.reimbursed_amount >= abs(transaction.amount):
                continue

            # 2. Verifica Data (se fornecida)
            match_data = True
            if data_busca_norm:
                data_celula_date_part = transaction.date.split()[0]
                if data_busca_norm not in data_celula_date_part:
                    match_data = False
            
            # 3. Verifica Descrição (Fuzzy)
            match_desc = False
            desc_lower = (transaction.description or "").lower()
            
            if not search_terms: 
                 search_terms = [w.lower() for w in descricao_compra.split()]

            found_terms = 0
            for term in search_terms:
                if term in desc_lower:
                    found_terms += 1
            
            if len(search_terms) == 1:
                match_desc = found_terms == 1
            else:
                match_desc = found_terms >= 1
            
            if match_data and match_desc:
                matches.append(transaction)
                if len(matches) >= 5: break
        
        return matches

    def find_transaction(self, date_query=None, amount_query=None, desc_query=None):
        """Busca genérica para edição passada. Retorna lista de Transaction."""
        from datetime import datetime, timedelta # Import local ou mover pro topo
        
        all_rows = self.sheets.get_all_rows()
        data_rows = list(enumerate(all_rows[1:], start=2))
        data_rows.reverse()
        
        matches = []
        
        # Normalização do date_query
        date_check = None
        if date_query:
            if date_query.lower() in ["hoje", "today"]:
                date_check = datetime.now().strftime("%d/%m/%Y")
            elif date_query.lower() in ["ontem", "yesterday"]:
                date_check = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
            else:
                date_check = date_query

        for idx, row in data_rows:
            transaction = Transaction.from_row(row, row_index=idx)
            
            # Checa Data
            if date_check and date_check not in transaction.date:
                continue
            
            # Checa Valor
            if amount_query is not None:
                if abs(transaction.amount) != abs(amount_query):
                     continue

            # Checa Descrição
            if desc_query:
                keywords = desc_query.lower().split()
                desc_lower = (transaction.description or "").lower()
                all_found = True
                for kw in keywords:
                    if kw not in desc_lower:
                        all_found = False
                        break
                if not all_found:
                    continue
            
            matches.append(transaction)
            if len(matches) >= 5: break
            
        return matches
        
    def get_expense_value(self, row_data):
        return self.sheets.get_expense_value(row_data)

    # --- Business Logic ---

    def process_reimbursement(self, transaction: Transaction, valor_reembolsado):
        """
        Executa a lógica de reembolso:
        - Calcula diferença.
        - Se excedente: capa original, cria nova entrada 'Reembolso'.
        - Se normal: atualiza original.
        Retorna um dict com resultados para a UI.
        """
        valor_compra_abs = abs(transaction.amount)
        diferenca = valor_reembolsado - valor_compra_abs
        
        result = {
            "valor_compra_abs": valor_compra_abs,
            "valor_reembolsado": valor_reembolsado,
            "diferenca": diferenca,
            "is_surplus": False,
            "surplus_amount": 0,
            "row_index": transaction.row_index
        }

        if diferenca > 0:
            # Excedente: Capa o reembolso no valor original
            self.sheets.update_reimbursement(transaction.row_index, valor_compra_abs)
            
            # Cria nova entrada para o excedente
            descricao_excedente = f"Reembolso Excedente: {transaction.description}"
            
            # Garante que a tag existe
            if "Reembolso" not in self.sheets.tag_options:
                self.sheets.add_category("Reembolso")
            
            # Salva o excedente (Pix por padrão para transferências)
            self.sheets.add_expense(diferenca, descricao_excedente, 0, "Reembolso", "Pix")
            
            result["is_surplus"] = True
            result["surplus_amount"] = diferenca
        else:
            # Normal ou parcial
            self.sheets.update_reimbursement(transaction.row_index, valor_reembolsado)

        return result

    def create_transaction(self, valor, descricao, tags, metodo):
        """
        Limpa dados e salva nova transação.
        """
        # Mapeamento de métodos comuns
        metodo_map = {
            "pix": "Pix", 
            "crédito": "Crédito", "credito": "Crédito", 
            "débito": "Débito", "debito": "Débito", 
            "caju": "Caju"
        }
        
        if metodo:
            metodo_clean = metodo_map.get(metodo.lower(), metodo.capitalize())
        else:
            metodo_clean = ""
            
        row_index = self.sheets.add_expense(valor, descricao, 0, tags, metodo_clean)
        
        return {
            "row_index": row_index,
            "valor": valor,
            "valor_abs": abs(valor),
            "descricao": descricao,
            "tags": tags,
            "metodo_clean": metodo_clean,
            "is_expense": valor < 0
        }

    # Proxy methods for updates (could be refactored further but needed for edit handlers)
    def update_expense_category(self, row, val): return self.sheets.update_expense_category(row, val)
    def update_expense_value(self, row, val): return self.sheets.update_expense_value(row, val)
    def update_description(self, row, val): return self.sheets.update_description(row, val)
    def update_payment_method(self, row, val): return self.sheets.update_payment_method(row, val)
