import tkinter as tk

class DWFrame(tk.Frame):
    def __init__(self,window:tk.Tk,param:str,obj:dict):
        super().__init__(window)
        value = obj["val"]
        if "popper" in obj:
            firstWidget = tk.Button(self,text=param,command= lambda:window.controller.make_popout(id=obj["popper"]))
        else:
            firstWidget = tk.Label(self,text=param)
        firstWidget.pack( side = "left")
        self.val_var = tk.StringVar(value=value) #this object makes for easier tracking of widget value with getter and setter methods
        if value =="True" or value == "False":
            secondWidget = tk.Checkbutton(self,variable=self.val_var,onvalue="True",offvalue="False")
        else:
            secondWidget = tk.Entry(self,width=10,textvariable=self.val_var)
        if "calcd" in obj:
            secondWidget.config(state="disabled")
        else:
            self.val_var.trace('w', window.controller.update) #this calls the update function anytime value changed
        secondWidget.pack( side = "left")
        
        