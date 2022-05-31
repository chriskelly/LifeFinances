from model import Model
from dashboard import Dashboard
from popout import Popout

class Controller:
    def __init__(self):
        self.model = Model()
        self.dashboard = Dashboard(self)
        self.param_frames ={}
            
    def main(self):
        self.dashboard.main() #just has the mainloop() that keeps the window open
        
    # this function called by DWFrame whenever input string modified by user
    def update(self, *args): # *args because StringVar() gives a lot of data in callbacks
        params_vals = self.model.run_calcs(self.get_params_vals()) #feeds data from frames to model
        self.update_frames(params_vals) #... and back to frames again
        self.model.save_params(self.get_params_vals()) # use this rather than params_val to keep string format for json
        
    def make_popout(self,id:int):
        popout_params = self.model.filter_params(include=True,attr="popout",attr_val=id)
        popout = Popout(window=self.dashboard,controller=self)
        frames = popout.make_frames(popout_params)
        for param,frame in frames.items():
            self.param_frames[param]=frame
            
    def get_params_vals(self):
        """Pull values from frames and return a dict of param names:values"""
        params_vals = {key:obj["val"] for (key,obj) in self.model.params.items()} # get all the old values to start with in case some frames haven't been intiated
        for k in self.param_frames.keys():
            params_vals[k]=self.param_frames[k].val_var.get()
        return params_vals
    
    def update_frames(self, params: dict):
        """Update all calculated tk.Entries to passed-in param:values"""
        for param,value in params.items():
            if "calcd" in self.model.params[param] and param in self.param_frames: # second condition prevents crashes if the frame of a calcd variable hasn't been loaded yet
                self.param_frames[param].val_var.set(value)

if __name__ == '__main__':
    simulator = Controller()
    simulator.main()
    