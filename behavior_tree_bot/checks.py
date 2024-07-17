from functools import reduce
import logging

from planet_wars import PlanetWars, Planet
from utility_functions import *

def if_neutral_planet_available(state):
    return any(state.neutral_planets())

def have_largest_fleet(state):
    return sum(planet.num_ships for planet in state.my_planets()) \
             + sum(fleet.num_ships for fleet in state.my_fleets()) \
           > sum(planet.num_ships for planet in state.enemy_planets()) \
             + sum(fleet.num_ships for fleet in state.enemy_fleets())

def multiple_planets_available(state):
    return len(state.my_planets()) >= 2

def planet_in_danger(state): #Do we need to send defenders to any planets?
    logging.info("CHECK: Is there a planet in danger?")
    for planet in get_attacked_planets(state):
        attackers = get_attacking_fleets(state, planet.ID)
        totalAttackers = 0
        for fleet in attackers:
            totalAttackers += fleet.num_ships
        defenders = get_defending_fleets(state, planet.ID)
        totalDefenders = 0
        for fleet in defenders:
            totalDefenders += fleet.num_ships
        logging.info(totalAttackers)
        logging.info(totalDefenders)
        if totalAttackers > totalDefenders:
            logging.info("CHECK: Found a planet in danger!")
            logging.info(planet.num_ships)
            return True
    logging.info("CHECK: No planets in danger")
    return False

def steal_stack_not_empty(state:PlanetWars, blackboard: dict) -> bool:
    logging.info("CHECK: Checking steal stack")
    if "attacked_neutral_planet_stack" not in blackboard:
        logging.info("CHECK: Steal stack key not found in blackboard")
        return False
    if blackboard["attacked_neutral_planet_stack"] is []:
        logging.info("CHECK: Blackboard stack is empty!")
        return False
    logging.info("CHECK: Success, steal stack contains planets")
    return True

def is_planet_stealable(state:PlanetWars, blackboard: dict) -> bool:
  assert blackboard.get("attacked_neutral_planet", None) is not None, "Planet to steal is none in check function"
  # Tweakable Params
  # Higer = Willing to consider stealing longer after initial enemy arrival
  arrival_turn_grace_period = 3
  # Higher = More aggresive and risky stealing. Multiply free ships by phaser_strength to get available stealing force.
  phaser_strength = 0.7
  # Higer = Willing to spend more ships to capture
  max_reinforcment_level = 50

  planet : Planet = blackboard.get("attacked_neutral_planet")
  attacking_fleets = [fleet for fleet in get_attacking_fleets(state, planet.ID) if fleet.owner == 2]
  attacking_fleets.sort(key=lambda fleet: fleet.turns_remaining)
  total_attacking_force = reduce(lambda a, b: a + b.num_ships, attacking_fleets, 0)
  total_attacking_force -= planet.num_ships
  
  first_arrival = attacking_fleets[0].turns_remaining

  if forecast_ship_count(state, planet, first_arrival + arrival_turn_grace_period) > max_reinforcment_level:
      return False

  nearby_allies = get_nearest_planets(state, planet.ID, max(first_arrival, arrival_turn_grace_period), 1)
  total_stealing_force = reduce(lambda a, b: a + get_free_ships(state, b.ID, phaser_strength), nearby_allies, 0)
  
  if total_attacking_force >= total_stealing_force:
      return False
  
  return True


def is_planet_weaker_than_our_strength(state: PlanetWars, blackboard: dict) -> bool:
    # Param
    # Only attack if the planet is weaker than 60% of our total strength
    total_strength_percentage = 0.6
    target = blackboard.get("capture_target", None)
    if target is None:
        logging.error("Capture Target is none in is_planet_weaker_than_our_strength check")
        return False
    total_strength = float(reduce(lambda a,b: a + b.num_ships, state.my_planets(), 0)) * total_strength_percentage
    logging.info(f"Total Strength:{ total_strength}")
    if target.num_ships > total_strength:
        return False
    return True


def will_planet_be_captured_by_us(state: PlanetWars, blackboard: dict):
    target = blackboard.get("capture_target", None)
    if target is None:
        logging.error("Capture Target is none in is_planet_weaker_than_our_strength check")
        return False
    attacking_fleets = get_attacking_fleets(state, target.ID)
    our_attacking_fleets = [fleet for fleet in attacking_fleets if fleet.owner == 1]
    
    if not our_attacking_fleets:
        return False
    
    if forecast_planet_owner(state, target) == 1:
        return True
    
    return False