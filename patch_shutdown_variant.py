"""Diagnostic only: bound lifecycle calls to two seconds, not a production fix.
PR 5438's additions already exist in 1.3.13; this is a separate experiment.
"""
from pathlib import Path
import sys
path=Path(sys.argv[1])/'nav2_lifecycle_manager/src/lifecycle_manager.cpp'
text=path.read_text()
old='node_map_[node_name]->change_state(transition)'
new='node_map_[node_name]->change_state(transition, std::chrono::seconds(2))'
if new not in text:
    assert text.count(old)==1
    path.write_text(text.replace(old,new))
