import tkinter as tk

class DWFrame(tk.Frame):
    def __init__(self,window:tk.Tk,key:str,value,enabled:bool):
        super().__init__(window)
        label = tk.Label(self,text=key)
        label.pack( side = "left")
        self.val_var = tk.StringVar(value=value) #this object makes for easier tracking of widget value with getter and setter methods
        if value =="True" or value == "False":
            secondWidget = tk.Checkbutton(self,variable=self.val_var,onvalue="True",offvalue="False")
        else:
            secondWidget = tk.Entry(self,width=10,textvariable=self.val_var)
        if not enabled:
            secondWidget.config(state="disabled")
        secondWidget.pack( side = "left")
        self.val_var.trace('w', window.controller.update) #this calls the update function anytime value changed
        
        