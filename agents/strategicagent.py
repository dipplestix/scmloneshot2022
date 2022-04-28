from agents.bettersyncagent import BetterSyncAgent
from agents.strategy import Strategy, StrategyGoldfishParetoAspiration
from agents.ufuns import BilateralUtilityFunction, OpponentUtilityFunction

class StrategicAgent(BetterSyncAgent):
    def __init__(self) -> None:
        super().__init__()
        self.strategy=Strategy()

    def est_frac_complete(self, negotiator_id):
        moves = self.response_count[negotiator_id] + self.proposal_count[negotiator_id]
        f = (moves - 0.5) / (2 * self.n_negotiation_rounds)
        return max(0, f)

    def calculate_ufun(self):
        other_offers = list(self.accepted_offers.values())
        return BilateralUtilityFunction(self.ufun, self.awi, other_offers)

    def get_first_offer(self, negotiator_id, state):
        t = self.est_frac_complete(negotiator_id)
        my_ufun = self.calculate_ufun()
        opp_ufun = OpponentUtilityFunction(1-self.awi.level, self.awi.n_competitors, last_opp_offer=None)
        self.proposal_count[negotiator_id] += 1
        return self.strategy.propose(my_ufun, opp_ufun, t)

    def get_response(self, negotiator_id, state, offer):
        self.response_count[negotiator_id] += 1
        t = self.est_frac_complete(negotiator_id)
        my_ufun = self.calculate_ufun()
        return self.strategy.respond(my_ufun, offer, t)

    def get_offer(self, negotiator_id, state, offer):
        t = self.est_frac_complete(negotiator_id)
        my_ufun = self.calculate_ufun()
        opp_ufun = OpponentUtilityFunction(1-self.awi.level, self.awi.n_competitors, last_opp_offer=offer)
        self.proposal_count[negotiator_id] += 1
        return self.strategy.propose(my_ufun, opp_ufun, t)

class GPAAgent(StrategicAgent):
    def __init__(self) -> None:
        super().__init__()
        self.strategy = StrategyGoldfishParetoAspiration()