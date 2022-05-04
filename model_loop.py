from scml import *
from scml.oneshot import *
from pprint import pprint
from copy import copy
import warnings
from typing import List
from datetime import datetime
import random
from pprint import pprint
from agents.bettersyncagent import BetterSyncAgent
from agents.strategicagent import GPAAgent
from tier1_agent import LearningAgent
import csv

TESTING = False
print_headers = True

def write_out(data, first=False):
    fields = data[0].keys()
    if first:
        key = 'w'
    else:
        key = 'a'
    with open("datarun1.csv", key) as csvfile: 
        csvwriter = csv.writer(csvfile) 
        if first:
            csvwriter.writerow(fields)
        for d in data:
            csvwriter.writerow(d.values())
    
def run_sim(first):
    # always include 3 of us
    # rest are opponent (5 - 13)
    # between 3/8 and 3/16 agents will be us collecting data
    n_agents_process_1 = random.randrange(4, 8 + 1)
    n_agents_process_2 = random.randrange(4, 8 + 1)
    n_agents = n_agents_process_1 + n_agents_process_2
    n_agents_not_us = n_agents - 3
    pop = [LearningAgent] * 100 + [GreedyOneShotAgent] * 100
    agent_types = (
        [GPAAgent] * 3 +
        random.sample(pop, k=n_agents_not_us)
    )
    random.shuffle(agent_types)
    # print(n_agents_process_1, n_agents_process_2)
    # pprint(agent_types)
    kwargs = {"n_agents_per_process": 1} if TESTING else {
        "n_agents_per_process": [n_agents_process_1, n_agents_process_2]
    }
    world = SCML2020OneShotWorld(
        **SCML2020OneShotWorld.generate(agent_types, **kwargs),
        construct_graphs=True,
        neg_time_limit=float('inf'),
        neg_step_time_limit=float('inf')
    )

    all_data = []

    num_days = 1 if TESTING else 50
    for day_idx in range(num_days):
        world.step()
        t = datetime.now()
    
    for agent_id in world.agents:
        if agent_id[2:5] == 'GPA':
            a = world.agents[agent_id]
            print(f"writing {len(a.data)}")
            all_data = all_data + a.data

    write_out(all_data, first=first)
        

def run_many_sims():
    run_sim(first=True)
    while(True):
        run_sim(first=False)

run_many_sims()
