from pydoc import allmethods
from re import A, S
from scml.scml2020.common import UNIT_PRICE
from scml.oneshot import OneShotUFun
from agents.ufuncalc import UFunCalc
import numpy as np

class BilateralUtilityFunction():
    """In this utility function we measure the utility of the current negotiation along with the
    bundle of offers that has been gathered through completed negotiations, with disagreement assumed 
    for all other ongoing negotiations"""
    def __init__(self, scmlufun, awi, other_offers):
        self.awi = awi
        self.offer_set = []
        min_price = self.awi.current_output_issues[UNIT_PRICE].min_value
        max_price = self.awi.current_output_issues[UNIT_PRICE].max_value
        self.offer_set.append((0, awi.current_step, 0))
        for q in range(1, 11):
            for p in range(min_price, max_price+1):
                self.offer_set.append((q, awi.current_step, p))
        self.scmlufun = scmlufun
        self.offers = other_offers

        # seller
        if self.awi.level == 0:
            exog_q = self.awi.state().exogenous_input_quantity
            for offer in other_offers:
                exog_q -= offer[0]
            self.best_offer = (exog_q, self.awi.current_step, max_price)
        # buyer
        else:
            exog_q = self.awi.state().exogenous_output_quantity
            for offer in other_offers:
                exog_q -= offer[0]
            self.best_offer = (exog_q, self.awi.current_step, min_price)

        # self.best_offer = (0, awi.current_step, 0)
        # best_offer_util = float('-inf')
        # for o in self.offer_set:
        #     o_util = self.__call__(o)
        #     if o_util > best_offer_util:
        #         best_offer_util = o_util
        #         self.best_offer = o
                
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

class PredictiveUtilityFunction(BilateralUtilityFunction):
    def __init__(self, scmlufun, awi, other_accepted_offers, other_received_offers, model, remaining_q, remaining_negotiations, time):
        self.model = model
        self.rem_q = remaining_q
        self.rem_n = remaining_negotiations
        self.time = time
        self.awi = awi
        self.offer_set = []
        self.min_price = self.awi.current_output_issues[UNIT_PRICE].min_value
        self.max_price = self.awi.current_output_issues[UNIT_PRICE].max_value
        self.level = self.awi.level
        self.offer_set.append((0, awi.current_step, 0))
        for q in range(1, 11):
            for p in range(self.min_price, self.max_price+1):
                self.offer_set.append((q, awi.current_step, p))
        self.scmlufun = scmlufun
        self.offers_accepted = other_accepted_offers
        self.offers_received = other_received_offers

        # seller
        if self.awi.level == 0:
            exog_q = self.awi.state().exogenous_input_quantity
            for offer in self.offers_accepted:
                exog_q -= offer[0]
            self.best_offer = (max(exog_q, 0), self.awi.current_step, self.max_price)
        # buyer
        else:
            exog_q = self.awi.state().exogenous_output_quantity
            for offer in self.offers_accepted:
                exog_q -= offer[0]
            self.best_offer = (max(exog_q, 0), self.awi.current_step, self.min_price)

        # self.best_offer = (0, awi.current_step, 0)
        # best_offer_util = float('-inf')
        # for o in self.offer_set:
        #     o_util = self.__call__(o)
        #     if o_util > best_offer_util:
        #         best_offer_util = o_util
        #         self.best_offer = o

    def generate_key(self, offer):
        if self.awi.level == 0:
            self.partners = self.awi.my_consumers
        else:
            self.partners = self.awi.my_suppliers

        keystr = ""
        if self.level == 1:
            keystr += "b"
        else:
            keystr += "s"
        keystr += f"s{self.rem_q}"
        keystr += f"o{offer[0]}"
        for t in range(4):
            if self.time <= (t+1)*5:
                keystr += f"t{t*5}+"
                break
        for r in range(4):
            if self.rem_n / len(self.partners) <= (r+1)*0.25:
                keystr += f"rem{r*0.25}+"
                break
        return keystr

    def __call__(self, offer):
        return super().__call__(offer)

    
class PredictiveUtilityFunctionMean(PredictiveUtilityFunction):
    def __call__(self, offer):
        predicted_outcomes = []
        for o in self.offers_received:
            key = self.generate_key(o)
            model_output = self.model(key, self.min_price, self.max_price)
            pred_outcome = [-1] * 3
            pred_outcome[0] = model_output[0]
            pred_outcome[1] = self.awi.current_step
            pred_outcome[2] = model_output[1]
            predicted_outcomes.append(tuple(pred_outcome))
            
        all_offers = predicted_outcomes + self.offers_accepted

        outputs = []
        if self.awi.level == 0:
            outputs = [True] * (len(all_offers)+1)
        else:
            outputs = [False] * (len(all_offers)+1)

        all_offers.append(offer)

        ufc = UFunCalc(self.scmlufun)
        utility = ufc.from_offers(all_offers, outputs)
        return utility

class PredictiveUtilityFunctionMeanOrDisagreement(PredictiveUtilityFunction):
    def __call__(self, offer):
        utils = []
        weights = []
        for i in range(2 ** len(self.offers_received)):
            bin_string = f'0{len(self.offers_received)}b'
            bin_rep = format(i, bin_string)

            predicted_outcomes = []
            weight = 1
            utility = 0
            for j, o in enumerate(self.offers_received):
                my_bin = int(bin_rep[j])
                key = self.generate_key(o)
                model_output = self.model(key, self.min_price, self.max_price)

                # agree
                if my_bin == 0:
                    pred_outcome = (model_output[0], self.awi.current_step, model_output[1])
                    predicted_outcomes.append(tuple(pred_outcome))
                    weight *= model_output[2]
                # disagree
                else:
                    pred_outcome = (0, self.awi.current_step, 0)
                    predicted_outcomes.append(tuple(pred_outcome))
                    weight *= model_output[3]
                
            all_offers = predicted_outcomes + self.offers_accepted

            outputs = []
            if self.awi.level == 0:
                outputs = [True] * (len(all_offers)+1)
            else:
                outputs = [False] * (len(all_offers)+1)

            all_offers.append(offer)

            ufc = UFunCalc(self.scmlufun)

            utility = ufc.from_offers(all_offers, outputs)

            utils.append(utility)
            weights.append(weight)

        np.testing.assert_allclose(np.sum(weights), 1, rtol=1e-5, atol=0)

        return np.dot(np.array(utils), np.array(weights))
        


