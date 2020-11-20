# original simulation written by https://github.com/tangbj, I copy-pasted the code then added
# the multiple-OT and highest-hp target selection logic

# hateful strikes deal between 22-29k damage every 1.2 to 2s (average of 1.6s)
# this simulation will only consider how many times a healing team of 3 will let an offtank die
# patchwerk will enrage during the last 5%, but we ignore that since tanks will save shield wall
# does not take into account batching

OFFTANK_MAX_HEALTH = 10000
FIGHT_LENGTH = 60 * 4
AVERAGE_MITIGATION = 0.7
PATCHWERK_MISS_CHANCE = 0.3
AVERAGE_PLUS_HEAL = 1000
AMPLIFY_MAGIC = True
MAGIC_ATTUNEMENT = True
POINTS_IN_IMPROVED_HEALING = 3
# assume there is some sort of variance between casts
REACTION_TIME = 0.2
HEALER_CRIT_CHANCE = 0.2
TOTAL_PLUS_HEAL = AVERAGE_PLUS_HEAL + (150 if AMPLIFY_MAGIC else 0) + (75 if MAGIC_ATTUNEMENT else 0)

import argparse
import heapq
import random
# import math

"""
# returns True if tank lives, False otherwise
# if prehealing is set to true, healers will begin precasting 1s before the start of the fight
def run_one_simulation(verbose=False, prehealing=False):
    tick = 0 if(not prehealing) else -1
    next_hateful_strike = 0
    tank_health = OFFTANK_MAX_HEALTH
    did_tank_live = True

    # we assume only slow heals are casted, so spells are first-in, first-out
    healing_queue = []
    # key is healer index, value is tick
    healers_next_cast = {
        0: -1,
        1: -1,
        2: -1,
    }

    while tick < FIGHT_LENGTH:
        if tick >= next_hateful_strike and tick > 0:
            # we apply damage first before healing (if both damage and heals occur on the same 0.1s tick)

            # test if patchwerk hits
            if random.random() >= PATCHWERK_MISS_CHANCE:
                damage = get_hateful_strike_damage()
                tank_health = max(tank_health - damage, 0)
            if verbose:
                print('Hateful strike hits for {} on {:.1f}s; Health - {}/{}'.format(damage, tick, tank_health, OFFTANK_MAX_HEALTH))
            if tank_health == 0:
                did_tank_live = False
            if verbose:
                print('TANK DIES; WHY NO HEALS NOOBS')
            return False
        # patchwerk misses
        else:
            if verbose:
                print('Patchwerk misses at {:.1f}s'.format(tick))
                next_hateful_strike += get_next_hateful_strike()

    # healing
    for index, value in enumerate(healing_queue):
        healer_index, heal_amount, time_heal_goes_off = value
        if tick >= time_heal_goes_off:
            new_tank_health = min(tank_health + heal_amount, OFFTANK_MAX_HEALTH)
            actual_amount_healed = new_tank_health - tank_health
            tank_health = new_tank_health
        if verbose:
            print('Healer {} healed Tank for {} at {:.1f}s; Health - {}/{}'.format(healer_index, actual_amount_healed, tick, tank_health, OFFTANK_MAX_HEALTH))
        del healing_queue[index]

    for k, v in healers_next_cast.items():
        if tick >= v:
            heal_amount, _, cast_time = get_heal('h4')
            cast_time = round(cast_time + REACTION_TIME * random.random(), 1)
            healing_queue.append((k, heal_amount, tick + cast_time))
            healers_next_cast[k] = tick + cast_time
            tick += 0.1

    if verbose:
        print('TANK SURVIVES')
    return True

# assume patchwerk will hit us every third hateful strike
def get_next_hateful_strike():
    seconds_later = 0
    for _ in range(3):
        seconds_later += (random.random() * (0.8) + 1.2)

    return math.floor(seconds_later * 10) / 10
"""

def get_hateful_strike_damage():
    damage = random.random() * (29000 - 22000) + 22000
    damage *= (1 - AVERAGE_MITIGATION)
    return round(damage)

# tuple is average base healing and unmodified healing cost and cast time
healing_spell_data = {
    'h4': (779.5, 305, 2.5),
}

# pass in name and rank of spell (e.g. h3, gh1)
def get_heal(spell):
    base_healing, mana_cost, cast_time = healing_spell_data.get(spell)
    mana_cost *= (1 - 0.05 * POINTS_IN_IMPROVED_HEALING)
    total_healing = base_healing + 3 / 3.5 * TOTAL_PLUS_HEAL
    if random.random() <= HEALER_CRIT_CHANCE:
        total_healing *= 1.5
    return total_healing, mana_cost, cast_time

class Event:
    def is_hateful(self):
        return self._entity == 0
    def __init__(self, entity, time):
        self._entity = entity # 0 for Patchwerk, 1 for first healer, 2 for second, 3 for third, etc.
        self._time = time # time in seconds from start of fight
    def __lt__(self, other):
        return self._time < other._time
    def __gt__(self, other):
        return other < self
    def __str__(self):
        time = "{0: >5}".format(str(self._time))
        name = ""
        if self._entity == 0:
            name = "Patchwerk Hateful"
        else:
            name = "Healer #{} Heal".format(self._entity)
        return "[Time {}] {}".format(time, name)

def get_timetonext_hateful():
    seconds_later = (random.random() * (0.8499) + 1.2)
    return round(seconds_later, 1)

def get_hateful_target(tanks_health):
    return tanks_health.index(max(tanks_health))

# tank 0 is healed by healers [1, 2, 3], tank 1 by healers [4, 5, 6], tank 2 by healers [7, 8, 9]
def get_heal_target(healer_idx):
    return (healer_idx + 2) // 3 - 1

def heal_tank(tanks_health, tank_idx, heal_qty):
    # print("Tank #{} ({} hp) is healed for {}".format(tank_idx, tanks_health[tank_idx], heal_qty))
    tanks_health[tank_idx] += heal_qty
    if tanks_health[tank_idx] > OFFTANK_MAX_HEALTH:
        # print("Overhealed {}".format(tanks_health[tank_idx] - OFFTANK_MAX_HEALTH))
        tanks_health[tank_idx] = OFFTANK_MAX_HEALTH

def smash_tank(tanks_health, tank_idx, dmg):
    if random.random() < PATCHWERK_MISS_CHANCE:
        # print("Hateful Strike MISSES tank #{}".format(tank_idx))
        return False
    # print("Hateful Strike hits tank #{} ({} hp) for {} dmg".format(tank_idx, tanks_health[tank_idx], dmg))
    tanks_health[tank_idx] -= dmg
    if tanks_health[tank_idx] <= 0:
        # print("Tank #{} has DIED! ({} Overkill)".format(tank_idx, -tanks_health[tank_idx]))
        return True
    return False

def run_simulation():
    PATCHWERK = 0
    event_heap = []
    heapq.heappush(event_heap, Event(PATCHWERK, 0))
    # print("Patchwerk first Hateful Strike scheduled to land at 0 seconds")
    for ii in range(1, 10):
        _, _, cast_time = get_heal('h4')
        start = round(random.random() * cast_time, 1)
        # print("Healer #{} randomly scheduled to land first heal at {} seconds".format(ii, start))
        heapq.heappush(event_heap, Event(ii, start))
    tanks_health = [OFFTANK_MAX_HEALTH, OFFTANK_MAX_HEALTH, OFFTANK_MAX_HEALTH]
    elapsed = 0
    heapq.heapify(event_heap)
    while elapsed < FIGHT_LENGTH:
        next_event = heapq.heappop(event_heap)
        # print("{} {}".format(tanks_health, next_event))
        if next_event.is_hateful():
            target_idx = get_hateful_target(tanks_health)
            death = smash_tank(tanks_health, target_idx, get_hateful_strike_damage())
            if death:
                break
            delay = get_timetonext_hateful()
            heapq.heappush(event_heap, Event(PATCHWERK, round(elapsed + delay, 1)))
        else:
            healer_idx = next_event._entity
            target_idx = get_heal_target(healer_idx)
            heal_amount, _, cast_time = get_heal('h4')
            heal_tank(tanks_health, target_idx, heal_amount)
            human_delay = round(REACTION_TIME * random.random(), 1)
            heapq.heappush(event_heap, Event(healer_idx, round(elapsed + cast_time + human_delay, 1)))
        elapsed = next_event._time # increment timer
    if elapsed >= FIGHT_LENGTH:
        # print("Congrats! Patchwerk is dead")
        return True
    else:
        # print("TANK DIES; WHY NO HEALS NOOBS")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sims", required=True)
    args = parser.parse_args()
    number_simulations = int(args.sims)
    number_survived = 0
    for _ in range(number_simulations):
        # print('Simulation {}'.format(_ + 1))
        # if run_one_simulation(prehealing=True):
        if run_simulation():
            number_survived += 1

    print('Number of times tank survived: {} ({}%)'.format(number_survived, number_survived / number_simulations * 100))
