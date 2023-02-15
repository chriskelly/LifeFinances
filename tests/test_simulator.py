"""Testing for simulator.py
run `python -m pytest` if VSCode Testing won't load

"""
import simulator

test_sim = simulator.test_unit()

def test_val():
    """Test quarterly modifier in simulator.val function"""
    test_sim.params['test_value'] = 15
    assert test_sim.val('test_value', quart_modifier='rate') == 2
    assert test_sim.val('test_value', quart_modifier='dollar') == 3.75
    assert test_sim.val('test_value', quart_modifier=None) == 15
