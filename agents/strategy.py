import math
from agents.ufuns import OpponentUtilityFunction
from negmas import ResponseType

class Strategy():
    def __init__(self):
        pass
        
    def propose():
        return NotImplementedError

    def respond():
        return NotImplementedError

class StrategyGoldfishParetoAspiration(Strategy):
    def __init__(self) -> None:
        self.ASP_VAL = 1
        self.NASH_BALANCE = 0.5

    def calculate_pareto_frontier(self, my_ufun, opp_ufun):
        frontier = []
        for offer1 in my_ufun.offer_set:
            my_util1 = my_ufun(offer1)
            opp_util1 = opp_ufun(offer1)
            is_pareto = True
            for offer2 in my_ufun.offer_set:
                my_util2 = my_ufun(offer2)
                opp_util2 = opp_ufun(offer2) 
                if (my_util2 > my_util1 and opp_util2 >= opp_util1) or (my_util2 >= my_util1 and opp_util2 > opp_util1):
                    is_pareto = False
                    break
            if is_pareto:
                frontier.append(offer1)
        
        return frontier

    def calculate_nash_point(self, my_ufun, opp_ufun, frontier):
        my_disagreement_util, opp_disagreement_util = my_ufun((0, 0, 0)), opp_ufun((0, 0, 0))
        max_value = float('-inf')
        current_best = None
        for offer in frontier:
            nash_value = (my_ufun(offer) - my_disagreement_util) * (opp_ufun(offer) - opp_disagreement_util)
            if nash_value > max_value:
                current_best = offer
                max_value = nash_value

        return current_best if not None else (0, 0, 0)

    def get_target_utility(self, my_ufun, opp_ufun, frontier, t):
        curr_asp_level = 1.0 - math.pow(t, self.ASP_VAL)
        nash_point = self.calculate_nash_point(my_ufun, opp_ufun, frontier)
        zero_util = my_ufun((0, 0, 0))
        start_util = my_ufun(my_ufun.best_offer)
        end_util = my_ufun(nash_point) * self.NASH_BALANCE + zero_util * (1-self.NASH_BALANCE)
        target_util = curr_asp_level * start_util + (1-curr_asp_level) * end_util
        return target_util

    def propose(self, my_ufun, opp_ufun, t):
        frontier = self.calculate_pareto_frontier(my_ufun, opp_ufun)
        target = self.get_target_utility(my_ufun, opp_ufun, frontier, t)

        best_target_offer = None
        best_distance = float('inf')
        for offer in frontier:
            if my_ufun(offer) >= target and my_ufun(offer) - target < best_distance:
                best_distance = my_ufun(offer) - target
                best_target_offer = offer

        return best_target_offer if not None else my_ufun.best_offer

    def respond(self, my_ufun, opp_offer, t):
        current_util_level = 1.0 - math.pow(t, self.ASP_VAL)
        if my_ufun(opp_offer) > current_util_level:
            return ResponseType.ACCEPT_OFFER
        else:
            return ResponseType.REJECT_OFFER

