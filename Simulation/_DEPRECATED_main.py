from _DEPRECATED_params_calcs import *
import json
import tkinter as tk

window = tk.Tk()
window.title("Life Finances")
window.minsize(width=500, height=500)

param_vals = {}
param_entries = {}
calcd_values = {}
updater = None

########### Load/save parameters
def load_params():
    global param_vals
    global param_entries
    with open('Simulation/params.json') as json_file:
        param_vals = json.load(json_file)
        for k,v in param_vals.items():
            entry=tk.Entry(width=10)
            entry.insert(tk.END, string=v)
            param_entries[k]=entry
    
def save_params():
    global param_vals
    with open('Simulation/params.json', 'w') as outfile:
        for k,v in param_entries.items():
            param_vals[k]=float(param_entries[k].get())
        json.dump(param_vals, outfile,indent=4)

########### Live Updating
def live_updating():
    global updater
    save_params()
    run_calcs()
    updater=window.after(1000, live_updating)
    
def stop_updating():
    window.after_cancel(updater)

########### Calculate values
def run_calcs(first=False):
    global calcd_values #hold all calculated values
    
    monthly_list = [param_vals["Budget (Monthly)"]]
    yearly_list = [param_vals["Budget (Yearly)"]]
    calcd_values["Yearly Budget"]=sum_yearly_budget(monthly_list,yearly_list)
    
    if not first: #update labels only after labels have been created in UI section
        i=0
        for v in calcd_values.values():
            calcd_labels[i].config(text=v)
            i+=1
        

load_params()
run_calcs(first=True)

########### UI Setup
#Setup user input
i=0
for k,v in param_entries.items():
    tk.Label(text=k).grid(column=0,row=i)
    v.grid(column=1,row=i) #value is an entry
    i+=1
#Setup displayed calculated values
calcd_labels = []
i=0
for k,v in calcd_values.items():
    tk.Label(text=k).grid(column=2,row=i)
    label=tk.Label(text=v)
    label.grid(column=3,row=i)
    calcd_labels.append(label)
    i+=1

    
    
#TODO: Ability to backup/restore parameters


live_updating()
    






window.mainloop() #needed to hold open window