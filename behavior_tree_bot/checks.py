from functools import reduce

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
    return len(state.my_planets()) > 2

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


def is_planet_weaker_than_our_strength(state: PlanetWars, blackboard: dict):
    # TODO
    return False


def will_planet_be_captured(state: PlanetWars, blackboard: dict):
    # TODO
    return False