"""Check the reviewed distribution's listed file hashes, using only Python stdlib."""
from pathlib import Path,PurePosixPath
import hashlib,json

ROOT=Path(__file__).resolve().parent

def main():
    m=json.loads((ROOT/'MANIFEST_SHA256.json').read_text());fail=[]
    for name,expected in m['files'].items():
        relative=PurePosixPath(name);p=ROOT/name
        if relative.is_absolute() or '..' in relative.parts or not p.resolve().is_relative_to(ROOT):fail.append(name)
        elif not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:fail.append(name)
    print(json.dumps({'status':'failed' if fail else 'passed','files_checked':len(m['files']),'mismatches':fail,
                      'limit':'Listed file consistency, not trusted-setup or production-chain authentication.'},indent=2))
    if fail:raise SystemExit(1)

if __name__=='__main__':main()
