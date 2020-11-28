#!/usr/bin/env python3

# original simulation written by https://github.com/tangbj and refactored by https://github.com/AnthonyChuah
# the multiple-OT and highest-hp target selection logic

# hateful strikes deal between 22-29k damage every 1.2s
# this simulation will only consider how many times a healing team of 3 will let an offtank die
# patchwerk will enrage during the last 5%, but we ignore that since tanks will save shield wall
# does not take into account batching

FIGHT_LENGTH = 60 * 4
AMPLIFY_MAGIC = True
MAGIC_ATTUNEMENT = True

# assume there is some sort of variance between casts
REACTION_TIME = 0.2
HEALER_CRIT_CHANCE = 0.13

import argparse
import datetime
import heapq
import logging
import logging.handlers
import math
import numpy
import random
import statistics
import sys
import os

from patchwerk_healers import heals_config

# creates logs folder if it doesn't exist

if not os.path.exists('logs'):
    os.makedirs('logs')

_filepath = 'logs/simulation_{:%Y%m%d-%H%M%S.%f}.log'.format(datetime.datetime.now())
_logformat = '%(levelname)s | %(message)s | %(filename)s:%(lineno)s %(funcName)s()'
_dateformat = '%Y%m%d-%H:%M:%S'
_fileHandler = logging.FileHandler(_filepath)
_fileHandler.setFormatter(logging.Formatter(_logformat, datefmt=_dateformat))
_consoleHandler = logging.StreamHandler(sys.stdout)
_consoleHandler.setFormatter(logging.Formatter(_logformat, datefmt=_dateformat))
_logger = logging.getLogger()
_logger.addHandler(_fileHandler)
_logger.addHandler(_consoleHandler)

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

class Tank:
    def __init__(self, name, max_health=11000, dodge_parry=0.3, mitigation=0.7, use_health_stone_when_critical=False):
        self.name = name
        self.max_health = max_health
        self.dodge_parry = dodge_parry
        self.mitigation = mitigation
        # self.use_health_stone_when_critical = use_health_stone_when_critical
        self.reset()

    def reset(self):
        self.current_health = self.max_health
        # tracks when we last used healthstone to determine if on CD
        # self._last_used_healthstone = -999

    # returns a tuple (does_tank_die, damage_taken)
    # returns True if tank dies, False otherwise
    def get_smashed(self, tick):
        # check for misses
        if random.random() < self.dodge_parry:
            logging.debug("[{:>5}s] Hateful Strike MISSES {}".format(tick, self.name))
            return (False, 0)

        dmg = self.get_damage()
        logging.debug("[{:>5}s] Hateful Strike hits {} ({} hp) for {} dmg".format(tick, self.name, self.current_health, dmg))
        self.current_health -= dmg
        if self.current_health <= 0:
            logging.debug("[{:>5}s] {} has DIED! ({} Overkill)".format(tick, self.name, -self.current_health))
            return (True, dmg)

        # xxx could simulate healthstone use
        return (False, dmg)

    def get_damage(self):
        damage = random.random() * (29000 - 22000) + 22000
        damage *= (1 - self.mitigation)
        return round(damage)

    # returns a tuple with total raw healing and overhealing
    def get_healed(self, heal_qty, tick, healer_name, is_crit):
        healing_verb = 'healed' if not is_crit else 'CRIT HEALED'
        logging.debug("[{:2f}s] {} ({} hp) is {} for {} by {}".format(tick, self.name, self.current_health, healing_verb, heal_qty, healer_name))
        self.current_health += heal_qty
        overhealing = 0
        if self.current_health > self.max_health:
            overhealing = self.current_health - self.max_health
            self.current_health = self.max_health

        return (heal_qty, overhealing)

    def __str__(self):
        return '{} ({} / {})'.format(self.name, self.current_health, self.max_health)

# tuple is average base healing and unmodified healing cost and cast time
# assume priest and shaman values are the same for now
healing_spell_data = {
    'priest': {
        'h2': (476, 205, 2.5),
        'h3': (624, 255, 2.5),
        'h4': (779.5, 305, 2.5),
        'gh1': (981.5, 370, 2.5),
    },
    'druid': {
        'ht4': (417.5, 185, 2.35),
        'ht5': (650.5, 270, 2.85),
        'ht6': (838, 335, 2.85),
        'ht7': (1050.5, 405, 2.85),
    },
    'shaman': {
        'h2': (476, 205, 2.5),
        'h3': (624, 255, 2.5),
        'h4': (779.5, 305, 2.5),
        'gh1': (981.5, 370, 2.5),
    }, 
}

def total_plus_heal(plus_heal):
    return plus_heal + (150 if AMPLIFY_MAGIC else 0) + (75 if MAGIC_ATTUNEMENT else 0)

class Healer:
    def __init__(self, idx, main_heal_used, assigned_tank_id, plus_heal, healclass):
        self.idx = idx
        self.main_heal_used = main_heal_used
        self.assigned_tank_id = assigned_tank_id
        self.plus_heal = plus_heal
        self.healclass = healclass
        self._spell_info = healing_spell_data.get(self.healclass)[self.main_heal_used]
        self.cast_time = self._spell_info[2]

    def _get_heal_amount(self):
        base_healing, mana_cost, cast_time = self._spell_info
        is_crit = False

        if self.healclass == 'druid':
            mana_cost *= 0.81
        # assume shamans and priests function similarly for now
        else:
            mana_cost *= 0.85
        
        # 10% increase to base healing talent
        if self.healclass in ['druid', 'priest']:
            base_healing *= 1.1
        
        # NOTE: Druid's HT4 and priest/shammy spells are base 3s cast time, while Druid's higher rank HT are 3.5s base cast time
        spell_coefficient = 3 / 3.5 if (self.healclass in ['priest', 'shaman'] or self.main_heal_used == 'ht4') \
            else 1
        total_healing = base_healing + spell_coefficient * total_plus_heal(self.plus_heal)

        if random.random() <= HEALER_CRIT_CHANCE:
            is_crit = True
            total_healing *= 1.5

            # for druid, criting will active nature's grace and make next spell cast faster
            if self.healclass == 'druid':
                cast_time -= 0.5

        return total_healing, mana_cost, cast_time, is_crit

    def get_heal(self):
        heal_amount, _, cast_time, is_crit = self._get_heal_amount()
        return (heal_amount, cast_time, self.assigned_tank_id, is_crit)

    def __str__(self):
        return 'Healer #{}'.format(self.idx)


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

def run_simulation(tanks_list, healers):
    for tank in tanks_list:
        tank.reset()

    # report statistics of hateful distribution amongst tanks
    damage_taken = [0, 0, 0]
    amount_of_hateful_strikes = [0, 0, 0]

    PATCHWERK = 0
    event_heap = []
    heapq.heappush(event_heap, Event(PATCHWERK, 0))

    logging.debug("Patchwerk first Hateful Strike scheduled to land at 0 seconds")
    for healer in healers:
        start = round(random.random() * healer.cast_time, 1)
        logging.debug("Healer randomly scheduled to land first heal at {} seconds".format(start))
        heapq.heappush(event_heap, Event(healer.idx + 1, start))

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

        if next_event.is_hateful():
            tank, target_idx = get_hateful_target(tanks_list)
            death, dmg = tank.get_smashed(elapsed)
            damage_taken[target_idx] += dmg
            amount_of_hateful_strikes[target_idx] += 1

            if death:
                break
            delay = get_timetonext_hateful()
            heapq.heappush(event_heap, Event(PATCHWERK, round(elapsed + delay, 1)))
        else:
            # note that healer entities are 1-indexed while lists are 0-indexed
            healer_idx = next_event._entity - 1
            healer = healers[healer_idx]
            heal_amount, cast_time, assigned_tank_id, is_crit = healer.get_heal()
            raw_healing, overhealing = tanks_list[assigned_tank_id].get_healed(heal_amount, elapsed, healer, is_crit)
            total_raw_healing += raw_healing
            total_overhealing += overhealing
            human_delay = round(REACTION_TIME * random.random(), 1)
            heapq.heappush(event_heap, Event(healer_idx + 1, round(elapsed + cast_time + human_delay, 1)))

    overhealing_percent = total_overhealing / total_raw_healing
    total_damage_taken = sum(damage_taken)
    total_hateful_strikes_taken = sum(amount_of_hateful_strikes)

    damage_taken_percentage = [dmg / total_damage_taken for dmg in damage_taken]
    hateful_strikes_taken_percentage = [num_hateful_strike / total_hateful_strikes_taken for num_hateful_strike in amount_of_hateful_strikes]
    if elapsed >= FIGHT_LENGTH:
        logging.debug("Congrats! Patchwerk is dead")
        return (True, overhealing_percent, damage_taken_percentage, hateful_strikes_taken_percentage)
    else:
        logging.debug("TANK DIES; WHY NO HEALS NOOBS")
        return (False, overhealing_percent, damage_taken_percentage, hateful_strikes_taken_percentage)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", required=False, action="store_true", help="set debug logging")
    parser.add_argument("--sims", required=True)
    args = parser.parse_args()

    if args.debug:
        _logger.setLevel(logging.DEBUG)
    else:
        _logger.setLevel(logging.INFO)
    logging.info('Log file written at path: {}'.format(_filepath))

    number_simulations = int(args.sims)
    number_survived = 0
    overhealing_list = []
    damage_taken_percentages_list = []
    hateful_strikes_taken_percentages_list = []

    tanks = [
        Tank(name='Doodoobear', max_health=11000, dodge_parry=0.25, mitigation=0.75),
        Tank(name='Cowchoppar', max_health=9900, dodge_parry=0.35, mitigation=0.725),
        Tank(name='LubbyLubba', max_health=9500, dodge_parry=0.35, mitigation=0.725),
    ]

    healers = []
    for ii in range(len(heals_config)):
        heal_config = heals_config[ii]
        healers.append(Healer(
            idx=ii,
            main_heal_used=heal_config[0],
            assigned_tank_id=heal_config[1],
            plus_heal=heal_config[2],
            healclass=heal_config[3],
        ))

    for _ in range(number_simulations):
        survived, overhealing_percent, damage_taken_percentage, hateful_strikes_taken_percentages_list = run_simulation(tanks, healers)
        overhealing_list.append(overhealing_percent)
        damage_taken_percentages_list.append(damage_taken_percentage)
        if survived:
            number_survived += 1

    logging.info('Number of times tanks survived: {} ({}%)'.format(number_survived, number_survived / number_simulations * 100))
    logging.info('Overhealing percent: {:.2f}%'.format(statistics.median(overhealing_list) * 100))
    damage_break_down = numpy.median(damage_taken_percentages_list, axis=0)

    logging.info('==== DAMAGE BREAKDOWN ====')
    for tank, percent_damage_taken in zip(tanks, damage_break_down):
        logging.info('{}: {:.1f}%'.format(tank, percent_damage_taken * 100))

    logging.info('==== NUMBER HATEFUL STRIKES BREAKDOWN ====')
    for tank, percent_hateful_strike_taken in zip(tanks, hateful_strikes_taken_percentages_list):
        logging.info('{}: {:.1f}%'.format(tank, percent_hateful_strike_taken * 100))
