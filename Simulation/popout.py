import tkinter as tk
from tkinter import ttk
from dualWidgetFrame import DWFrame


class Popout(tk.Toplevel):
    def __init__(self, window,controller):
        super().__init__(window)
        self.title('Toplevel Window')

        self.controller = controller #using in DWFrame class to access controller.update command
        self.param_frames = {}
        
    def make_frames(self,params:dict):
        """Make a frame for each parameter. Frame includes a label and appropriate second widget"""
        temp_frames ={}
        for param,obj in params.items():
            frame = DWFrame(window=self,param=param,obj=obj)
            frame.pack()
            temp_frames[param] = frame
        return temp_frames
        
    def set_params(self, params: dict):
        """Update all calculated tk.Entries to passed-in params values"""
        for key,value in params.items():
            if self.param_frames[key].enabled:
                continue
            self.param_frames[key].val_var.set(value)
