import sys
sys.path.insert(0, '../')
from planet_wars import issue_order, get_blackboard
from utility_functions import *

def attack_weakest_enemy_planet(state):
    logging.info('FUNCTION: Running function: Attack Weakest Enemy Planet')
    # (1) Find my strongest planet.
    strongest_planet = max(state.my_planets(), key=lambda t: t.num_ships, default=None)

    #Error check.
    if strongest_planet is None: 
        logging.info('FUNCTION: Attack failed! No strongest_planet found')
        return False

    # (2) Firing one fleet at a time, like the original code had, is a bad strategy. But we should have some limit.
    #     Make sure our strongest planet isn't too weak after we send out the ship.
    if strongest_planet.num_ships < 20: 
        logging.info('FUNCTION: Attack failed! Strongest planet not strong enough!')
        return False

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
        logging.info('FUNCTION: Attack failed! One of source/destination is illegal!')
        return False
    else:
        # (4) Send half the ships from my strongest planet to the weakest enemy planet.
        logging.info('FUNCTION: Attack success!')
        return issue_order(state, strongest_planet.ID, weakest_planet.ID, strongest_planet.num_ships / 2)
    
def steal_targeted_neutral_planet(state):
    blackboard = get_blackboard()
    logging.info('FUNCTION: Running function: Steal Targeted Neutral Planet')
    if "attacked_neutral_planet" not in blackboard:
        logging.info('FUNCTION: Steal failed! No planet currently targeted')
        return False
    targeted_planet: Planet = blackboard["attacked_neutral_planet"] #Get our target planet
    #Get our nearest planets to it, that can reach it in time
    soonest_attacker = min([fleet for fleet in get_attacking_fleets(state, targeted_planet.ID) if fleet.owner == 1], key=lambda p: p.turns_remaining)
    nearest_thieves = get_nearest_planets(state, targeted_planet.ID, soonest_attacker, 1)
    if nearest_thieves is []:
        logging.info('FUNCTION: Steal failed! No planets close enough to save!')
        return False
    #So, we have some planets in nearest_thieves. Let's narrow it down to those that haven't already sent a fleet to this planet.
    potential_thieves = []
    for planet in nearest_thieves:
        sentFleet = False
        for fleet in state.my_fleets():
            if fleet.source_planet is planet:
                sentFleet = True
        if not sentFleet:
            potential_thieves.append(planet)
    if potential_thieves is []:
        logging.info('FUNCTION: Steal failed! No planets close enough to save that have already sent troops!') #This is our big cutoff. If every planet within range has sent a defender, stop the steal sequence here.
        return False
    logging.info('FUNCTION: Steal success! Sending planet to attempt to snatch the planet from under their noses, Commander!')
    return issue_order(state, potential_thieves[0].ID, targeted_planet.ID, potential_thieves[0].num_ships/4)

def spread_to_weakest_neutral_planet(state):
    logging.info('FUNCTION: Running function: Spread To Weakest Neutral Planet')
    # (1) Find my strongest planet.
    strongest_planet = max(state.my_planets(), key=lambda p: p.num_ships, default=None)

    #Error check.
    if strongest_planet is None: 
        logging.info('FUNCTION: Spread failed! No strongest_planet found!')
        return False

    # (2) Firing one fleet at a time, like the original code had, is a bad strategy. But we should have some limit.
    #     Make sure our strongest planet isn't too weak after we send out the ship.
    if strongest_planet.num_ships < 10: 
        logging.info('FUNCTION: Spread failed! Strongest planet not strong enough!')
        return False

    # (3) Get the nearest & weakest neutral planet.
    weakest_planets = get_weakest_planets(state, 0, strongest_planet.ID)
    nearest_planets = get_nearest_planets(state, strongest_planet.ID, 10, 0) #10 is a sample for number of turns. I don't know if that's too much or too little yet.
    nearest_weakest_planets = set(nearest_planets).intersection(weakest_planets)

    # (4) Identify the nearest, weakest neutral planet.
    weakest_planet = min(nearest_weakest_planets, key=lambda p: p.num_ships, default=None)

    if not strongest_planet or not weakest_planet:
        # No legal source or destination
        logging.info('FUNCTION: Spread failed! One of source/destination is illegal!')
        return False
    else:
        # (4) Send half the ships from my strongest planet to the weakest enemy planet.
        logging.info('FUNCTION: Spread success! Number of ships on target planet:')
        logging.info(weakest_planet.num_ships)
        return issue_order(state, strongest_planet.ID, weakest_planet.ID, strongest_planet.num_ships / 2)

def defend_targeted_planets(state):
    # (1) Get the planet that is closest to being overtaken and is not actively being defended.
    planetInDanger = None
    highestPriority = 0
    currentDefender = None
    for planet in get_attacked_planets(state):
        # (1a) Get the soonest attack on the planet
        attackers = get_attacking_fleets(state, planet.ID)
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
        logging.info("FUNCTION: Defense failed! No planet needs defending!")
        return False
    logging.info("FUNCTION: Defense success! Sending reinforcements to our ally, Commander!")
    logging.info(currentDefender.num_ships)
    logging.info(planetInDanger.num_ships)
    logging.info(highestPriority)
    return issue_order(state, currentDefender.ID, planetInDanger.ID, currentDefender.num_ships/2)

def issue_capture_order(state):
    blackboard = get_blackboard()
    order = blackboard.get("order", None)
    if "order" is None:
        logging.error("Order is not set in issue_capture_order")
        return False
    result = issue_order(state, order.source_id, order.dest_id, order.num_ships)
    logging.info(f"Order issued?: {result}, {order}")
    return result