import sys
sys.path.insert(0, '../')
from planet_wars import issue_order
from utility_functions import *

def attack_weakest_enemy_planet(state):
    # (1) Find my strongest planet.
    strongest_planet = max(state.my_planets(), key=lambda t: t.num_ships, default=None)

    #Error check.
    if strongest_planet is None: return False

    # (2) Firing one fleet at a time, like the original code had, is a bad strategy. But we should have some limit.
    #     Make sure our strongest planet isn't too weak after we send out the ship.
    if strongest_planet.num_ships < 20: return False

    # (3) Find the weakest enemy planet that is within a range of some number of turns.
    rangeLimit = 10
    searchable_planets = get_nearest_planets(state, strongest_planet.ID, rangeLimit, 2)
    while(searchable_planets == []):
        rangeLimit += 10
        searchable_planets = get_nearest_planets(state, strongest_planet.ID, rangeLimit, 2)
        if rangeLimit > 100:
            return False
    weakest_planet = min(searchable_planets, key=lambda t: t.num_ships, default=None)

    if not strongest_planet or not weakest_planet:
        # No legal source or destination
        return False
    else:
        # (4) Send half the ships from my strongest planet to the weakest enemy planet.
        return issue_order(state, strongest_planet.ID, weakest_planet.ID, strongest_planet.num_ships / 2)

def spread_to_weakest_neutral_planet(state):
    # (1) Find my strongest planet.
    strongest_planet = max(state.my_planets(), key=lambda p: p.num_ships, default=None)

    #Error check.
    if strongest_planet is None: return False

    # (2) Firing one fleet at a time, like the original code had, is a bad strategy. But we should have some limit.
    #     Make sure our strongest planet isn't too weak after we send out the ship.
    if strongest_planet.num_ships < 50: return False

    # (3) Get the nearest & weakest neutral planet.
    weakest_planets = get_weakest_planets(state, 0, strongest_planet.ID)
    nearest_planets = get_nearest_planets(state, strongest_planet.ID, 5, 0) #5 is a sample for number of turns. I don't know if that's too much or too little yet.
    nearest_weakest_planets = set(nearest_planets).intersection(weakest_planets)

    # (4) Identify the nearest, weakest neutral planet.
    weakest_planet = min(nearest_weakest_planets, key=lambda p: p.num_ships, default=None)

    if not strongest_planet or not weakest_planet:
        # No legal source or destination
        return False
    else:
        # (4) Send half the ships from my strongest planet to the weakest enemy planet.
        return issue_order(state, strongest_planet.ID, weakest_planet.ID, strongest_planet.num_ships / 2)

def defend_targeted_planets(state):
    # (1) Get the planet that is closest to being overtaken and is not actively being defended.
    planetInDanger = None
    highestPriority = 0
    currentDefender = None
    for planet in get_attacked_planets(state):
        # (1a) Get the soonest attack on the planet
        attackers = get_attacking_fleets(state, planet.ID)
        if len(attackers) <= 0:
            return False
        soonestAttacker = min(attackers, key=lambda p:p.turns_remaining, default=0)
        # (1b) Get the priority of the current planet based on that attacking fleet.
        priority, defender = get_priority(state, planet, soonestAttacker)
        if defender is None: continue #Skip this planet
        # (1b) Determine if this planet is a higher priority
        if planetInDanger is None or priority > highestPriority:
            highestPriority = priority
            planetInDanger = planet
            currentDefender = defender
    if highestPriority < 0 or planetInDanger is None:
        return True
    return issue_order(state, currentDefender.ID, planetInDanger.ID, highestPriority)