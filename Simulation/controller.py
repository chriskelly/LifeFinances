from model import Model
from view import View
from dashboard import Dashboard
from popout import Popout

class Controller:
    def __init__(self):
        self.model = Model()
        #self.view = View(self)
        self.dashboard = Dashboard()
            
    def main(self):
        primary_view_params = self.model.filter_params(include=False,attr="pop-out")
        # self.view.make_frames(primary_view_params) #inital param_vals loaded from json
        # self.view.main() #just has the mainloop() that keeps the window open
        primary_view = Popout(self.dashboard,self)
        primary_view.make_frames(primary_view_params)
        self.dashboard.main()
        
    # this function called by DWFrame whenever input string modified by user
    def update(self, *args): # *args because StringVar() gives a lot of data in callbacks
        params_vals = self.model.run_calcs(self.view.get_params_vals()) #feeds data from view to model
        self.view.set_params(params_vals) #... and back to view again
        self.model.save_params(self.view.get_params_vals())    
        
    def make_pop_out_view(self,id:int):
        view = View(self)
        view_params = self.model.filter_params(include=True,attr="pop-out",attr_val=id)
        view.make_frames(view_params)

if __name__ == '__main__':
    simulator = Controller()
    simulator.main()
    