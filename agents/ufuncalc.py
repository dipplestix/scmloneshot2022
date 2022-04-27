from copy import deepcopy
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union
from scml.scml2020.common import QUANTITY, TIME, UNIT_PRICE


class UFunCalc():
    def __init__(self, ufun) -> None:
        self.ufun = ufun 

    def from_offers(
        self, offers: Iterable[Tuple], outputs: Iterable[bool], return_producible=False
    ) -> Union[float, Tuple[float, int]]:
        """
        Calculates the utility value given a list of offers and whether each
        offer is for output or not (= input).

        Args:
            offers: An iterable (e.g. list) of tuples each with three values:
                    (quantity, time, unit price) IN THAT ORDER. Time is ignored
                    and can be set to any value.
            outputs: An iterable of the same length as offers of booleans
                     specifying for each offer whether it is an offer for buying
                     the agent's output product.
            return_producible: If true, the producible quantity will be returned
        Remarks:
            - This method takes into account the exogenous contract information
              passed when constructing the ufun.
        """

        def order(x):
            """A helper function to order contracts in the following fashion:
            1. input contracts are ordered from cheapest to most expensive.
            2. output contracts are ordered from highest price to cheapest.
            3. The relative order of input and output contracts is indeterminate.
            """
            offer, is_output, is_exogenous = x
            # if is_exogenous and self.force_exogenous:
            #     return float("-inf")
            return -offer[UNIT_PRICE] if is_output else offer[UNIT_PRICE]

        # copy inputs because we are going to modify them.
        offers, outputs = deepcopy(list(offers)), deepcopy(list(outputs))
        # indicate that all inputs are not exogenous and that we are adding two
        # exogenous contracts after them.
        exogenous = [False] * len(offers) + [True, True]
        # add exogenous contracts as offers one for input and another for output
        offers += [
            (self.ufun.ex_qin, 0, self.ufun.ex_pin / self.ufun.ex_qin if self.ufun.ex_qin else 0),
            (self.ufun.ex_qout, 0, self.ufun.ex_pout / self.ufun.ex_qout if self.ufun.ex_qout else 0),
        ]
        outputs += [False, True]
        # initialize some variables
        qin, qout, pin, pout = 0, 0, 0, 0
        qin_bar, going_bankrupt = 0, self.ufun.current_balance < 0
        pout_bar = 0
        # we are going to collect output contracts in output_offers
        output_offers = []
        # sort contracts in the optimal order of execution: from cheapest when
        # buying and from the most expensive when selling. See `order` above.
        sorted_offers = list(sorted(zip(offers, outputs, exogenous), key=order))

        # we calculate the total quantity we are are required to pay for `qin` and
        # the associated amount of money we are going to pay `pin`. Moreover,
        # we calculate the total quantity we can actually buy given our limited
        # money balance (`qin_bar`).
        for offer, is_output, is_exogenous in sorted_offers:
            offer = self.ufun.outcome_as_tuple(offer)
            if is_output:
                output_offers.append((offer, is_exogenous))
                continue
            topay_this_time = offer[UNIT_PRICE] * offer[QUANTITY]
            if not going_bankrupt and (
                pin + topay_this_time + offer[QUANTITY] * self.ufun.production_cost
                > self.ufun.current_balance
            ):
                unit_total_cost = offer[UNIT_PRICE] + self.ufun.production_cost
                can_buy = int((self.ufun.current_balance - pin) // unit_total_cost)
                qin_bar = qin + can_buy
                going_bankrupt = True
            pin += topay_this_time
            qin += offer[QUANTITY]

        if not going_bankrupt:
            qin_bar = qin

        # calculate the maximum amount we can produce given our limited production
        # capacity and the input we CAN BUY
        n_lines = self.ufun.n_lines
        producible = min(qin_bar, n_lines)

        # No need to this test now because we test for the ability to produce with
        # the ability to buy items. The factory buys cheaper items and produces them
        # before attempting more expensive ones. This may or may not be optimal but
        # who cars. It is consistent that it is all that matters.
        # # if we do not have enough money to pay for production in full, we limit
        # # the producible quantity to what we can actually produce
        # if (
        #     self.production_cost
        #     and producible * self.production_cost > self.current_balance
        # ):
        #     producible = int(self.current_balance // self.production_cost)

        # find the total sale quantity (qout) and money (pout). Moreover find
        # the actual amount of money we will receive
        done_selling = False
        for offer, is_exogenous in output_offers:
            if not done_selling:
                if qout + offer[QUANTITY] >= producible:
                    assert producible >= qout, f"producible {producible}, qout {qout}"
                    can_sell = producible - qout
                    done_selling = True
                else:
                    can_sell = offer[QUANTITY]
                pout_bar += can_sell * offer[UNIT_PRICE]
            pout += offer[UNIT_PRICE] * offer[QUANTITY]
            qout += offer[QUANTITY]

        # should never produce more than we signed to sell
        producible = min(producible, qout)

        # we cannot produce more than our capacity or inputs and we should not
        # produce more than our required outputs
        producible = min(qin, self.ufun.n_lines, producible)

        # the scale with which to multiply disposal_cost and shortfall_penalty
        # if no scale is given then the unit price will be used.
        output_penalty = self.ufun.output_penalty_scale
        if output_penalty is None:
            output_penalty = pout / qout if qout else 0
        output_penalty *= self.ufun.shortfall_penalty * max(0, qout - producible)
        input_penalty = self.ufun.input_penalty_scale
        if input_penalty is None:
            input_penalty = pin / qin if qin else 0
        input_penalty *= self.ufun.disposal_cost * max(0, qin - producible)

        # call a helper method giving it the total quantity and money in and out.
        u = self.ufun.from_aggregates(
            qin, qout, producible, pin, pout_bar, input_penalty, output_penalty
        )
        if return_producible:
            # the real producible quantity is the minimum of what we can produce
            # given supplies and production capacity and what we can sell.
            return u, producible
        return u


def from_aggregates(
        self,
        qin: int,
        qout_signed: int,
        qout_sold: int,
        pin: int,
        pout: int,
        input_penalty,
        output_penalty,
    ) -> float:
        """
        Calculates the utility from aggregates of input/output quantity/prices

        Args:
            qin: Input quantity (total including all exogenous contracts).
            qout_signed: Output quantity (total including all exogenous contracts)
                         that the agent agreed to sell.
            qout_sold: Output quantity (total including all exogenous contracts)
                       that the agent will actually sell.
            pin: Input total price (i.e. unit price * qin).
            pout: Output total price (i.e. unit price * qin).
            input_penalty: total disposal cost
            output_penalty: total shortfall penalty

        Remarks:
            - Most likely, you do not need to directly call this method. Consider
              `from_offers` and `from_contracts` that take current balance and
              exogenous contract information (passed during ufun construction)
              into account.
            - The method respects production capacity (n. lines). The
              agent cannot produce more than the number of lines it has.
            - This method does not take exogenous contracts or current balance
              into account.
            - The method assumes that the agent CAN pay for all input
              and production.

        """
        assert qout_sold <= qout_signed, f"sold: {qout_sold}, signed: {qout_signed}"

        # production capacity
        lines = self.ufun.n_lines

        # we cannot produce more than our capacity or inputs and we should not
        # produce more than our required outputs
        produced = min(qin, lines, qout_sold)

        # self explanatory. right?  few notes:
        # 1. You pay disposal costs for anything that you buy and do not produce
        #    and sell. Because we know that you sell no more than what you produce
        #    we can multiply the disposal cost with the difference between input
        #    quantity and the amount produced
        # 2. You pay shortfall penalty for anything that you should have sold but
        #    did not. The only reason you cannot sell something is if you cannot
        #    produce it. That is why the shortfall penalty is multiplied by the
        #    difference between what you should have sold and the produced amount.
        u = (
            pout
            - pin
            - self.ufun.production_cost * produced
            - input_penalty
            - output_penalty
        )
        if not self.ufun.normalized:
            return u
        # normalize values between zero and one if needed.
        rng = self.ufun.max_utility - self.ufun.min_utility
        if rng < 1e-12:
            return 1.0
        return (u - self.ufun.min_utility) / rng