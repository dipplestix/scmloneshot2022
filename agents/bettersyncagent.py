from scml.oneshot import *
from negmas import ResponseType
from scml.scml2020.common import QUANTITY, TIME, UNIT_PRICE
import numpy as np
import random
from math import floor

class BetterSyncAgent(OneShotAgent):
    def init(self):
        # Initializes the agent.
        # Gets the probability of different exogenous contracts quantities given the world size
        # Does some administrative stuff based on the level of the agent
        self.world_size = f'{len(self.awi.all_consumers[0])} {len(self.awi.all_consumers[1])}'
        self.max_wait = len(self.awi.all_consumers[0]) + len(self.awi.all_consumers[1]) + 1
        if self.awi.level == 0:
            self.partners = self.awi.my_consumers
            self.output = [True]
            self.partner = 'buyer'

        elif self.awi.level == 1:
            self.partners = self.awi.my_suppliers
            self.output = [False]
            self.partner = 'seller'

        self.balances = {c: [] for c in self.partners}
        self.n_negotiation_rounds = self.awi.settings["neg_n_steps"]
        self.debug = False

    def before_step(self):
        # Sets the agent up for the round.
        # Resets the number of proposals/offers/waits to 0
        # Finds information about the exogenous contracts for the round
        if (self.awi.current_step - 1) % 5 == 0:
            for c in self.partners:
                self.balances[c].append(self.awi.reports_at_step(self.awi.current_step - 1)[c].cash)

        self.accepted_offers = {}
        self.received_offers = {}
        self.sent_offers = {c: 'First' for c in self.partners}

        self.proposal_count = {c: 0 for c in self.partners}
        self.response_count = {c: 0 for c in self.partners}
        self.wait_count = {c: 0 for c in self.partners}

        self.num_in = self.awi.exogenous_contract_summary[0][0]
        self.num_out = self.awi.exogenous_contract_summary[-1][0]
        self.ufun.find_limit(True)
        self.ufun.find_limit(False)

        if self.awi.level == 0:
            self.q = self.awi.state().exogenous_input_quantity
            self.min_price = self.awi.current_output_issues[UNIT_PRICE].min_value
            self.max_price = self.awi.current_output_issues[UNIT_PRICE].max_value

        elif self.awi.level == 1:
            self.q = self.awi.state().exogenous_output_quantity
            self.min_price = self.awi.current_input_issues[UNIT_PRICE].min_value
            self.max_price = self.awi.current_input_issues[UNIT_PRICE].max_value

    def propose(self, negotiator_id: str, state) -> "Outcome":
        self.wait_count[negotiator_id] = 0
        if self.sent_offers[negotiator_id] == 'First':
            offer = self.get_first_offer(negotiator_id, state)
            self.sent_offers[negotiator_id] = offer
        else:
            offer = self.sent_offers[negotiator_id]
        if self.debug:
            print(f'I am proposing {offer} to {negotiator_id}')
        return offer

    def respond(self, negotiator_id, state, offer):
        self.cleanup(negotiator_id, offer)
        if self.wait_count[negotiator_id] < (self.max_wait - 1) and len(self.received_offers) < len(self.partners):
            self.wait_count[negotiator_id] += 1
            response = ResponseType.WAIT
        else:
            response = self.get_response(negotiator_id, state, offer)
        if response == ResponseType.REJECT_OFFER:
            self.sent_offers[negotiator_id] = self.get_offer(negotiator_id, state, offer)
        else:
            self.sent_offers[negotiator_id] = [0, self.awi.current_step, 0]
        if self.debug:
            if response != ResponseType.WAIT:
                print(f'I have {len(self.received_offers)} offers waiting for me: {self.received_offers}')
                print(f'I am responding to {negotiator_id}\'s offer of {offer} with {response} after waiting {self.wait_count[negotiator_id]} times')
                print(f'The time step is {state.step}')
        return response

    def on_negotiation_success(self, contract, mechanism):
        negotiator_id = contract.annotation[self.partner]
        q = contract.agreement['quantity']
        p = contract.agreement['unit_price']
        offer = [-1]*3
        offer[TIME] = self.awi.current_step
        offer[QUANTITY] = q
        offer[UNIT_PRICE] = p
        self.q -= q
        self.accepted_offers[negotiator_id] = tuple(offer)

    def on_negotiation_failure(self, partners, annotation, mechanism, state):
        pass
    
    def get_first_offer(self, negotiator_id, state):
        self.proposal_count[negotiator_id] += 1

    def cleanup(self, negotiator_id, offer):
        try:
            del self.sent_offers[negotiator_id]
        except:
            pass
        self.received_offers[negotiator_id] = offer

    def get_response(self, negotiator_id, state, offer):
        self.response_count[negotiator_id] += 1

    def get_offer(self, negotiator_id, state, offer):
        self.proposal_count[negotiator_id] += 1


class TestAgent(BetterSyncAgent):
    def init(self):
        # Initializes the agent.
        # Gets the probability of different exogenous contracts quantities given the world size
        # Does some administrative stuff based on the level of the agent
        self.world_size = f'{len(self.awi.all_consumers[0])} {len(self.awi.all_consumers[1])}'
        self.max_wait = len(self.awi.all_consumers[0]) + len(self.awi.all_consumers[1]) + 1
        if self.awi.level == 0:
            self.partners = self.awi.my_consumers
            self.output = [True]
            self.partner = 'buyer'

        elif self.awi.level == 1:
            self.partners = self.awi.my_suppliers
            self.output = [False]
            self.partner = 'seller'

        self.balances = {c: [] for c in self.partners}

    def before_step(self):
        # Sets the agent up for the round.
        # Resets the number of proposals/offers/waits to 0
        # Finds information about the exogenous contracts for the round
        # Finds a target quantity and price for each negotiation based on the exog summary and balances of the agents
        if (self.awi.current_step - 1) % 5 == 0:
            for c in self.partners:
                self.balances[c].append(self.awi.reports_at_step(self.awi.current_step - 1)[c].cash)

        self.accepted_offers = {}
        self.received_offers = {}
        self.sent_offers = {c: 'First' for c in self.partners}

        self.proposal_count = {c: 0 for c in self.partners}
        self.response_count = {c: 0 for c in self.partners}
        self.wait_count = {c: 0 for c in self.partners}

        self.num_in = self.awi.exogenous_contract_summary[0][0]
        self.num_out = self.awi.exogenous_contract_summary[-1][0]
        self.ufun.find_limit(True)
        self.ufun.find_limit(False)

        if self.awi.level == 0:
            self.q = self.awi.state().exogenous_input_quantity
            self.desperation = self.num_in/self.num_out
            self.min_price = self.awi.current_output_issues[UNIT_PRICE].min_value
            self.max_price = self.awi.current_output_issues[UNIT_PRICE].max_value
            if self.desperation < 1:
                target_price = self.max_price
            else:
                for price in range(self.min_price, self.max_price+1):
                    target_price = self.min_price
                    frac = 1.3/self.desperation
                    if self.ufun([self.q, 0, price]) > frac*(self.ufun.max_utility - self.ufun([0, 0, 0])):
                        target_price = price
                        break

        elif self.awi.level == 1:
            self.q = self.awi.state().exogenous_output_quantity
            self.desperation = self.num_out/self.num_in
            self.min_price = self.awi.current_input_issues[UNIT_PRICE].min_value
            self.max_price = self.awi.current_input_issues[UNIT_PRICE].max_value
            if self.desperation < 1:
                target_price = self.min_price
            else:
                for price in range(self.max_price, self.min_price - 1, -1):
                    target_price = self.max_price
                    if self.ufun([self.q, 0, price]) > 1/self.desperation*(self.ufun.max_utility - self.ufun([0, 0, 0])):
                        target_price = price
                        break
        if self.awi.current_step == 0:
            dist = {p: np.round(self.q/len(self.partners)) for p in self.partners}
        else:
            ratios = {c: 1/self.balances[c][-1] for c in self.balances}
            const = self.q/(sum(ratios.values()))
            dist = {c: floor(ratios[c]*const) for c in self.partners}
        while sum(dist.values()) < self.q:
            dist[random.choice(list(dist.keys()))] += 1
        self.target_q = dist
        self.target_price = {c: target_price for c in self.partners}


    def propose(self, negotiator_id: str, state) -> "Outcome":
        self.wait_count[negotiator_id] = 0
        if self.sent_offers[negotiator_id] == 'First':
            offer = self.get_first_offer(negotiator_id, state)
            self.sent_offers[negotiator_id] = offer
        else:
            offer = self.sent_offers[negotiator_id]
        return offer


    def respond(self, negotiator_id, state, offer):
        self.cleanup(negotiator_id, offer)
        if sum(self.target_q.values()) <= 0:
            response = ResponseType.END_NEGOTIATION
        elif self.wait_count[negotiator_id] < (self.max_wait - 1) and len(self.received_offers) != len(self.target_q):
            self.wait_count[negotiator_id] += 1
            response = ResponseType.WAIT
        else:
            response = self.get_response(negotiator_id, state, offer)
        if response == ResponseType.REJECT_OFFER:
            self.sent_offers[negotiator_id] = self.get_offer(negotiator_id, state, offer)
        else:
            self.sent_offers[negotiator_id] = [0, 0, 0]
        return response


    def on_negotiation_success(self, contract, mechanism):
        print("success")
        negotiator_id = contract.annotation[self.partner]
        target = self.target_q[negotiator_id]
        q = contract.agreement['quantity']
        p = contract.agreement['unit_price']

        offer = [-1]*3
        offer[TIME] = self.awi.current_step
        offer[QUANTITY] = q
        offer[UNIT_PRICE] = p

        del self.target_price[negotiator_id]
        del self.target_q[negotiator_id]

        if target > q:
            diff = target - offer[QUANTITY]
            overage = False
        elif target < q:
            diff = -(target - offer[QUANTITY])
            overage = True
        elif target == q:
            diff = 0

        while diff > 0 and sum(self.target_q.values()) > 0:
            ind = random.choice(list(self.target_q.keys()))
            if overage:
                if self.target_q[ind] > 0:
                    self.target_q[ind] -= 1
                    diff -= 1
            else:
                self.target_q[ind] += 1
                diff -= 1

        self.accepted_offers[negotiator_id] = offer


    def on_negotiation_failure(self, partners, annotation, mechanism, state):
        print("failure :(")
        print(state.step)
        negotiator_id = annotation[self.partner]
        target = self.target_q[negotiator_id]

        del self.target_price[negotiator_id]
        del self.target_q[negotiator_id]

        diff = target
        while diff > 0 and len(self.target_q) > 0:
            ind = random.choice(list(self.target_q.keys()))
            self.target_q[ind] -= 1
            diff -= 1


    def get_first_offer(self, negotiator_id, state):
        offer = [-1]*3
        offer[UNIT_PRICE] = self.target_price[negotiator_id]
        offer[QUANTITY] = self.target_q[negotiator_id]
        offer[TIME] = self.awi.current_step
        self.proposal_count[negotiator_id] += 1
        toffer = tuple(offer)
        print(toffer)
        return toffer

    def cleanup(self, negotiator_id, offer):
        try:
            del self.sent_offers[negotiator_id]
        except:
            pass
        self.received_offers[negotiator_id] = offer

    def get_response(self, negotiator_id, state, offer):
        if self.awi.level == 0:
            if offer[UNIT_PRICE] >= self.target_price[negotiator_id] and offer[QUANTITY] <= self.target_q[negotiator_id] + 1:
                response = ResponseType.ACCEPT_OFFER
            else:
                response = ResponseType.REJECT_OFFER
        if self.awi.level == 1:
            if offer[UNIT_PRICE] <= self.target_price[negotiator_id] and offer[QUANTITY] <= self.target_q[negotiator_id] + 1:
                response = ResponseType.ACCEPT_OFFER
            else:
                response = ResponseType.REJECT_OFFER
        self.response_count[negotiator_id] += 1
        if response != ResponseType.WAIT:
            del self.received_offers[negotiator_id]
        return response

    def get_offer(self, negotiator_id, state, offer):
        offer = [-1]*3
        if self.awi.level == 0:
            offer[UNIT_PRICE] = int(self.target_price[negotiator_id]*.97**(state.step))
        else:
            offer[UNIT_PRICE] = int(self.target_price[negotiator_id]*1.03**(state.step))
        self.target_price[negotiator_id] = offer[UNIT_PRICE]
        offer[QUANTITY] = self.target_q[negotiator_id]
        offer[TIME] = self.awi.current_step
        self.proposal_count[negotiator_id] += 1
        return tuple(offer)
