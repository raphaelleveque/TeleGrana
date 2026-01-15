import os
import gspread
from datetime import datetime

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
        """Cria os cabeçalhos se a primeira linha estiver vazia."""
        headers = ["Data", "Usuário", "Valor", "Reembolsado", "Descricao", "Tags"]
        first_row = self.ws.row_values(1)
        
        if not first_row:
            self.ws.insert_row(headers, 1)
            # Formata em negrito usando notação A1
            self.ws.format("A1:F1", {"textFormat": {"bold": True}})
            return "Headers criados."
        return "Headers já existentes."

    def add_expense(self, user, valor, descricao, reembolsado=False, tags=""):
        """Adiciona uma nova linha de gasto."""
        data = datetime.now().strftime('%d/%m/%Y %H:%M')
        # Google Sheets entende True/False como checkbox se configurado
        nova_linha = [data, user, valor, reembolsado, descricao, tags]
        self.ws.append_row(nova_linha)