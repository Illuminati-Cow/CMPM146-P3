#!/usr/bin/env python
#

"""
// There is already a basic strategy in place here. You can use it as a
// starting point, or you can throw it out entirely and replace it with your
// own.
"""
import logging, traceback, sys, os, inspect
logging.basicConfig(filename=__file__[:-3] +'.log', filemode='w', level=logging.DEBUG)
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
from collections import namedtuple

from behavior_tree_bot.behaviors import *
from behavior_tree_bot.checks import *
from behavior_tree_bot.bt_nodes import *

from planet_wars import PlanetWars, finish_turn

blackboard = {}

def get_blackboard() -> dict:
    return blackboard

# You have to improve this tree or create an entire new one that is capable
# of winning against all the 5 opponent bots
def setup_behavior_tree():
    assert blackboard is not None
    # Top-down construction of behavior tree
    root = Selector(name='High Level Ordering of Strategies')

    offensive_plan = Sequence(name='Offensive Strategy')
    # TEST REMOVE SUCCEEDER!!!!!!!!!!!! 
    largest_fleet_check = Succeeder(Check(have_largest_fleet))
    # Out of order so that it works
    capture_sequence = Sequence(name="Capture Behavior")
    attack = capture_sequence
    # attack = Action(attack_weakest_enemy_planet)
    offensive_plan.child_nodes = [
        largest_fleet_check,
        SetVar(blackboard, "capture_target", lambda state: get_weakest_planets(state, 2)[0]),
        attack
    ]

    spread_sequence = Sequence(name='Spread Strategy')
    neutral_planet_check = Check(if_neutral_planet_available)
    spread_action = Action(spread_to_weakest_neutral_planet)
    spread_sequence.child_nodes = [neutral_planet_check, spread_action]

    defense_sequence = Sequence(name='Defensive Strategy')
    defendable_planet_check = Check(multiple_planets_available)
    defense_action = Action(defend_targeted_planets)
    defense_sequence.child_nodes = [defendable_planet_check, defense_action]

    Order = namedtuple('Order', ['num_ships', 'source_id', 'dest_id', 'arrival_time'])
    muster_phaser_strength = 0.65
    capture_sequence.child_nodes = [
        Inverter(IsVarNull(blackboard, "capture_target")),
        Sequence(name="Capture Sequence", child_nodes=[
            Sequence(name="Capturable Check", child_nodes=[
                Check(is_planet_weaker_than_our_strength, blackboard),
                Inverter(Check(will_planet_be_captured_by_us, blackboard))
            ]),
            Sequence(name="Attack Sequence", child_nodes=[
                SetVar(
                    blackboard, 
                    "strongest_ally_planets", 
                    lambda state: get_strongest_planets(state, 1, blackboard["capture_target"].ID),
                ),
                Sequence(name="Muster Sequence", child_nodes=[
                    Inverter(IsVarNull(blackboard, "strongest_ally_planets")),
                    # Reset Values
                    SetVar(blackboard, "attack_strength", lambda state: 0),
                    SetVar(blackboard, "attack_max_arrival_time", lambda state: 0),
                    UntilFailure(
                        Sequence([
                            PopFromStack(blackboard, "strongest_ally_planets", "muster_ally"),
                            Check(lambda state, blackboard: get_free_ships(state, blackboard["muster_ally"].ID) > 0, blackboard),
                            Sequence(name="Setting Order Variables", child_nodes=[
                                SetVar(
                                    blackboard,
                                    "order", 
                                    lambda state: \
                                        Order(
                                            get_free_ships(state, blackboard["muster_ally"].ID, muster_phaser_strength), 
                                            blackboard["muster_ally"].ID,
                                            blackboard['capture_target'].ID,
                                            state.distance(blackboard["muster_ally"].ID, blackboard['capture_target'].ID)
                                        )
                                ),
                                SetVar(
                                    blackboard,
                                    "attack_strength", 
                                    lambda state: blackboard["attack_strength"] + blackboard["order"].num_ships
                                ),
                                SetVar(
                                    blackboard,
                                    "attack_max_arrival_time", 
                                    lambda state: max(blackboard["attack_max_arrival_time"], blackboard["order"].arrival_time)
                                )
                            ]),
                            PushToStack(blackboard, "orders", "order")
                        ]),
                    ),
                ]),
                Sequence(name="Order Sequence", child_nodes=[
                    # REMOVE SUCCEEDER TEST!!!!!!!!
                    Succeeder(Check(
                        lambda state, blackboard: blackboard["attack_strength"] > \
                            forecast_ship_count(state, blackboard["capture_target"], blackboard["attack_max_arrival_time"]),
                        blackboard
                    )),
                    UntilFailure(Sequence(name="Issue Order Sequence", child_nodes=[
                        PopFromStack(blackboard, "orders", "order"),
                        # REMOVE SUCCEEDER TEST!!!!!!!!
                        Succeeder(Action(lambda state: issue_order(state, blackboard["order"].source_id, blackboard["order"].dest_id, blackboard["order"].num_ships))),
                    ]))
                ])
            ])
        ])
    ]

    steal_sequence = Sequence(name='Stealing Strategy')
    get_attacked_neutral_planets_stack = SetVar(
        blackboard,
        "attacked_neutral_planet_stack", 
        lambda state: [np for np in get_attacked_planets(state) if np.owner == 0]
    )
    iterate_through_neutral_stack = Sequence()
    capture_stealable_planet = Sequence()
    continue_until_success = Inverter(capture_stealable_planet)
    try_until_steal = UntilFailure(iterate_through_neutral_stack)
    steal_sequence.child_nodes = [
        get_attacked_neutral_planets_stack,
        try_until_steal
    ]
    # try_until_success
    iterate_through_neutral_stack.child_nodes = [
        PopFromStack(blackboard, "attacked_netural_planets", "attacked_neutral_planet"),
        continue_until_success
    ]
    # continue_until_success
    capture_stealable_planet.child_nodes = [
        Check(is_planet_stealable, blackboard),
        SetVar(blackboard, "capture_target", lambda: blackboard["attacked_neutral_planet"]),
        capture_sequence
    ]

    root.child_nodes = [offensive_plan, spread_sequence, defense_sequence]

    logging.info('\n' + root.tree_to_string())
    return root

# You don't need to change this function
def do_turn(state):
    behavior_tree.execute(planet_wars)

if __name__ == '__main__':
    logging.basicConfig(filename=__file__[:-3] + '.log', filemode='w', level=logging.DEBUG)
    logging.log(logging.INFO, "Setting up behavior tree")
    behavior_tree = setup_behavior_tree()
    try:
        map_data = ''
        while True:
            current_line = input()
            if len(current_line) >= 2 and current_line.startswith("go"):
                planet_wars = PlanetWars(map_data)
                do_turn(planet_wars)
                finish_turn()
                map_data = ''
            else:
                map_data += current_line + '\n'

    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')
    except Exception:
        traceback.print_exc(file=sys.stdout)
        logging.exception("Error in bot.")
