# LCOE

Project's Title: LCOE Calculation -- Anora Rewrite

Project Description: \
This project calculates the LCOE of single-source and hybrid-source generations that are backed up by gases. \
Note that some hybrid-source generations are backed up by batteries. Due to the fact that it is impossible to \
discern the backup source from the input files, this project can only be used to calculate hybrid-source generations \
that are backed up by gases. The codes was originally written by Henry Zhang and rewrote by Anora Wu. 

Table of Contents (in anora_rewrite file): 
1. csv_inputs: input files used for calculation
2. csv_outputs: output files storing the data frame containing all inputs and LCOE calculation results
3. rewrite_python3.ipynb: Rewrite codes written by Henry Zhang for reference
4. load_inputs.py: python file loading inputs of generations, clean data, and calculate escalation factors
5. lcoe_calc.py: LCOE calculation

How to Run the Project: \
First run load_inputs.py, then run lcoe_calc.py. After that, you can find results in csv_outputs.
