# python -m pytest test_pytest.py

from models import model

def test_param_loading():
    # confirm that all parameter names in the details are also in the values dict and vice versa
    vals,details = model.load_params()
    assert not (details.keys() ^ vals.keys())
