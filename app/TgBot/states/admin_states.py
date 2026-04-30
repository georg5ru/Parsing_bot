from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    waiting_broadcast_text = State()
    waiting_price_value = State()