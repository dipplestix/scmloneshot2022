from logging.handlers import MemoryHandler
from agents.bettersyncagent import BetterSyncAgent
from agents.strategy import Strategy, StrategyAspiration, StrategyGoldfishParetoAspiration
from agents.ufuns import BilateralUtilityFunction, OpponentUtilityFunction, PredictiveUtilityFunctionMean, PredictiveUtilityFunctionMeanOrDisagreement
from agents.model import MeanModel, MeanOrDisagreementModel

class StrategicAgent(BetterSyncAgent):
    def __init__(self) -> None:
        super().__init__()
        self.strategy=Strategy()

    def est_frac_complete(self, negotiator_id):
        moves = self.response_count[negotiator_id] + self.proposal_count[negotiator_id]
        f = (moves - 0.5) / (2 * self.n_negotiation_rounds)
        return max(0, f)

    def calculate_ufun(self, negotiator_id):
        other_offers = list(self.accepted_offers.values())
        return BilateralUtilityFunction(self.ufun, self.awi, other_offers)

    def get_first_offer(self, negotiator_id, state):
        t = self.est_frac_complete(negotiator_id)
        my_ufun = self.calculate_ufun(negotiator_id)
        opp_ufun = OpponentUtilityFunction(1-self.awi.level, self.awi.n_competitors, last_opp_offer=None)
        self.proposal_count[negotiator_id] += 1
        return self.strategy.propose(my_ufun, opp_ufun, t)

    def get_response(self, negotiator_id, state, offer):
        self.response_count[negotiator_id] += 1
        t = self.est_frac_complete(negotiator_id)
        my_ufun = self.calculate_ufun(negotiator_id)
        return self.strategy.respond(my_ufun, offer, t)

    def get_offer(self, negotiator_id, state, offer):
        t = self.est_frac_complete(negotiator_id)
        my_ufun = self.calculate_ufun(negotiator_id)
        opp_ufun = OpponentUtilityFunction(1-self.awi.level, self.awi.n_competitors, last_opp_offer=offer)
        self.proposal_count[negotiator_id] += 1
        return self.strategy.propose(my_ufun, opp_ufun, t)

class AspirationAgent(StrategicAgent):
    def __init__(self) -> None:
        super().__init__()
        self.strategy = StrategyAspiration()

class AspirationMODAgent(AspirationAgent):
    def __init__(self) -> None:
        super().__init__()
        self.model = MeanOrDisagreementModel('datarun1.csv')
        self.strategy = StrategyAspiration()

    def before_step(self):
        super().before_step()
        self.remaining_exog = self.q
        self.remaining_negotiations = len(self.partners)

    def on_negotiation_failure(self, partners, annotation, mechanism, state):
        super().on_negotiation_failure(partners, annotation, mechanism, state)
        self.remaining_negotiations -= 1
    
    def on_negotiation_success(self, contract, mechanism):
        super().on_negotiation_success(contract, mechanism)
        self.remaining_exog -= contract.agreement['quantity']
        self.remaining_negotiations -= 1

    def calculate_ufun(self, negotiator_id):
        other_accepted_offers = list(self.accepted_offers.values())
        other_received_offers = []
        for k, v in self.received_offers.items():
            if k != negotiator_id:
                other_received_offers.append(v)
        time = self.response_count[negotiator_id] + self.proposal_count[negotiator_id]
        return PredictiveUtilityFunctionMeanOrDisagreement(self.ufun, self.awi, other_accepted_offers, other_received_offers, self.model, self.remaining_exog, self.remaining_negotiations, time)

class GPAAgent(StrategicAgent):
    def __init__(self) -> None:
        super().__init__()
        self.strategy = StrategyGoldfishParetoAspiration()

class GPAMeanModelAgent(GPAAgent):
    def __init__(self) -> None:
        super().__init__()
        self.model = MeanModel('datarun1.csv')
        self.strategy = StrategyGoldfishParetoAspiration()

    def before_step(self):
        super().before_step()
        self.remaining_exog = self.q
        self.remaining_negotiations = len(self.partners)

    def on_negotiation_failure(self, partners, annotation, mechanism, state):
        super().on_negotiation_failure(partners, annotation, mechanism, state)
        self.remaining_negotiations -= 1
    
    def on_negotiation_success(self, contract, mechanism):
        super().on_negotiation_success(contract, mechanism)
        self.remaining_exog -= contract.agreement['quantity']
        self.remaining_negotiations -= 1

    def calculate_ufun(self, negotiator_id):
        other_accepted_offers = list(self.accepted_offers.values())
        other_received_offers = []
        for k, v in self.received_offers.items():
            if k != negotiator_id:
                other_received_offers.append(v)
        time = self.response_count[negotiator_id] + self.proposal_count[negotiator_id]
        return PredictiveUtilityFunctionMean(self.ufun, self.awi, other_accepted_offers, other_received_offers, self.model, self.remaining_exog, self.remaining_negotiations, time)

class GPAMeanOrDisagreementAgent(GPAAgent):
    def __init__(self) -> None:
        super().__init__()
        self.model = MeanOrDisagreementModel('datarun1.csv')
        self.strategy = StrategyGoldfishParetoAspiration()
        
    def before_step(self):
        super().before_step()
        self.remaining_exog = self.q
        self.remaining_negotiations = len(self.partners)

    def on_negotiation_failure(self, partners, annotation, mechanism, state):
        super().on_negotiation_failure(partners, annotation, mechanism, state)
        self.remaining_negotiations -= 1
    
    def on_negotiation_success(self, contract, mechanism):
        super().on_negotiation_success(contract, mechanism)
        self.remaining_exog -= contract.agreement['quantity']
        self.remaining_negotiations -= 1

    def calculate_ufun(self, negotiator_id):
        other_accepted_offers = list(self.accepted_offers.values())
        other_received_offers = []
        for k, v in self.received_offers.items():
            if k != negotiator_id:
                other_received_offers.append(v)
        time = self.response_count[negotiator_id] + self.proposal_count[negotiator_id]
        return PredictiveUtilityFunctionMeanOrDisagreement(self.ufun, self.awi, other_accepted_offers, other_received_offers, self.model, self.remaining_exog, self.remaining_negotiations, time)
