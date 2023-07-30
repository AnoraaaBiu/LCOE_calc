The formatting of each CSV file of inputs is absolutely crucial. The first row must
only consist of the variable names exactly as they are used in the input_init.py file
The second row consists of the numeric inputs. At the moment, the program does not 
do error-checking on the variable names.

If any input is formatted as a schedule (e.g. "construction schedule") then it must
be in a separate CSV file. At the moment, you must also add a bit of code at the end
of input_init.py in the "load_from_csv()" function.



At this point, when I hand-enter inputs, I first enter them as Excel files then save

as CSV. You can delete the Excel files if you wish, although they do not take up much

room. If you are using a Mac, save as “WINDOWS CSV FORMAT” since the Mac CSV format 

causes issues.