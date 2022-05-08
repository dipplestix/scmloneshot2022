from agents.bettersyncagent import BetterSyncAgent
from agents.strategy import Strategy, StrategyGoldfishParetoAspiration
from agents.ufuns import BilateralUtilityFunction, OpponentUtilityFunction
from math import ceil
from negmas import ResponseType
from scml.scml2020.common import QUANTITY, TIME, UNIT_PRICE


class NewAgent(BetterSyncAgent):
    def init(self):
        super().init()
        self.target_q = {nid: 0 for nid in self.partners}
        self.debug = False
        
    def before_step(self):
        super().before_step()
        self.target_q = {nid: ceil(self.q/len(self.partners)) for nid in self.partners}
        if self.awi.level == 0:
            self.best_price = self.awi.current_output_issues[2].values[1]
            self.worst_price = self.awi.current_output_issues[2].values[0]
        if self.awi.level == 1:
            self.best_price = self.awi.current_input_issues[2].values[0]
            self.worst_price = self.awi.current_input_issues[2].values[1]
        self.active_partners = self.partners[:]

    def get_first_offer(self, negotiator_id, state):
        self.proposal_count[negotiator_id] += 1
        offer = [-1]*3
        offer[TIME] = self.awi.current_step
        offer[QUANTITY] = self.target_q[negotiator_id]
        offer[UNIT_PRICE] = self.best_price
        return tuple(offer)

    def get_response(self, negotiator_id, state, offer):
        prop = self.get_offer(negotiator_id, state, offer)
        if self.get_diff([offer]) >= self.get_diff([prop]):
            return ResponseType.ACCEPT_OFFER
        else:
            return ResponseType.REJECT_OFFER
        
    def get_offer(self, negotiator_id, state, offer):
        t = state.time/20
        offer = [-1]*3
        offer[TIME] = self.awi.current_step
        offer[QUANTITY] = self.target_q[negotiator_id]
        try:
            offer[UNIT_PRICE] = self.ufun.invert()(1-t/50, True)[2]
        except:
            offer[UNIT_PRICE] = self.max_price
        return tuple(offer)

    def on_negotiation_failure(self, partners, annotation, mechanism, state):
        other_partner = [p for p in partners if p != str(self.awi.agent)][0]
        self.active_partners.remove(other_partner)
        i = 0
        while self.target_q[other_partner] > 0 and len(self.active_partners) > 0:
            dis_to = self.active_partners[i]
            self.target_q[dis_to] += 1
            self.target_q[other_partner] -= 1
            i = (i + 1) % len(self.active_partners)

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
        self.active_partners.remove(negotiator_id)
        if self.target_q[negotiator_id] > q:
            diff = self.target_q[negotiator_id] - q
            i = 0
            while diff > 0 and len(self.active_partners) > 0:
                dis_to = self.active_partners[i]
                self.target_q[dis_to] -= 1
                diff -= 1
                i = (i + 1) % len(self.active_partners)
        self.target_q[negotiator_id] = 0
