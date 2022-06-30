# LifeFinances

Current project is all in the simulation folder. 
Still needs to be organized into M-V-C folders. 
Simulation/Controller.py is the main() for running the GUI. 
Simulation/Simulator.py is isolated from rest of MVC for now and is the current work in progress

If you want to see the real ugly stuff, check out GoogleScripts/Simulation.gs for the javascript version I use in Google Sheets. To be honest though, I am, for the most part, following that old structure in the new Simulator.py.

Current goal is to make finish the Simulator so I can feed it a set of parameters and get back a success rate. Now that I've finished the income portion (mostly), I can work on the monte carlo portion. In GenerateReturns/main.py, I made a simple function to generate gaussian random returns (used them for the Google Sheet version). I'll need to move that into the Simulator. Either that or stick with a pre-generated set of returns. Not sure which will be faster. I also need to add inflation to that random generator.
