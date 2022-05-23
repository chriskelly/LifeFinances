import tkinter as tk
from tkinter import ttk
from dualWidgetFrame import DWFrame

class View(tk.Tk):
    def __init__(self,controller):
        super().__init__()
        self.title("Life Finances")
        #self.minsize(width=500, height=500)
        
        self.controller = controller #using in DWFrame class to access controller.update command
        
        self.param_frames = {}
                
    def main(self):
        self.mainloop()
        
    def make_frames(self,params:dict):
        """Make a frame for each parameter. Frame includes a label and appropriate second widget"""
        for k,obj in params.items():
            frame = DWFrame(window=self,key=k,value=obj["val"],enabled=(False if "calcd" in obj else True))
            frame.pack()
            self.param_frames[k] = frame
    
    def get_params_vals(self):
        """Pull values from view and return a dict of param names:values"""
        params_vals = {}
        for k in self.param_frames.keys():
            params_vals[k]=self.param_frames[k].val_var.get()
        return params_vals
        
    def set_params(self, params: dict):
        """Update all calculated tk.Entries to passed-in params values"""
        for key,value in params.items():
            if not self.param_frames[key].enabled:
                continue
            self.param_frames[key].val_var.set(value)
        