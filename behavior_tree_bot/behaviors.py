import sys
from functools import *
from typing import List
import logging
sys.path.insert(0, '../')
from planet_wars import issue_order, get_blackboard, PlanetWars, Fleet, Planet
# from utility_functions import *
from math import floor

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
        return issue_order(state, strongest_planet.ID, weakest_planet.ID, floor(strongest_planet.num_ships / 2))
    
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
    return issue_order(state, potential_thieves[0].ID, targeted_planet.ID, floor(potential_thieves[0].num_ships/4))

def spread_to_weakest_neutral_planet(state):
    logging.info('FUNCTION: Running function: Spread To Weakest Neutral Planet')
    # (1) Find my strongest planet.
    strongest_planet = max([planet for planet in state.my_planets() if get_attacking_fleets(state, planet.ID) is []], key=lambda p: p.num_ships, default=None)

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
        return issue_order(state, strongest_planet.ID, weakest_planet.ID, floor(strongest_planet.num_ships / 4))

def defend_targeted_planets(state):
    logging.info('FUNCTION: Running function: Defend Targeted Planets')
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
    if highestPriority < 0:
        logging.info("FUNCTION: Defense failed! Highest priority is less than zero!")
    if highestPriority < 0 or planetInDanger is None:
        logging.info("FUNCTION: Defense failed! No planet is able to defend!")
        return False
    logging.info("FUNCTION: Defense success! Sending reinforcements to our ally, Commander!")
    logging.info(f"Defender's ships: {currentDefender.num_ships}")
    logging.info(f"Planet in danger's ships: {planetInDanger.num_ships}")
    logging.info(f"Priority: {highestPriority}")
    return issue_order(state, currentDefender.ID, planetInDanger.ID, floor(currentDefender.num_ships/4))

def issue_capture_order(state):
    blackboard = get_blackboard()
    order = blackboard.get("order", None)
    if "order" is None:
        logging.error("Order is not set in issue_capture_order")
        return False
    # Fix for program crashing with negative ships
    if order.num_ships <= 0:
        return False
    result = issue_order(state, order.source_id, order.dest_id, order.num_ships)
    logging.info(f"Order issued?: {result}, {order}")
    return result


#~~~~~~~~~~~~~~~~~~~~UTILITY FUNCTIONS - NOT BEHAVIORS!!~~~~~~~~~~~~~~~~~~~~

def get_pinned_ships(state: PlanetWars, planet_id: int) -> int:
    """    
    Parameters:
        state (PlanetWars): The current game state
        planet_id (int): The ID of the planet
    
    Returns:
        int: The number of ships pinned by an attacking force
    """
    ship_count = state.planets[planet_id].num_ships
    attacking_ships = sum(fleet.num_ships for fleet in state.enemy_fleets() if fleet.destination_planet == planet_id)
    return min(ship_count, attacking_ships)


def get_free_ships(state: PlanetWars, planet_id: int, percentage: float = 1) -> int:
    """
    Parameters:
        state (PlanetWars): The current game state
        planet_id (int): The ID of the planet
        percentage (float): Only include a percentage of the total free ships. [0-1]
    
    Returns:
        int: The number of ships that are not pinned by an attacking force
    """
    percentage = min(max(percentage, 0), 1)
    pinned_ships = get_pinned_ships(state, planet_id)
    total_ships = state.planets[planet_id].num_ships
    free_ships = total_ships - pinned_ships
    free_ships *= percentage
    free_ships = int(free_ships)
    print(f"Free Ships on Planet {planet_id}: {free_ships}", file=open("log_test.txt", "w"), flush=True)
    return max(free_ships, 0)


def get_attacked_planets(state: PlanetWars) -> List[Planet]:
    """
    Parameters:
        state (PlanetWars): The current game state
    
    Returns:
        List[Planet]: A list of planets that are being attacked by the enemy
    """
    attacked_planets = [state.planets[fleet.destination_planet] for fleet in state.enemy_fleets()]
    return attacked_planets


def get_planets(state: PlanetWars, planet_ids: List[int]) -> List[Planet]:
    """
    Parameters:
        state (PlanetWars): The current game state
        planet_ids (List[int]): The IDs of the planets
    
    Returns:
        List[Planet]: A list of planets with the given IDs
    """
    planets = [planet for planet in state.planets if planet.ID in planet_ids]
    return planets


def forecast_ship_count(state: PlanetWars, planet: Planet, num_turns: int) -> int:
    """
    Calculate the number of ships a planet will have in a number of turns.
    This includes production and fleets in flight at the time of the function call.

    Parameters:
        planet (Planet): The planet to forecast the ship count for.
        num_turns (int): The number of turns to forecast.

    Returns:
        int: The forecasted ship count for the planet.
    """ 
    ship_count = planet.num_ships
    attacking_fleets = get_attacking_fleets(state, planet_id=planet.ID)
    arriving_fleets = [fleet for fleet in attacking_fleets if fleet.turns_remaining <= num_turns]
    
    if not arriving_fleets:
        return ship_count + planet.growth_rate * num_turns
    
    arriving_fleets.sort(key=lambda fleet: fleet.turns_remaining)
    first_arrival = arriving_fleets[0].turns_remaining
    
    if (first_arrival > num_turns and planet.owner == 0) or num_turns <= 0:
        return ship_count
    
    ally_ship_count = reduce(lambda a, b: a + b.num_ships, [f for f in arriving_fleets if f.owner == 1], 0)
    enemy_ship_count = reduce(lambda a, b: a + b.num_ships, [f for f in arriving_fleets if f.owner == 2], 0)
    if planet.owner == 0:
        ship_count = abs(ship_count - abs(ally_ship_count - enemy_ship_count))
    else:
        ship_count += abs(ally_ship_count - enemy_ship_count)
    if planet.owner == 0:
        ship_count += planet.growth_rate * (num_turns - first_arrival)
    else:
        ship_count += planet.growth_rate * num_turns
    logging.info(f"UTILITY: Ship count acquired, {ship_count}")
    return ship_count


def forecast_planet_owner(state: PlanetWars, planet: Planet) -> int:
    """
    Calculate the number of ships a planet will have in a number of turns.
    This includes production and fleets in flight at the time of the function call.

    Parameters:
        planet (Planet): The planet to forecast.

    Returns:
        int: The forecasted ship count for the planet.
    """
    ship_count = planet.num_ships
    current_owner = planet.owner
    attacking_fleets = get_attacking_fleets(state, planet_id=planet.ID)
    arriving_fleets = [fleet for fleet in attacking_fleets]
    arriving_fleets.sort(key=lambda fleet: fleet.turns_remaining, reverse=True)
    logging.info(f"forecast_planet_owner: arriving_fleets {arriving_fleets}")
    
    if not arriving_fleets:
        return planet.owner
    
    last_arrival = arriving_fleets[0].turns_remaining
    for turn in range(last_arrival+1):
        ship_count += planet.growth_rate if current_owner != 0 else 0
        fleets = []
        while arriving_fleets and arriving_fleets[-1].turns_remaining == turn:
            fleets.append(arriving_fleets.pop())
        ally_ship_count = reduce(lambda a, b: a + b.num_ships, [f for f in fleets if f.owner == 1], 0)
        enemy_ship_count = reduce(lambda a, b: a + b.num_ships, [f for f in fleets if f.owner == 2], 0)
        match current_owner:
            case 0:
                ship_count -= abs(ally_ship_count - enemy_ship_count)
                if ship_count > 0:
                    continue
                elif ally_ship_count > enemy_ship_count:
                    current_owner = 1
                else:
                    current_owner = 2
            case 1:
                ship_count += ally_ship_count
                ship_count -= enemy_ship_count
                if ship_count < 0:
                    ship_count = abs(ship_count)
                    current_owner = 2
            case 2:
                ship_count += enemy_ship_count
                ship_count -= ally_ship_count
                if ship_count < 0:
                    ship_count = abs(ship_count)
                    current_owner = 1

    return current_owner

def get_attacking_fleets(state: PlanetWars, planet_id: int) -> List[Fleet]:
    """
    Parameters:
        state (PlanetWars): The current game state
        planet_id (int): The ID of the planet
    
    Returns:
        List[Fleet]: A list of fleets that are attacking the planet. Includes both ally and enemy fleets depending on planet owner.
    """
    owner = state.planets[planet_id].owner
    if owner == 2:
        ally_fleets = state.my_fleets()
    if owner == 1:
        ally_fleets = state.enemy_fleets()
    else:
        dupl_fleets = state.my_fleets()
        dupl_fleets.extend(state.enemy_fleets())
        ally_fleets = dupl_fleets
    attacking_fleets = [fleet for fleet in ally_fleets if fleet.destination_planet == planet_id]
    return attacking_fleets

def get_defending_fleets(state: PlanetWars, planet_id: int) -> List[Fleet]:
    """
    Returns a list of the ally fleets currently defending the given planet.

    Parameters:
        state (PlanetWars): The curretn game state
        planet_id (int): The ID of the planet
    
    Returns:
        List[Fleet]: A list of fleets that are defending the planet.
    """
    owner = state.planets[planet_id].owner
    if owner == 1:
        ally_fleets = state.my_fleets()
    if owner == 2:
        ally_fleets = state.enemy_fleets()
    else:
        return [] #A neutral planet will have no defenders, only attackers :(
    defending_fleets = [fleet for fleet in ally_fleets if fleet.destination_planet == planet_id]
    return defending_fleets


def get_nearest_planets(state: PlanetWars, planet_id: int, num_turns: int=float('INF'), player_id: int = None) -> List[Planet]:
    """
    Return a sorted list of the nearest planets to a given planet.
    num_turns determines the turn horizon cutoff point after which planets are excluded.
    Optional player_id will filter in planets with that id.

    Parameters:
        state (PlanetWars): The current game state
        planet_id (int): The ID of the planet
        num_turns (int): The number of turns the planets are reachable in
        player_id (int, optional): The ID of the player to filter in planets (default: all planets)

    Returns:
        List[Planet]: A sorted list of nearest planets
    """
    logging.info("UTILITY: Getting nearest planets")
    planet = None
    assert planet_id in [p.ID for p in state.planets], "Planet ID not found in state"
    planet = state.planets[planet_id]
    planets = [p for p in state.planets if p.ID != planet_id and p.owner == player_id and state.distance(planet.ID, p.ID) <= num_turns]
    planets.sort(key=lambda p: state.distance(planet.ID, p.ID))
    return planets


def get_weakest_planets(state: PlanetWars, player_id: int, planet_id: int = None, cutoff: int = float('INF')) -> List[Planet]:
    """
    Return a list of planets owned by a player that have under the cutoff number of ships, sorted with the weakest first.
    
    Parameters:
        state (PlanetWars): The current game state
        player_id (int): The ID of the player
        planet_id (int, optional): The ID of the planet to sort based on distance and weakness (default: None)
        cutoff (int, optional): The cutoff (inc.) number of ships (default: INF)
    
    Returns:
        List[Planet]: A sorted list of weakest planets owned by the player
    """
    if planet_id:
        planets = [p for p in state.planets if p.owner == player_id and p.ID != planet_id and p.num_ships <= cutoff]
        planets.sort(key=lambda p: (state.distance(planet_id, p.ID) * 2 + p.num_ships))
    else:
        planets = [p for p in state.planets if p.owner == player_id and p.num_ships <= cutoff]
        planets.sort(key=lambda p: p.num_ships)
    return planets


def get_strongest_planets(state: PlanetWars, player_id: int, planet_id: int = None, cutoff: int = float('INF')) -> List[Planet]:
    """
    Return a list of planets owned by a player that have under the cutoff number of ships, sorted with the strongest first.
    
    Parameters:
        state (PlanetWars): The current game state
        player_id (int): The ID of the player
        planet_id (int, optional): The ID of the planet to sort based on distance and strength (default: None)
        cutoff (int, optional): The cutoff (inc.) number of ships (default: INF)
    
    Returns:
        List[Planet]: A sorted list of the strongest planets owned by the player
    """
    return get_weakest_planets(state, player_id, planet_id, cutoff)[::-1]


def max_reinforcements(state: PlanetWars, planet_id: int, num_turns: int) -> int:
    """
    Calculate the maximum amount of reinforcements that a planet can receive in a given number of turns.
    Includes growth rate and ships in flight at the time of the function call.

    Parameters:
        state (PlanetWars): The current game state
        planet_id (int): The ID of the target planet
        num_turns (int): The number of turns to consider

    Returns:
        int: The maximum amount of reinforcements that the planet can receive including growth rate and ships in flight
    """
    reinforcements = forecast_ship_count(state, state.planets[planet_id], num_turns)
    for p in state.planets:
        if p.ID != planet_id and state.distance(planet_id, p.ID) <= num_turns:
            reinforcements += forecast_ship_count(state, p, num_turns - state.distance(planet_id, p.ID))
    return reinforcements


def get_production_factor(state: PlanetWars, planet_id: int) -> float:
    """
    Return the production value of this planet. The production value is a ratio based on the growth_rate of the planet and the number of ships guarding it.

    Parameters:
        state (PlanetWars): The current game state
        planet_id (int): The ID of the planet

    Returns:
        float: The production value of the planet
    """
    planet = state.planets[planet_id]
    production_factor = planet.growth_rate / (planet.num_ships / 10 + 1)
    return production_factor

def has_sent_fleet(state: PlanetWars, source_planet: Planet, destination_planet: Planet) -> bool:
    #Determine if source_planet has sent a fleet to destination_planet.
    matching_fleets = []
    if source_planet.owner is destination_planet.owner:
        matching_fleets = [fleet for fleet in get_defending_fleets(state, destination_planet.ID) if fleet.source_planet is source_planet]
    else:
        matching_fleets = [fleet for fleet in get_attacking_fleets(state, destination_planet.ID) if fleet.source_planet is source_planet]
    return len(matching_fleets) > 0

def get_priority(state: PlanetWars, planet: Planet, attacker: Fleet):
    """
    Return a number representing the number of ships needed to defend the given planet. Takes into account:
        - The soonest attacking force's number of ships, & how soon it'll arrive
        - The number of ships on the target planet when the attacking force arrives
        - The number of ships currently defending the planet
        - How far away the nearest planet with sufficient troops is
        - And if a defending fleet can't reach the planet in time, how many ships will need to be sent to overtake the enemy force.

    Parameters:
        state (PlanetWars): The current game state
        planet (Planet): The planet being attacked
    
        Returns: 
            int: The priority, AKA the number of ships needed to defend the planet
            Planet: The planet that should defend the targeted planet
    
    """
    priority = attacker.num_ships
    priority -= planet.num_ships
    priority -= sum([fleet.num_ships for fleet in get_defending_fleets(state, planet.ID)])
    #Current priority is the number of ships that will be needed to prevent the planet to be overtaken.
    possibleDefenders = get_nearest_planets(state, planet.ID, player_id=1)
    if len(possibleDefenders) <= 0:
        logging.info("UTILITY: No possible defenders")
        return 0, None
    defender = possibleDefenders[0]
    ind = 0
    while defender.num_ships < priority or has_sent_fleet(state, defender, planet):
        ind+=1
        if ind > len(possibleDefenders)-1:
            logging.info("UTILITY: No planet has enough troops to defend")
            return 0, None
        defender = possibleDefenders[ind]
    logging.info(f"UTILITY: Got priority of {priority}")
    return priority, defender

# def get_most_valuable_neutral_planet(state:PlanetWars):
#     #Take into account: distance from the strongest planet?, growth rate of the planet, number of ships currently on the planet
#     #Nearest should be the highest priority, then growth rate, then number of ships on the planet
#     #priority = distance 60%, growth rate 30%, then number of ships on the planet 10%
#     # get_strongest_planets(state, 1)[0].ID,
#     highest_priority = 0
#     target = None
#     starting_options = get_nearest_planets(state, get_strongest_planets(state, 1)[0].ID, 20, 0)
#     for planet in starting_options:

    # sorted_for_growth_rate = starting_options.sort(key=lambda planet: planet.growth_rate, reverse=True)

    #arriving_fleets.sort(key=lambda fleet: fleet.turns_remaining)