# Purpose: Load inputs for the LCOE calculations. 
# Author: Wanru(Anora) Wu
# Reference: Henry Zhang

import pandas as pd
import os
import csv


################# GENERAL SETTINGS ##################
# Change to your own directory of inputs
os.chdir(r'C:\Users\Anora\OneDrive\Desktop\LCOE\anora_rewrite\csv_inputs')

# List of generations. 
source = ['coal', 'coal with CCS', 'gas', 'gas with CCS', 
          'hydro', 'nuclear', 'solar', 'wind', 'offshore wind', 
          'hydro_hybrid', 
          'solar_hybrid', 
          'wind_hybrid',    
          'offshore wind_hybrid', 
          'gas (advanced ct)']

# Temporary helper function to convert dictionaries' keys into intergers
def convert_keys_to_int(dic: dict):
    new_dic = {int(k): v for k, v in dic.items()}
    return new_dic


################### LOAD INPUTS ###################

# 'general inputs' is a dictionary containing 
general_inputs = pd.read_csv('general.csv').to_dict('records')[0]

# Get the year parameter
p0_yr    = general_inputs['period_0_yr'] 
start_yr = general_inputs['start_yr'] 
end_yr   = general_inputs['end_yr'] 

# The data frame used to store single-source generations' inputs
single_data = pd.DataFrame()

# Load input for single-source generations
# Note that we load inputs of the backup source as other single 
# Source generations and extract its information later
for source_name in source: 
    if source_name.find('hybrid') == -1: # single source

        # Dictionaries for construction and depreciation schedule 
        constr = pd.read_csv(source_name + '_construction_schedule.csv').to_dict('records')[0]
        constr = convert_keys_to_int(constr)
        depr   = pd.read_csv('DEFAULT_depreciation_schedule.csv').to_dict('records')[0]
        depr   = convert_keys_to_int(depr)

        # Fix the format of construction & depreciation schedules so that the keys
        # are years, not periods. The /100.0 is for percentage correction
        constr_sched  = {}      # corrected construction schedule as fraction/decimal
        depr_sched    = {}      # corrected depreciation schedule as fraction/decimal
        for yr in range(start_yr, end_yr + 1):
            try:
                constr_sched[yr] = constr[yr - p0_yr] / 100.0
            except KeyError:
                constr_sched[yr] = 0
            try:
                depr_sched[yr]   = depr[yr - p0_yr] / 100.0
            except KeyError:
                depr_sched[yr]   = 0
        
        # Fuel price schdule
        try:
            fuel_sched = list(csv.DictReader(open(source_name + '_fuel_price_schedule.csv')))[0]
            fuel_sched = convert_keys_to_int(fuel_sched)
        except IOError:
            fuel_sched = None


        # Methane schedule and carbon schedule
        meth_sched = pd.read_csv('METHANE_schedule.csv').to_dict('records')[0]
        meth_sched = convert_keys_to_int(meth_sched)
        carb_sched = pd.read_csv('CARBON_schedule.csv').to_dict('records')[0]
        carb_sched = convert_keys_to_int(carb_sched)
        
        # Merge all inputs into one dataframe
        data = pd.DataFrame({'constr_sched':pd.Series(constr_sched),
                             'depr_sched':pd.Series(depr_sched),
                             'fuel_sched':pd.Series(fuel_sched),
                             'meth_sched':pd.Series(meth_sched),
                             'carb_sched':pd.Series(carb_sched)})
        
        # Extract year column from index
        data.reset_index(inplace=True)
        data = data.rename(columns = {'index': 'year'})
        data.astype({'year': 'int'}) # change years to int  
        
        # Load other basic inputs into the data frame
        # First convert basic inputs into dictionary 
        # Use disctionaty keys as columns names and 
        # dictionary values as column values
        basic_input = pd.read_csv(source_name + '.csv').to_dict('records')[0]
        for k,v in basic_input.items():
            data[str(k)] = v # add dictionary's information to the data frame
        
        # Non-carbon-cost
        try:
            non_carbon_c = pd.read_csv(source_name + '_non_carbon_costs.csv').to_dict('records')[0]
        except: # otherwise use default
            non_carbon_c = {'mean': 0}
        data['non_carbon_c'] = non_carbon_c['mean']

        # Insert the column of source name
        data.insert(0, 'name', source_name) 
        
        # Add data to the data frame that contains 
        # Information for all single-source generations
        single_data = pd.concat([single_data,data])

# dataframe that contain inputs of hybrid-source generations
hybrid_data = pd.DataFrame() 
# dataframe that contain inputs of all generations (single and hybrid ones)
rawdata = pd.DataFrame() 

# Load inputs of hybrid-source generations, including renewable sources,
# auxiliary information. Inputs of renewables are replicated from 
# single-source generations. Backup source inputs are loaded with
# single-source generation and will be extracted later. 
for source_name in source:
    if source_name.find('hybrid') != -1: # Load input of renewable sources
        # Extract name of renewable source
        renewable = source_name[:source_name.find('_')] 
        # Replicate information from single source generations
        hybrid_data = single_data.loc[single_data['name'] == renewable] 
        # Add generation name 
        hybrid_data['name'] = source_name

        # Auxiliary information
        # First convert Auxiliary inputs into dictionary 
        # Use disctionaty keys as columns names and dictionary values as column values
        aux_input = pd.read_csv(source_name + '_aux.csv').to_dict('records')[0]
        for k,v in aux_input.items():
            # add dictionary's information to the data frame
            hybrid_data[str(k)] = v 

        # Concat all inputs into the data frame of all 
        # generations (single and hybrid ones)
        rawdata = pd.concat([rawdata,hybrid_data])

# Concat inputs of single sources into the big data frame
rawdata = pd.concat([single_data,rawdata])
rawdata.fillna(0,inplace=True)

# Clean data
# Columns whose values need to convert into floats
cols = [col for col in rawdata.columns if col not in ['name', 'year']]
# Convert columns to float
for col in cols:
    rawdata[col] = rawdata[col].astype(float)



############ ESCALATION FACTORS CALCULATION ############

# 'fl_shift_yr' is the final year (e.g. 2040) of using 
# EIA fuel projections (and afterwards using inflation instead)
shift_yr = 2040

# 'fl_shift_fls' is a list of the fuels with the EIA projection shift (e.g. coal, gas)
fl_shift_fls = ['coal', 'gas', 'nuclear']

# Data frame that contains escalation factors and inputs of all generations
rawdata_esc = pd.DataFrame()

# Calculating escalation factors
for source_name in source:
    # Extract core generation type 
    # core_gen_type is "coal" if the input generation type is "Coal with CCS"
    # Note that we also calculated backup source's escalation factor here
    core_gen_type = source_name.partition(' ')[0].lower()
    # A condition that used later to specify the data used in the data frame
    condition = (rawdata['name'] == source_name)

    esc = {} # dictionary that contains escalation factors
    rates = {} # dictionary that contains rates used to calculate escalation factors
    # Inflation. the /100.0 are for percentage correction
    rates['inf'] = 1 + (float(general_inputs['inf'])/100.0)

    # Note that O&M and Fuel escalation rates account for inflation!
    rates['om'] = ((1 + (float(general_inputs['inf'])/100.0)) * 
                   (1 + (float(general_inputs['om_real'])/100.0)))
    
    # Extract the value of fl_real 
    # Since fl_real is the same across all years, 
    # so I just picked start_yr randomly.
    fl_real = list(rawdata.loc[(condition) & (
                   rawdata['year'] == start_yr), 'fl_real'])[0]
    if (rawdata.loc[condition, 'fuel_sched'] == 0).all():
        rates['fl'] = (1 + (float(general_inputs['inf']/100.0))) * \
            (1 + (fl_real)/100.0)

    # Iterate over three types of escalation factors
    for f in ['inf', 'om', 'fl']:
        esc[f] = {}
        if f == 'fl' and (core_gen_type in fl_shift_fls):
            # Use EIA projection for fuel escalation until fl_shift_yr=2040,
            # Then use inflation factor beyond that
            base_price = list(rawdata.loc[condition & (
                rawdata['year'] == start_yr), 'fuel_sched'])[0]
            shift_price = list(rawdata.loc[condition & (
                rawdata['year'] == shift_yr), 'fuel_sched'])[0]
            rawdata.loc[condition, 'fl_c'] = base_price
            for yr in range(start_yr, shift_yr + 1):
                if base_price != 0:
                    esc[f][yr] = (list(rawdata.loc[(condition) & (rawdata['year'] == yr), 'fuel_sched'])[0] *
                                  (rates['inf'] ** (yr - start_yr)) / base_price)
                else:  # if initial price is 0, escalation values are infinite
                    esc[f][yr] = 0
            for yr in range(shift_yr + 1, end_yr + 1):
                if base_price != 0:
                    esc[f][yr] = (shift_price / base_price) * \
                        (rates['inf'] ** (yr - start_yr))
                else:  # if initial price is 0, escalation values are infinite
                    esc[f][yr] = 0
        else:
            # Simple exponential annual growth in escalation factor
            for yr in range(start_yr, end_yr + 1):
                esc[f][yr] = rates[f] ** (yr - start_yr)

    # Discount factor using WACC, with baseline year equal to start year
    if source_name.find('hybrid') == -1:
        wacc = float(general_inputs['wacc']) / 100.0    # percentage correction
    else:
        wacc = list(rawdata.loc[(rawdata['name'] == source_name) & (
            rawdata['year'] == p0_yr), 'hybrid_wacc'])[0] / 100
    esc['disc'] = {}
    for period in range(0, end_yr - start_yr + 1):    # +1 is to include end year
        esc['disc'][period + start_yr] = 1/(1 + wacc)**(period + 0)

    # Merge dict into dataframe
    escalation_data = pd.DataFrame.from_dict(esc)
    # Extract year column from index
    escalation_data.reset_index(inplace=True)
    escalation_data.rename(columns={'index': 'year'}, inplace=True)
    # Add generation name
    escalation_data.insert(0, 'name', source_name)

    # Data frame containing all inputs of one generation
    filtered_rawdata = rawdata[rawdata['name'] == source_name]
    # Merge with escalation_data
    filtered_rawdata = filtered_rawdata.merge(
                       escalation_data, on=['name', 'year'], how='outer')
    # Merge with the rawdata_esc data frame
    rawdata_esc = pd.concat([rawdata_esc, filtered_rawdata], ignore_index=True)


############ EXTRACT BACKUP SOURCE INPUTS ############

# For each generation, we aim to append a backup source input as 
# columns in the dataframe. For single-source generations those 
# columns are filled with '0's.

# Extract backup source data
backup_data = rawdata_esc.loc[rawdata_esc['name']=='gas (advanced ct)']

# Drop repetitive columns
backup_data.drop(['equiv_cap','equiv_cap_fac','cap_fac_max',
                  'hybrid_tax','hybrid_wacc','name','inf',
                  'om'],axis=1,inplace=True)

# Add prefix to each column and change column name
backup_data = backup_data.add_prefix('backup_')
backup_data.rename(columns={'backup_year': 'year'},inplace=True)

# Append the backup source data back 
rawdata_esc = rawdata_esc.loc[rawdata_esc['name']!='gas (advanced ct)']
rawdata_esc = rawdata_esc.merge(backup_data,on='year',how='outer')

# For single-source generations, set the columns for backup source to be '0'.
single_sources = [i for i in source if i.find('hybrid') == -1]
for col in rawdata_esc.columns:
    if col.startswith('backup'):
        rawdata_esc.loc[rawdata_esc['name'].isin(single_sources), col] = 0

# compute the mean backup capacity factor for hybrid sources
# pct to decimal
rawdata_esc['backup_cf_mean'] = ((rawdata_esc['equiv_cap'] * (rawdata_esc['equiv_cap_fac'] 
                                / 100.0) - rawdata_esc['cap'] * (rawdata_esc['cap_fac'] / 100.0)) 
                                / rawdata_esc['backup_cap'])
rawdata_esc.loc[rawdata_esc['backup_cf_mean'] == float('-inf'), 'backup_cf_mean'] = 0



############ OUTPUT THE DATA FRAME TO CSV ############
rawdata_esc = rawdata_esc.sort_values(['name','year'])

# change to your own directory of outputs
os.chdir(r'C:\Users\Anora\OneDrive\Desktop\LCOE\anora_rewrite\csv_outputs')
rawdata_esc.to_csv('rawdata_esc.csv')


