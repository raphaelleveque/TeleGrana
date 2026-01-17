import pytest
from services.ai_handler import AIService

@pytest.fixture(scope="module")
def ai_service():
    return AIService()

@pytest.mark.asyncio
@pytest.mark.parametrize("text,expected_intent", [
    # Insertion
    ("Gastei 50 reais no McDonald's", "insert"),
    ("Recebi 5000 de salário hoje", "insert"),
    ("Comprei hoje um picolé no crédito de 11 reais", "insert"),
    ("Almoço 45 reais no Pix", "insert"),
    ("Paguei 20 no Caju", "insert"),
    ("Acabei de ganhar 100 reais num sorteio", "insert"),
    ("Vendi meu Kindle por 300 reais", "insert"),
    
    # Query
    ("Quanto eu gastei essa semana?", "query"),
    ("Qual meu saldo total?", "query"),
    ("Resumo do mês de janeiro", "query"),
    ("Quanto gastei no crédito em dezembro?", "query"),
    ("Saldo sem considerar o Caju", "query"),
    ("Qual foi meu maior gasto esse ano?", "query"),
    ("Me mostre meus ganhos deste mês", "query"),
    
    # Reimburse
    ("Eu comprei um playstation 5 dia 16, minha mae reembolsou 2000 reais", "reimburse"),
    ("Reembolsou 20 reais do Uber", "reimburse"),
    ("Recebi estorno de 50 reais da Amazon", "reimburse"),
    ("Estorno do iFood dia 12", "reimburse"),
    ("A empresa reembolsou os 100 da viagem", "reimburse"),
    ("Recebi o estorno do ingresso", "reimburse"),
    ("Aquele gasto do mercado foi estornado", "reimburse"),
    
    # Edit
    ("Mude a tag da última compra para Lazer", "edit"),
    ("Ajuste o valor para 100 reais", "edit"),
    ("Não foi no Pix, foi no Crédito", "edit"),
    ("Corrija o nome para Supermercado", "edit"),
    ("Altere a data daquela compra pra ontem", "edit"),
    ("Mude a descrição do gasto de 50 reais", "edit"),
    ("Edite a transação de hoje cedo", "edit"),
    ("Conserte a tag do almoço", "edit"),
    
    # Tags
    ("Quais são as minhas tags?", "tags"),
    ("Crie a tag Viagem", "tags"),
    ("Remova a categoria Lazer", "tags"),
    ("Listar todas as categorias", "tags"),
    ("Quero ver as tags de gasto", "tags"),
    ("Adicione 'Investimento' às minhas categorias", "tags"),
    
    # Other
    ("Oi, tudo bem?", "other"),
    ("Como você funciona?", "other"),
    ("Obrigado", "other"),
    ("Me conte uma piada", "other"),
    ("Qual o sentido da vida?", "other"),
    ("Tchau", "other"),
    ("Bom dia pessoal", "other"),
    ("Quero falar com um humano", "other"),
    ("Você sabe latir?", "other"),
    ("Pode me ajudar com uma coisa?", "other"),
    ("Quem te criou?", "other"),
])
async def test_detect_intent(ai_service, text, expected_intent):
    result = await ai_service.detect_intent(text)
    assert result.get("intent") == expected_intent
