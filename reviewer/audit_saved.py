"""Read-only audit of the preserved benchmark and the review's actual local replay.

Python standard library only. This verifies recorded identities, ABI field
bindings, receipt reconciliation, paired gas and repetition coverage. It is not
itself a Groth16 pairing implementation: cryptographic execution is rerun by
the supplied Go and Solidity harnesses.
"""
from pathlib import Path
import copy,hashlib,json,re,statistics

ROOT=Path(__file__).resolve().parents[1]
MODES={'direct_uncompressed':('verifyProofInternal',256),
       'compressed':('verifyCompressedProof',128),'legacy_uncompressed':('verifyProof',256)}

def require(value,message):
    if not value: raise ValueError(message)

def load(p):return json.loads((ROOT/p).read_text())

def verify_run(proofs,old,replay):
    require(len(proofs['samples'])==50,'proof count')
    expected={(k,t,m) for k in range(2,7) for t in range(10) for m in MODES}
    old_rows={(x['k'],x['trial'],x['mode']):x for x in old['verification_transactions']}
    new_rows={(x['k'],x['trial'],x['mode']):x for x in replay['verification_transactions']}
    require(len(old_rows)==len(old['verification_transactions'])==150,'duplicate/missing original row')
    require(len(new_rows)==len(replay['verification_transactions'])==150,'duplicate/missing replay row')
    require(set(old_rows)==set(new_rows)==expected,'profile/trial/mode coverage')
    index={(s['k'],s['trial']):s for s in proofs['samples']}
    require(len(index)==50,'duplicate proof identity')
    require(replay['reviewer_observed_client']=='anvil/v1.3.1','observed client')
    require(int(replay['reviewer_observed_chain'],16)==31337,'observed chain')
    addresses={d['k']:d['address'].lower() for d in replay['deployments']}
    require(len(addresses)==len(replay['deployments'])==5 and set(addresses)==set(range(2,7)),'deployment coverage')
    selectors=load('supplemental/abi-selectors.json')
    for d in replay['deployments']:
        code=bytes.fromhex(d['observed_runtime_bytecode'][2:])
        require(hashlib.sha256(code).hexdigest()==d['runtime_bytecode_sha256'],'runtime hash')
        prior=next(x for x in old['deployments'] if x['k']==d['k'])
        require(prior['runtime_bytecode_sha256']==d['runtime_bytecode_sha256'],'recompiled runtime identity')
    for key,row in new_rows.items():
        original=old_rows[key];sample=index[key[:2]];name,size=MODES[key[2]]
        require(row['function']==name,'route/function binding')
        require(row['status']==1 and row['proof_accepted'] is True,'valid proof result')
        require(row['read_only_result']==('true' if key[2]=='legacy_uncompressed' else 'returned without revert'),'read-only acceptance')
        for field in ['calldata','gas_used','intrinsic_gas','execution_gas_excluding_intrinsic','function','read_only_result','proof_accepted','status']:
            require(row[field]==original[field],'original/replay mismatch: '+field)
        data=bytes.fromhex(row['calldata'][2:]);args=data[4:]
        require(row['calldata'][:10]==selectors[str(key[0])][name]['selector'],'ABI selector binding')
        require(len(data)==4+size+32*(8*key[0]+2),'complete calldata length')
        require(len(data)==row['calldata_bytes'],'reported calldata length')
        require(data.count(0)==row['calldata_zero_bytes'],'zero-byte count')
        require(len(data)-data.count(0)==row['calldata_nonzero_bytes'],'nonzero-byte count')
        intrinsic=21000+4*data.count(0)+16*(len(data)-data.count(0))
        require(intrinsic==row['intrinsic_gas'],'intrinsic gas')
        require(int(row['gas_used'])-intrinsic==int(row['execution_gas_excluding_intrinsic']),'gas decomposition')
        if key[2]!='compressed':require(args[:256].hex()==sample['proof_hex'][2:],'proof-byte binding')
        else:
            compressed=[int.from_bytes(args[i:i+32],'big') for i in range(0,128,32)]
            require(compressed==list(map(int,row['compressed_words'])),'compressed-word binding')
        signals=[str(int.from_bytes(args[i:i+32],'big')) for i in range(size,len(args),32)]
        require(signals==sample['public_signals'],'public-input binding')
        receipt,tx=row['raw_receipt'],row['raw_transaction']
        require(receipt['transactionHash']==tx['hash']==row['transaction_hash'],'transaction identity')
        require(int(receipt['status'],16)==row['status'],'raw receipt status')
        require(int(receipt['gasUsed'],16)==int(row['gas_used']),'raw receipt gas')
        require(tx['input']==row['calldata'],'raw transaction input')
        require(tx['to'].lower()==addresses[key[0]],'deployed recipient')
        require(receipt['to'].lower()==tx['to'].lower(),'receipt recipient')
        require(receipt['blockHash']==tx['blockHash'] and receipt['blockNumber']==tx['blockNumber'],'receipt block binding')
        require(int(tx['chainId'],16)==31337,'raw transaction chain')
    require(len(old['controls'])==len(replay['controls'])==16,'control count')
    expected_controls={(k,'altered public input with original proof',m) for k in range(2,7) for m in MODES}|{(2,'public input equal to scalar-field modulus','direct_uncompressed')}
    require({(x['k'],x['control'],x['mode'])for x in replay['controls']}==expected_controls,'negative control coverage')
    for a,b in zip(old['controls'],replay['controls']):
        require(b['proof_accepted'] is False,'control acceptance flag')
        require(a['calldata']==b['calldata'] and a['gas_used']==b['gas_used'],'control replay match')
        require(b['status']==(1 if b['mode']=='legacy_uncompressed' else 0),'control receipt outcome')
        require(int(b['raw_receipt']['status'],16)==b['status'],'control raw receipt')
        require(b['raw_transaction']['input']==b['calldata'],'control raw calldata')
        require(int(b['raw_receipt']['gasUsed'],16)==int(b['gas_used']),'control raw gas')
        require(b['raw_receipt']['transactionHash']==b['raw_transaction']['hash']==b['transaction_hash'],'control transaction identity')
        require(b['raw_receipt']['to'].lower()==b['raw_transaction']['to'].lower()==addresses[b['k']],'control recipient')
        require(b['raw_receipt']['blockHash']==b['raw_transaction']['blockHash'] and b['raw_receipt']['blockNumber']==b['raw_transaction']['blockNumber'],'control block binding')
        name=MODES[b['mode']][0]
        require(b['calldata'][:10]==selectors[str(b['k'])][name]['selector'],'control ABI selector')
        expected_error=None if b['mode']=='legacy_uncompressed' else 'PublicInputNotInField' if b['control']=='public input equal to scalar-field modulus' else 'ProofInvalid'
        require(a['decoded_error']==b['decoded_error']==expected_error,'control decoded error')
        if b['mode']=='legacy_uncompressed':require(b['read_only_result']=='false','false-return control')
    pairs=[]
    for k in range(2,7):
        for trial in range(10):
            a,b=(new_rows[k,trial,m] for m in ['direct_uncompressed','compressed'])
            delta=int(b['gas_used'])-int(a['gas_used'])
            saved=a['intrinsic_gas']-b['intrinsic_gas']
            extra=int(b['execution_gas_excluding_intrinsic'])-int(a['execution_gas_excluding_intrinsic'])
            require(delta==extra-saved and delta>0,'paired gas direction or reconciliation')
            pairs.append({'k':k,'delta':delta,'pct':100*delta/int(a['gas_used'])})
    return pairs

def main():
    manifest=(ROOT/'original/SHA256SUMS.txt').read_text().splitlines()
    for line in manifest:
        expected,name=line.split(maxsplit=1);name=name.lstrip('*');path=ROOT/'original'/name
        require(hashlib.sha256(path.read_bytes()).hexdigest()==expected,'original file integrity: '+name)
    all_pairs=[]; datasets=[]
    for run in range(1,4):
        proofs=load(f'original/results/proofs-run-{run}.json')
        old=load(f'original/results/evm-run-{run}.json')
        replay=load(f'reviewer/evm-run-{run}.json')
        require(hashlib.sha256((ROOT/f'original/results/proofs-run-{run}.json').read_bytes()).hexdigest()==old['proof_source_sha256']==replay['proof_source_sha256'],'proof report identity')
        all_pairs+=verify_run(proofs,old,replay);datasets.append((proofs,old,replay))
    summary=load('original/results/summary.json')
    for p in summary['profiles']:
        require(statistics.median(x['pct'] for x in all_pairs if x['k']==p['k'])==p['paired_compression_gas_change_pct']['median'],'median paired percentage')
    mutants=[]
    for label,mutate in [
        ('receipt gas changed',lambda d:d['verification_transactions'][0]['raw_receipt'].__setitem__('gasUsed','0x1')),
        ('public input changed',lambda d:d['verification_transactions'][0].__setitem__('calldata',d['verification_transactions'][0]['calldata'][:-2]+'ff')),
        ('route relabelled',lambda d:d['verification_transactions'][0].__setitem__('function','verifyProof')),
        ('control incorrectly marked accepted',lambda d:d['controls'][0].__setitem__('proof_accepted',True)),
    ]:
        p,o,r=datasets[0];modified=copy.deepcopy(r);mutate(modified)
        try:verify_run(p,o,modified)
        except (ValueError,KeyError):mutants.append({'test':label,'rejected':True})
        else:raise ValueError('Audit mutation was not detected: '+label)
    new=load('reviewer/regenerated-proofs.json')
    require(len(new['samples'])==50 and len(new['profiles'])==5,'regenerated proof coverage')
    for p in new['profiles']:
        old=next(x for x in load('original/results/proofs-run-1.json')['profiles'] if x['k']==p['k'])
        require(p==old,'regenerated circuit profile')
    result={'status':'passed','original_manifest_files':len(manifest),'replayed_valid_transactions':450,
            'replayed_rejection_controls':48,'paired_gas_results_exactly_reproduced':150,
            'regenerated_proofs_in_native_check':50,'local_audit_mutations':mutants,
            'limit':'Saved-data bindings and a recorded local replay; not mainnet, ceremony replay, live transport or independent validation of every original receipt.'}
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
