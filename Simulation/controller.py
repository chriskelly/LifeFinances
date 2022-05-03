from model import Model
from view import View

class Controller:
    def __init__(self):
        self.model = Model()
        self.view = View(self)
        
        self.calcd_values = {}
        '''#TODO store values to be calc'd in a list here.
        The dual widget frame can be fed a disable/enable based on 
            if the parameter exists in the calc'd list
        All params, including calc'd params, should be stored in the param_vals
            and the params.json and synced as changes made
        Could make it to where if the value is true/false, DWFrame makes a checkbox
            rather than an entry. Everything else would be either enabled or disabled entries
        How to track entries? Create them in view and feed them to DWFrame 
            or make them in DWFrame? Need to be able to pull value, which could just be a 
            method in DWFrame. Could accomodate for whatever widget is used.
        '''
    
    def main(self):
        self.view.make_entries(self.model.param_vals)
        self.run_calcs(first=True)
        self.view.layout()
        self.view.live_updating()
        self.view.main()
    
    def _get_params(self):
        return self.view.get_param_vals()
        
    def save_params(self):
        self.model.save_params(self._get_params())
        
    def live_updating(self):
        self.view.live_updating()
        
    def run_calcs(self,first=False):
        params = self._get_params()         
        monthly_list = [params["Budget (Monthly)"]]
        yearly_list = [self._get_params()["Budget (Yearly)"]]
        self.calcd_values["Yearly Budget"]=self.model.sum_yearly_budget(monthly_list,yearly_list)
        
        if not first: #update labels only after labels have been created in UI section
            self.view.update_labels(self.calcd_values)
        

if __name__ == '__main__':
    simulator = Controller()
    simulator.main()
    