import tkinter as tk
from tkinter import ttk

class Dashboard(tk.Tk):
    def __init__(self,controller):
        super().__init__()
        self.title("Life Finances")
        self.minsize(width=500, height=500)   
        
        self.controller = controller
        
        button = tk.Button(text="Parameters", command= lambda:controller.make_popout(id=0))
        button.pack()     
                
    def main(self):
        self.mainloop()
        