"""Export the actual isolated candidate source diff for local review."""
import difflib
import sys
from pathlib import Path

root=Path(__file__).resolve().parent
base=Path('/home/learner/nav2-shutdown-build')
old=base/'baseline/src/navigation2-1.3.13'
variant=sys.argv[1] if len(sys.argv)>1 else 'shutdown-cancellation'
if variant not in ('shutdown-cancellation','shutdown-coordinated','main-coordinated'): raise SystemExit('Unknown variant')
new=base/variant/'src/navigation2-1.3.13'
if variant=='main-coordinated':
    source='navigation2-d7bf2ac06fe778c21c6141eb49b4d3e2c0c82d3a'
    old=Path('/home/learner/nav2-upstream-audit')/source
    new=base/variant/'src'/source
parts=[]
for relative in ['nav2_lifecycle_manager/include/nav2_lifecycle_manager/lifecycle_manager.hpp',
                 'nav2_lifecycle_manager/src/lifecycle_manager.cpp']:
    parts.extend(difflib.unified_diff((old/relative).read_text().splitlines(True),
        (new/relative).read_text().splitlines(True),fromfile='a/'+relative,tofile='b/'+relative))
relative='nav2_lifecycle_manager/include/nav2_lifecycle_manager/shutdown_lifecycle_client.hpp'
parts.extend(difflib.unified_diff([],(new/relative).read_text().splitlines(True),
    fromfile='/dev/null',tofile='b/'+relative))
filename='coordinated-prototype.patch' if variant=='shutdown-coordinated' else 'cancellation-prototype.patch'
if variant=='main-coordinated': filename='main-coordinated.patch'
(root/'docs'/filename).write_text(''.join(parts))
