# Purpose: LCOE calculations. 
# Author: Wanru(Anora) Wu
# Reference: Henry Zhang

import os
import pandas as pd
from load_inputs import *

################# GENERAL SETTINGS ##################

# Load all inputs
# Change to your own directory of calcs
os.chdir(r"C:\Users\Anora\OneDrive\Desktop\LCOE\anora_rewrite\csv_outputs")
data = pd.read_csv("rawdata_esc.csv")

# Temporary helper function which turns values before or equal to
# the speficied year to 0 
def zero_out_before_year(data, year:int, cols:list):
    data.loc[data['year'] <= year, cols] = 0
    return data

# Basic cleaning
data = data.fillna(0)
data['cap_fac'] = data['cap_fac']/ 100.0 # Correct for percentage
data['backup_cap_fac'] = data['backup_cap_fac']/100.0
tax = general_inputs['tax'] / 100.0 # Correct for percentage


############## SINGLE-SOURCE GENERATION LCOE ###############

# calc
data['s_op'] = (1-tax) * data.cap * data.cap_fac * data.disc * data.inf * 8766 * (10 ** -6)

# Capital cost 
data['cnstr_inf'] = data.constr_sched * data.inf
cnstr_inf_sum = data[['cnstr_inf','name']].groupby(['name']).sum()
cnstr_inf_sum.rename(columns={"cnstr_inf":"cnstr_inf_sum"}, inplace=True)
data = data.merge(cnstr_inf_sum,on='name',how='outer')
data['s_c'] =  (data.cap * data.on_c * data.disc * (data.constr_sched * data.inf - 
                tax * data.depr_sched * data.cnstr_inf_sum) * (10 ** -3))

# Fixed O&M cost
data['s_om_f'] = (1-tax) * data.cap * data.fx_om_c * data.om * data.disc * (10 ** -3)

# Variable O&M cost
data['s_om_v'] = (1-tax) * data.cap * data.cap_fac * data.vr_om_c * data.om * \
                  data.disc * 8766 * (10 ** -6)

# Fuel cost
data['s_f']     = (1-tax) * data.cap * data.cap_fac * data.fl_c * data.heat_rate \
                * data.disc * data.fl * 8766 * (10 ** -9)

# Waste cost (nonzero only for nuclear)
data['s_w']     = (1-tax) * data.cap * data.cap_fac * data.waste_fee * data.disc * 8766 * (10 ** -3)
data['s_f']     = data['s_f'] + data['s_w']

# Decommissioning cost (nonzero only for nuclear)
s_decom = (1-tax) * list(data.loc[(data['name']=='nuclear')&(data['year']==end_yr),'disc'])[0] \
                  * list(data.loc[(data['name']=='nuclear')&(data['year']==end_yr),'inf'])[0] \
                  * list(data.loc[(data['name']=='nuclear')&(data['year']==end_yr),'on_c'])[0] \
                  * 0.175

# Social cost of carbon and methane
# Demoninator of scc
data['disc_inf_scc']     = data.disc * data.inf * data.carb_sched 
# Demoninator of scm
data['disc_inf_scm']     = data.disc * data.inf * data.meth_sched 
# Nominator
data['disc_inf']       = data.disc * data.inf

# Transmission cost
data['s_t']             = data.trans_cost

# Non GHG cost
data['s_non_ghg_c']       = data.non_carbon_c

# Keep only one values in columns 
# so that in later summation they will keep their original value
data = zero_out_before_year(data,end_yr-1,['s_t','s_non_ghg_c','kgCO2 per MWh','leak_rate','heat_rate'])

# Eliminate values before or equal to the p0 year (2023)
data = zero_out_before_year(data,p0_yr,['s_om_f','s_om_v','s_f','s_w','s_op',
                                        'disc_inf_scc','disc_inf','disc_inf_scm'])
# Summation of all years
calc = data[['name','s_c','s_om_f','s_om_v','s_f','s_w','s_op',
               'disc_inf_scc','disc_inf','disc_inf_scm',
               's_t','s_non_ghg_c','kgCO2 per MWh','leak_rate','heat_rate']].groupby(['name']).sum()

# Add decommissioning cost to the capital cost of nuclear
calc.at['nuclear','s_c'] +=  s_decom

calc['s_scc'] = calc.disc_inf_scc * calc['kgCO2 per MWh'] / calc.disc_inf * (10 ** -4)
calc['s_scm'] = (calc.disc_inf_scm * calc.leak_rate * calc.heat_rate / 
                 calc.disc_inf) * (10 ** -9)* 0.96899 * 19.3
# Need to use 10^(-9) not 10^(-7) because of how I code percentages


############### HYBRID-SOURCE GENERATION LCOE ###############

# Reset tax 
for source_name in source:
    if not (data.loc[data['name']==source_name,'hybrid_tax'] == 0).all():
        data.loc[data['name']==source_name,'tax'] = \
        list(data.loc[(data['name']==source_name) & (data['year']==p0_yr),'hybrid_tax'])[0] / 100 

# Backup source calc
data['b_op'] = ((1-data.tax)*data.backup_cap * data.backup_cf_mean * 
                 data.disc * data.inf * 8766 * (10 ** -6))

# Backup source capital cost
data['b_cnstr_inf'] = data.backup_constr_sched * data.inf
b_cnstr_inf_sum = data[['b_cnstr_inf','name']].groupby(['name']).sum()
b_cnstr_inf_sum.rename(columns={"b_cnstr_inf":"b_cnstr_inf_sum"}, inplace=True)
data = data.merge(b_cnstr_inf_sum,on='name',how='outer')
data['b_c'] = data.backup_cap * data.backup_on_c * data.backup_disc * (data.backup_constr_sched \
            * data.inf - data.tax * data.backup_depr_sched * data.b_cnstr_inf_sum) * (10 ** -3)

# Backup source fixed O&M cost
data['b_om_f'] = ((1-data.tax) * data.backup_cap * data.backup_fx_om_c * 
                   data.backup_disc * data.om * (10 ** -3))

# Backup source variable O&M cost
data['b_om_v'] = ((1-data.tax) * data.backup_cap * data.backup_cf_mean * 
                   data.backup_vr_om_c * data.backup_disc * data.om * 8766 * (10 ** -6))

# Backup source fuel cost
data['b_f']    = ((1-data.tax) * data.backup_cap * data.backup_cf_mean * 
                  data.backup_fl_c * data.backup_heat_rate * data.backup_disc * 
                  data.backup_fl * 8766 * (10 ** -9))

# Hybrid transmission cost
data['h_t']    = ((data.backup_trans_cost * data.backup_cap_fac * data.backup_cap + 
                  data.trans_cost * data.cap_fac * data.cap) / 
                 (data.backup_cf_mean * data.backup_cap + data.cap_fac * data.cap))

# Backup non carbon cost
data['b_non_ghg_c']  = data.backup_non_carbon_c

# Social cost renewable source weight
data['r_sc_w'] = (data.cap * data.cap_fac) / (data.cap * data.cap_fac + 
                  data.backup_cap * data.backup_cf_mean)
# Social cost backup source weight
data['b_sc_w'] = (data.backup_cap * data.backup_cf_mean) / (data.cap * 
                  data.cap_fac + data.backup_cap * data.backup_cf_mean)

# Eliminate values before or equal to the p0 year (2023)
data = zero_out_before_year(data,p0_yr,['b_om_f','b_om_v','b_f','b_op'])

# Keep only one values in columns 
# so that in later summation they will keep their original value
data = zero_out_before_year(data,end_yr-1,['h_t','b_non_ghg_c','h_scc',
                                           'r_sc_w','b_sc_w','backup_kgCO2 per MWh',
                                           'backup_leak_rate','backup_heat_rate'])

# Sum across all years
h_calc = data[['name','b_c','b_om_f','b_om_v','b_f','b_op','h_t',
                 'r_sc_w','b_sc_w','b_non_ghg_c','backup_kgCO2 per MWh',
                 'backup_leak_rate','backup_heat_rate']].groupby(['name']).sum()
# Merge with single-source generation calculation results
calc = calc.merge(h_calc,on='name',how='outer')

# Calculate hybrid calc and costs
# Hybrid calc
calc['h_op'] = calc.b_op + calc.s_op

# Hybrid capital cost
calc['h_c']  = calc.b_c + calc.s_c

# Hybrid fixed O&M cost
calc['h_om_f'] = calc.s_om_f + calc.b_om_f

# Hybrid variable O&M cost
calc['h_om_v'] = calc.s_om_v + calc.b_om_v

# Hybrid fuel cost
calc['h_f'] = calc.b_f

# Hybrid social cost of carbon and methane
# Need to divide by disc_inf to get the raw output in MWh
raw_output_main = calc.s_op / calc.disc_inf
raw_output_backup = calc.b_op / calc.disc_inf
em_main = calc["kgCO2 per MWh"]
em_backup = calc["backup_kgCO2 per MWh"]
scalar_c = (((em_main * raw_output_main) + (em_backup * raw_output_backup)) / 
          (raw_output_main + raw_output_backup))
calc['h_scc'] = scalar_c * calc.disc_inf_scc / calc.disc_inf * (10 ** -4)
scalar_m = (calc.backup_leak_rate * calc.b_sc_w * (10 ** (-9)) * 
            0.969 * 19.3 * calc.backup_heat_rate)
# Need to use 10^(-9) not 10^(-7) because of how I code percentages
calc['h_scm'] = scalar_m * calc.disc_inf_scm / calc.disc_inf 

# Hybrid social cost of non GHG cost
calc['h_non_ghg_c'] = calc.r_sc_w * calc.s_non_ghg_c + calc.b_sc_w * calc.b_non_ghg_c


########## GENERATE LCOE CALCULATION RESULTS ##########

# LCOE calculation for single-source generations
calc['Online year'] = p0_yr+1
calc['Capital'] = calc.s_c / calc.s_op / 10
calc['Fixed O&M'] = calc.s_om_f / calc.s_op / 10
calc['Variable O&M'] = calc.s_om_v / calc.s_op /10
calc['Fuel'] = calc.s_f / calc.s_op / 10
calc['Carbon'] = calc.s_scc
calc['Methane'] = calc.s_scm
calc['Transmission'] = calc.s_t
calc['Non-GHG External Costs'] = calc.s_non_ghg_c

# LCOE calculation for hybrid-source generations
calc['h_Capital'] = calc.h_c / calc.h_op / 10
calc['h_Fixed O&M'] = calc.h_om_f / calc.h_op / 10
calc['h_Variable O&M'] = calc.h_om_v / calc.h_op /10
calc['h_Fuel'] = calc.h_f / calc.h_op / 10
calc['h_Carbon'] = calc.h_scc
calc['h_Methane'] = calc.h_scm
calc['h_Transmission'] = calc.h_t
calc['h_Non-GHG External Costs'] = calc.h_non_ghg_c

# Update the LCOE calculation results for hybrid-source generations
hybrid_source = [i for i in source if i.find("hybrid") != -1]
col_list = ['Capital','Fixed O&M','Variable O&M','Fuel','Carbon','Methane'
           ,'Transmission','Non-GHG External Costs']
for col in col_list:
    calc.loc[hybrid_source, col] = calc.loc[hybrid_source, 'h_' + col]

# Extract LCOE results into the data frame "output"
calc.reset_index(inplace=True)
col_list.insert(0,'name')
col_list.insert(1,'Online year')
output = calc[col_list].copy()

# Additional LCOE calculation
output['Effective SCC'] = calc.disc_inf_scc / calc.disc_inf
output['Effective SCM'] = calc.disc_inf_scm / calc.disc_inf
output['LCOE base'] = (output.Capital + output['Fixed O&M'] + output['Variable O&M'] + 
                       output.Fuel + output.Transmission)
output['GHG External Costs'] = output.Carbon + output.Methane
output['LCOE w/ Total Social Costs'] = (output.Carbon + output.Methane + 
                                        output['Non-GHG External Costs'] + output['LCOE base'])


############ OUTPUT THE RESULTS TO CSV ############

# change to your own directory of calcs
os.chdir(r'C:\Users\Anora\OneDrive\Desktop\LCOE\anora_rewrite\csv_outputs')
output.to_csv('all_lcoe_results.csv')


