import os
import gspread
from datetime import datetime, timedelta, date
from gspread_formatting import *

class GoogleSheetsService:
    def __init__(self):
        self.gc = gspread.service_account(filename='credentials.json')
        sheet_id = os.getenv('GOOGLE_SHEET_ID')
        
        if not sheet_id:
            raise ValueError("❌ GOOGLE_SHEET_ID não encontrado no .env!")
            
        try:
            self.sh = self.gc.open_by_key(sheet_id)
            self.ws = self.sh.get_worksheet(0)
        except Exception as e:
            print(f"❌ Erro ao abrir planilha com ID: {sheet_id}")
            raise e

        self.expense_tags = ["Mercado", "Viagem", "Restaurante", "Academia", "Compras", "Outros"]
        self.income_tags = ["Salário", "Presente", "Outros"]
        self.tag_options = list(set(self.expense_tags + self.income_tags))
        self.metodo_options = ["Pix", "Crédito", "Débito", "Caju"]

        
    def test_connectivity(self):
        """Retorna True se conseguir ler o título da planilha."""
        return bool(self.sh.title)

    def setup_headers(self):    
        """Cria os cabeçalhos: Data, Valor, Reembolsado (valor em reais), Descrição, Tags e Método de Pagamento."""
        headers = [
            "Data", 
            "Valor", 
            "Reembolsado", 
            "Descrição", 
            "Tags", 
            "Método de Pagamento"
        ]
        
        first_row = self.ws.row_values(1)
        
        if not first_row:
            self.ws.insert_row(headers, 1)
            self.ws.format("A1:F1", {"textFormat": {"bold": True}})
            self.apply_validations()
            return "Headers criados com as novas categorias."

        return "Headers já existentes."
    
    def apply_validations(self):
        """Define as listas suspensas para as colunas Tags (F) e Método (G)."""
        
        set_data_validation_for_cell_range(
            self.ws, 
            "E2:E1000", 
            DataValidationRule(
                BooleanCondition('ONE_OF_LIST', self.tag_options),
                showCustomUi=True
            )
        )

        set_data_validation_for_cell_range(
            self.ws, 
            "F2:F1000", 
            DataValidationRule(
                BooleanCondition('ONE_OF_LIST', self.metodo_options),
                showCustomUi=True
            )
        )

    def add_category(self, category, category_type='expense'):
        """Adiciona uma nova categoria à lista de validação e atualiza a planilha.

        Args:
            category: A nova categoria a ser adicionada.
            category_type: 'expense' or 'income'.
        """
        if category_type == 'expense':
            if category not in self.expense_tags:
                self.expense_tags.append(category)
                self.tag_options = list(set(self.expense_tags + self.income_tags))
                self.apply_validations()
                return True
        elif category_type == 'income':
            if category not in self.income_tags:
                self.income_tags.append(category)
                self.tag_options = list(set(self.expense_tags + self.income_tags))
                self.apply_validations()
                return True
        return False

    def add_expense(self, valor, descricao, reembolsado=0, tags="", metodo_pagamento=""):
        """Adiciona uma nova linha de gasto e retorna o número da linha.
        
        Args:
            valor: Valor numérico do gasto
            descricao: Descrição do gasto
            reembolsado: Valor reembolsado em reais (padrão: 0)
            tags: Tag da categoria (padrão: "")
            metodo_pagamento: Método de pagamento (padrão: "")
        
        Returns:
            int: O número da linha onde os dados foram inseridos.
        """
        data = datetime.now().strftime('%d/%m/%Y %H:%M')
        # Ordem: Data, Valor, Reembolsado, Descrição, Tags, Método de Pagamento
        nova_linha = [data, valor, reembolsado, descricao, tags, metodo_pagamento]
        result = self.ws.append_row(nova_linha)

        # Extrai o número da linha do resultado. Ex: 'Sheet1!A12:F12' -> 12
        range_str = result['updates']['updatedRange']
        # Remove o nome da planilha e pega o número da linha
        row_number_str = ''.join(filter(str.isdigit, range_str.split('!')[1].split(':')[0]))
        return int(row_number_str)
    
    def find_expense_by_date_and_desc(self, data_compra, descricao_compra):
        """Busca uma despesa por data e descrição.
        
        Args:
            data_compra: Data no formato dd/mm/yyyy
            descricao_compra: Descrição ou palavra-chave da compra
            
        Returns:
            Lista de tuplas (row_index, row_data) com as despesas encontradas
        """
        # Busca todas as linhas (pula o cabeçalho)
        all_rows = self.ws.get_all_values()
        matches = []
        
        # Normaliza a data de busca (remove hora se houver)
        data_busca = data_compra.split()[0] if ' ' in data_compra else data_compra
        
        for idx, row in enumerate(all_rows[1:], start=2):  # Começa na linha 2 (pula header)
            if len(row) < 6:
                continue
                
            data_celula = row[0]  # Coluna A - Data
            descricao_celula = row[3].lower() if len(row) > 3 else ""  # Coluna D - Descrição
            reembolsado_celula = row[2] if len(row) > 2 else "0"  # Coluna C - Reembolsado
            
            # Verifica se já está totalmente reembolsado (valor reembolsado >= valor da compra)
            try:
                valor_reembolsado = float(str(reembolsado_celula).replace(',', '.')) if reembolsado_celula else 0
                valor_compra = self.get_expense_value(row)
                # Se já foi reembolsado igual ou mais que o valor, pula
                if valor_reembolsado >= valor_compra:
                    continue
            except:
                pass  # Se não conseguir calcular, continua a busca
            
            # Verifica data (pode ter hora, então compara só a data)
            data_celula_sem_hora = data_celula.split()[0] if ' ' in data_celula else data_celula
            
            # Normaliza datas para comparação (dd/mm/yyyy)
            # Remove zeros à esquerda e normaliza formato
            def normalize_date(date_str):
                parts = date_str.split('/')
                if len(parts) == 3:
                    return f"{int(parts[0]):02d}/{int(parts[1]):02d}/{parts[2]}"
                return date_str
            
            try:
                data_busca_norm = normalize_date(data_busca)
                data_celula_norm = normalize_date(data_celula_sem_hora)
                data_match = data_busca_norm == data_celula_norm or data_busca in data_celula_sem_hora or data_celula_sem_hora in data_busca
            except:
                # Fallback para comparação simples
                data_match = data_busca in data_celula_sem_hora or data_celula_sem_hora in data_busca
            
            # Verifica se a descrição contém a palavra-chave
            desc_match = descricao_compra.lower() in descricao_celula or descricao_celula in descricao_compra.lower()
            
            if data_match and desc_match:
                matches.append((idx, row))
        
        return matches
    
    def find_transaction(self, date_query=None, amount_query=None, desc_query=None):
        """Busca transação flexível para edição.
        
        Args:
            date_query: 'today', 'yesterday' ou data dd/mm/yyyy
            amount_query: valor float (busca exata ou aproximada)
            desc_query: string parcial
            
        Returns:
            Lista de tuplas (row_index, row_data)
        """
        all_rows = self.ws.get_all_values()
        matches = []
        
        # Resolve a data
        target_date_str = None
        if date_query:
            if date_query == 'today':
                target_date_str = datetime.now().strftime('%d/%m/%Y')
            elif date_query == 'yesterday':
                target_date_str = (datetime.now() - timedelta(days=1)).strftime('%d/%m/%Y')
            else:
                target_date_str = date_query
        
        for idx, row in enumerate(all_rows[1:], start=2):
            if len(row) < 6: continue
            
            # Dados da linha
            row_date_str = row[0].split()[0] # remove hora
            row_desc = row[3]
            try:
                row_val = self.get_expense_value(row)
                row_val_abs = abs(row_val)
            except:
                row_val_abs = 0

            # Checks
            match_date = True
            if target_date_str:
                # Normalização simples de string
                match_date = (target_date_str in row_date_str)
            
            match_amount = True
            if amount_query is not None:
                # Compara valor absoluto, permitindo pequena margem
                query_abs = abs(float(amount_query))
                match_amount = abs(query_abs - row_val_abs) < 0.1
            
            match_desc = True
            if desc_query:
                match_desc = desc_query.lower() in row_desc.lower()

            if match_date and match_amount and match_desc:
                matches.append((idx, row))
                
        return matches

    def update_reimbursement(self, row_index, valor_reembolsado):
        """Atualiza o valor reembolsado de uma despesa (coluna C).
        
        Args:
            row_index: Índice da linha (1-based)
            valor_reembolsado: Valor em reais que foi reembolsado
        """
        # Coluna C é o índice 3 (A=1, B=2, C=3)
        self.ws.update_cell(row_index, 3, valor_reembolsado)

    def update_expense_category(self, row_index, category):
        """Atualiza a categoria (tag) de uma despesa.

        Args:
            row_index: Índice da linha a ser atualizada.
            category: A nova categoria a ser definida.
        """
        # Coluna E (5) é a de Tags
        self.ws.update_cell(row_index, 5, category)

    def update_expense_value(self, row_index, value):
        """Atualiza o valor de uma despesa (coluna B)."""
        self.ws.update_cell(row_index, 2, value)

    def update_description(self, row_index, description):
        """Atualiza a descrição de uma despesa (coluna D)."""
        self.ws.update_cell(row_index, 4, description)

    def update_payment_method(self, row_index, method):
        """Atualiza o método de pagamento de uma despesa (coluna F)."""
        self.ws.update_cell(row_index, 6, method)
    
    def get_expense_value(self, row_data):
        """Extrai o valor de uma linha de despesa.
        
        Args:
            row_data: Lista com os valores da linha
            
        Returns:
            float: Valor da despesa
        """
        if len(row_data) > 1:
            try:
                return float(str(row_data[1]).replace(',', '.'))
            except (ValueError, TypeError):
                return 0.0
        return 0.0