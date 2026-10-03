"""Export the actual isolated candidate source diff for local review."""
import difflib
from pathlib import Path

root=Path(__file__).resolve().parent
base=Path('/home/learner/nav2-shutdown-build')
old=base/'baseline/src/navigation2-1.3.13'
new=base/'shutdown-cancellation/src/navigation2-1.3.13'
parts=[]
for relative in ['nav2_lifecycle_manager/include/nav2_lifecycle_manager/lifecycle_manager.hpp',
                 'nav2_lifecycle_manager/src/lifecycle_manager.cpp']:
    parts.extend(difflib.unified_diff((old/relative).read_text().splitlines(True),
        (new/relative).read_text().splitlines(True),fromfile='a/'+relative,tofile='b/'+relative))
relative='nav2_lifecycle_manager/include/nav2_lifecycle_manager/shutdown_lifecycle_client.hpp'
parts.extend(difflib.unified_diff([],(new/relative).read_text().splitlines(True),
    fromfile='/dev/null',tofile='b/'+relative))
(root/'docs/cancellation-prototype.patch').write_text(''.join(parts))
