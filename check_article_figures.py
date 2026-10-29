"""Check article tables, figure data, PNG dimensions and the embedded logo."""
from pathlib import Path
import base64,hashlib,json,re,struct,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent

def require(value,message):
    if not value:raise ValueError(message)

def main():
    original=json.loads((ROOT/"original/results/summary.json").read_text())
    extra=json.loads((ROOT/"supplemental/results/analysis.json").read_text())["summary"]
    figure_data=json.loads((ROOT/"figure-data.json").read_text())
    require(figure_data=={"original":original,"supplemental":extra},"figure source data")
    article=(ROOT/"ARTICLE_COPY.md").read_text()
    size_rows=re.findall(r"^\| k=([2-6]) \| ([\d,]+) \| ([\d,]+) bytes \| ([\d,]+) bytes \| ([\d.]+)% \|$",article,re.M)
    gas_rows=re.findall(r"^\| k=([2-6]) \| ([\d,]+) \| ([\d,.]+) \| ([\d.]+)% \|$",article,re.M)
    require(len(size_rows)==len(gas_rows)==5,"article table coverage")
    for p,a,b in zip(original["profiles"],size_rows,gas_rows):
        k=p["k"]
        require(tuple(a)==(str(k),str(p["public_inputs"]),f'{p["uncompressed_calldata_bytes"]:,}',f'{p["compressed_calldata_bytes"]:,}',f'{p["calldata_reduction_pct"]:.2f}'),"article calldata table")
        compressed=p["gas"]["compressed"]["median"]
        c=f"{compressed:,.1f}"if compressed%1 else f"{compressed:,.0f}"
        require(tuple(b)==(str(k),f'{p["gas"]["direct_uncompressed"]["median"]:,.0f}',c,f'{p["paired_compression_gas_change_pct"]["median"]:.2f}'),"article gas table")
    for phrase in ["135 accepted verification transactions","6,701 gas","2,024 to 2,060 gas","9,615 to 10,175 gas"]:
        require(phrase in article,"missing article evidence phrase: "+phrase)
    files=[
        ("01-enygma-banner",1280),("02-proof-versus-calldata",1800),
        ("03-paired-gas-reconciliation",1800),("04-proof-acceptance-versus-receipt",1800),
        ("05-fresh-proof-trace-evidence",1800),
    ]
    mark=(ROOT/"reviewer/rayls-mark-original.png").read_bytes()
    mark_hash=hashlib.sha256(mark).hexdigest()
    require(mark_hash=="75e95e00b76d284facc82f1bd67f9abe344df454349d39d9a3a111293a7041b1","original logo identity")
    texts={}
    for name,height in files:
        png=(ROOT/"images"/(name+".png")).read_bytes()
        require(png[:8]==b"\x89PNG\r\n\x1a\n"and struct.unpack(">II",png[16:24])==(3200,height),"figure PNG dimensions")
        tree=ET.fromstring((ROOT/"images"/(name+".svg")).read_text())
        images=tree.findall("{http://www.w3.org/2000/svg}image")
        require(len(images)==1,"one original logo per SVG")
        uri=images[0].attrib["{http://www.w3.org/1999/xlink}href"]
        require(hashlib.sha256(base64.b64decode(uri.split(",",1)[1])).hexdigest()==mark_hash,"unchanged embedded logo")
        texts[name]=" ".join(tree.itertext())
    for p in original["profiles"]:
        require(f'{p["uncompressed_calldata_bytes"]:,} B'in texts["02-proof-versus-calldata"]and f'{p["compressed_calldata_bytes"]:,} B'in texts["02-proof-versus-calldata"],"figure calldata values")
    for value in ["+12,123","-2,048","+10,075"]:
        require(value in texts["03-paired-gas-reconciliation"],"original paired example figure")
    for value in ["Original: 48 rejected controls","33 reverted receipts","15 successful receipts returning false"]:
        require(value in texts["04-proof-acceptance-versus-receipt"],"original control figure")
    for value in ["15 witness variants","45 new native proofs","135 accepted calls","15 paired traces","6,701 gas","2,024 to 2,060"]:
        require(value in texts["05-fresh-proof-trace-evidence"],"supplemental figure value")
    require(extra["valid_solidity_transactions"]==135 and extra["traced_pairs"]==15 and extra["traced_intrinsic_saving_min"]==2024 and extra["traced_intrinsic_saving_max"]==2060,"supplemental figure source")
    print(json.dumps({"status":"passed","article_table_rows":10,"figures":5,"banner_ratio":"5:2","internal_ratio":"16:9","logo_sha256":mark_hash,
      "limit":"Checks numerical content and file properties; visual layout was also inspected separately."},indent=2))

if __name__=="__main__":main()
