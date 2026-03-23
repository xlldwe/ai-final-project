from aiogram.fsm.state import State, StatesGroup


class OrderStates(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    waiting_address = State()
    waiting_delivery_type = State()
    confirming_order = State()


class AdminAddItem(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_price = State()
    waiting_category = State()


class AdminRemoveItem(StatesGroup):
    waiting_item_id = State()


class FeedbackStates(StatesGroup):
    waiting_feedback = State()