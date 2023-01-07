from models import model

def test_param_loading():
    assert model.load_params() != None