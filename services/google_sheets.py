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

        self.expense_tags = ["Mercado", "Viagem", "Restaurante", "Academia", "Compras", "Gasolina", "Outros"]
        self.income_tags = ["Salário", "Presente", "Reembolso", "Outros"]
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

    def add_expense(self, valor, descricao, reembolsado=0, tags="", metodo_pagamento="", data_custom=None):
        """Adiciona uma nova linha de gasto e retorna o número da linha.
        
        Args:
            valor: Valor numérico do gasto
            descricao: Descrição do gasto
            reembolsado: Valor reembolsado em reais (padrão: 0)
            tags: Tag da categoria (padrão: "")
            metodo_pagamento: Método de pagamento (padrão: "")
            data_custom: Data no formato dd/mm/yyyy (opcional)
        
        Returns:
            int: O número da linha onde os dados foram inseridos.
        """
        if data_custom:
            data = data_custom
        else:
            data = datetime.now().strftime('%d/%m/%Y %H:%M')
            
        # Ordem: Data, Valor, Reembolsado, Descrição, Tags, Método de Pagamento
        nova_linha = [data, valor, reembolsado, descricao, tags, metodo_pagamento]
        result = self.ws.append_row(nova_linha)

        # Extrai o número da linha do resultado. Ex: 'Sheet1!A12:F12' -> 12
        range_str = result['updates']['updatedRange']
        # Remove o nome da planilha e pega o número da linha
        row_number_str = ''.join(filter(str.isdigit, range_str.split('!')[1].split(':')[0]))
        return int(row_number_str)
    
        return matches
    
    # Logic moved to TransactionService
    def get_all_rows(self):
        """Retorna todas as linhas da planilha."""
        return self.ws.get_all_values()
    
    # Logic moved to TransactionService
    def find_transaction_logic_placeholder(self):
        pass

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