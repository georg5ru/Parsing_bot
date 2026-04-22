from aiogram.fsm.state import State, StatesGroup


class SettingsStates(StatesGroup):
    choosing_option = State()
    choosing_format = State()
    choosing_period = State()