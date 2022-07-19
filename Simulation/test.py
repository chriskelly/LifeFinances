import os
 
SAVE_DIR = 'Saved'
for file in os.scandir(SAVE_DIR):
    os.remove(file.path)