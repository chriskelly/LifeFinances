import tkinter as tk

class DWFrame(tk.Frame):
    def __init__(self,window,key,value,enabled):
        super().__init__(window)
        self.val_var = tk.StringVar()
        self.val_var.trace('w', window.controller.update)
        label = tk.Label(self,text=key)
        label.pack( side = "left")
        entry = tk.Entry(self,width=10,textvariable=self.val_var)
        entry.insert(tk.END, string=value)
        if not enabled:
            entry.config(state="disabled")
        entry.pack( side = "left")
        
        