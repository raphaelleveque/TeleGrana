import pytest
import json
from datetime import datetime
from services.ai_handler import AIService

EXPENSE_TAGS = ["Alimentação", "Lazer", "Transporte", "Farmácia", "Uber", "Mercado"]
INCOME_TAGS = ["Salário", "Reembolso", "Freela"]
METHODS = ["Pix", "Crédito", "Débito", "Caju"]

@pytest.fixture(scope="module")
def ai_service():
    return AIService()

@pytest.mark.asyncio
async def test_parse_expense_complex(ai_service):
    text = "R$ 120,50 no supermercado dia 15 no cartao de debito"
    res = await ai_service.parse_expense(text, EXPENSE_TAGS, INCOME_TAGS)
    assert res["valor"] == -120.5
    assert "supermercado" in res["descricao"].lower()
    assert res["metodo_pagamento"] == "Débito"

@pytest.mark.asyncio
async def test_parse_income_extra(ai_service):
    text = "Vendi meu celular por 800 reais no Pix"
    res = await ai_service.parse_expense(text, EXPENSE_TAGS, INCOME_TAGS)
    assert res["valor"] == 800.0
    assert "celular" in res["descricao"].lower()
    assert res["metodo_pagamento"] == "Pix"

@pytest.mark.asyncio
async def test_parse_query_dates(ai_service):
    text = "Quanto gastei de 01/01 a 10/01?"
    res = await ai_service.parse_query_intent(text, METHODS)
    assert res["start_date"] == "01/01/2026"
    # End date is exclusive (next day)
    assert res["end_date"] == "11/01/2026"

@pytest.mark.asyncio
async def test_parse_expense_simple_prompt(ai_service):
    text = "Gastei 1500 na viagem de ferias"
    res = await ai_service.parse_expense(text, EXPENSE_TAGS, INCOME_TAGS)
    assert res["valor"] == -1500.0
    assert "viagem" in res["descricao"].lower()
    assert res["tags"] in ["Viagem", "Lazer", "Transporte"] # Flexible tag

@pytest.mark.asyncio
async def test_parse_query_relative(ai_service):
    text = "Quanto gastei no Uber desde ontem?"
    res = await ai_service.parse_query_intent(text, METHODS)
    assert res["query_type"] == "spent"
    assert res["include_methods"] == [] # Implicit all if not mentioned

@pytest.mark.asyncio
async def test_parse_reimbursement_no_date(ai_service):
    text = "Recebi reembolso de 50 reais do iFood"
    res = await ai_service.parse_reimbursement(text)
    assert res["valor_reembolsado"] == 50.0
    assert "ifood" in res["descricao_compra"].lower()

@pytest.mark.asyncio
async def test_parse_expense_no_item(ai_service):
    # Testing case where only value exists
    text = "Gastei 50 hoje"
    res = await ai_service.parse_expense(text, EXPENSE_TAGS, INCOME_TAGS)
    assert res["valor"] == -50.0
    assert res["descricao"] is not None # Accept any AI-generated description
