from services.google_sheets import GoogleSheetsService
from models.transaction import Transaction
import unicodedata

def normalize_text(text):
    """Remove acentos e converte para minúsculas."""
    if not text: return ""
    return "".join(
        c for c in unicodedata.normalize('NFD', str(text).lower())
        if unicodedata.category(c) != 'Mn'
    )

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
                query_norm = normalize_text(desc_query)
                keywords = query_norm.split()
                desc_norm = normalize_text(transaction.description or "")
                all_found = True
                for kw in keywords:
                    if kw not in desc_norm:
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

    def create_transaction(self, valor, descricao, tags, metodo, data=None):
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
            
        row_index = self.sheets.add_expense(valor, descricao, 0, tags, metodo_clean, data_custom=data)
        
        return {
            "row_index": row_index,
            "valor": valor,
            "valor_abs": abs(valor),
            "descricao": descricao,
            "tags": tags,
            "metodo_clean": metodo_clean,
            "is_expense": valor < 0
        }

    def calculate_totals(self, start_date_str=None, end_date_str=None, query_type=None, exclude_methods=None, include_methods=None):
        """
        Calcula totais de gastos ou ganhos baseado em um range de datas e filtros.
        Gasto = abs(Amount + Reimbursed) para Amount < 0.
        Ganho = Amount para Amount > 0.
        """
        from datetime import datetime, timedelta
        
        all_rows = self.sheets.get_all_rows()
        now = datetime.now()
        
        start_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%d/%m/%Y")
            except ValueError:
                pass
        
        end_date = None
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%d/%m/%Y")
            except ValueError:
                pass
        
        total_spent = 0.0
        total_gain = 0.0
        items_included = []
        
        # Filtros normalizados
        excl_norm = [m.title() for m in (exclude_methods or [])]
        incl_norm = [m.title() for m in (include_methods or [])]

        for row in all_rows[1:]:
            t = Transaction.from_row(row)
            
            # 1. Filtro de Data
            try:
                t_date_str = t.date.split()[0]
                t_date = datetime.strptime(t_date_str, "%d/%m/%Y")
                
                if start_date and t_date < start_date:
                    continue
                if end_date and t_date >= end_date:
                    continue
            except (ValueError, IndexError, TypeError):
                continue
                
            # 2. Filtro de Métodos (Caju, Crédito, etc)
            metodo_t = (t.payment_method or "").title()
            
            if excl_norm and metodo_t in excl_norm:
                continue
            if incl_norm and metodo_t not in incl_norm:
                continue
            
            # 3. Lógica de Cálculo
            # Gasto Líquido = Amount + Reimbursed (se < 0)
            # Ganho = Amount + Reimbursed (se > 0)
            net_val = t.amount + t.reimbursed_amount
            
            if net_val < 0:
                abs_net = abs(net_val)
                total_spent += abs_net
                items_included.append({
                    "desc": t.description or "Sem descrição",
                    "val": -abs_net,
                    "date": t_date_str
                })
            elif net_val > 0:
                total_gain += net_val
                items_included.append({
                    "desc": t.description or "Sem descrição",
                    "val": net_val,
                    "date": t_date_str
                })
            # Se net_val == 0, ignoramos do total (totalmente reembolsado)
                
        return {
            "spent": total_spent,
            "gain": total_gain,
            "balance": total_gain - total_spent,
            "items": items_included,
            "query_type": query_type
        }

    # Proxy methods for updates (could be refactored further but needed for edit handlers)
    def update_expense_category(self, row, val): return self.sheets.update_expense_category(row, val)
    def update_expense_value(self, row, val): return self.sheets.update_expense_value(row, val)
    def update_description(self, row, val): return self.sheets.update_description(row, val)
    def update_payment_method(self, row, val): return self.sheets.update_payment_method(row, val)
