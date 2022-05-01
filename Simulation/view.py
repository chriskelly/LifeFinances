import tkinter as tk
from tkinter import ttk

class View(tk.Tk):
    def __init__(self,controller):
        super().__init__()
        self.title("Life Finances")
        self.minsize(width=500, height=500)
        
        self.controller = controller
        
        self.param_entries = {}
        self.calcd_labels = []
        
        self.updater = None
        
    def main(self):
        self.mainloop()
        
    def make_entries(self,param_vals):
        for k,v in param_vals.items():
            entry=tk.Entry(width=10)
            entry.insert(tk.END, string=v)
            self.param_entries[k]=entry
    
    def get_param_vals(self):
        param_vals = {}
        entries = self.param_entries
        for k,v in self.param_entries.items():
            param_vals[k]=float(self.param_entries[k].get())
        return param_vals
    
    def live_updating(self):
        global updater
        self.controller.save_params()
        self.controller.run_calcs()
        updater=self.after(1000, self.live_updating)
    def stop_updating(self):
        self.after_cancel(updater)
        
    def layout(self):
        #Setup user input
        i=0
        for k,v in self.param_entries.items():
            tk.Label(text=k).grid(column=0,row=i)
            v.grid(column=1,row=i) #value is an entry
            i+=1
        #Setup displayed calculated values
        i=0
        for k,v in self.controller.calcd_values.items():
            tk.Label(text=k).grid(column=2,row=i)
            label=tk.Label(text=v)
            label.grid(column=3,row=i)
            self.calcd_labels.append(label)
            i+=1
            
    def update_labels(self,calcd_values):
        i=0
        for v in calcd_values.values():
            self.calcd_labels[i].config(text=v)
            i+=1