"""Testing for Models/user.py
run `python3 -m pytest` if VSCode Testing won't load

"""
from models.user import UserForm, append_field
from models.model import Model
from app import app

with app.app_context():
    form = UserForm(obj=Model().user)

# Define a test case for the income field
def test_append_income():
    initial_length = len(form.income_profiles.entries)
    with app.app_context():
        append_field(form, field = 'income')
    assert len(form.income_profiles.entries) == initial_length + 1

# Define a test case for the kid field
def test_append_kid():
    initial_length = len(form.kids.entries)
    with app.app_context():
        append_field(form, field = 'kid')
    assert len(form.kids.entries) == initial_length + 1

# Define a test case for the earning field
def test_append_earning():
    initial_length = len(form.earnings.entries)
    with app.app_context():
        append_field(form, field = 'earning')
    assert len(form.earnings.entries) == initial_length + 1
