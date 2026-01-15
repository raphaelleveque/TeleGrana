import os
import gspread
from datetime import datetime
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

        
    def test_connectivity(self):
        """Retorna True se conseguir ler o título da planilha."""
        return bool(self.sh.title)

    def setup_headers(self):    
        """Cria os cabeçalhos: Data, Valor, Reembolsado, Descrição, Tags e Método de Pagamento."""
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
        
        tag_options = ["Mercado", "Viagem", "Restaurante", "Academia", "Compras", "Outros"]
        metodo_options = ["Pix", "Crédito", "Débito", "Caju"]

        set_data_validation_for_cell_range(
            self.ws, 
            "E2:E1000", 
            DataValidationRule(
                BooleanCondition('ONE_OF_LIST', tag_options),
                showCustomUi=True
            )
        )

        set_data_validation_for_cell_range(
            self.ws, 
            "F2:F1000", 
            DataValidationRule(
                BooleanCondition('ONE_OF_LIST', metodo_options),
                showCustomUi=True
            )
        )

    def add_expense(self, valor, descricao, reembolsado=False, tags="", metodo_pagamento=""):
        """Adiciona uma nova linha de gasto.
        
        Args:
            valor: Valor numérico do gasto
            descricao: Descrição do gasto
            reembolsado: Se foi reembolsado (padrão: False)
            tags: Tag da categoria (padrão: "")
            metodo_pagamento: Método de pagamento (padrão: "")
        """
        data = datetime.now().strftime('%d/%m/%Y %H:%M')
        # Ordem: Data, Valor, Reembolsado, Descrição, Tags, Método de Pagamento
        nova_linha = [data, valor, reembolsado, descricao, tags, metodo_pagamento]
        self.ws.append_row(nova_linha)