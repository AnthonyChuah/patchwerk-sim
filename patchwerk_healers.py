# NOTE: for priests, add the additional healing from spirtual guidance directly to plus heal

# healer_id : [heal_used, tank_id, +heal, class]
# priest: h4, shaman: h2, druid: ?
# in reality we may be running 10 healers, with 1 druid "floating"
# we could simulate it as a "boost" to the healing powers of the other healers

# risky scenario: only 9 healers instead of 10
# INFO | Number of times tanks survived: 958 (95.8%) | patchwerk-sim.py:271 <module>()
# INFO | ==== NUMBER HATEFUL STRIKES BREAKDOWN ==== | patchwerk-sim.py:279 <module>()
# INFO | Doodoobear (7665.200000000001 / 11000): 46.5% | patchwerk-sim.py:281 <module>()
# INFO | Cowchoppar (9900 / 9900): 37.0% | patchwerk-sim.py:281 <module>()
# INFO | LubbyLubba (9500 / 9500): 16.5% | patchwerk-sim.py:281 <module>()

heals_config = [
    ['h4', 0, 1160, 'priest'],
    ['h4', 0, 1160, 'priest'],
    ['h4', 0, 1160, 'priest'],
    ['ht4', 0, 1030, 'druid'],
    ['h2', 1, 1160, 'priest'],
    ['h2', 1, 1160, 'priest'],
    ['ht4', 1, 1030, 'druid'],
    ['h2', 2, 1160, 'priest'],
    ['h2', 2, 1160, 'priest'],
    ['h2', 2, 1160, 'priest'],
]


# floating biased druid scenario: 10 healers, with 1 druid spot-healing either OT#2 or OT#3
# Number of times tanks survived: 1000 (100.0%) | patchwerk-sim.py:271 <module>()
# INFO | ==== NUMBER HATEFUL STRIKES BREAKDOWN ==== | patchwerk-sim.py:279 <module>()
# INFO | Doodoobear (6471.475 / 11000): 45.5% | patchwerk-sim.py:281 <module>()
# INFO | Cowchoppar (9900 / 9900): 37.5% | patchwerk-sim.py:281 <module>()
# INFO | LubbyLubba (7998.357142857143 / 9500): 17.0% | patchwerk-sim.py:281 <module>()
"""
heals_config = [
    ['h4', 0, 1000, 'priest'],
    ['h2', 0, 1000, 'shaman'],
    ['h2', 0, 1000, 'shaman'],
    ['h4', 1, 1250, 'priest'],
    ['h2', 1, 1250, 'shaman'],
    ['h2', 1, 1250, 'shaman'],
    ['h4', 2, 1250, 'priest'],
    ['h4', 2, 1250, 'priest'],
    ['h2', 2, 1250, 'shaman'],
]
"""

# floating fair druid scenario: 10 healers, with 1 druid spot-healing any of the 3 OTs
# INFO | Number of times tanks survived: 1000 (100.0%) | patchwerk-sim.py:271 <module>()
# INFO | ==== NUMBER HATEFUL STRIKES BREAKDOWN ==== | patchwerk-sim.py:279 <module>()
# INFO | Doodoobear (11000 / 11000): 50.0% | patchwerk-sim.py:281 <module>()
# INFO | Cowchoppar (9900 / 9900): 32.5% | patchwerk-sim.py:281 <module>()
# INFO | LubbyLubba (9500 / 9500): 17.5% | patchwerk-sim.py:281 <module>()
# """
# heals_config = [
#     ['h4', 0, 1167, 'priest'],
#     ['h2', 0, 1167, 'shaman'],
#     ['h2', 0, 1167, 'shaman'],
#     ['h4', 1, 1167, 'priest'],
#     ['h2', 1, 1167, 'shaman'],
#     ['h2', 1, 1167, 'shaman'],
#     ['h4', 2, 1167, 'priest'],
#     ['h4', 2, 1167, 'priest'],
#     ['h2', 2, 1167, 'shaman'],
# ]
# """

# fat bear scenario: 10 healers, with 4 healers on the fat bear
# INFO | Number of times tanks survived: 990 (99.0%) | patchwerk-sim.py:271 <module>()
# INFO | ==== NUMBER HATEFUL STRIKES BREAKDOWN ==== | patchwerk-sim.py:279 <module>()
# INFO | Doodoobear (11000 / 11000): 56.0% | patchwerk-sim.py:281 <module>()
# INFO | Cowchoppar (9900 / 9900): 30.5% | patchwerk-sim.py:281 <module>()
# INFO | LubbyLubba (9500 / 9500): 13.5% | patchwerk-sim.py:281 <module>()
"""
heals_config = [
    ['h4', 0, 1000, 'priest'],
    ['h2', 0, 1000, 'shaman'],
    ['h2', 0, 1000, 'shaman'],
    ['h2', 0, 1000, 'druid'],
    ['h4', 1, 1000, 'priest'],
    ['h2', 1, 1000, 'shaman'],
    ['h2', 1, 1000, 'shaman'],
    ['h4', 2, 1000, 'priest'],
    ['h4', 2, 1000, 'priest'],
    ['h2', 2, 1000, 'shaman'],
]
"""
