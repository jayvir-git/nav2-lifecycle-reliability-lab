"""Alternate unchanged baseline/candidate full experiments; retain every outcome."""
import argparse
import json
from pathlib import Path
import subprocess
import time

parser=argparse.ArgumentParser()
parser.add_argument('--pairs',type=int,default=3)
parser.add_argument('--candidate',choices=['shutdown-cancellation','shutdown-coordinated'],default='shutdown-cancellation')
args=parser.parse_args()
if not 1 <= args.pairs <= 20: parser.error('pairs must be between 1 and 20')
root=Path(__file__).resolve().parent
target=root/'results'/('reliability-'+str(time.time_ns())+'.json')
report={'pairs_requested':args.pairs,'candidate':args.candidate,'order':'baseline then candidate, serially, no middleware changes','runs':[]}
for pair in range(args.pairs):
    for variant in ('baseline',args.candidate):
        before=set((root/'results').glob('failure-experiment-*.json'))
        run=subprocess.run(['bash',str(root/'run_cancellation_experiment.sh'),variant],timeout=650)
        created=set((root/'results').glob('failure-experiment-*.json'))-before
        if len(created)!=1: raise RuntimeError('Cannot identify unique combined report')
        path=created.pop()
        evidence=json.loads(path.read_text())
        warnings=[]
        resources=[]
        for phase in evidence['runs']:
            lines=(root/'results'/phase['run']/'launch.log').read_text().splitlines()
            warnings.extend({'run':phase['run'],'message':line} for line in lines if 'failed to send response' in line)
            resources.append({'run':phase['run'],**json.loads((root/'results'/phase['run']/'resources.json').read_text())})
        report['runs'].append({'pair':pair+1,'variant':variant,'exit_code':run.returncode,
            'evidence_file':path.name,'result':evidence,'response_delivery_warnings':warnings,'resources':resources})
        target.write_text(json.dumps(report,indent=2))
        print('REPEAT',pair+1,variant,'success',evidence['success'],'response warnings',len(warnings),flush=True)
print(target,flush=True)
