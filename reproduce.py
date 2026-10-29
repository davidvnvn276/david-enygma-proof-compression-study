"""Preserving reproduction of local verifier transactions or native proof generation.

The saved-data audit is always run first. Requested execution happens in a new
output directory, leaving the delivered original/ observations unchanged.
"""
import argparse,datetime,importlib.util,json,os,shutil,socket,subprocess,sys,tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True

def run(command,cwd,env,log):
    print('Running',Path(str(command[0])).name,*map(str,command[1:3]),flush=True)
    with log.open('w') as f:
        p=subprocess.run(list(map(str,command)),cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
    if p.returncode:raise RuntimeError(f'Command failed ({p.returncode}); inspect {log}')

def main():
    if not __debug__:raise SystemExit('Run without -O: the original analyzer uses assertions.')
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--evm',action='store_true');ap.add_argument('--native',action='store_true')
    ap.add_argument('--anvil');ap.add_argument('--go');ap.add_argument('--output')
    a=ap.parse_args()
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=Path(a.output).resolve() if a.output else ROOT/'runs'/stamp
    if out==ROOT or out.is_relative_to(ROOT/'original') or out.is_relative_to(ROOT/'reviewer'):
        raise SystemExit('Output must be separate from the preserved evidence.')
    out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ)
    results={'scope':'Local reproduction; no live Rayls transactions or end-to-end payment execution.','steps':[]}
    run([sys.executable,ROOT/'verify_integrity.py'],ROOT,env,out/'integrity.log')
    run([sys.executable,ROOT/'reviewer/audit_saved.py'],ROOT,env,out/'saved-audit.log')
    results['steps'].append({'name':'saved_audit','passed':True})
    if a.evm:
        if not a.anvil:raise SystemExit('Supply --anvil with the Anvil 1.3.1 executable path.')
        anvil=Path(a.anvil).expanduser().resolve()
        version=subprocess.check_output([str(anvil),'--version'],text=True)
        if '1.3.1' not in version:raise SystemExit('This fixed benchmark expects Anvil 1.3.1.')
        for port in (18546,18547,18548):
            with socket.socket() as s:
                if s.connect_ex(('127.0.0.1',port))==0:raise SystemExit(f'Local port {port} is already in use.')
        study=out/'evm-study';shutil.copytree(ROOT/'original',study)
        harness=study/'evm-harness'
        shutil.copyfile(ROOT/'reviewer/evm-recheck.mjs',harness/'reviewer-run.mjs')
        npm=shutil.which('npm.cmd' if os.name=='nt' else 'npm')
        node=shutil.which('node')
        if not npm or not node:raise SystemExit('Install the recorded Node.js toolchain before this stage.')
        run([npm,'ci','--ignore-scripts','--no-audit','--no-fund'],harness,env,out/'npm-install.log')
        evm_env=dict(env,DAVID_STUDY_ROOT=str(study),DAVID_ANVIL_PATH=str(anvil))
        run([node,'reviewer-run.mjs'],harness,evm_env,out/'evm-replay.log')
        run([sys.executable,study/'analyze.py'],study,env,out/'replayed-analysis.log')
        spec=importlib.util.spec_from_file_location('review_audit',ROOT/'reviewer/audit_saved.py')
        audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
        comparisons=[]
        for i in range(1,4):
            p=json.loads((ROOT/f'original/results/proofs-run-{i}.json').read_text())
            old=json.loads((ROOT/f'original/results/evm-run-{i}.json').read_text())
            fresh=json.loads((study/f'results/evm-run-{i}.json').read_text())
            comparisons+=audit.verify_run(p,old,fresh)
        results['steps'].append({'name':'fresh_evm_replay','passed':True,'paired_gas_matches':len(comparisons),'accepted_verification_transactions':450,'rejection_controls':48,'anvil_version':version.strip()})
    if a.native:
        go=a.go or shutil.which('go')
        if not go:raise SystemExit('Supply --go with the Go 1.26.2 executable path.')
        go=Path(go).expanduser().resolve()
        version=subprocess.check_output([str(go),'version'],text=True)
        if 'go1.26.2' not in version:raise SystemExit('This pinned source expects Go 1.26.2.')
        dest=out/'gnark-source';dest.mkdir()
        with tarfile.open(ROOT/'reviewer/pinned-gnark-source.tar.gz') as t:t.extractall(dest,filter='data')
        checkout=next(dest.iterdir())
        for p in (ROOT/'original/published-artifacts').rglob('*'):
            if p.is_file():
                target=checkout/'last_build'/p.relative_to(ROOT/'original/published-artifacts')
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
        study=checkout/'pkg/circuits/enygma/enygma-payments/david-cost-study';study.mkdir(exist_ok=True)
        shutil.copyfile(ROOT/'original/cost_test.go',study/'cost_test.go')
        output=out/'regenerated-proofs.json'
        native_env=dict(env,DAVID_GNARK_ROOT=str(checkout),DAVID_COST_RUN_ID='review-regeneration',DAVID_COST_OUTPUT=str(output))
        run([go,'test','-count=1','-timeout=10m','-v','./pkg/circuits/enygma/enygma-payments/david-cost-study'],checkout,native_env,out/'native-generation.log')
        data=json.loads(output.read_text())
        if len(data['samples'])!=50:raise RuntimeError('Unexpected regenerated proof count')
        results['steps'].append({'name':'native_regeneration','passed':True,'recorded_proofs':50,'profiles':5,'go_version':version.strip(),'limit':'Not added to the original 150-pair statistics.'})
    results['status']='passed'
    (out/'reproduction-summary.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))
    print('Output:',out)

if __name__=='__main__':main()
