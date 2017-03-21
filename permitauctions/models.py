from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency as c, currency_range
)
from otree.db.models import Model, ForeignKey
import random
from .generate_random_costs import costs1, assign_costs, generate_output_prices
import numpy as np


author = 'Derek Wu (derek.x.wu@gmail.com, dxw7za)'

doc = """
Permit trading with an emission containment reserve
"""

class Constants(BaseConstants):
    ### App metadata
    name_in_url = 'permit_trading'
    players_per_group = None  # Puts all users in one group
    num_rounds = 10

    ### Production constants
    emission_intensity_high = 2  # permits required per plant
    emission_intensity_low = 1
    production_capacity_high = 4  # number of plants per  player
    production_capacity_low = 4
    low_emitter_min_cost = c(9)
    low_emitter_max_cost = c(14)
    high_emitter_min_cost = c(5)
    high_emitter_max_cost = c(9)
    must_run = 0

    low_output_price = c(21)
    high_output_price_increment = c(8)  
    high_price_probability = 0.5
    initial_cash_endowment_high = c(120)
    initial_cash_endowment_low = c(50)

    ### Auction details
    ecr_trigger_price = c(7)  # Will tell users that permits were taken from the pool
    reserve_increment = 1
    reserve_price = c(4)  # absolutely no bids below reserve price; don't even let them try
    maximum_bid = c(20)
    bid_price_increment = c(0.5)
    num_bids_high = 4
    num_bids_low = 4

    price_containment_trigger = c(12)
    price_containment_reserve_amount = 10  # Max permits to add if price over containment trigger
    # simply add permits to bring the price down
    penalty_amount = c(25)  # can run without permits, but it's bad

    ### Misc
    payout_rate = 0.5  # 0-1, testers actually get paid
    # sets of bids should go to high or low emitters always, e.g. high = {15, 12, 16} and low = {4,6,3}
    

class Subsession(BaseSubsession):
    number_sold_auction = models.PositiveIntegerField()
    auction_price = models.CurrencyField()
    ecr_reserve_amount_used = models.PositiveIntegerField(initial=0)
    pcr_amount_added = models.PositiveIntegerField(initial=0)
    output_price = models.CurrencyField()
    permits_available = models.IntegerField()
    initial_auction_price = models.CurrencyField()

    def before_session_starts(self):
        # All random draws must take place once at the start of the process.
        self.ecr_reserve_amount = self.session.config['initial_ecr_reserve_amount']
        self.permits_available = self.session.config['initial_cap'] - (self.round_number - 1) * self.session.config['cap_decrement']
        num_low_emitters = self.session.config['num_low_emitters']
        num_high_emitters = self.session.config['num_high_emitters']

        # This occurs num_rounds times, but all at session start - not for initializing between rounds
        if self.round_number == 1:
            self.group_randomly()
            random.seed(self.session.config['random_seed'])
            """ 
            The new cost function draws all costs for the entire session. 
            Costs change in each round
             Pass only the session and Constants objects to the cost function 
            """
            all_costs = costs1(self.session,Constants,self.session.config['random_seed'])
            self.session.vars['costs1'] = all_costs
            output_prices = generate_output_prices(Constants,self.session.config['output_price_random_seed'],Constants.num_rounds)
            self.session.vars['output_prices'] = output_prices
        all_costs = self.session.vars['costs1']
        self.output_price = self.session.vars['output_prices'][self.round_number-1]
        for player in self.get_players():
            if self.round_number == 1:
                player.participant.vars['first_name'] = player.first_name
                player.participant.vars['last_name'] = player.last_name
                player.participant.vars['computing_ID'] = player.computing_ID
            if player.role() == 'high_emitter':
                player.money = Constants.initial_cash_endowment_high
                player.capacity = Constants.production_capacity_high
                player.emission_intensity = Constants.emission_intensity_high
                player_index = (self.round_number-1)*num_high_emitters + player.id_in_group-num_low_emitters-1
                costs = assign_costs(player,all_costs['high_emitters'],player_index)
            elif player.role() == 'low_emitter':
                player.money = Constants.initial_cash_endowment_low
                player.capacity = Constants.production_capacity_low
                player.emission_intensity = Constants.emission_intensity_low
                player_index = (self.round_number-1)*num_low_emitters + player.id_in_group-1
                costs = assign_costs(player,all_costs['low_emitters'],player_index)
            player.generate_bid_stubs()
            player.generate_unit_stubs(costs)
        

class Group(BaseGroup):
    pass


class Player(BasePlayer):
    first_name = models.CharField(initial='Fred')
    last_name = models.CharField(initial='Jones')
    computing_ID = models.CharField(initial='fj2b')
    money = models.CurrencyField()
    permits = models.PositiveIntegerField(initial=0)
    capacity = models.PositiveIntegerField()
    emission_intensity = models.PositiveIntegerField()
    permits_purchased_auction = models.PositiveIntegerField()
    penalty = models.CurrencyField()

    # Need to make the choices array dynamic 
    production_amount = models.PositiveIntegerField(min=Constants.must_run, max=4, choices=range(Constants.must_run,Constants.production_capacity_low+1))
    #min_production = models.PositiveIntegerField(initial=1)

    # Bids - 4 for production plants, 2 for buying extra permits
    #permits_won = models.PositiveIntegerField(initial=0)

    def role(self):
        # play with group_randomly()
        if self.id_in_group > self.session.config['num_low_emitters']:
            return 'high_emitter'
        else:
            return 'low_emitter'

    # Helper function to retrieve bids
    def get_bids(self):
        bid_qs = Bid.objects.filter(player__exact=self).filter(bid__isnull=False)
        return [dec.bid for dec in bid_qs]
        

    # Helper function to retreive plant costs
    def get_costs(self):
        unit_qs = Unit.objects.filter(player__exact=self).order_by('cost')
        return [dec.cost for dec in unit_qs]
        
    def generate_bid_stubs(self):
        """
        Create a fixed number of "bid stubs", i.e. bid objects that have places for bids and 
        may contain values needed later.
        """
        if self.role() == 'high_emitter':
            num_bids = Constants.num_bids_high
        else:
            num_bids = Constants.num_bids_low
        for _ in range(num_bids):
            bid = self.bid_set.create()    # create a new bid object as part of the player's bid set
            bid.round = self.subsession.round_number
            bid.pid_in_group = self.id_in_group   
            bid.save()   # important: save to DB!

    def generate_unit_stubs(self,player_costs):
        """
        Create a fixed number of "unit stubs".
        """
        player_costs = sorted(player_costs)
        if self.role() == 'high_emitter':
            capacity = Constants.production_capacity_high
        else:
            capacity = Constants.production_capacity_low
        for i in range(capacity):
            unit = self.unit_set.create()    # create a new bid object as part of the player's bid set
            unit.unit_num=i
            unit.cost = player_costs[i]
            #bid.value = random.randint(1, 10)   # don't forget to "import random" before!
            unit.save()   # important: save to DB!

        
class Bid(Model):   # our custom model inherits from Django's base class "Model"
    BID_CHOICES = currency_range(c(Constants.reserve_price), c(Constants.maximum_bid), c(Constants.bid_price_increment))
    #value = models.IntegerField()    # will be randomly generated
    round = models.PositiveIntegerField()
    bid = models.CurrencyField(choices=BID_CHOICES)
    accepted = models.PositiveIntegerField()
    pid_in_group = models.PositiveIntegerField()
    player = ForeignKey(Player)    # creates 1:m relation -> this bid was made by a certain player

    
class Unit(Model):   # our custom model inherits from Django's base class "Model"
    #value = models.IntegerField()    # will be randomly generated
    unit_num = models.IntegerField()
    cost = models.CurrencyField()
    unit_used = models.PositiveIntegerField()
    player = ForeignKey(Player)    # creates 1:m relation -> this bid was made by a certain player    
    
    
    