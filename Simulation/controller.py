from model import Model
from view import View

class Controller:
    def __init__(self):
        self.model = Model()
        self.view = View(self)
            
    def main(self):
        self.view.make_frames(self.model.params) #inital param_vals loaded from json
        self.view.main() #just has the mainloop() that keeps the window open
        
    # this function called by DWFrame whenever input string modified by user
    def update(self, *args): # *args because StringVar() gives a lot of data in callbacks
        params_vals = self.model.run_calcs(self.view.get_params_vals()) #feeds data from view to model
        self.view.set_params(params_vals) #... and back to view again
        self.model.save_params(self.view.get_params_vals())        

if __name__ == '__main__':
    simulator = Controller()
    simulator.main()
    