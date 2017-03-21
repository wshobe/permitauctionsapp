from otree.api import Currency as c, currency_range
from . import models
from ._builtin import Page, WaitPage
from .models import Constants, Bid
from math import floor
import random
import numpy as np
import pandas as pd
from django.db.models import Count, Min, Sum, Avg
from .generate_random_costs import costs1, assign_costs, generate_output_prices
from .helper_functions import make_initial_rounds_table
from django.forms import modelformset_factory

def vars_for_all_templates(self):
    permits_available = self.subsession.permits_available
    num_participants = self.session.config['num_high_emitters'] + self.session.config['num_low_emitters']
    ecr_reserve_amount = self.session.config['initial_ecr_reserve_amount']  # compliance reserve
    debug = self.session.config['debug']
    output_price = self.subsession.output_price
    return {
                'permits_available': permits_available,
                'ecr_reserve_amount': ecr_reserve_amount,
                'output_price': output_price,
                'num_participants': num_participants,
                'rounds':list(range(self.session.config['last_round'])),
                'debug': debug
    }

class Signin(Page):
    form_model = models.Player
    form_fields = ['first_name', 'last_name', 'computing_ID']
    
    def is_displayed(self):
        # Putting this code here is hacky; but see models.py for why this isn't in before_session_starts
        # We do not need to put constant attributes of players here. These are set in subsession #1.
        # The only things that need to go here are items that depend on player actions.
        if self.subsession.round_number > 1:
            for player in self.subsession.get_players():
                old_player = player.in_previous_rounds()[-1]
                player.money = old_player.money
                player.permits = old_player.permits
                player.first_name = old_player.first_name
                player.last_name = old_player.last_name
                player_computing_ID = old_player.computing_ID

        return self.round_number == 1 


    """def vars_for_template(self):
        bid_qs = Bid.objects.filter(player__exact=self.player)
        return {'bids': zip([dec.bid for dec in bid_qs])
            }"""


class SigninWaitPage(WaitPage):
    def is_displayed(self):
        return (self.round_number == 1 & self.session.config['show_instructions'] == True)


class Instructions1(Page):
    def is_displayed(self):
        return (self.round_number == 1 & self.session.config['show_instructions'] == True)

    def vars_for_template(self):
        #player_type = "high" if self.player.emission_intensity == Constants.emission_intensity_high else "low"
        if self.player.emission_intensity  == Constants.emission_intensity_high:
            player_type = "high"
            num_bids = Constants.num_bids_high
        else:
            player_type = "low"
            num_bids = Constants.num_bids_low
        high_output_price = Constants.low_output_price + Constants.high_output_price_increment
        return {
                'high_output_price':high_output_price,
                'player_type': player_type,
                'num_bids': num_bids,
                'initial_cash_endowment': self.player.money
            }

class Instructions2(Page):
    def is_displayed(self):
        return (self.round_number == 1 & self.session.config['show_instructions'] == True)

    def vars_for_template(self):
        #player_type = "high" if self.player.emission_intensity == Constants.emission_intensity_high else "low"
        if self.player.emission_intensity  == Constants.emission_intensity_high:
            player_type = "high"
            num_bids = Constants.num_bids_high
        else:
            player_type = "low"
            num_bids = Constants.num_bids_low
        high_output_price = Constants.low_output_price + Constants.high_output_price_increment
        return {
                'high_output_price':high_output_price,
                'player_type': player_type,
                'num_bids': num_bids,
                'initial_cash_endowment': self.player.money
            }

class Instructions3(Page):
    def is_displayed(self):
        return (self.round_number == 1 & self.session.config['show_instructions'] == True)

    def vars_for_template(self):
        output_price = self.subsession.output_price
        # list of (cost, expected value) for each plant
        cost_list = [
                (   index,
                    cost,
                    self.subsession.output_price - cost,
                    self.player.emission_intensity,
                    (self.subsession.output_price - cost)/self.player.emission_intensity
                ) for index,cost in enumerate(self.player.get_costs())]
        """cost_list = [
                        (
                            cost,
                            output_price - cost,
                            (output_price - cost)/self.player.emission_intensity,
                            output_price
                        ) for cost in self.player.get_costs()]"""
        #player_type = "high" if self.player.emission_intensity == Constants.emission_intensity_high else "low"
        if self.player.emission_intensity  == Constants.emission_intensity_high:
            player_type = "high"
            num_bids = Constants.num_bids_high
        else:
            player_type = "low"
            num_bids = Constants.num_bids_low
        high_output_price = Constants.low_output_price + Constants.high_output_price_increment
        return {
                'cost_list': cost_list,
                'max_bid_dollar_value': self.player.money + (self.player.capacity*output_price),
                'high_output_price':high_output_price,
                'player_type': player_type,
                'num_bids': num_bids,
                'initial_cash_endowment': self.player.money
            }

class Instructions4(Page):
    def is_displayed(self):
        return (self.round_number == 1 & self.session.config['show_instructions'] == True)

    def vars_for_template(self):
        #player_type = "high" if self.player.emission_intensity == Constants.emission_intensity_high else "low"
        if self.player.emission_intensity  == Constants.emission_intensity_high:
            player_type = "high"
            num_bids = Constants.num_bids_high
        else:
            player_type = "low"
            num_bids = Constants.num_bids_low
        high_output_price = Constants.low_output_price + Constants.high_output_price_increment
        table_data = make_initial_rounds_table(self.session,Constants)
        table_data.output_prices = table_data.output_prices.astype(int)
        #assert False
        return {
                'num_rounds':Constants.num_rounds,
                'high_output_price':high_output_price,
                'player_type': player_type,
                'num_bids': num_bids,
                'table_data':table_data,
                'output_prices':table_data.output_prices[:self.subsession.round_number],
                'initial_cash_endowment': self.player.money
            }

# This bid form set is for the auction bid list.

BidFormSet = modelformset_factory(Bid, fields=("bid",), extra=0)

class Auction(Page):

    def vars_for_template(self):
        output_price = self.subsession.output_price
        # list of (cost, expected value) for each plant
        costs = self.player.get_costs()
        """        cost_list = [
                        (
                            cost,
                            self.subsession.output_price - cost,
                            (self.subsession.output_price - cost)/self.player.emission_intensity,
                            index
                        ) for index,cost in enumerate(self.player.get_costs())]"""
        cost_list = [
                        (
                            cost,
                            output_price - cost,
                            (output_price - cost)/self.player.emission_intensity,
                            output_price
                        ) for cost in costs]
        # get bids for this player
        bid_qs = self.player.bid_set.all()
        #assert len(bid_qs) == Constants.num_bids_per_round

        bids_formset = BidFormSet(queryset=bid_qs)
        bid_fields = [field for field in [form for form in bids_formset]]
#        assert False
        #table_data = [bid.pk for bid in bid_qs]
        table_data = make_initial_rounds_table(self.session,Constants)
        output_prices = table_data.output_prices.astype(int)[:self.subsession.round_number]
        total_net_value = sum([output_price-cost for cost in costs])
        #assert False,"permit value {:f}".format(test)
        return {
                'bid_formset': bids_formset,
                #'bid_values_and_forms': zip([dec.value for dec in bid_qs], bids_formset.forms),
                'table_data': table_data,
                'output_prices':output_prices,
                'cost_list': cost_list,
                'bid_table': zip(bid_fields,cost_list),
                'max_bid_dollar_value': self.player.money + total_net_value
                }

    def before_next_page(self):
        # get the raw submitted data as dict
        submitted_data = self.form.data
        if self.player.role() == 'high_emitter':
            num_bids = Constants.num_bids_high
        else:
            num_bids = Constants.num_bids_low
        # get all bids belonging to this player and save as dict with bid ID lookup
        bid_objs_by_id = {dec.pk: dec for dec in self.player.bid_set.all()}
        assert len(bid_objs_by_id) == num_bids

        for i in range(num_bids):
            input_prefix = 'form-%d-' % i

            # get the inputs
            dec_id = int(submitted_data[input_prefix + 'id'])
            bid = submitted_data[input_prefix + 'bid']
            # lookup by ID and save submitted data
            dec = bid_objs_by_id[dec_id]

            if bid != '':
                dec.bid = bid
            else:
                dec.bid = None
            # important: save to DB!
            dec.save()


class AuctionConfirm(Page):
    # TODO: Add a way for user to correct values without having to go back
    # TODO: Do not allow bids for more than the max total bid amount. 
    #    Maybe this should be done on the auction page itself.

    def vars_for_template(self):
        bid_qs = Bid.objects.filter(player__exact=self.player).filter(bid__isnull=False)
        return {'bid_list': [dec.bid for dec in bid_qs]}
        #return {'bid_list': self.player.get_bids()}


# Returns the price of the first rejected bid
# If there are not enough bids to consume the permit pool, returns the lowest bid
def second_price_auction(num_permits, num_bids, bids):
    permits_available = num_permits
    if num_bids <= permits_available:
        auction_price = Constants.reserve_price
    else:
        auction_price = bids.bid[permits_available]   # First rejected bid
    return auction_price

class AuctionWaitPage(WaitPage):
    title_text = "Please wait"
    """
    Almost all of this work is done in memory in a dataframe. This is much faster and less reliant on 
    very fast data connections. 
    """
    def after_all_players_arrive(self):
        permits_available = self.subsession.permits_available
        # Get all bid records for all players in this round and put the records in a dataframe
        bid_qs = Bid.objects.filter(player__session_id=self.session.id).filter(round=self.subsession.round_number).filter(bid__isnull=False)
        bids_df = pd.DataFrame(list(bid_qs.order_by('-bid').values('id','bid','accepted','player_id','pid_in_group')))
        num_bids = len(bids_df)
        self.subsession.ecr_reserve_amount_used = 0
        # Get a preliminary auction price, then check for price collar conditions
        auction_price = second_price_auction(permits_available,num_bids, bids_df)
        self.subsession.initial_auction_price = auction_price
        starting_ecr_reserve = self.session.config['initial_ecr_reserve_amount']
        pcr_trigger = Constants.price_containment_trigger
        pcr_available = Constants.price_containment_reserve_amount
        # If the initial price is below the ecr_trigger, remove some allowances from the ecr.
        if auction_price < Constants.ecr_trigger_price:
            diff = Constants.ecr_trigger_price - auction_price
            # Just division, not floor division
            removed = min(round((diff / c(0.6) * Constants.reserve_increment)), starting_ecr_reserve)
            self.subsession.ecr_reserve_amount_used = removed
            permits_available = permits_available - removed
            auction_price = second_price_auction(permits_available,num_bids, bids_df)
        # If the initial price is above the upper limit, release some of the pcr
        elif auction_price > pcr_trigger:
            #assert False, "auction_price > pcr_trigger"
            if bids_df.bid[permits_available - 1 + pcr_available] > pcr_trigger:
                self.subsession.pcr_amount_added = pcr_available
                permits_available = permits_available + pcr_available
            else:
                pcr_added = 0
                while auction_price > pcr_trigger:
                    pcr_added += 1
                    if bids_df.bid[permits_available - 1 + pcr_added] == pcr_trigger:
                        break
                auction_price = pcr_trigger
                self.subsession.pcr_amount_added = pcr_added
                permits_available = permits_available + pcr_added
        # This is my final offer!
        self.subsession.auction_price = auction_price
        # Now, assign permits to players by marking bids in bids_df as accepted
        bids_df.accepted = 0  # Only bids at or above the reserve are included in bids_df
        # If the world is awash in permits...
        if permits_available >= len(bids_df):
            bids_df.accepted = 1
        # If the auction closes normally with no ties
        elif auction_price > bids_df.bid.iloc[permits_available]:
            bids_df.accepted[bids_df.bid > auction_price] = 1
        # Take care of ties
        else:
            bids_df.accepted[bids_df.bid > auction_price] = 1
            temp_accepted = int(bids_df.sum()['accepted'])
            remaining = permits_available - temp_accepted
            count = len(bids_df[bids_df.bid==auction_price])
            rnd = np.random.permutation(count)
            grab = bids_df.index[bids_df.bid==auction_price].take(rnd)[:remaining]
            bids_df.accepted.loc[grab] = 1
        # Save bid accepted information to the bid data
        for bid_record in bid_qs:
            bid_record.accepted = bids_df.accepted.ix[bids_df.id==bid_record.id].item()
            bid_record.save()
        # Calculate the total purchases for each player and save to the player record
        self.subsession.number_sold_auction = bids_df.accepted.sum()
        purchased = bids_df.groupby('pid_in_group',as_index=False).sum()
        for index,accepted in zip(purchased.pid_in_group,purchased.accepted):
            player = self.group.get_player_by_id(index)
            player.permits_purchased_auction = accepted
            player.permits = player.permits + accepted
            player.money = player.money - c(float(auction_price)*accepted)
    
    def vars_for_template(self):
        bid_qs = [(dec.pk, dec.bid) for dec in self.player.bid_set.all()]
        return {'bid_list': bid_qs}


class AuctionResults(Page):
    def vars_for_template(self):
        pool_change = abs(self.subsession.ecr_reserve_amount_used)
        permits_available = self.subsession.permits_available
        auction_price = self.subsession.auction_price
        ecr_removed = self.subsession.ecr_reserve_amount_used
        # Retrieve only this player's bids
        player_id = self.player.id
        bids = self.player.bid_set.all().filter(bid__isnull=False).order_by('-bid').values('bid','accepted')
        num_bids = len(bids)
        num_successful_bids = bids.aggregate(total_won = Sum('accepted'))['total_won']
        no_bids_accepted = True if num_successful_bids == 0 else False
        no_bids_rejected = True if (num_bids == 0 or num_bids == num_successful_bids) else False
        return {
            'player_name': self.player.first_name,
            'player_id': player_id,
            'bids': [(index,bid['accepted'],bid['bid']) for index,bid in enumerate(bids)],
            'permits_available': permits_available,
            'permits_available': permits_available,
            'this_player_bought': self.player.permits_purchased_auction,
            'how_many_accepted': num_successful_bids,
            'num_bids': num_bids,
            'no_bids_accepted': no_bids_accepted,
            'no_bids_rejected': no_bids_rejected,
            'ecr_removed': ecr_removed,
            'auction_price': auction_price,
            'total_spent': auction_price*num_successful_bids,
            'pool_change': pool_change  #,
        }

class Production(Page):
    form_model = models.Player
    form_fields = ['production_amount']

# It doesn't look like this function is used.
    """def production_amount_choices(self):
        # range(1,0) returns an empty list. 'base' forces the minimum choice of 1
        # This does not allow a player to over-produce. Probably needs to be changed.
        base = [1]
        if self.player.role() == 'high_emitter':
            return base + list(range(2, min((self.player.permits // 2) + 1, Constants.production_capacity_high + 1)))
        elif self.player.role() == 'low_emitter':
            return base + list(range(2, min(self.player.permits + 1, Constants.production_capacity_low + 1)))"""

    def vars_for_template(self):
        # List of (cost, expected value) pairs
        cost_list = [(cost, 
                    self.subsession.output_price - cost,
                    (self.subsession.output_price - cost)/self.player.emission_intensity) for cost in self.player.get_costs()]
        return {'cost_list': cost_list}

    def before_next_page(self):
        costs = self.player.get_costs()
        num_plants = self.player.production_amount

        # Money for however many plants they chose to run
        for i in range(num_plants):
            self.player.money = self.player.money + self.subsession.output_price - costs[i]

        # consume necessary permits for operating
        permits_required = num_plants * self.player.emission_intensity
        net_permits = self.player.permits - permits_required
        if net_permits < 0:
            self.player.penalty = net_permits * Constants.penalty_amount
            self.player.money = self.player.money + self.player.penalty # Penalty is a negative amount
            self.player.permits = 0
        else:
            self.player.permits = self.player.permits - permits_required
            self.player.penalty = 0


class RoundResults(Page):
    def vars_for_template(self):
        return {
            'permits_used': self.player.emission_intensity * self.player.production_amount,
            'spent_auction': self.player.permits_purchased_auction * self.subsession.auction_price,
            'earnings': self.player.production_amount*self.subsession.output_price
        }


class FinalResults(Page):
    def is_displayed(self):
        return (self.round_number == self.session.config['last_round'] | self.round_number == Constants.num_rounds)

    def vars_for_template(self):
        return {
            'payout': self.player.money * Constants.payout_rate
        }

            
page_sequence = [
    Signin,
    SigninWaitPage,
    Instructions1,
    Instructions2,
    Instructions3,
    Instructions4,
    Auction,
    AuctionConfirm,
    AuctionWaitPage,
    AuctionResults,
    Production,
    RoundResults,
    FinalResults
]
