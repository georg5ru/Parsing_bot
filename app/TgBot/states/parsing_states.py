from aiogram.fsm.state import State, StatesGroup


class ParsingStates(StatesGroup):
    choosing_platform = State()
    entering_account = State()
    choosing_period = State()