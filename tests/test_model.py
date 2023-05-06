"""Testing for Models/model.py
run `python3 -m pytest` if VSCode Testing won't load

"""
from models import model
from app import app

def test_save_user():
    # Create a model and store the current user age
    mdl = model.Model()
    original_age = mdl.user.age
    # Change the user age and save the user
    mdl.user.age += 1
    with app.app_context():
        mdl.save_user()
    # Create a new model and check that the user age has been updated
    mdl2 = model.Model()
    assert mdl2.user.age == original_age + 1
    # Reset the age and save
    mdl.user.age = original_age
    with app.app_context():
        mdl.save_user()
    # Create a new model and check that the age is reset
    mdl3 = model.Model()
    assert mdl3.user.age == original_age
