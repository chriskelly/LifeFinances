from model import Model
from view import View

CALCD_PARAMS = ["Domestic Proportion"]

class Controller:
    def __init__(self):
        self.model = Model()
        self.view = View(self,CALCD_PARAMS) #feeding CALCD_PARAMS so that view knows which inputs to disable
            
    def main(self):
        self.view.make_frames(self.model.params) #inital param_vals loaded from json
        self.view.main() #just has the mainloop() that keeps the window open
        
    #function called whenever input string modified by user
    def update(self, *args): # *args because StringVar() gives a lot of data in callbacks
        params = self.model.run_calcs(self.view.get_params()) #feeds data from view to model
        self.view.set_params(params) #... and back to view again
        self.model.save_params(self.view.get_params())        

if __name__ == '__main__':
    simulator = Controller()
    simulator.main()
    