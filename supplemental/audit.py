"""Audit the saved supplemental native-to-Solidity evidence using Python stdlib.

This binds captured records and recalculates costs. Cryptographic execution is
performed by the Go and Solidity harnesses, not by this saved-data checker.
"""
from pathlib import Path
import argparse,collections,copy,hashlib,json,statistics

ROOT=Path(__file__).resolve().parents[1]
MODES={"direct_uncompressed":("verifyProofInternal",256),
       "compressed":("verifyCompressedProof",128),
       "legacy_uncompressed":("verifyProof",256)}
CASES={"moved_sender","full_balance","all_receivers"}

def require(value,message):
    if not value:raise ValueError(message)

def integer(value):
    return int(value,16)if isinstance(value,str)and value.startswith("0x")else int(value)

def precompiles(trace):
    counts=collections.Counter();gas=collections.Counter();stack=[trace]
    while stack:
        frame=stack.pop();stack.extend(frame.get("calls",[]))
        if frame.get("to"):
            address=int(frame["to"],16)
            if 1<=address<=9:
                require(not frame.get("error"),"failed precompile in accepted trace")
                counts[address]+=1;gas[address]+=integer(frame["gasUsed"])
    return {str(k):v for k,v in sorted(counts.items())},{str(k):v for k,v in sorted(gas.items())}

def audit(native,evm,proof_bytes,selectors,baseline):
    require(native["recorded_proofs"]==len(native["samples"])==45,"native proof count")
    require(native["go_version"]=="go1.26.2"and evm["solc_version"].startswith("0.8.30+"),"recorded compiler versions")
    require(native["source_commit"]=="be20e7fb1fcbafccbc5450d0b5900e27c2e53788","circuit source pin")
    require(evm["contract_source_commit"]=="ed8863885c8ed5d5d317d47a34c063907192687a","contract source pin")
    require(hashlib.sha256(proof_bytes).hexdigest()==evm["native_proofs_sha256"],"native report identity")
    require(evm["observed_client"]=="anvil/v1.3.1"and integer(evm["observed_chain"])==31337,"observed EVM")
    require(evm["compiler_settings"]==baseline["compiler_settings"],"compiler configuration")
    require(evm["compiler_input_sha256"]==hashlib.sha256((ROOT/"original/results/solc-input.json").read_bytes()).hexdigest(),"compiler input identity")
    fixtures={(f["k"],f["id"]):f for f in native["fixtures"]}
    require(len(fixtures)==len(native["fixtures"])==15,"fixture coverage")
    for k in range(2,7):
        for case in CASES:
            f=fixtures[k,case];credits=f["recipient_units_by_position"];sender=f["sender_position"]
            require(len(credits)==k and credits[sender]==0,"recipient positions")
            require(sum(credits)==f["transfer_units"]<=f["sender_previous_units"],"conserved affordable fixture")
            if case=="moved_sender":require(sender==k-1 and f["sender_previous_units"]==1000 and credits[0]==f["transfer_units"]==1,"moved sender fixture")
            elif case=="full_balance":require(sender==0 and f["sender_previous_units"]==f["transfer_units"]==credits[k-1]==100,"full balance fixture")
            else:require(sender==0 and f["sender_previous_units"]==1000 and f["transfer_units"]==60 and all(x==60//(k-1)for x in credits[1:]),"all receiver fixture")
    profiles={p["k"]:p for p in native["profiles"]}
    require(len(profiles)==len(native["profiles"])==5,"profile coverage")
    original=json.loads((ROOT/"original/results/proofs-run-1.json").read_text())
    require(profiles=={p["k"]:p for p in original["profiles"]},"circuit identity")
    samples={(s["k"],s["case_id"],s["trial"]):s for s in native["samples"]}
    expected={(k,c,t)for k in range(2,7)for c in CASES for t in range(3)}
    require(set(samples)==expected and len(samples)==45,"sample identity coverage")
    rows={(r["k"],r["case_id"],r["trial"],r["mode"]):r for r in evm["verification_transactions"]}
    require(len(rows)==len(evm["verification_transactions"])==135,"route row uniqueness")
    require(set(rows)=={(*key,m)for key in expected for m in MODES},"all routes for all fresh proofs")
    deployments={d["k"]:d for d in evm["deployments"]}
    require(len(deployments)==len(evm["deployments"])==5,"deployment coverage")
    for k,d in deployments.items():
        code=bytes.fromhex(d["runtime_bytecode"][2:])
        require(hashlib.sha256(code).hexdigest()==d["runtime_sha256"],"runtime bytes")
        prior=next(x for x in baseline["deployments"]if x["k"]==k)
        require(d["runtime_sha256"]==prior["runtime_bytecode_sha256"],"same pinned verifier runtime")
        require(integer(d["raw_receipt"]["status"])==1 and d["raw_receipt"]["contractAddress"].lower()==d["address"].lower(),"deployment receipt")
    def binding(row):
        k,mode=row["k"],row["mode"];name,size=MODES[mode]
        require(row["function"]==name,"route/function")
        data=bytes.fromhex(row["calldata"][2:]);zero=data.count(0)
        require(row["calldata"][:10]==selectors[str(k)][name]["selector"],"ABI selector")
        require(len(data)==4+size+32*(8*k+2)==row["calldata_bytes"],"ABI size")
        require(zero==row["zero_bytes"]and len(data)-zero==row["nonzero_bytes"],"calldata byte composition")
        require(row["intrinsic_gas"]==21000+4*zero+16*(len(data)-zero),"intrinsic gas")
        require(row["gas_used"]==row["intrinsic_gas"]+row["execution_gas"],"gas decomposition")
        receipt,tx=row["raw_receipt"],row["raw_transaction"]
        require(receipt["transactionHash"]==tx["hash"]==row["transaction_hash"],"transaction identity")
        require(receipt["blockHash"]==tx["blockHash"]and receipt["blockNumber"]==tx["blockNumber"],"block binding")
        require(receipt["to"].lower()==tx["to"].lower()==deployments[k]["address"].lower(),"recipient binding")
        require(tx["input"]==row["calldata"],"raw calldata")
        require(integer(receipt["gasUsed"])==row["gas_used"]and integer(receipt["status"])==row["status"],"raw receipt")
        require(integer(tx["chainId"])==31337,"raw transaction chain")
        return data[4:],size
    traces=[]
    for key,row in rows.items():
        k,case,trial,mode=key;sample=samples[key[:3]];args,size=binding(row)
        require(row["status"]==1 and row["proof_accepted"]is True,"valid proof outcome")
        require(row["read_only_result"]==("true"if mode=="legacy_uncompressed"else"returned without revert"),"valid read-only result")
        if mode!="compressed":require(args[:256].hex()==sample["proof_hex"][2:],"native proof bytes")
        else:require([int.from_bytes(args[i:i+32],"big")for i in range(0,128,32)]==list(map(int,row["compressed_words"])),"compressed words")
        actual=[str(int.from_bytes(args[i:i+32],"big"))for i in range(size,len(args),32)]
        require(actual==sample["public_signals"],"native public input binding")
        expected_order=list(MODES)if trial%2==0 else list(reversed(MODES))
        require(row["route_order"]==expected_order,"alternating route order")
        require(bool(row.get("raw_call_trace"))==(trial==0 and mode!="legacy_uncompressed"),"trace sample selection")
        if row.get("raw_call_trace"):
            trace=row["raw_call_trace"]
            require(trace["input"]==row["calldata"]and trace["to"].lower()==deployments[k]["address"].lower(),"trace transaction binding")
            require(integer(trace["gasUsed"])==row["gas_used"]and not trace.get("error"),"trace receipt gas")
            counts,gas=precompiles(trace)
            require(counts.get("6")==counts.get("7")==8*k+2 and counts.get("8")==1,"shared EC/pairing work")
            require(counts.get("5",0)==(5 if mode=="compressed"else 0),"modexp call count")
            if mode=="compressed":require(gas.get("5")==6701,"observed modexp gas")
            traces.append({"k":k,"case_id":case,"mode":mode,"precompile_calls":counts,"precompile_callee_gas":gas})
    require(len(traces)==30,"trace coverage")
    controls=evm["controls"]
    identities={(r["k"],r["case_id"],r["control"],r["mode"])for r in controls}
    expected_controls={(k,c,"altered_public_input",m)for k in range(2,7)for c in CASES for m in MODES}|{(k,"moved_sender","wrong_profile_proof",m)for k in range(2,7)for m in MODES}
    require(len(controls)==len(identities)==60 and identities==expected_controls,"control coverage")
    for row in controls:
        args,size=binding(row);mode=row["mode"]
        require(row["proof_accepted"]is False and row["status"]==(1 if mode=="legacy_uncompressed"else 0),"control outcome")
        require(row["read_only_result"]==("false"if mode=="legacy_uncompressed"else"reverted"),"control return")
        require(row["decoded_error"]==(None if mode=="legacy_uncompressed"else"ProofInvalid"),"decoded control error")
        own=samples[row["k"],row["case_id"],0]
        expected_signals=list(map(int,own["public_signals"]))
        if row["control"]=="altered_public_input":expected_signals[0]=(expected_signals[0]+1)%21888242871839275222246405745257275088548364400416034343698204186575808495617
        else:
            source_k=2 if row["k"]==6 else row["k"]+1
            require(row["proof_from_k"]==source_k,"wrong-profile source identity")
        require([int.from_bytes(args[i:i+32],"big")for i in range(size,len(args),32)]==expected_signals,"control public input")
        if mode!="compressed":
            source=own if row["control"]=="altered_public_input"else samples[row["proof_from_k"],"moved_sender",0]
            require(args[:256].hex()==source["proof_hex"][2:],"control proof identity")
        else:
            source_key=(row["k"],row["case_id"],0,"compressed")if row["control"]=="altered_public_input"else(row["proof_from_k"],"moved_sender",0,"compressed")
            expected_proof=bytes.fromhex(rows[source_key]["calldata"][2:])[4:132]
            require(args[:128]==expected_proof,"compressed control proof identity")
    cc=native["constraint_controls"]
    require(len(cc)==10 and {(c["k"],c["name"])for c in cc}=={(k,n)for k in range(2,7)for n in ["insufficient_sender_balance","nonzero_sum_transfer"]},"constraint control coverage")
    require(all(c["rejected"]is True and c["solver_error"]for c in cc),"constraint control result")
    pairs=[]
    for k,case,trial in sorted(expected):
        a,b=(rows[k,case,trial,m]for m in ["direct_uncompressed","compressed"])
        delta=b["gas_used"]-a["gas_used"];saved=a["intrinsic_gas"]-b["intrinsic_gas"];extra=b["execution_gas"]-a["execution_gas"]
        require(a["calldata_bytes"]-b["calldata_bytes"]==128 and delta==extra-saved,"paired reconciliation")
        if trial==0:require(6701>saved,"extra modexp cost exceeds calldata saving in traced pair")
        pairs.append({"k":k,"case_id":case,"trial":trial,"direct_gas":a["gas_used"],"compressed_gas":b["gas_used"],
          "saved_calldata_bytes":128,"saved_intrinsic_gas":saved,"extra_execution_gas":extra,
          "total_gas_increase":delta,"paired_increase_pct":100*delta/a["gas_used"],
          "hypothetical_extra_uniform_data_charge_break_even":delta/128})
    summary={"status":"passed","new_native_proofs":45,"fixture_variants":15,"valid_solidity_transactions":135,
      "rejected_solidity_controls":60,"reverted_control_receipts":sum(r["status"]==0 for r in controls),
      "successful_control_receipts_returning_false":sum(r["status"]==1 for r in controls),
      "rejected_native_constraint_controls":10,"paired_comparisons":45,
      "compressed_gas_increase_pairs":sum(p["total_gas_increase"]>0 for p in pairs),
      "gas_increase_min":min(p["total_gas_increase"]for p in pairs),"gas_increase_max":max(p["total_gas_increase"]for p in pairs),
      "traced_pairs":15,"extra_modexp_calls_per_traced_compressed_call":5,"extra_modexp_callee_gas_per_traced_call":6701,
      "traced_intrinsic_saving_min":min(p["saved_intrinsic_gas"]for p in pairs if p["trial"]==0),
      "traced_intrinsic_saving_max":max(p["saved_intrinsic_gas"]for p in pairs if p["trial"]==0),
      "limit":"Supplemental synthetic witnesses and standalone local verifiers; not full payment, live transport, production pricing or a privacy audit."}
    return {"summary":summary,"pairs":pairs,"traces":traces}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--native",default=str(ROOT/"supplemental/results/native-proofs.json"))
    ap.add_argument("--evm",default=str(ROOT/"supplemental/results/evm-report.json"))
    ap.add_argument("--output")
    args=ap.parse_args()
    raw=Path(args.native).read_bytes()
    native=json.loads(raw);evm=json.loads(Path(args.evm).read_text())
    selectors=json.loads((ROOT/"supplemental/abi-selectors.json").read_text())
    baseline=json.loads((ROOT/"original/results/evm-run-1.json").read_text())
    result=audit(native,evm,raw,selectors,baseline)
    mutants=[]
    for name,mutate in [
        ("fixture amount changed",lambda n,e:n["fixtures"][0].__setitem__("transfer_units",999)),
        ("receipt gas changed",lambda n,e:e["verification_transactions"][0]["raw_receipt"].__setitem__("gasUsed","0x1")),
        ("control recipient changed",lambda n,e:e["controls"][0]["raw_transaction"].__setitem__("to","0x"+"00"*20)),
        ("trace gas changed",lambda n,e:e["verification_transactions"][0]["raw_call_trace"].__setitem__("gasUsed","0x1")),
    ]:
        n,e=copy.deepcopy(native),copy.deepcopy(evm);mutate(n,e)
        try:audit(n,e,raw,selectors,baseline)
        except (ValueError,KeyError):mutants.append({"case":name,"rejected":True})
        else:raise ValueError("Copied-record mutation was not detected: "+name)
    result["summary"]["copied_record_mutations"]=mutants
    if args.output:Path(args.output).write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result["summary"],indent=2))

if __name__=="__main__":main()
