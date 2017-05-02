import pandas as pd
import numpy as np
from otree.api import Currency as c
import logging
from decimal import Decimal


def make_rounds_table(subsession,output_prices_for_table,round_numbers,period_caps,full_capacity_demand):
    '''Create the data structure that is used to construct the running table of round information:
    round numbers, cap for each round, aggregate production capacity, output_price, auction price, ecr_used'''
    num_rounds = len(round_numbers)
    this_round = subsession.round_number
    #round_numbers = list(range(1,num_rounds+1))
    #round_numbers = np.arange(1,num_rounds+1)
    #output_prices =      
    auction_prices_none = [None]*num_rounds
    auction_prices = [s.auction_price for s in subsession.in_all_rounds()]   # [:num_rounds]
    auction_prices = auction_prices + auction_prices_none[len(auction_prices):]
    #assert False
    #period_caps = session.vars['period_caps']
    #full_capacity_permit_demand = session.vars['full_capacity_permit_demand']
    table_data = pd.DataFrame(
        {
            'round_numbers': round_numbers,
            'period_caps': period_caps,
            'output_prices': output_prices_for_table,
            'auction_prices': auction_prices,
            'full_capacity_permit_demand': full_capacity_demand
        },
        index=round_numbers,
        columns=['round_numbers','period_caps','output_prices','auction_prices','full_capacity_permit_demand']
        )
    table_data.output_prices[this_round:num_rounds] = None
    table_data.auction_prices[this_round:num_rounds] = None
    return table_data

def make_supply_schedule(subsession,constants):
    '''Build the supply schedule. Its  length is equal to the maximum number of bids that can 
       possibly be entered.'''
    num_low_emitters = subsession.session.config['num_low_emitters']
    num_high_emitters = subsession.session.config['num_high_emitters']
    initial_ecr_reserve_amount = subsession.session.config['initial_ecr_reserve_amount']
    ecr_reserve_amount = subsession.session.config['initial_ecr_reserve_amount']
    ecr_increment = subsession.session.config['ecr_reserve_increment']
    ecr_trigger_price = subsession.session.config['ecr_trigger_price']
    pcr_reserve_amount = subsession.session.config['price_containment_reserve_amount'] 
    emission_intensity_high = constants.emission_intensity_high
    emission_intensity_low = constants.emission_intensity_low
    num_possible_bids = num_low_emitters*constants.num_bids_low*emission_intensity_low + \
                        num_high_emitters*constants.num_bids_high*emission_intensity_high
    #supply_step_all = ecr_increment == initial_ecr_reserve_amount
    ecr_price_increment = 1/ecr_increment
    #num_ecr_steps = int(ecr_increment/ecr_reserve_amount)
    ecr_trigger_price = subsession.session.config['ecr_trigger_price']
    permits_available = subsession.permits_available
    reserve_price = constants.reserve_price
    pcr_trigger_price = subsession.session.config['price_containment_trigger']
    q_star = max(0,permits_available - ecr_reserve_amount)
    if subsession.session.config['supply_step']:
        # Supply reduction in one big step
        supply_step = np.ones(initial_ecr_reserve_amount)*ecr_trigger_price
    else:
        #Smooth linear supply reduction
        supply_step = np.linspace(float(reserve_price), ecr_trigger_price,num = permits_available - q_star,endpoint=False,retstep=True)
        step_size = supply_step[1]
        supply_step = (supply_step[0]*2).round()/2
        #assert False
    supply = np.empty(num_possible_bids+permits_available+len(supply_step)+pcr_reserve_amount)
    supply[:q_star] = reserve_price
    supply[q_star:permits_available] = supply_step
    supply[permits_available:permits_available+pcr_reserve_amount] = pcr_trigger_price
    supply[permits_available+pcr_reserve_amount:len(supply)] = constants.maximum_bid + 10
    #assert False
    return supply
    
def calculate_auction_price(these_bids,supply_curve,subsession,reserve_price):
    # these_bids is the bids_df pd data frame
    #log = logging.getLogger('permitauctionsapp')
    #log.info('In function: calculate_auction_price')
    bids = these_bids.sort(['bid'],ascending=False)
    num_bids = len(bids)
    supply = supply_curve[:num_bids]
    ecr_reserve_amount = subsession.session.config['initial_ecr_reserve_amount']
    pcr_reserve_amount = subsession.session.config['price_containment_reserve_amount']
    ecr_trigger_price = subsession.session.config['ecr_trigger_price']
    permits_available = subsession.permits_available
    q_star = permits_available - ecr_reserve_amount
    max_permits = permits_available + pcr_reserve_amount
    # Take care of the improbable "no bids" case
    # This actually cannot happen. The function is never called in the no bids case.
    if len(bids) == 0:
        return {'price':reserve_price,'first_rejected_bid':reserve_price,'accepted': [],'ecr_reserve_amount_used': 0 }
    # If the number of bids is less than the number available accept them all and return the reserve price.
    '''
        This is the normal case. Loop through the bids from high to low until the supply 
        is exhausted. Accept these, set the auction price and reject all lower bids.
    '''
    first_rejected_bid = -1
    price = -1
    last_positive_bid_index = -1
    pcr_added = 0
    ecr_reserve_amount_used = 0
    for index, bid in enumerate(bids.bid,1):
        if index == num_bids:
            # We have gone through all of the bids. There is no "next" bid.
            if first_rejected_bid == -1:
                # No bids are below the supply curve.
                bids.accepted[index-1] = 1
                first_rejected_bid = -1
                price = supply[index-1]
                if last_positive_bid_index >= q_star -1 and last_positive_bid_index < permits_available - 1:
                    price = supply[index-1]
                elif index >= permits_available + 1 and index < max_permits - 1:
                    pcr_added += 1
                last_positive_bid_index = index - 1
                #log.info('Last bid - last_positive_bid_index: %d' % last_positive_bid_index)
                #log.info('Last bid - price: %d' % price)
            else:
                # We know the last bid was below the supply curve, because
                # an earlier bid was below the supply curve.
                bids.accepted[index-1] = 0
        # Bid is greater than or equal to supply and there are still permits available
        # Since the last bid has already been processed, we know that bids[index] exists.
        elif bids.bid[index] >= supply[index] and index < permits_available + 1:
            bids.accepted[index-1] = 1
            next
        elif bids.bid[index] < supply[index]:
            # Bid falls below the supply curve
            if first_rejected_bid == -1:
                first_rejected_bid = bids.bid[index]
                price = supply[index-1]
                bids.accepted[index-1] = 1
                last_positive_bid_index = index - 1
                #log.info('1st rejected bid - last_positive_bid_index: %d' % last_positive_bid_index)
                #log.info('1st rejected bid - price: {0:.2f}'.format(price))
            else:
                # Some bid has already fallen below the supply curve
                bids.accepted[index-1] = 0
        elif index >= permits_available + 1 and index < max_permits - 1:
            # The bid number has exceeded the number of permits available
            if bids.bid[index] > supply[index]:
                # Add permits from the PCR
                pcr_added += 1
                #log.info('pcr_added: %d' % pcr_added)
                bids.accepted[index-1] = 1
            else:
                bids.accepted[index-1] = 1
                first_rejected_bid = bids.bid[index]
                price = bids.bid[index]
                last_positive_bid_index = index - 1
                #log.info('PCR range - last_positive_bid_index: %d' % last_positive_bid_index)
                #log.info('PCR range - price: {0:.2f}'.format(price))
    if last_positive_bid_index < q_star - 1:
        ecr_reserve_amount_used = ecr_reserve_amount
        #subsession.permits_available = permits_available - ecr_reserve_amount
        #log.info('ECR all - last_positive_bid_index: %d' % last_positive_bid_index)
    elif last_positive_bid_index >= q_star -1 and last_positive_bid_index <= permits_available - 1:
        ecr_reserve_amount_used = permits_available - last_positive_bid_index - 1
        #subsession.permits_available = permits_available - self.subsession.ecr_reserve_amount_used 
        #log.info('ECR range - last_positive_bid_index: %d' % last_positive_bid_index)
    bids = bids.sort_index()
    return {'price':price,
            'first_rejected_bid':first_rejected_bid,
            'accepted':bids.accepted,
            'pcr_amount_added': pcr_added,
            'ecr_reserve_amount_used':ecr_reserve_amount_used}


def calculate_auction_price1(these_bids,supply_curve,subsession,constants):
    reserve_price = constants.reserve_price
    if len(these_bids) == 0:
        return {'price':reserve_price,'first_rejected_bid':reserve_price}
    supply = supply_curve[:num_bids]
    diff = bids - supply
    ecr_increment = subsession.session.config['ecr_reserve_increment']
    ecr_trigger_price = subsession.session.config['ecr_trigger_price']
    pcr_trigger_price = subsession.session.config['price_containment_trigger']
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

