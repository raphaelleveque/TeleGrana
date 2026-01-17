import pytest
from unittest.mock import MagicMock
from services.transaction_service import TransactionService
from models.transaction import Transaction

@pytest.fixture
def service():
    # Mock GoogleSheetsService
    ts = TransactionService()
    ts.sheets = MagicMock()
    return ts

def test_calculate_totals_basic(service):
    # Setup mock data
    # Rows: Data, Valor, Reembolsado, Descrição, Tags, Método
    mock_rows = [
        ["Data", "Valor", "Reembolsado", "Descrição", "Tags", "Método"],
        ["17/01/2026", "-100", "0", "Compra 1", "Mercado", "Crédito"],
        ["17/01/2026", "-50", "20", "Compra 2", "Lazer", "Pix"], # Net -30
        ["17/01/2026", "1000", "0", "Salário", "Salário", "Pix"],
    ]
    service.sheets.get_all_rows.return_value = mock_rows

    res = service.calculate_totals(start_date_str="17/01/2026")
    
    assert res["spent"] == 130.0 # 100 + (50-20)
    assert res["gain"] == 1000.0
    assert res["balance"] == 870.0

def test_calculate_totals_with_filters(service):
    mock_rows = [
        ["Data", "Valor", "Reembolsado", "Descrição", "Tags", "Método"],
        ["17/01/2026", "-100", "0", "Credito Item", "Tag", "Crédito"],
        ["17/01/2026", "-50", "0", "Pix Item", "Tag", "Pix"],
    ]
    service.sheets.get_all_rows.return_value = mock_rows

    # Filter only Credit
    res = service.calculate_totals(include_methods=["Crédito"])
    assert res["spent"] == 100.0
    
    # Exclude Credit (only Pix remains)
    res = service.calculate_totals(exclude_methods=["Crédito"])
    assert res["spent"] == 50.0

def test_process_reimbursement_surplus(service):
    # Transaction: -50 spent
    t = Transaction(date="17/01/2026", amount=-50.0, reimbursed_amount=0.0, 
                    description="Uber", category="Transporte", payment_method="Pix", row_index=2)
    
    # Reimburse 60 (10 surplus)
    res = service.process_reimbursement(t, 60.0)
    
    assert res["is_surplus"] is True
    assert res["surplus_amount"] == 10.0
    # Original should be capped at 50
    service.sheets.update_reimbursement.assert_called_with(2, 50.0)
    # New row for surplus
    service.sheets.add_expense.assert_called()

def test_normalize_text_logic():
    from services.transaction_service import normalize_text
    assert normalize_text("Café") == "cafe"
    assert normalize_text("Açúcar") == "acucar"
    assert normalize_text("Água mineral") == "agua mineral"
