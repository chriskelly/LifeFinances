from model import Model
from view import View

CALCD_PARAMS = ["Yearly Budget"]

class Controller:
    def __init__(self):
        self.model = Model()
        self.view = View(self)
            
    def main(self):
        self.view.make_frames(self.model.param_vals,CALCD_PARAMS)
        self.view.main()
    
    def _get_params(self):
        return self.view.get_param_vals()
        
    def update(self, *args): # *args because StringVar() gives a lot of data in callbacks
        self.run_calcs()
        self.model.save_params(self._get_params())
        
    def run_calcs(self):
        params = self._get_params()         
        monthly_list = [params["Budget (Monthly)"]]
        yearly_list = [self._get_params()["Budget (Yearly)"]]
        self.view.set_val("Yearly Budget",self.model.sum_yearly_budget(monthly_list,yearly_list))
        

if __name__ == '__main__':
    simulator = Controller()
    simulator.main()
    