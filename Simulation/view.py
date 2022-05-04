import tkinter as tk
from tkinter import ttk
from dualWidgetFrame import DWFrame

class View(tk.Tk):
    def __init__(self,controller):
        super().__init__()
        self.title("Life Finances")
        self.minsize(width=500, height=500)
        
        self.controller = controller
        
        self.param_frames = {}
                
    def main(self):
        self.mainloop()
        
    def make_frames(self,param_vals,CALCD_PARAMS):
        for k,v in param_vals.items():
            frame = DWFrame(window=self,key=k,value=v,enabled=(False if k in CALCD_PARAMS else True))
            frame.pack()
            self.param_frames[k] = frame
    
    def get_param_vals(self):
        param_vals = {}
        for k in self.param_frames.keys():
            param_vals[k]=float(self.param_frames[k].val_var.get())
        return param_vals
    
    def set_val(self,key,value):
        self.param_frames[key].val_var.set(value)