from aiogram.fsm.state import State, StatesGroup

class ExpenseState(StatesGroup):
    AwaitingEdit = State()
