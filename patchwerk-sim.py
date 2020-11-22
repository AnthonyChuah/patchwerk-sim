# original simulation written by https://github.com/tangbj and refactored by https://github.com/AnthonyChuah
# the multiple-OT and highest-hp target selection logic

# hateful strikes deal between 22-29k damage every 1.2s
# this simulation will only consider how many times a healing team of 3 will let an offtank die
# patchwerk will enrage during the last 5%, but we ignore that since tanks will save shield wall
# does not take into account batching

BEARTANK_MAX_HEALTH = 15000
OFFTANK_MAX_HEALTH = 11000
FIGHT_LENGTH = 60 * 4
AVERAGE_MITIGATION = 0.7
PATCHWERK_MISS_CHANCE = 0.3
AVERAGE_PLUS_HEAL = 1000
AMPLIFY_MAGIC = True
MAGIC_ATTUNEMENT = True

# HOLY TALENTS
POINTS_IN_IMPROVED_HEALING = 3
POINTS_IN_SPIRITUAL_HEALING = 5
POINTS_IN_SPIRITUAL_GUIDANCE = 5

# assume there is some sort of variance between casts
REACTION_TIME = 0.2
HEALER_CRIT_CHANCE = 0.2

# assume rough spirit score of 350
TOTAL_PLUS_HEAL = AVERAGE_PLUS_HEAL + (150 if AMPLIFY_MAGIC else 0) + (75 if MAGIC_ATTUNEMENT else 0) + \
    (350 * 0.25 * POINTS_IN_SPIRITUAL_GUIDANCE / 5)

import argparse
import heapq
import statistics
import random


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
    # spirutal healing adds max of 10% to base heal
    base_healing *= (1 + POINTS_IN_SPIRITUAL_HEALING / 5 * 0.1)
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

# updated hateful strike to hit every 1.2s instead of random number from 1.2 to 2s
def get_timetonext_hateful():
    return 1.2
    # seconds_later = (random.random() * (0.8499) + 1.2)
#     return round(seconds_later, 1)

def get_hateful_target(tanks_health):
    return tanks_health.index(max(tanks_health))

# tank 0 is healed by healers [1, 2, 3], tank 1 by healers [4, 5, 6], tank 2 by healers [7, 8, 9]
def get_heal_target(healer_idx):
    return (healer_idx + 2) // 3 - 1

# returns a tuple with total raw healing and overhealing
def heal_tank(tanks_health, tank_idx, heal_qty, max_tanks_health):
    # print("Tank #{} ({} hp) is healed for {}".format(tank_idx, tanks_health[tank_idx], heal_qty))
    tanks_health[tank_idx] += heal_qty
    overhealing = 0
    if tanks_health[tank_idx] > max_tanks_health:
        overhealing = tanks_health[tank_idx] - max_tanks_health
        tanks_health[tank_idx] = max_tanks_health

    return (heal_qty, overhealing)

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

    # for analysis
    total_raw_healing = 0
    total_overhealing = 0

    tanks_max_health = [BEARTANK_MAX_HEALTH, OFFTANK_MAX_HEALTH, OFFTANK_MAX_HEALTH]
    tanks_health = tanks_max_health.copy()
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
            raw_healing, overhealing = heal_tank(tanks_health, target_idx, heal_amount, tanks_max_health[target_idx])
            total_raw_healing += raw_healing
            total_overhealing += overhealing
            human_delay = round(REACTION_TIME * random.random(), 1)
            heapq.heappush(event_heap, Event(healer_idx, round(elapsed + cast_time + human_delay, 1)))
        elapsed = next_event._time # increment timer

    overhealing_percent = total_overhealing / total_raw_healing
    if elapsed >= FIGHT_LENGTH:
        # print("Congrats! Patchwerk is dead")
        return (True, overhealing_percent)
    else:
        # print("TANK DIES; WHY NO HEALS NOOBS")
        return (False, overhealing_percent)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sims", required=True)
    args = parser.parse_args()
    number_simulations = int(args.sims)
    number_survived = 0
    overhealing_list = []
    for _ in range(number_simulations):
        survived, overhealing_percent = run_simulation()
        overhealing_list.append(overhealing_percent)
        if survived:
            number_survived += 1

    print('Number of times tank survived: {} ({}%)'.format(number_survived, number_survived / number_simulations * 100))
    print('Overhealing percent: {:.2f}%'.format(statistics.median(overhealing_list) * 100))