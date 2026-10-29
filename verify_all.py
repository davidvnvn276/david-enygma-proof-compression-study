"""Read-only checks of all saved Enygma evidence. Python standard library only."""
from pathlib import Path
import argparse,json,subprocess,sys

ROOT=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json",action="store_true",help="Print complete component reports")
    a=ap.parse_args()
    if not __debug__:raise SystemExit("Run without Python -O.")
    reports={}
    for name,path in [
        ("distribution_integrity","verify_integrity.py"),
        ("original_and_replay_evidence","reviewer/audit_saved.py"),
        ("supplemental_native_to_evm_evidence","supplemental/audit.py"),
        ("article_and_figure_consistency","check_article_figures.py"),
    ]:
        result=subprocess.run([sys.executable,str(ROOT/path)],cwd=ROOT,text=True,capture_output=True)
        if result.returncode:
            print("FAIL:",name)
            print(result.stdout+result.stderr)
            raise SystemExit(result.returncode)
        reports[name]=json.loads(result.stdout)
        if not a.json:print("PASS:",name)
    if a.json:print(json.dumps(reports,indent=2))
    else:
        print("All saved-evidence checks passed.")
        print("Original/replay: 450 accepted calls; 48 rejection controls; 150 matched gas pairs.")
        print("Supplement: 45 fresh proofs; 135 accepted calls; 60 rejection controls; 15 traced pairs.")
        print("This command checks saved records. It does not generate proofs or execute Solidity.")
        print("See README.md for a fresh execution.")

if __name__=="__main__":main()
