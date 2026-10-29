"""Generate supplemental witnesses and pass their fresh proofs through Solidity.

Works in a new directory. Uses published keys and unmodified pinned circuits
and verifiers. No Rayls RPC, wallet credential or mainnet transaction is used.
"""
from pathlib import Path
import argparse,datetime,json,os,shutil,socket,subprocess,sys,tarfile

ROOT=Path(__file__).resolve().parents[1]

def command(args,cwd,env,log):
    print("Running:",Path(str(args[0])).name,*map(str,args[1:3]),flush=True)
    with log.open("w")as f:
        p=subprocess.run(list(map(str,args)),cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
    if p.returncode:raise RuntimeError(f"Command failed ({p.returncode}); inspect {log}")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anvil",required=True)
    ap.add_argument("--go")
    ap.add_argument("--output")
    a=ap.parse_args()
    if not __debug__:raise SystemExit("Run without Python -O.")
    if a.output:
        out=Path(a.output).expanduser().resolve()
    else:
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        out=ROOT/"runs"/("supplemental-"+stamp)
    if out==ROOT or any(out.is_relative_to(ROOT/n)for n in ["original","reviewer","supplemental","images"]):
        raise SystemExit("Output must be outside the preserved evidence directories.")
    out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ)
    command([sys.executable,ROOT/"verify_all.py"],ROOT,env,out/"saved-check.log")
    go=a.go or shutil.which("go")
    node=shutil.which("node");npm=shutil.which("npm.cmd"if os.name=="nt"else"npm")
    if not go or not node or not npm:raise SystemExit("Install Go 1.26.2 and Node.js 24.22.1.")
    go=Path(go).expanduser().resolve();anvil=Path(a.anvil).expanduser().resolve()
    versions={
        "go":subprocess.check_output([str(go),"version"],text=True).strip(),
        "node":subprocess.check_output([node,"--version"],text=True).strip(),
        "anvil":subprocess.check_output([str(anvil),"--version"],text=True).strip(),
    }
    if "go1.26.2 "not in versions["go"]or versions["node"]!="v24.22.1"or"1.3.1"not in versions["anvil"]:
        raise SystemExit("Use the fixed toolchain versions in README.md.")
    with socket.socket()as s:
        if s.connect_ex(("127.0.0.1",18549))==0:raise SystemExit("Local port 18549 is already in use.")
    dest=out/"gnark-source";dest.mkdir()
    with tarfile.open(ROOT/"reviewer/pinned-gnark-source.tar.gz")as t:t.extractall(dest,filter="data")
    checkout=next(dest.iterdir())
    for p in(ROOT/"original/published-artifacts").rglob("*"):
        if p.is_file():
            target=checkout/"last_build"/p.relative_to(ROOT/"original/published-artifacts")
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    study=checkout/"pkg/circuits/enygma/enygma-payments/david-cost-study";study.mkdir(exist_ok=True)
    shutil.copyfile(ROOT/"original/cost_test.go",study/"cost_test.go")
    shutil.copyfile(ROOT/"supplemental/fixtures_test.go",study/"fixtures_test.go")
    native=out/"native-proofs.json"
    native_env=dict(env,DAVID_GNARK_ROOT=str(checkout),DAVID_COST_OUTPUT=str(native))
    command([go,"test","-count=1","-timeout=10m","-run","^TestSupplementalFixtures$","-v","./pkg/circuits/enygma/enygma-payments/david-cost-study"],checkout,native_env,out/"native-generation.log")
    evm=out/"evm-study";shutil.copytree(ROOT/"original",evm)
    harness=evm/"evm-harness"
    shutil.copyfile(ROOT/"supplemental/evm-variants.mjs",harness/"evm-variants.mjs")
    command([npm,"ci","--ignore-scripts","--no-audit","--no-fund"],harness,env,out/"npm-install.log")
    evm_report=out/"evm-report.json"
    evm_env=dict(env,DAVID_STUDY_ROOT=str(evm),DAVID_VARIANTS_PROOFS=str(native),DAVID_VARIANTS_OUTPUT=str(evm_report),DAVID_ANVIL_PATH=str(anvil))
    command([node,"evm-variants.mjs"],harness,evm_env,out/"evm-execution.log")
    analysis=out/"analysis.json"
    command([sys.executable,ROOT/"supplemental/audit.py","--native",native,"--evm",evm_report,"--output",analysis],ROOT,env,out/"fresh-audit.log")
    result=json.loads(analysis.read_text())
    report={"status":"passed","toolchains":versions,"result":result["summary"],
        "scope":"Fresh native generation to standalone Solidity verification; not full Enygma payment or live network execution."}
    (out/"reproduction-summary.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    print("Output:",out)

if __name__=="__main__":main()
