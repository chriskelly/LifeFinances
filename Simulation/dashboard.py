import tkinter as tk
from tkinter import ttk

class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Life Finances")
        self.minsize(width=500, height=500)        
                
    def main(self):
        self.mainloop()
        