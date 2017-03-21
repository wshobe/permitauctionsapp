#import numpy as np
import pandas as pd
from otree.api import Currency as c

def make_initial_rounds_table(session,constants):
    '''Create the data structure that is used to construct the running table of round information:
    round numbers, cap for each round, aggregate production capacity, output_price, auction price, ecr_used'''
    num_rounds = session.config['last_round']
    num_low_emitters = session.config['num_low_emitters']
    num_high_emitters = session.config['num_high_emitters']
    round_numbers = list(range(1,num_rounds+1))
    period_caps = [session.config['initial_cap'] - (round-1)*session.config['cap_decrement'] for round in round_numbers]
    output_prices = session.vars['output_prices'][:num_rounds]     # In currency
    full_capacity_permit_demand = [(constants.production_capacity_high*constants.emission_intensity_high*num_high_emitters) + 
                                (constants.production_capacity_low*constants.emission_intensity_low*num_low_emitters)]*num_rounds
    table_data = pd.DataFrame({'round_numbers':round_numbers,
                        'period_caps':period_caps,
                        'output_prices':output_prices,
                        'full_capacity_permit_demand':full_capacity_permit_demand},
                        index=round_numbers,
                        columns=['round_numbers','period_caps','output_prices','full_capacity_permit_demand'])
    return table_data
