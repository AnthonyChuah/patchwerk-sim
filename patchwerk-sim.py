# original simulation written by https://github.com/tangbj and refactored by https://github.com/AnthonyChuah
# the multiple-OT and highest-hp target selection logic

# hateful strikes deal between 22-29k damage every 1.2s
# this simulation will only consider how many times a healing team of 3 will let an offtank die
# patchwerk will enrage during the last 5%, but we ignore that since tanks will save shield wall
# does not take into account batching

import sys

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

class Tank:
    def __init__(self, name, max_health=11000, dodge_parry=0.3, mitigation=0.7):
        self.name = name
        self.max_health = max_health
        self.dodge_parry = dodge_parry
        self.mitigation = mitigation
        self.current_health = self.max_health

    def reset(self):
        self.current_health = self.max_health

    # returns True if tank dies, False otherwise
    def get_smashed(self):
        # check for misses
        if random.random() < self.dodge_parry:
            # print("Hateful Strike MISSES {}".format(self.name))
            return False

        dmg = self.get_damage()
        # print("Hateful Strike hits {} ({} hp) for {} dmg".format(self.name, self.current_health, dmg))
        self.current_health -= dmg
        if self.current_health <= 0:
            # print("{} has DIED! ({} Overkill)".format(self.name, -self.current_health))
            return True
        return False

    def get_damage(self):
        damage = random.random() * (29000 - 22000) + 22000
        damage *= (1 - self.mitigation)
        return round(damage)

    # returns a tuple with total raw healing and overhealing
    def get_healed(self, heal_qty):
        # print("{} ({} hp) is healed for {}".format(self.name, self.current_health, heal_qty))
        self.current_health += heal_qty
        overhealing = 0
        if self.current_health > self.max_health:
            overhealing = self.current_health - self.max_health
            self.current_health = self.max_health

        return (heal_qty, overhealing)

    def __str__(self):
        return self.name

# updated hateful strike to hit every 1.2s instead of random number from 1.2 to 2s
def get_timetonext_hateful():
    return 1.2

# returns a tuple of (tank_to_be_hit_next, tank_index)
def get_hateful_target(tanks):
    highest_health_tank_index = -1
    highest_health_tank = -999

    for index, tank in enumerate(tanks):
        if tank.current_health > highest_health_tank:
            highest_health_tank = tank.current_health
            highest_health_tank_index = index

    return tanks[highest_health_tank_index], highest_health_tank_index

# tank 0 is healed by healers [1, 2, 3], tank 1 by healers [4, 5, 6], tank 2 by healers [7, 8, 9]
def get_heal_target(healer_idx):
    return (healer_idx + 2) // 3 - 1

def run_simulation(tanks_list):
    # each time we run a simulation, we should reset the state of each tank
    for tank in tanks_list:
        tank.reset()

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

    elapsed = 0
    heapq.heapify(event_heap)
    while True:
        next_event = heapq.heappop(event_heap)
        elapsed = next_event._time
        if elapsed >= FIGHT_LENGTH:
            break
        # print("{} {}".format(tanks_health, next_event))
        if next_event.is_hateful():
            tank, target_idx = get_hateful_target(tanks_list)
            death = tank.get_smashed()

            if death:
                break
            delay = get_timetonext_hateful()
            heapq.heappush(event_heap, Event(PATCHWERK, round(elapsed + delay, 1)))
        else:
            healer_idx = next_event._entity
            target_idx = get_heal_target(healer_idx)
            heal_amount, _, cast_time = get_heal('h4')
            raw_healing, overhealing = tanks_list[target_idx].get_healed(heal_amount)
            total_raw_healing += raw_healing
            total_overhealing += overhealing
            human_delay = round(REACTION_TIME * random.random(), 1)
            heapq.heappush(event_heap, Event(healer_idx, round(elapsed + cast_time + human_delay, 1)))

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
    
    tanks = [
        Tank(name='Bearly', max_health=13000, dodge_parry=0.25, mitigation=0.75),
        Tank(name='Zug Zug', max_health=9500, dodge_parry=0.35, mitigation=0.725),
        Tank(name='CTS', max_health=9500, dodge_parry=0.35, mitigation=0.725),
    ]

    for _ in range(number_simulations):
        survived, overhealing_percent = run_simulation(tanks)
        overhealing_list.append(overhealing_percent)
        if survived:
            number_survived += 1
    
    print('\nNumber of times tank survived: {} ({}%)'.format(number_survived, number_survived / number_simulations * 100))
    print('Overhealing percent: {:.2f}%'.format(statistics.median(overhealing_list) * 100))
