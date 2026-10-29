"""Reconcile recorded proof generation and local EVM verifier transactions."""
from pathlib import Path
import json,hashlib,csv,statistics,collections

ROOT=Path(__file__).resolve().parent
RESULTS=ROOT/'results'

def quantiles(values):
    q=statistics.quantiles(values,n=4,method='inclusive')
    return {'n':len(values),'median':statistics.median(values),'min':min(values),'q1':q[0],'q3':q[2],'max':max(values)}

def main():
    proof_runs=[json.loads((RESULTS/f'proofs-run-{i}.json').read_text())for i in range(1,4)]
    evm_runs=[json.loads((RESULTS/f'evm-run-{i}.json').read_text())for i in range(1,4)]
    positive=[];controls=[];profiles={};native=[];pairs=[]
    for i,(proof,evm)in enumerate(zip(proof_runs,evm_runs),1):
        assert proof['run_id']==evm['run_id']==f'run-{i}'
        assert evm['proof_source_sha256']==hashlib.sha256((RESULTS/f'proofs-run-{i}.json').read_bytes()).hexdigest()
        assert len(proof['samples'])==50 and len(evm['verification_transactions'])==150 and len(evm['controls'])==16
        for profile in proof['profiles']:
            k=profile['k'];assert profile['public_inputs']==8*k+2
            if k in profiles:assert profiles[k]==profile
            profiles[k]=profile
        proof_index={(s['k'],s['trial']):s for s in proof['samples']}
        for s in proof['samples']:native.append({'run':i,**s})
        indexed={}
        for row in evm['verification_transactions']:
            assert row['status']==1 and row['proof_accepted']is True
            assert row['public_input_count']==8*row['k']+2
            assert row['public_input_component_bytes']==32*row['public_input_count']
            assert row['proof_component_bytes']==(128 if row['mode']=='compressed' else 256)
            data=bytes.fromhex(row['calldata'][2:]);zeros=data.count(0)
            assert len(data)==row['calldata_bytes']==4+row['proof_component_bytes']+row['public_input_component_bytes']
            assert row['intrinsic_gas']==21000+4*zeros+16*(len(data)-zeros)
            assert int(row['gas_used'])==row['intrinsic_gas']+int(row['execution_gas_excluding_intrinsic'])
            s=proof_index[(row['k'],row['trial'])]
            args=data[4:];n=row['proof_component_bytes']
            if row['mode']!='compressed':assert args[:256].hex()==s['proof_hex'][2:]
            actual_public=[str(int.from_bytes(args[j:j+32],'big'))for j in range(n,len(args),32)]
            assert actual_public==s['public_signals']
            indexed[(row['k'],row['trial'],row['mode'])]=row
            positive.append({'run':i,**row})
        for row in evm['controls']:
            assert row['proof_accepted']is False
            if row['mode']=='legacy_uncompressed':assert row['status']==1 and row['read_only_result']=='false'
            else:assert row['status']==0
            controls.append({'run':i,**row})
        for k in range(2,7):
            for trial in range(10):
                a=indexed[(k,trial,'direct_uncompressed')];b=indexed[(k,trial,'compressed')];legacy=indexed[(k,trial,'legacy_uncompressed')]
                saved_bytes=a['calldata_bytes']-b['calldata_bytes'];assert saved_bytes==128
                saved_intrinsic=a['intrinsic_gas']-b['intrinsic_gas']
                extra_execution=int(b['execution_gas_excluding_intrinsic'])-int(a['execution_gas_excluding_intrinsic'])
                gas_change=int(b['gas_used'])-int(a['gas_used'])
                assert gas_change==extra_execution-saved_intrinsic
                legacy_change=int(b['gas_used'])-int(legacy['gas_used'])
                pairs.append({'run':i,'k':k,'trial':trial,'uncompressed_calldata_bytes':a['calldata_bytes'],'compressed_calldata_bytes':b['calldata_bytes'],'saved_bytes':saved_bytes,'calldata_reduction_pct':100*saved_bytes/a['calldata_bytes'],'uncompressed_gas':int(a['gas_used']),'compressed_gas':int(b['gas_used']),'legacy_uncompressed_gas':int(legacy['gas_used']),'compression_gas_change':gas_change,'compression_gas_change_pct':100*gas_change/int(a['gas_used']),'compression_vs_legacy_gas_change':legacy_change,'compression_vs_legacy_gas_change_pct':100*legacy_change/int(legacy['gas_used']),'saved_intrinsic_gas':saved_intrinsic,'extra_execution_gas':extra_execution})
    rows=[]
    for k in range(2,7):
        a=[p for p in pairs if p['k']==k]
        costs={mode:quantiles([int(r['gas_used'])for r in positive if r['k']==k and r['mode']==mode])for mode in ['direct_uncompressed','compressed','legacy_uncompressed']}
        rows.append({'k':k,'constraints':profiles[k]['constraints'],'public_inputs':profiles[k]['public_inputs'],'uncompressed_proof_bytes':256,'compressed_proof_bytes':128,'uncompressed_calldata_bytes':a[0]['uncompressed_calldata_bytes'],'compressed_calldata_bytes':a[0]['compressed_calldata_bytes'],'calldata_reduction_pct':a[0]['calldata_reduction_pct'],'gas':costs,'paired_compression_gas_change':quantiles([p['compression_gas_change']for p in a]),'paired_compression_gas_change_pct':quantiles([p['compression_gas_change_pct']for p in a]),'paired_compression_vs_legacy_gas_change':quantiles([p['compression_vs_legacy_gas_change']for p in a]),'paired_compression_vs_legacy_gas_change_pct':quantiles([p['compression_vs_legacy_gas_change_pct']for p in a]),'proof_generation_ms_context_only':quantiles([p['prove_ns']/1e6 for p in native if p['k']==k])})
    summary={'scope':'Published Rayls Enygma verifier benchmark on a local Shanghai EVM. No mainnet fees, whole-payment gas, production latency, anonymity-strength or deployment claims.','circuit_source_commit':'be20e7fb1fcbafccbc5450d0b5900e27c2e53788','contract_source_commit':'ed8863885c8ed5d5d317d47a34c063907192687a','recorded_proofs':len(native),'additional_excluded_warmup_proofs':3*5*2,'fresh_proof_processes':3,'fresh_evm_processes':3,'verifier_deployments':sum(len(r['deployments'])for r in evm_runs),'accepted_proof_transactions':len(positive),'paired_compression_comparisons':len(pairs),'rejected_proof_controls':len(controls),'control_transaction_reverts':sum(x['status']==0 for x in controls),'control_successful_receipts_returning_false':sum(x['status']==1 for x in controls),'compression_gas_increase_pairs':sum(p['compression_gas_change']>0 for p in pairs),'compression_gas_decrease_pairs':sum(p['compression_gas_change']<0 for p in pairs),'profiles':rows}
    (RESULTS/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    with (RESULTS/'paired-comparisons.csv').open('w',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(pairs[0]));w.writeheader();w.writerows(pairs)
    table=[]
    for r in rows:table.append({'k':r['k'],'constraints':r['constraints'],'public_inputs':r['public_inputs'],'uncompressed_calldata_bytes':r['uncompressed_calldata_bytes'],'compressed_calldata_bytes':r['compressed_calldata_bytes'],'calldata_reduction_pct':r['calldata_reduction_pct'],'direct_uncompressed_median_gas':r['gas']['direct_uncompressed']['median'],'compressed_median_gas':r['gas']['compressed']['median'],'legacy_uncompressed_median_gas':r['gas']['legacy_uncompressed']['median'],'paired_compression_gas_change_median':r['paired_compression_gas_change']['median'],'paired_compression_gas_change_pct_median':r['paired_compression_gas_change_pct']['median']})
    with (RESULTS/'profile-summary.csv').open('w',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    print(json.dumps({k:v for k,v in summary.items()if k!='profiles'},indent=2));print(json.dumps(table,indent=2))

if __name__=='__main__':main()
