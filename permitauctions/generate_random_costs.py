import numpy as np
from scipy.stats import bernoulli
from otree.api import Currency as c

def costs1(session, constants):
    np.random.seed(session.config['random_seed'])
    num_rounds = constants.num_rounds
    num_low_users = session.config['num_low_emitters']
    num_high_users = session.config['num_high_emitters']
    capacity_low = constants.production_capacity_low
    capacity_high = constants.production_capacity_high
    low_emitter_min_cost  = int(session.config['low_emitter_min_cost'])
    low_emitter_max_cost  = int(session.config['low_emitter_max_cost'])
    high_emitter_min_cost = int(session.config['high_emitter_min_cost'])
    high_emitter_max_cost = int(session.config['high_emitter_max_cost'])
    high = np.random.randint(high_emitter_min_cost,high_emitter_max_cost+1,size=(num_rounds*num_high_users,capacity_high))
    low = np.random.randint(low_emitter_min_cost,low_emitter_max_cost+1,size=(num_rounds*num_low_users,capacity_low))
    output_table = {}
    output_table['high_emitters'] = high.astype(float)
    output_table['low_emitters'] = low.astype(float)
    return output_table

def assign_costs(player,data,player_index,):
    costs = sorted(data[player_index])
    return costs

def generate_output_prices(session,constants):
    np.random.seed(session.config['output_price_random_seed'])
    output_prices = float(session.config['low_output_price']) + bernoulli.rvs(constants.high_price_probability, 
                    size=constants.num_rounds)*float(session.config['high_output_price_increment'])
    return output_prices.astype(float) 

