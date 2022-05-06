import tkinter as tk
from tkinter import ttk
from dualWidgetFrame import DWFrame

class View(tk.Tk):
    def __init__(self,controller,CALCD_PARAMS:list):
        super().__init__()
        self.title("Life Finances")
        #self.minsize(width=500, height=500)
        
        self.controller = controller #using in DWFrame class to acess controller.update command
        
        self.CALCD_PARAMS = CALCD_PARAMS #used to disable entries and prevent overwriting non-calcd entries
        self.param_frames = {}
                
    def main(self):
        self.mainloop()
        
    def make_frames(self,params:dict):
        """Make a frame for each parameter. Frame includes a label and appropriate second widget"""
        for k,v in params.items():
            frame = DWFrame(window=self,key=k,value=v,enabled=(False if k in self.CALCD_PARAMS else True))
            frame.pack()
            self.param_frames[k] = frame
    
    def get_params(self):
        """Pull values from view and return params dict"""
        params = {}
        for k in self.param_frames.keys():
            params[k]=self.param_frames[k].val_var.get()
        return params
        
    def set_params(self, params: dict):
        """Update all calculated entries to passed-in params values"""
        for key,value in params.items():
            if key not in self.CALCD_PARAMS:
                continue
            self.param_frames[key].val_var.set(value)
        