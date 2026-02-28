import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from backfill_pickers import _picker_for


def test_first_three_picks_skip_jack():
    assert _picker_for(1) == 'SS'
    assert _picker_for(2) == 'DG'
    assert _picker_for(3) == 'RB'


def test_fourth_pick_restarts_with_ss_not_jack():
    assert _picker_for(4) == 'SS'


def test_jack_first_appears_at_pick_7():
    assert _picker_for(5) == 'DG'
    assert _picker_for(6) == 'RB'
    assert _picker_for(7) == 'JC'


def test_full_cycle_repeats_after_first():
    # Second full cycle: picks 8–11
    assert _picker_for(8)  == 'SS'
    assert _picker_for(9)  == 'DG'
    assert _picker_for(10) == 'RB'
    assert _picker_for(11) == 'JC'
    # Third cycle: picks 12–15
    assert _picker_for(12) == 'SS'
    assert _picker_for(13) == 'DG'
    assert _picker_for(14) == 'RB'
    assert _picker_for(15) == 'JC'
