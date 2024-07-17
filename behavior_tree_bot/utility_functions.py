from functools import *
from typing import List
import logging

from planet_wars import PlanetWars, Fleet, Planet

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
    arriving_fleets.sort(key=lambda fleet: fleet.turns_remaining)
    first_arrival = arriving_fleets[0].turns_remaining

    if (first_arrival >= num_turns and planet.owner == 0) or num_turns <= 0:
        return ship_count
    
    if planet.owner == 0:
        ship_count += planet.growth_rate * num_turns - first_arrival
    else:
        ship_count += planet.growth_rate * num_turns
    ally_ship_count = reduce(lambda a, b: a + b.num_ships, [f for f in arriving_fleets if f.owner == 1], 0)
    enemy_ship_count = reduce(lambda a, b: a + b.num_ships, [f for f in arriving_fleets if f.owner == 2], 0)
    ship_count += abs(ally_ship_count - enemy_ship_count)
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

    if not arriving_fleets:
        return planet.owner
    
    last_arrival = arriving_fleets[0].turns_remaining
    for turn in range(last_arrival):
        ship_count += planet.growth_rate if current_owner != 0 else 0
        fleets = []
        while arriving_fleets and arriving_fleets[-1].turns_remaining == turn:
            fleets.append(arriving_fleets.pop())
        ally_ship_count = reduce(lambda a, b: a + b.num_ships, [f for f in fleets if f.owner == 1], 0)
        enemy_ship_count = reduce(lambda a, b: a + b.num_ships, [f for f in fleets if f.owner == 2], 0)
        match planet.owner:
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
        dupl_fleets = state.my_fleets()
        dupl_fleets.extend(state.enemy_fleets())
        ally_fleets = dupl_fleets
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
    priority -= forecast_ship_count(state, planet, attacker.turns_remaining) 
    priority -= sum([fleet.num_ships for fleet in get_defending_fleets(state, planet.ID)])
    #Current priority is the number of ships that will be needed to prevent the planet to be overtaken.
    possibleDefenders = get_nearest_planets(state, planet.ID, player_id=1)
    defender = possibleDefenders[0]
    ind = 0
    while defender.num_ships < priority: #Could potentially add a +20 or something like that if we want the defending planet to not totally be defenseless after.
        ind+=1
        if ind > len(possibleDefenders+1):
            return 0, None
        defender = possibleDefenders[ind]
    return priority, defender