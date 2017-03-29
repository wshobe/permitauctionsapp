import json
import random
import numpy as np
from scipy.stats import bernoulli
from otree.api import Currency as c

def costs1(session, constants):
    np.random.seed(session.config['random_seed'])
    num_rounds = session.config['num_rounds']
    num_lowE = session.config['num_low_emitters']
    num_highE = session.config['num_high_emitters']
    capacity_low = constants.production_capacity_low
    capacity_high = constants.production_capacity_high
    lowE_min_cost  = session.config['low_emitter_min_cost']
    lowE_max_cost  = session.config['low_emitter_max_cost']
    highE_min_cost = session.config['high_emitter_min_cost']
    highE_max_cost = session.config['high_emitter_max_cost']
    high = np.random.randint(highE_min_cost, highE_max_cost + 1, size=(num_rounds * num_highE, capacity_high))
    low = np.random.randint(lowE_min_cost, lowE_max_cost + 1, size=(num_rounds * num_lowE, capacity_low))
    output_table = {
    	'high_emitter': high.astype(float),
    	'low_emitter': low.astype(float)
    }
    return output_table

def generate_output_prices(session, constants):
    np.random.seed(session.config['output_price_random_seed'])
    price_gap = session.config['high_output_price'] - session.config['low_output_price']
    output_prices = session.config['low_output_price'] + bernoulli.rvs(constants.high_price_probability, size=constants.num_rounds) * price_gap
    return output_prices.astype(float)

# TODO: Any reason to keep this?
def generate_costs(num_low, num_high, low_min, low_max, high_min, high_max):
	random.seed(111)

	num_high_emitters = num_high
	num_low_emitters = num_low
	emission_capacity_high = 4
	emission_capacity_low = 4
	low_emitter_min_cost = low_min
	low_emitter_max_cost = low_max
	high_emitter_min_cost = high_min
	high_emitter_max_cost = high_max

	output_table = {}
	high_table = []
	low_table = []

	for i in range(num_high_emitters):
		costs = []
		for j in range(emission_capacity_high):
			costs.append(random.randint(high_emitter_min_cost, high_emitter_max_cost))
		high_table.append(costs)

	for i in range(num_low_emitters):
		costs = []
		for j in range(emission_capacity_low):
			costs.append(random.randint(low_emitter_min_cost, low_emitter_max_cost))
		low_table.append(costs)

	output_table['high_emitters'] = high_table
	output_table['low_emitters'] = low_table

	return output_table

if __name__ == '__main__':
	costs = generate_costs(1, 1, 5, 10, 4, 8)
	print(costs)

	#	JSON format:
	# 	{
	# 		'high_emitters': [
	# 			[#, #, #, #],
	# 			[#, #, #, #],
	# 			...
	# 		],
	# 		'low_emitters': [
	# 			[#, #, #, #],
	# 			...
	# 		]
	# 	}
	#
	#
	# with open('random_costs_output.json', 'w') as f:
	# 	f.write(json.dumps(costs))


	#	CSV format:
	#	num_high_emitters
	#	num_low_emitters
	#	#,#,#,#,
	#	... (for each high emitter)
	#	#,#,#,#
	#	... (for each low emitter)
	#
	#
	# with open('random_costs_output.csv', 'w') as f:
	# 	for key in costs:
	# 		f.write(str(len(costs[key])))
	# 		f.write('\n')
	# 	for key in costs:
	# 		for values in costs[key]:
	# 			for value in values:
	# 				f.write(str(value))
	# 				f.write(',')
	# 			f.write('\n')
