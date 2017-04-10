import pandas as pd
import numpy as np
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
    max_low_emitter_demand = constants.production_capacity_low * constants.emission_intensity_low * session.config['num_low_emitters']
    max_high_emitter_demand = constants.production_capacity_high * constants.emission_intensity_high * session.config['num_high_emitters']
    full_capacity_permit_demand = [max_low_emitter_demand + max_high_emitter_demand] * num_rounds
    table_data = pd.DataFrame(
        {
            'round_numbers':round_numbers,
            'period_caps':period_caps,
            'output_prices':output_prices,
            'full_capacity_permit_demand':full_capacity_permit_demand
        },
        index=round_numbers,
        columns=['round_numbers','period_caps','output_prices','full_capacity_permit_demand']
        )
    return table_data

def make_supply_schedule(subsession,constants):
    '''Build the supply schedule. Its  length is equal to the maximum number of bids that can 
       possibly be entered.'''
    num_low_emitters = subsession.session.config['num_low_emitters']
    num_high_emitters = subsession.session.config['num_high_emitters']
    emission_intensity_high = constants.emission_intensity_high
    emission_intensity_low = constants.emission_intensity_low
    num_possible_bids = num_low_emitters*constants.num_bids_low*emission_intensity_low + \
                        num_high_emitters*constants.num_bids_high*emission_intensity_high
    ecr_increment = constants.reserve_increment
    ecr_price_increment = 1/ecr_increment
    ecr_trigger_price = subsession.session.config['ecr_trigger_price']
    permits_available = subsession.permits_available
    reserve_price = constants.reserve_price
    pcr_trigger_price = subsession.session.config['price_containment_trigger']
    q_star = permits_available - ecr_increment *int(ecr_trigger_price - reserve_price)
    supply_step = np.arange(reserve_price, ecr_trigger_price+ecr_price_increment,ecr_price_increment)
    supply = np.empty(num_possible_bids+permits_available+len(supply_step))
    supply[:q_star-1] = reserve_price
    supply[q_star-1:permits_available] = supply_step
    supply[permits_available:supply.size] = pcr_trigger_price
    return supply
    
def calculate_auction_price(these_bids,supply_curve,subsession,constants):
    bids = these_bids.bid.values.astype(np.float64)
    num_bids = bids.size
    supply = supply_curve[:num_bids]
    diff = bids - supply
    first_rejected_bid = -1
    ecr_increment = constants.reserve_increment
    ecr_trigger_price = subsession.session.config['ecr_trigger_price']
    pcr_trigger_price = subsession.session.config['price_containment_trigger']
    reserve_price = constants.reserve_price
    permits_available = subsession.permits_available
    q_star = permits_available - ecr_increment *int(ecr_trigger_price - reserve_price)
    if any(diff < 0):
        first_negative_value_index = np.nonzero(diff < 0)[0][0]
    else:
        first_negative_value_index = 0
    if (num_bids < q_star):
        price = reserve_price 
        first_rejected_bid = reserve_price
# No bids fall below the supply curve
    elif not(first_negative_value_index):
        if num_bids <= permits_available:
            first_rejected_bid = supply[num_bids-1]
            price = supply[num_bids-1]
        else:
            price = bids[permits_available]
            first_rejected_bid = bids[permits_available]  
# First bid > Q is above trigger
    elif (num_bids > permits_available and bids[permits_available] > pcr_trigger_price):
        price = bids[permits_available]
        first_rejected_bid = bids[permits_available]
    elif first_negative_value_index <= permits_available:
        first_rejected_bid = bids[first_negative_value_index]
        price = max(bids[first_negative_value_index],supply[first_negative_value_index-1])
# Edge case x = Q and bid > supply price
    elif bids[permits_available-1] > supply[permits_available-1]:   
        first_rejected_bid = bids[permits_available]
        price = max(bids[permits_available],supply[permits_available-1])
    return {'price':price,'first_rejected_bid':first_rejected_bid}
