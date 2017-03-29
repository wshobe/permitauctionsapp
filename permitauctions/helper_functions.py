import pandas as pd

def make_initial_rounds_table(session, constants):
    """Create the data structure that is used to construct the running table of round information:
    round numbers, cap for each round, aggregate production capacity, output_price, auction price, ecr_used"""
    num_rounds = session.config['num_rounds']
    round_numbers = list(range(1, num_rounds + 1))
    period_caps = [session.config['initial_cap'] - (round_num - 1) * session.config['cap_decrement'] for round_num in round_numbers]

    max_low_emitter_demand = constants.production_capacity_low * constants.emission_intensity_low * session.config['num_low_emitters']
    max_high_emitter_demand = constants.production_capacity_high * constants.emission_intensity_high * session.config['num_high_emitters']
    full_capacity_permit_demand = [max_low_emitter_demand + max_high_emitter_demand] * num_rounds

    table_data = pd.DataFrame(
        {
            'round_numbers': round_numbers,
            'period_caps': period_caps,
            'output_prices': session.vars['output_prices'],
            'full_capacity_permit_demand': full_capacity_permit_demand
        },
        index=round_numbers,
        columns=[
            'round_numbers',
            'period_caps',
            'output_prices',
            'full_capacity_permit_demand'
        ]
    )
    return table_data

