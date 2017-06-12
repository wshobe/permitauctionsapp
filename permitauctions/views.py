from otree.api import Currency as c, currency_range
from ._builtin import Page, WaitPage
from .models import Bid, Constants, Player
from math import floor
import numpy as np
import pandas as pd
from django.db.models import Count, Min, Sum, Avg
from .generate_random_costs import costs1, assign_costs, generate_output_prices
from .helper_functions import make_rounds_table,make_supply_schedule,calculate_auction_price
from django.forms import modelformset_factory
from django.http import HttpResponse
import logging


def vars_for_all_templates(self):
    round_number = self.subsession.round_number
    permits_available = self.subsession.permits_available
    num_participants = self.session.config['num_high_emitters'] + self.session.config['num_low_emitters']
    output_price = c(self.subsession.output_price)
    high_output_price = self.session.config['low_output_price'] + self.session.config['high_output_price_increment']
    table_data = make_rounds_table(self.subsession,
        self.session.vars['output_prices_for_table'],
        self.session.vars['round_numbers'],
        self.session.vars['period_caps'],
        self.session.vars['full_capacity_permit_demand'])
    #player_payoffs = [p.money * self.session.config['payout_rate'] for p in self.subsession.get_players()]
    #mean_payoff = np.mean(player_payoffs)
    return {
        'permits_available': permits_available,
        'output_price': output_price,
        'high_output_price': high_output_price,
        'num_participants': num_participants,
        'table_data': table_data,
        'rounds':list(range(self.session.config['last_round'])),
    }

class Signin(Page):
    form_model = Player
    form_fields = ['first_name', 'last_name', 'computing_ID']

    def is_displayed(self):
        # Putting this code here is hacky; see models.py for why this isn't in before_session_starts
        # We do not need to put constant attributes of players here. These are set in subsession #1.
        # The only things that need to go here are items that depend on player actions.
        if self.subsession.round_number > 1:
            for player in self.subsession.get_players():
                old_player = player.in_previous_rounds()[-1]
                player.money = old_player.money
                #player.starting_permits = old_player.permits
                player.permits = old_player.permits
                player.first_name = old_player.first_name
                player.last_name = old_player.last_name
                player.computing_ID = old_player.computing_ID
        return self.round_number == 1

class SigninWaitPage(WaitPage):
    def is_displayed(self):
        return self.round_number == 1 and self.session.config['show_instructions']


class Instructions1(Page):
    def is_displayed(self):
        return self.round_number == 1 and self.session.config['show_instructions']

    def vars_for_template(self):
        if self.player.role() == 'high_emitter':
            player_type = "high"
            num_bids = Constants.num_bids_high
        else:
            player_type = "low"
            num_bids = Constants.num_bids_low
        return {
            'player_type': player_type,
            'num_bids': num_bids,
            'initial_cash_endowment': self.player.money
        }

class Instructions2(Page):
    def is_displayed(self):
        return self.round_number == 1 and self.session.config['show_instructions']

    def vars_for_template(self):
        if self.player.role() == 'high_emitter':
            player_type = "high"
            num_bids = Constants.num_bids_high
        else:
            player_type = "low"
            num_bids = Constants.num_bids_low
        return {
            'player_type': player_type,
            'num_bids': num_bids,
            'initial_cash_endowment': self.player.money
        }

class Instructions3(Page):
    def is_displayed(self):
        return self.round_number == 1 and self.session.config['show_instructions']

    def vars_for_template(self):
        output_price = c(self.subsession.output_price)
        # list of (cost, expected value) for each plant
        cost_list = [
                (   
                    index,
                    cost,
                    self.player.emission_intensity,
                    self.subsession.output_price - cost,
                    (self.subsession.output_price - cost)/self.player.emission_intensity
                ) for index,cost in enumerate(self.player.get_costs())]
        if self.player.role() == 'high_emitter':
            player_type = "high"
            num_bids = Constants.num_bids_high
        else:
            player_type = "low"
            num_bids = Constants.num_bids_low
        return {
            'cost_list': cost_list,
            # TODO: Why have this limit at all, if the players aren't expected to misplay
            'max_bid_dollar_value': self.player.money + (self.player.capacity * output_price),
            'player_type': player_type,
            'num_bids': num_bids,
            'initial_cash_endowment': self.player.money
        }

class Instructions4(Page):
    def is_displayed(self):
        return self.round_number == 1 and self.session.config['show_instructions']

    def vars_for_template(self):
        if self.player.role() == 'high_emitter':
            player_type = "high"
            num_bids = Constants.num_bids_high
        else:
            player_type = "low"
            num_bids = Constants.num_bids_low
        return {
            'num_rounds': Constants.num_rounds,
            'payout_percent': self.session.config['payout_rate']*100,
            'player_type': player_type,
            'num_bids': num_bids,
            'initial_cash_endowment': self.player.money
        }

# This bid form set is for the auction bid list.
BidFormSet = modelformset_factory(Bid, fields=("bid",), extra=0)

class Auction(Page):
    def vars_for_template(self):
        output_price = self.subsession.output_price
        # list of (cost, expected value) for each plant
        costs = self.player.get_costs()
        cost_list = [
            (
                cost,
                output_price - cost,
                (output_price - cost) / self.player.emission_intensity,
                output_price
            ) for cost in costs
        ]

        # get bids for this player
        bid_qs = self.player.bid_set.all()
        #assert len(bid_qs) == Constants.num_bids_per_round
        bids_formset = BidFormSet(queryset=bid_qs)
        bid_fields = [field for field in [form for form in bids_formset]]
        if self.player.role() == 'high_emitter':
            num_bids = Constants.num_bids_high
        else:
            num_bids = Constants.num_bids_low
        total_net_value = sum([output_price - cost for cost in costs])
        #assert False, "permit value {:f}".format(test)
        return {
            'bid_formset': bids_formset,
            'cost_list': cost_list,
            'bid_table': zip(bid_fields, cost_list),
            'bid_entries': bid_fields[:num_bids],
            'max_bid_dollar_value': self.player.money + total_net_value,
            'player_money': self.player.money.to_number(),
            'allow_deficit': self.session.config["allow_deficit_bids"]
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
        #assert len(bid_objs_by_id) == num_bids

        for i in range(num_bids):
            input_prefix = 'form-%d-' % i
            # get the inputs
            dec_id = int(submitted_data[input_prefix + 'id'])
            bid_submitted = submitted_data[input_prefix + 'bid']
            # double the bids for high emitters
            for j in range(self.player.emission_intensity):
                # lookup by ID and save submitted data
                # TODO: i * num_bids + j so bids are next to each other instead of interleaved?
                bid_row = bid_objs_by_id[dec_id + (j * num_bids)]
                if bid_submitted != '':
                    bid_row.bid = bid_submitted
                else:
                    bid_row.bid = None
                # important: save to DB!
                bid_row.save()


class AuctionConfirm(Page):
    # TODO: Add a way for user to correct values without having to go back
    # TODO: Do not allow bids for more than the max total bid amount.
    #    Maybe this should be done on the auction page itself.

    def vars_for_template(self):
        bid_qs = Bid.objects.filter(player__exact=self.player).filter(bid__isnull=False).order_by('-bid')
        return {'bid_list': [dec.bid for dec in bid_qs]}
        #return {'bid_list': self.player.get_bids()}

class AuctionWaitPage(WaitPage):
    title_text = "Please wait"
    """
    Almost all of this work is done in memory in a dataframe. This is much faster and less reliant on very fast data connections.
    """
    def after_all_players_arrive(self):
        permits_available = self.subsession.permits_available
        ecr_reserve_amount = self.session.config['initial_ecr_reserve_amount']
        self.subsession.ecr_reserve_amount_used = 0
        # Get all bid records for all players in this round and put the records in a dataframe
        supply = make_supply_schedule(self.subsession,Constants)
        bid_qs = Bid.objects.filter(player__session_id=self.session.id).filter(round=self.subsession.round_number).filter(bid__isnull=False)
        num_bids = len(bid_qs)
        if num_bids > 0:
            bids_df = pd.DataFrame(list(bid_qs.order_by('-bid').values('id', 'bid', 'accepted', 'player_id', 'pid_in_group')))
            auction_close = calculate_auction_price(bids_df,supply,self.subsession,Constants.reserve_price)
            auction_price = auction_close['price']
            #log = logging.getLogger('permitauctionsapp')
            #log.info('aapa auction_price: {0:.2f}'.format(auction_price))
            permits_available = self.subsession.permits_available
            first_rejected_bid = auction_close['first_rejected_bid']
            bids_df.accepted = auction_close['accepted']
            self.subsession.pcr_amount_added = auction_close['pcr_amount_added']
            self.subsession.ecr_reserve_amount_used = auction_close['ecr_reserve_amount_used']
            self.subsession.number_sold_auction = bids_df.accepted.sum()
            #log.info('aapa permits_available: {}'.format(permits_available))
            #log.info('aapa ecr_reserve_amount_used: {}'.format(auction_close['ecr_reserve_amount_used']))
            #log.info('aapa first_rejected_bid: {0:.2f}'.format(auction_close['first_rejected_bid']))
            #log.info('aapa pcr_amount_added: {}'.format(auction_close['pcr_amount_added']))
        else:
            auction_price = Constants.reserve_price
            first_rejected_bid = Constants.reserve_price
            self.subsession.ecr_reserve_amount_used = ecr_reserve_amount
            self.subsession.number_sold_auction = 0
            for player in self.subsession.get_players():
                player.permits_purchased_auction = 0
        self.subsession.auction_price = auction_price
        pcr_trigger = self.session.config['price_containment_trigger']
        pcr_available = self.session.config['price_containment_reserve_amount']
        #if auction_price == Constants.reserve_price:
        #    self.subsession.ecr_reserve_amount_used = self.session.config['initial_ecr_reserve_amount']
            #permits_available = permits_available - self.session.config['initial_ecr_reserve_amount']
        # If the initial price is below the ecr_trigger but above the reserve, 
        #      remove some allowances from the ecr.
        #if auction_price == self.session.config['ecr_trigger_price']:
        #    self.subsession.ecr_reserve_amount_used = permits_available - self.subsession.number_sold_auction
        #    purchased = bids_df.groupby('pid_in_group')[['accepted']].sum()
        #    self.subsession.ecr_reserve_amount_used = permits_available - purchased
        # Now, assign permits to players by marking bids in bids_df as accepted
        if num_bids > 0:
            # Take care of ties
            if first_rejected_bid > 0:
                count = len(bids_df[bids_df.bid == first_rejected_bid])
                num_accepted = int(bids_df.accepted[bids_df.bid == first_rejected_bid].sum())   # int(bids_df.sum()['accepted'])
                # Reset all to zero
                bids_df.accepted[bids_df.bid == first_rejected_bid] = 0
                #    remaining = permits_available - temp_accepted
                rnd = np.random.permutation(count)
                grab = bids_df.index[bids_df.bid == first_rejected_bid].take(rnd)[:num_accepted]
                bids_df.accepted.loc[grab] = 1
                #log = logging.getLogger('permitauctionsapp')
                #log.info('count: %d' % count)
                #log.info('num accepted: %d' % num_accepted)
                # Save bid accepted information to the bid data
            for bid_record in bid_qs:
                bid_record.accepted = bids_df.accepted.ix[bids_df.id == bid_record.id].item()
                bid_record.save()
            # Calculate the total purchases for each player and save to the player record
            self.subsession.number_sold_auction = bids_df.accepted.sum()
            purchased = bids_df.groupby('pid_in_group')[['accepted']].sum()
            for index,accepted in zip(purchased.index,purchased.accepted):
                player = self.group.get_player_by_id(index)
                purchased_at_auction = 0 if accepted is None else accepted
                player.permits_purchased_auction = purchased_at_auction
                player.permits = player.permits + purchased_at_auction
                player.money = player.money - c(float(auction_price) * purchased_at_auction)
            for player in self.subsession.get_players():
                purchased = 0 if player.permits_purchased_auction is None else player.permits_purchased_auction
                player.permits_purchased_auction = purchased
        
    def vars_for_template(self):
        bid_qs = [(dec.pk, dec.bid) for dec in self.player.bid_set.all()]
        return {'bid_list': bid_qs}

class AuctionResults(Page):
    def vars_for_template(self):
        auction_price = self.subsession.auction_price
        ecr_removed = self.subsession.ecr_reserve_amount_used
        pcr_added = self.subsession.pcr_amount_added
        # Retrieve only this player's bids
        player_id = self.player.id
        bids = self.player.bid_set.all().filter(bid__isnull=False).order_by('-bid').values('bid', 'accepted')
        num_bids = len(bids)
        num_successful_bids = 0 if num_bids == 0 else bids.aggregate(total_won=Sum('accepted'))['total_won']
        no_bids_accepted = (num_bids == 0 or num_successful_bids == 0)
        no_bids_rejected = (num_bids == 0 or num_bids == num_successful_bids)
        return {
            'player_name': self.player.first_name,
            'player_id': player_id,
            'bids': [(index, bid['accepted'], bid['bid']) for index, bid in enumerate(bids)],
            'this_player_bought': self.player.permits_purchased_auction,
            'how_many_accepted': num_successful_bids,
            'num_bids': num_bids,
            'no_bids_accepted': no_bids_accepted,
            'no_bids_rejected': no_bids_rejected,
            'ecr_removed': ecr_removed,
            'pcr_added': pcr_added,
            'auction_price': auction_price,
            'total_spent': auction_price * num_successful_bids,
            'pool_change': abs(self.subsession.ecr_reserve_amount_used)
        }

class Production(Page):
    form_model = Player
    form_fields = ['production_amount']

    def vars_for_template(self):
        # List of (cost, expected value) pairs
        cost_list = [
            (
                cost,
                self.subsession.output_price - cost,
                (self.subsession.output_price - cost) / self.player.emission_intensity
            ) for cost in self.player.get_costs()
        ]
        return {'cost_list': cost_list}

    def before_next_page(self):
        costs = self.player.get_costs()
        num_plants = self.player.production_amount

        # Money for however many plants they chose to run
        output_price = self.subsession.output_price
        earnings = c(0)
        cash_holdings = self.player.money
        for i in range(num_plants):
            earnings = earnings + output_price - costs[i]
        cash_holdings = cash_holdings + earnings
        # consume necessary permits for operating
        permits_required = num_plants * self.player.emission_intensity
        net_permits = self.player.permits - permits_required
        if net_permits < 0:
            self.player.penalty = net_permits * Constants.penalty_amount
            self.player.money = cash_holdings + self.player.penalty # Penalty is a negative amount
            self.player.payoff = (cash_holdings + self.player.penalty) * self.session.config['payout_rate']
            self.player.permits = 0
        else:
            self.player.permits = self.player.permits - permits_required
            self.player.penalty = 0
            self.player.money = cash_holdings
            self.player.payoff = cash_holdings * self.session.config['payout_rate']


class RoundResults(Page):
    def vars_for_template(self):
        permits_purchased = 0 if self.player.permits_purchased_auction is None else self.player.permits_purchased_auction
        return {
            'permits_used': self.player.emission_intensity * self.player.production_amount,
            'spent_auction': permits_purchased * self.subsession.auction_price,
            'penalty': abs(self.player.penalty),
            'earnings': self.player.production_amount*self.subsession.output_price
        }

class FinalResults(Page):
    def is_displayed(self):
        return (self.round_number >= self.session.config['last_round'] or self.round_number >= Constants.num_rounds)

    def vars_for_template(self):
        return {
            'payout': self.player.money * self.session.config['payout_rate'],
            'net_payout': self.player.money * self.session.config['payout_rate'] - 6
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
