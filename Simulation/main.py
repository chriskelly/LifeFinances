from parameter import Parameter
import json
import tkinter as tk

window = tk.Tk()
window.title("Life Finances")
window.minsize(width=500, height=500)

# Load/save parameters
def load_params():
    with open('params.json') as json_file:
        params = json.load(json_file)
        for k,v in params.items():
            entry=tk.Entry(width=10)
            entry.insert(tk.END, string=v)
            params[k]=entry
    return params
    
def save_params():
    saveFile = {}
    with open('params.json', 'w') as outfile:
        for k,v in params.items():
            saveFile[k]=float(params[k].get())
        json.dump(saveFile, outfile,indent=4)

params=load_params()

# Layout labels, entries, and buttons
i=0
for k,v in params.items():
    tk.Label(text=k).grid(column=0,row=i)
    v.grid(column=1,row=i) #value is an entry
    i+=1
    
tk.Button(text="Save", command=save_params).grid(column=1,row=i)
    
#TODO: Create framework for pulling param values
#TODO: Ability to backup/restore parameters
    






window.mainloop() #needed to hold open window