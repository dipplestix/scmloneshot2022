from scml.scml2020.common import UNIT_PRICE
from scml.oneshot import OneShotUFun
from agents.ufuncalc import UFunCalc

class BilateralUtilityFunction():
    def __init__(self, scmlufun, awi, other_offers):
        self.awi = awi
        self.offer_set = []
        min_price = self.awi.current_output_issues[UNIT_PRICE].min_value
        max_price = self.awi.current_output_issues[UNIT_PRICE].max_value
        for q in range(11):
            for p in range(min_price, max_price+1):
                self.offer_set.append((q, awi.current_step, p))
        self.scmlufun = scmlufun
        self.offers = other_offers

        self.best_offer = (0, awi.current_step, 0)
        best_offer_util = float('-inf')
        for o in self.offer_set:
            o_util = self.__call__(o)
            if o_util > best_offer_util:
                best_offer_util = o_util
                self.best_offer = o
                
    def __call__(self, offer):
        outputs = []
        if self.awi.level == 0:
            outputs = [True] * (len(self.offers)+1)
        else:
            outputs = [False] * (len(self.offers)+1)
                
        all_offers = []
        for o in self.offers:
            all_offers.append(tuple(o))
        all_offers.append(tuple(offer))

        ufc = UFunCalc(self.scmlufun)
        utility = ufc.from_offers(all_offers, outputs)
        return utility

class OpponentUtilityFunction():
    EXPECTED_QUANT_TABLE = { 0: 8.9992004, 1: 9.02894599 }
    
    def __init__(self, opp_level, n_competitors, last_opp_offer=None):
        
        self.level = opp_level
        self.n_partners = n_competitors + 1

        self.expected_prod_cost = (self.level+1) * 2.5
        self.expected_disp_cost = 0.1
        self.expected_shortfall_cost = 0.6

        self.needed_exog = last_opp_offer[0] if last_opp_offer else (
            self.EXPECTED_QUANT_TABLE[self.level] / self.n_partners)
        ex_pin = 10 * self.needed_exog if self.level == 0 else 0
        ex_pout = 27 * self.needed_exog if self.level == 1 else 0
        ex_qin = self.needed_exog if self.level == 0 else 0
        ex_qout = self.needed_exog if self.level == 1 else 0
        input_agent = True if self.level == 0 else False
        output_agent = False if self.level == 0 else True
        input_product = None

        self.scml_ufun = OneShotUFun(
            ex_pin=ex_pin,
            ex_qin=ex_qin,
            ex_pout=ex_pout,
            ex_qout=ex_qout,
            input_product=input_product,
            input_agent=input_agent,
            output_agent=output_agent,
            production_cost=self.expected_prod_cost,
            disposal_cost=self.expected_disp_cost,
            shortfall_penalty=self.expected_shortfall_cost,
            input_penalty_scale=None,
            output_penalty_scale=None,
            n_input_negs=None,
            n_output_negs=None,
            current_step=1)

    def __call__(self, offer):
        return self.scml_ufun(offer)
