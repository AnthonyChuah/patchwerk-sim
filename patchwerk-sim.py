# original simulation written by https://github.com/tangbj and refactored by https://github.com/AnthonyChuah
# the multiple-OT and highest-hp target selection logic

# hateful strikes deal between 22-29k damage every 1.2s
# this simulation will only consider how many times a healing team of 3 will let an offtank die
# patchwerk will enrage during the last 5%, but we ignore that since tanks will save shield wall
# does not take into account batching

FIGHT_LENGTH = 60 * 4
AVERAGE_MITIGATION = 0.7
PATCHWERK_MISS_CHANCE = 0.3
AVERAGE_PLUS_HEAL = 1060
AMPLIFY_MAGIC = True
MAGIC_ATTUNEMENT = True

# HOLY TALENTS
POINTS_IN_IMPROVED_HEALING = 3
POINTS_IN_SPIRITUAL_HEALING = 5
POINTS_IN_SPIRITUAL_GUIDANCE = 5

# assume there is some sort of variance between casts
REACTION_TIME = 0.2
HEALER_CRIT_CHANCE = 0.13

# assume rough spirit score of 350
TOTAL_PLUS_HEAL = AVERAGE_PLUS_HEAL + (150 if AMPLIFY_MAGIC else 0) + (75 if MAGIC_ATTUNEMENT else 0) + \
    (350 * 0.25 * POINTS_IN_SPIRITUAL_GUIDANCE / 5)

import math
import argparse
import heapq
import statistics
import random
import numpy


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
    def __init__(self, name, max_health=11000, dodge_parry=0.3, mitigation=0.7, use_health_stone_when_critical=False):
        self.name = name
        self.max_health = max_health
        self.dodge_parry = dodge_parry
        self.mitigation = mitigation
        self.use_health_stone_when_critical = use_health_stone_when_critical
        self.reset()

    def reset(self):
        self.current_health = self.max_health
        # tracks when we last used healthstone to determine if on CD
        self._last_used_healthstone = -999

    # takes a tick argument, which is the time when tank takes damage
    # returns a tuple (does_tank_die, damage_taken)
    # returns True if tank dies, False otherwise
    def get_smashed(self, tick):
        # check for misses
        if random.random() < self.dodge_parry:
            # print("Hateful Strike MISSES {}".format(self.name))
            return (False, 0)

        dmg = self.get_damage()
        # print("Hateful Strike hits {} ({} hp) for {} dmg".format(self.name, self.current_health, dmg))
        self.current_health -= dmg
        if self.current_health <= 0:
            # print("{} has DIED! ({} Overkill)".format(self.name, -self.current_health))
            return (True, dmg)

        # if self.use_health_stone_when_critical and \
        #         self.current_health / self.max_health <= 0.2 and tick - self._last_used_healthstone >= 120:
        #     self.get_healed(1440) 
        #     self._last_used_healthstone = tick
            # print('{} used healthstone at {}s'.format(self.name, tick))

        return (False, dmg)

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
        return '{} ({} / {})'.format(self.name, self.current_health, self.max_health)

# tuple is average base healing and unmodified healing cost and cast time
healing_spell_data = {
    'h2': (476, 205, 2.5),
    'h3': (624, 255, 2.5),
    'h4': (779.5, 305, 2.5),
    'gh1': (981.5, 370, 2.5),
}

class Healer:
    def __init__(self, entity, main_heal_used, assigned_tank_id):
        self.entity = entity
        self.name = 'Healer #{}'.format(entity)
        self.main_heal_used = main_heal_used
        self.assigned_tank_id = assigned_tank_id
        self.cast_time = healing_spell_data[self.main_heal_used][2]

    def _get_heal_amount(self):
        base_healing, mana_cost, cast_time = healing_spell_data.get(self.main_heal_used)
        mana_cost *= (1 - 0.05 * POINTS_IN_IMPROVED_HEALING)
        # spirutal healing adds max of 10% to base heal
        base_healing *= (1 + POINTS_IN_SPIRITUAL_HEALING / 5 * 0.1)
        total_healing = base_healing + 3 / 3.5 * TOTAL_PLUS_HEAL
        if random.random() <= HEALER_CRIT_CHANCE:
            total_healing *= 1.5
        return total_healing, mana_cost, cast_time

    def get_heal(self):
        heal_amount, _, cast_time = self._get_heal_amount()
        return (heal_amount, cast_time, self.assigned_tank_id)

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

def run_simulation(tanks_list, healers_dict):
    # each time we run a simulation, we should reset the state of each tank
    for tank in tanks_list:
        tank.reset()

    # tracks the total damage taken by each tank
    damage_taken = [0, 0, 0]
    amount_of_hateful_strikes = [0, 0, 0]

    PATCHWERK = 0
    event_heap = []
    heapq.heappush(event_heap, Event(PATCHWERK, 0))
    with open('logs.txt', 'a') as f:
        # print("Patchwerk first Hateful Strike scheduled to land at 0 seconds")
        for healer in healers_dict.values():
            start = round(random.random() * healer.cast_time, 1)
            # f.write("{} randomly scheduled to land first heal at {} seconds\n".format(healer.name, start))
            heapq.heappush(event_heap, Event(healer.entity, start))

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

            f.write("{}\n".format(next_event))
            if next_event.is_hateful():
                tank, target_idx = get_hateful_target(tanks_list)
                # f.write('SELECTING HATEFUL STRIKE TARGET\n')
                # f.write('{}\n'.format([str(tank) for tank in tanks_list]))
                death, dmg = tank.get_smashed(elapsed)
                damage_taken[target_idx] += dmg
                if dmg == 0:
                    pass
                    f.write('Patchwerk attacks {} at {}s and misses'.format(tank.name, elapsed))
                else:
                    pass
                    f.write("Patchwerk hits {} at {}s for {}\n".format(tank.name, \
                        elapsed, math.ceil(dmg)))
                amount_of_hateful_strikes[target_idx] += 1

                if death:
                    break
                delay = get_timetonext_hateful()
                heapq.heappush(event_heap, Event(PATCHWERK, round(elapsed + delay, 1)))
            else:
                # note that healer entities are 1-indexed while lists are 0-indexed
                healer_idx = next_event._entity
                healer = healers_dict[healer_idx]
                heal_amount, cast_time, assigned_tank_id = healer.get_heal()
                raw_healing, overhealing = tanks_list[assigned_tank_id].get_healed(heal_amount)
                f.write("{} heals {} at {}s for {} ({} overheal)\n".format(healer.name, tanks_list[assigned_tank_id].name, \
                    elapsed, math.ceil(heal_amount - overhealing), math.floor(overhealing)))

                total_raw_healing += raw_healing
                total_overhealing += overhealing
                human_delay = round(REACTION_TIME * random.random(), 1)
                heapq.heappush(event_heap, Event(healer_idx, round(elapsed + cast_time + human_delay, 1)))

        overhealing_percent = total_overhealing / total_raw_healing
        total_damage_taken = sum(damage_taken)
        total_hateful_strikes_taken = sum(amount_of_hateful_strikes)

        damage_taken_percentage = [dmg / total_damage_taken for dmg in damage_taken]
        hateful_strikes_taken_percentage = [num_hateful_strike / total_hateful_strikes_taken \
            for num_hateful_strike in amount_of_hateful_strikes]
        if elapsed >= FIGHT_LENGTH:
            f.write("Congrats! Patchwerk is dead\n")
            return (True, overhealing_percent, damage_taken_percentage, hateful_strikes_taken_percentage)
        else:
            f.write("TANK DIES; WHY NO HEALS NOOBS\n")
            return (False, overhealing_percent, damage_taken_percentage, hateful_strikes_taken_percentage)

        f.write('\n\n\n')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sims", required=True)
    args = parser.parse_args()
    number_simulations = int(args.sims)
    number_survived = 0
    overhealing_list = []
    damage_taken_percentages_list = []
    hateful_strikes_taken_percentages_list = []
    
    tanks = [
        Tank(name='Bearly', max_health=11000, dodge_parry=0.25, mitigation=0.75),
        Tank(name='Zug Zug', max_health=9498, dodge_parry=0.35, mitigation=0.7),
        Tank(name='CTS', max_health=9499, dodge_parry=0.35, mitigation=0.7),
    ]

    # creates healers
    # we use a dict as healer entities start with 1 rather than 0
    # minimises confusions
    healers = {}

    # # 12 healer set up
    # for healer_idx in range(1, 10):
    #     assigned_tank_id = (healer_idx + 2) // 3 - 1
    #     # test having different heals for different healers
    #     # main_heal = 'h3'if healer_idx > 3 else 'gh1'
    #     main_heal = 'h4'
    #     healers[healer_idx] = Healer(entity=healer_idx, main_heal_used=main_heal, assigned_tank_id=assigned_tank_id)

    # 13 healer set up
    for healer_idx in range(1, 11):
        if healer_idx <= 4:
            assigned_tank_id = 0
        elif healer_idx <= 8:
            assigned_tank_id = 1
        else:
            assigned_tank_id = 2
        # test having different heals for different healers
        main_heal = 'h2'if healer_idx > 4 else 'h4'
        # main_heal = 'h3'
        healers[healer_idx] = Healer(entity=healer_idx, main_heal_used=main_heal, assigned_tank_id=assigned_tank_id)


    for _ in range(number_simulations):
        survived, overhealing_percent, damage_taken_percentage, hateful_strikes_taken_percentages_list = run_simulation(tanks, healers)
        overhealing_list.append(overhealing_percent)
        damage_taken_percentages_list.append(damage_taken_percentage)
        if survived:
            number_survived += 1

    print('\nNumber of times tank survived: {} ({}%)'.format(number_survived, number_survived / number_simulations * 100))
    print('Overhealing percent: {:.2f}%'.format(statistics.median(overhealing_list) * 100))
    damage_break_down = numpy.median(damage_taken_percentages_list, axis=0)

    print('\nDAMAGE BREAKDOWN')
    for tank, percent_damage_taken in zip(tanks, damage_break_down):
        print('{}: {:.1f}%'.format(tank, percent_damage_taken * 100))

    print('\nNUMBER HATEFUL STRIKES BREAKDOWN')
    for tank, percent_hateful_strike_taken in zip(tanks, hateful_strikes_taken_percentages_list):
        print('{}: {:.1f}%'.format(tank, percent_hateful_strike_taken * 100))

