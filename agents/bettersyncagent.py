from scml.oneshot import *
from negmas import ResponseType
from scml.scml2020.common import QUANTITY, TIME, UNIT_PRICE

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

        self.data_collection = False
        if self.data_collection:
            self.preliminary_data = {c: [] for c in self.partners}
            self.data = []

    def add_pre_datum(self, negotiator_id, rem_exog, opp_last_exog, time, remaining_negotiations):
        datum = {}
        datum['my_remaining_exog'] = rem_exog
        datum['opp_last_exog'] = opp_last_exog
        datum['time'] = time
        datum['rem_negotiations'] = remaining_negotiations
        self.preliminary_data[negotiator_id].append(datum)

    def move_data(self, negotiator_id, q, p):
        for datum in self.preliminary_data[negotiator_id]:
            datum['q'] = q
            datum['p'] = p
            datum['rem_negotiations'] = datum['rem_negotiations'] / len(self.partners)
            datum['level'] = self.partner
            datum['min_price'] = self.min_price
            datum['max_price'] = self.max_price
            self.data.append(datum)

    def before_step(self):
        # Sets the agent up for the round.
        # Resets the number of proposals/offers/waits to 0
        # Finds information about the exogenous contracts for the round
        # print("\n")
        # print("new day")
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
            # print("seller")

        elif self.awi.level == 1:
            self.q = self.awi.state().exogenous_output_quantity
            self.min_price = self.awi.current_input_issues[UNIT_PRICE].min_value
            self.max_price = self.awi.current_input_issues[UNIT_PRICE].max_value
            # print("buyer")

        # print(f"price range: {self.min_price},{self.max_price}")
        # print(f"exog: {self.q}")

        if self.data_collection:
            self.preliminary_data = {c: [] for c in self.partners}
        self.remaining_exog = self.q
        self.remaining_negotiations = len(self.partners)

    def propose(self, negotiator_id: str, state) -> "Outcome":
        self.wait_count[negotiator_id] = 0
        if self.sent_offers[negotiator_id] == 'First':
            offer = self.get_first_offer(negotiator_id, state)
            self.sent_offers[negotiator_id] = offer
        else:
            offer = self.sent_offers[negotiator_id]
            if self.data_collection:
                try:
                    self.add_pre_datum(negotiator_id, self.remaining_exog, self.received_offers[negotiator_id][QUANTITY], state.step, self.remaining_negotiations)
                except:
                    pass
        #print(f"My proposal to {negotiator_id}: {offer}")
        # if offer[0] >= self.remaining_exog + 2:
        #     print(f"making very large offer {offer[0], self.remaining_exog}")
        return offer

    def respond(self, negotiator_id, state, offer):
        self.cleanup(negotiator_id, offer)
        if self.wait_count[negotiator_id] < (self.max_wait - 1):
            self.wait_count[negotiator_id] += 1
            response = ResponseType.WAIT
        else:
            response = self.get_response(negotiator_id, state, offer)
        if response == ResponseType.REJECT_OFFER:
            self.sent_offers[negotiator_id] = self.get_offer(negotiator_id, state, offer)
        else:
            self.sent_offers[negotiator_id] = [0, self.awi.current_step, 0]
        # if offer[0] >= self.remaining_exog + 2 and response == ResponseType.ACCEPT_OFFER:
        #     print("want to accept very large offer")
        return response

    def on_negotiation_success(self, contract, mechanism):
        negotiator_id = contract.annotation[self.partner]
        q = contract.agreement['quantity']
        p = contract.agreement['unit_price']

        offer = [-1]*3
        offer[TIME] = self.awi.current_step
        offer[QUANTITY] = q
        offer[UNIT_PRICE] = p

        self.accepted_offers[negotiator_id] = offer

        if self.data_collection:
            self.move_data(negotiator_id, q, p)
            self.remaining_exog -= q
            self.remaining_negotiations -= 1

    def on_negotiation_failure(self, partners, annotation, mechanism, state):
        if self.data_collection:
            negotiator_id = annotation[self.partner]
            self.move_data(negotiator_id, 0, 0)
            self.remaining_negotiations -= 1
    
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



