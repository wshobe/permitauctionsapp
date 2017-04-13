from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency as c, currency_range
)
from otree.db.models import Model, ForeignKey
from .generate_random_costs import costs1, assign_costs, generate_output_prices

author = 'Derek Wu (derek.x.wu@gmail.com, dxw7za)'

doc = """
Permit trading with an emission containment reserve
"""

class Constants(BaseConstants):
    ### App metadata
    name_in_url = 'permit_trading'
    players_per_group = None  # Puts all players in one group
    num_rounds = 30

    ### Production constants
    emission_intensity_high = 2  # permits required per plant ***Change this at your peril!!!
    emission_intensity_low = 1
    production_capacity_high = 4  # number of plants per player
    production_capacity_low = 4
    must_run = 0  # number of plants each player is required to produce from

    high_price_probability = 0.5
    initial_cash_endowment_high = c(100)
    initial_cash_endowment_low = c(50)

    ### Auction details
    #ecr_trigger_price = c(7)  # Price to start removing permits from the pool
    reserve_increment = 2
    reserve_price = c(5)  # absolutely no bids below reserve price; don't even let them try
    maximum_bid = c(30)
    bid_price_increment = c(0.5)
    num_bids_high = 4
    num_bids_low = 4

    penalty_amount = c(25)  # Cost of running a plant without necessary permits

    ### Misc
    payout_rate = 0.01  # Conversion rate from player.money to real-life payout

class Subsession(BaseSubsession):
    number_sold_auction = models.PositiveIntegerField()
    auction_price = models.CurrencyField()
    ecr_reserve_amount_used = models.PositiveIntegerField(initial=0)
    pcr_amount_added = models.PositiveIntegerField(initial=0)
    output_price = models.CurrencyField()
    permits_available = models.IntegerField()
    initial_auction_price = models.CurrencyField()

    def before_session_starts(self):
        # This occurs num_rounds times, but all at session start - not for initializing between rounds
        # All random draws must take place once at the start of the process.
        self.ecr_reserve_amount = self.session.config['initial_ecr_reserve_amount']
        self.permits_available = self.session.config['initial_cap'] - (self.round_number - 1) * self.session.config['cap_decrement']
        num_low_emitters = self.session.config['num_low_emitters']
        num_high_emitters = self.session.config['num_high_emitters']

        if self.round_number == 1:
            self.group_randomly()
            """ 
            The new cost function draws all costs for the entire session. 
            Costs change in each round
             Pass only the session and Constants objects to the cost function 
            """
            self.session.vars['costs1'] = costs1(self.session,Constants)
            self.session.vars['output_prices'] = generate_output_prices(self.session,Constants)
        all_costs = self.session.vars['costs1']
        self.output_price = self.session.vars['output_prices'][self.round_number - 1]
        for player in self.get_players():
            if self.round_number == 1:
                player.participant.vars['first_name'] = player.first_name
                player.participant.vars['last_name'] = player.last_name
                player.participant.vars['computing_ID'] = player.computing_ID
            if player.role() == 'high_emitter':
                player.money = Constants.initial_cash_endowment_high
                player.capacity = Constants.production_capacity_high
                player.emission_intensity = Constants.emission_intensity_high
                # TODO: Is this doing what you think it is
                player_index = (self.round_number - 1) * num_high_emitters + player.id_in_group - num_low_emitters - 1
                costs = assign_costs(player,all_costs['high_emitters'],player_index)
            elif player.role() == 'low_emitter':
                player.money = Constants.initial_cash_endowment_low
                player.capacity = Constants.production_capacity_low
                player.emission_intensity = Constants.emission_intensity_low
                player_index = (self.round_number - 1) * num_low_emitters + player.id_in_group - 1
                costs = assign_costs(player,all_costs['low_emitters'],player_index)
            player.generate_bid_stubs()
            player.generate_unit_stubs(costs)
            # Costs need to be sorted by player
            #player.generate_unit_stubs(self.session.vars['costs'][player.role()][player_index])

    def vars_for_admin_report(self):
        money = sorted([p.money for p in self.get_players()])
#        session_qs = Session.objects.filter(round_number<=self.round_number)
        return {'money': money}


class Group(BaseGroup):
    pass

class Player(BasePlayer):
    first_name = models.CharField()
    last_name = models.CharField()
    computing_ID = models.CharField()
    money = models.CurrencyField()
    permits = models.PositiveIntegerField(initial=0)
    capacity = models.PositiveIntegerField()
    emission_intensity = models.PositiveIntegerField()
    permits_purchased_auction = models.PositiveIntegerField()
    penalty = models.CurrencyField()

    # Need to make the choices array dynamic 
    production_amount = models.PositiveIntegerField(min=Constants.must_run, max=4, choices=range(Constants.must_run,Constants.production_capacity_low+1))

    def role(self):
        if self.id_in_group > self.session.config['num_low_emitters']:
            return 'high_emitter'
        else:
            return 'low_emitter'

    # Helper function to retrieve bids
    def get_bids(self):
        bid_qs = Bid.objects.filter(player__exact=self).filter(bid__isnull=False)
        return [bids.bid for bids in bid_qs]

    # Helper function to retreive plant costs
    def get_costs(self):
        unit_qs = Unit.objects.filter(player__exact=self).order_by('cost')
        return [unit.cost for unit in unit_qs]

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
            bid = self.bid_set.create() # create a new bid object as part of the player's bid set
            bid.round = self.subsession.round_number
            bid.pid_in_group = self.id_in_group
            bid.save()   # important: save to DB!
            if self.role() == 'high_emitter':
                bid2 = self.bid_set.create() # Double the bids for high emitters
                bid2.round = self.subsession.round_number
                bid2.pid_in_group = self.id_in_group
                bid2.save()

    def generate_unit_stubs(self, player_costs):
        """
        Create a fixed number of production unit stubs.
        """
        player_costs = sorted(player_costs)
        if self.role() == 'high_emitter':
            capacity = Constants.production_capacity_high
        else:
            capacity = Constants.production_capacity_low
        for i in range(capacity):
            unit = self.unit_set.create() # add new production unit to set
            unit.unit_num = i
            unit.cost = player_costs[i]
            unit.save() # important: save to DB!


class Bid(Model):  # inherits from Django's base "Model"
    BID_CHOICES = currency_range(c(Constants.reserve_price), c(Constants.maximum_bid), c(Constants.bid_price_increment))
    round = models.PositiveIntegerField()
    bid = models.CurrencyField(choices=BID_CHOICES)
    accepted = models.PositiveIntegerField()
    pid_in_group = models.PositiveIntegerField()
    player = ForeignKey(Player)    # creates 1:m relation -> this bid was made by a certain player


class Unit(Model):  # inherits from Django's base "Model"
    unit_num = models.IntegerField()
    cost = models.CurrencyField()
    unit_used = models.PositiveIntegerField()
    player = ForeignKey(Player)  # creates 1:m relation -> this bid was made by a certain player
