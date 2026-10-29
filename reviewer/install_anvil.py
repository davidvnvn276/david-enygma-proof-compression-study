"""Download the official pinned Linux amd64 Anvil binary and verify its archive."""
import argparse,hashlib,platform,shutil,tarfile,urllib.request
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',required=True);a=ap.parse_args()
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','AMD64'):
        raise SystemExit('This helper is only for the tested Linux amd64 archive; use the appropriate official release for other platforms.')
    output=Path(a.output).expanduser().resolve();output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():raise SystemExit('Output already exists; choose a new path.')
    archive=output.parent/'foundry_v1.3.1_linux_amd64.tar.gz'
    url='https://github.com/foundry-rs/foundry/releases/download/v1.3.1/foundry_v1.3.1_linux_amd64.tar.gz'
    with urllib.request.urlopen(url,timeout=45) as r,archive.open('wb') as f:shutil.copyfileobj(r,f)
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest!='baad3e1b06d6f310d210c93e95258a03d923fe610f8d0742138f2245f94abd7c':raise SystemExit('Archive hash mismatch')
    with tarfile.open(archive) as t:
        member=next(m for m in t.getmembers() if Path(m.name).name=='anvil')
        with t.extractfile(member) as src,output.open('wb') as dst:shutil.copyfileobj(src,dst)
    output.chmod(0o755);print('Verified official Anvil 1.3.1:',output)

if __name__=='__main__':main()
