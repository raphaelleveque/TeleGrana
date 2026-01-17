import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bot.handlers import handle_edit
from bot.states import ExpenseState

@pytest.mark.asyncio
async def test_handle_edit_insert_intent_clears_state():
    """
    Testa se ao enviar um novo gasto ('insert') enquanto o bot espera uma ediçao,
    ele limpa o estado e processa como novo.
    """
    # Mocking message
    message = AsyncMock()
    message.text = "Uber 25 no Pix"
    message.from_user.id = 12345
    
    # Mocking state
    state = AsyncMock()
    
    # Mocking AI and Service (already global in handlers.py, we patch them)
    with patch('bot.handlers.ai_service', new_callable=AsyncMock) as mock_ai, \
         patch('bot.handlers.handle_message', new_callable=AsyncMock) as mock_handle_msg, \
         patch('bot.handlers.MY_ID', 12345):
        
        # Simula o roteador dizendo que é um INSERT
        mock_ai.detect_intent.return_value = {"intent": "insert"}
        
        await handle_edit(message, state)
        
        # Verificações
        state.clear.assert_called_once()
        mock_handle_msg.assert_called_once_with(message, state)
        # Nao deve chamar o especialista de ediçao
        mock_ai.parse_past_edit.assert_not_called()

@pytest.mark.asyncio
async def test_handle_edit_actual_edit():
    """
    Testa se ao enviar uma correção, ele chama o especialista de edição.
    """
    message = AsyncMock()
    message.text = "O valor é 30"
    message.from_user.id = 12345
    state = AsyncMock()
    state.get_data.return_value = {"last_transaction_row": 5}
    
    with patch('bot.handlers.ai_service', new_callable=AsyncMock) as mock_ai, \
         patch('bot.handlers.service') as mock_service, \
         patch('bot.handlers.MY_ID', 12345):
        
        mock_ai.detect_intent.return_value = {"intent": "edit"}
        mock_ai.parse_past_edit.return_value = {
            "is_past_edit": True,
            "updates": {"amount": 30.0}
        }
        # Mocking find_transaction or similar if needed, but handle_edit uses sheets directly sometimes
        mock_service.sheets.get_all_rows.return_value = [["Header"], ["Row 1"], ["Row 2"], ["Row 3"], ["Row 4"], ["17/01", "-50", "0"]]
        mock_service.get_expense_value.return_value = -50.0

        await handle_edit(message, state)
        
        mock_ai.parse_past_edit.assert_called_once()
        mock_service.update_expense_value.assert_called_with(5, -30.0)
        state.clear.assert_called_once()
