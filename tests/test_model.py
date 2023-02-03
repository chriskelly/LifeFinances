"""Testing for Models/model.py
run `python -m pytest` if VSCode Testing won't load

"""
import sqlalchemy as db
from models import model

def test_load_params():
    """confirm that all parameter names in the details are also in the values dict and vice versa
    """
    vals, details = model.load_params()
    assert vals # confirm vals loaded and isn't empty
    assert details # confirm details loaded and isn't empty
    assert not details.keys() ^ vals.keys()

def test_db_cmd():
    """Confirm the Database connection works"""
    table_column_map = {
        'job_incomes' : 'starting_income',
        'kids' : 'birth_year',
        'earnings_records' : 'year',
        'users' : 'user_age'
    }
    test_value = -1
    for table, column in table_column_map.items():
        # First create a new row with the test value in the specific column
        model.db_cmd(db.text(f'INSERT INTO {table} ({column}) VALUES ({test_value})'))
        # Then read that value from the database
        values, columns = model.db_cmd(db.text(f'SELECT * from {table}\
                                                WHERE {column} = {test_value}'))
        # Confirm it matches
        assert values[0][list(columns).index(column)] == test_value
        # Delete the created data
        model.db_cmd(db.text(f'DELETE FROM {table} WHERE {column} = {test_value}'))
