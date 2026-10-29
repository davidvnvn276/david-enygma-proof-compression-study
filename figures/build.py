from pathlib import Path
import json,base64,html,subprocess
from PIL import Image,ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'images';OUT.mkdir(exist_ok=True)
PREVIEW=ROOT/'runs/figure-previews';PREVIEW.mkdir(parents=True,exist_ok=True)
V=json.loads((ROOT/'supplemental/results/analysis.json').read_text())['summary']
S=json.loads((ROOT/'original/results/summary.json').read_text())
LOGO=base64.b64encode((ROOT/'reviewer/rayls-mark-original.png').read_bytes()).decode()
INK='#121118';PAPER='#F0F1F6';PURPLE='#7651EC';LILAC='#B69BFF';LIME='#EEFF30';GREY='#626171';LINE='#D7D8E3'
FONT=Path('/usr/share/fonts/truetype/dejavu')
ALL=[]

class C:
 def __init__(self,title,h=900):
  self.h=h;self.title=title;self.e=[];self.bounds=[]
  self.e.append('<title>'+html.escape(title)+'</title><defs><pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="#DADCE7" stroke-width="0.65"/></pattern></defs>')
  self.rect(0,0,1600,h,PAPER);self.rect(0,0,1600,h,'url(#grid)')
  self.e.append('<path d="M1230 0H1600V250H1400L1230 90Z" fill="'+LILAC+'"/>')
  self.e.append(f'<path d="M0 {h-100}H155L255 {h}H0Z" fill="{LIME}"/>')
  self.rect(0,0,450,6,PURPLE);self.rect(450,0,180,6,LIME)
  self.rect(1421,27,135,135,INK,cut=15)
  self.e.append('<image x="1429" y="35" width="119" height="119" xlink:href="data:image/png;base64,'+LOGO+'"/>')
 def rect(self,x,y,w,h,fill,stroke=None,cut=0):
  a=f'<path d="M{x} {y}H{x+w-cut}L{x+w} {y+cut}V{y+h}H{x}Z"' if cut else f'<rect x="{x}" y="{y}" width="{w}" height="{h}"'
  self.e.append(a+f' fill="{fill}"'+(f' stroke="{stroke}" stroke-width="1.5"' if stroke else '')+'/>')
 def line(self,x,y,x2,y2,color=LINE,width=1.5):self.e.append(f'<path d="M{x} {y}L{x2} {y2}" stroke="{color}" stroke-width="{width}"/>')
 def t(self,x,y,s,size=24,color=INK,bold=False,mono=False,maxw=None,anchor='start'):
  file='DejaVuSans'+('Mono' if mono else '')+('-Bold' if bold else '')+'.ttf'
  w=ImageFont.truetype(str(FONT/file),size).getlength(s)
  if maxw is not None and w>maxw:raise ValueError(f'{s}: {w}>{maxw}')
  left=x-w if anchor=='end' else x-w/2 if anchor=='middle' else x
  if left<0 or left+w>1600 or y>self.h:raise ValueError('Canvas overflow '+s)
  self.bounds.append({'text':s,'x':left,'width':w,'baseline':y,'size':size})
  self.e.append(f'<text x="{x}" y="{y}" font-family="DejaVu Sans'+(' Mono' if mono else '')+f'" font-size="{size}" font-weight="'+('700' if bold else '400')+f'" fill="{color}" text-anchor="{anchor}">'+html.escape(s)+'</text>')
 def label(self,x,y,s,color=PURPLE):self.t(x,y,s,19,color,True,True)
 def foot(self,s):
  self.rect(60,self.h-75,1480,46,INK);self.rect(60,self.h-75,8,46,LIME)
  self.t(84,self.h-45,s,20,'white',maxw=1420)
 def save(self,name):
  svg=OUT/(name+'.svg');png=OUT/(name+'.png')
  svg.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1600" height="{self.h}" viewBox="0 0 1600 {self.h}">'+''.join(self.e)+'</svg>')
  subprocess.run(['inkscape',str(svg),'--export-type=png','--export-width=3200','--export-filename='+str(png)],check=True,capture_output=True)
  im=Image.open(png);assert im.size==(3200,self.h*2)
  im.resize((1200,self.h*3//4),Image.Resampling.LANCZOS).save(PREVIEW/(name+'-preview.png'))
  ALL.append({'file':name+'.svg','text_bounds':self.bounds})
  print('Created',png.name,flush=True)

def cover():
 c=C('Does a smaller ZK proof mean lower gas?',640)
 c.label(62,56,'RAYLS ENYGMA - A CONTROLLED VERIFIER BENCHMARK')
 c.t(58,136,'Does a smaller proof',64,bold=True,maxw=1290)
 c.t(58,215,'mean lower gas?',72,bold=True,maxw=1300)
 c.rect(62,259,676,275,INK,cut=22)
 c.label(91,303,'PROOF REPRESENTATION',LILAC)
 c.t(86,406,'256',98,'white',True);c.t(338,398,'to',38,LILAC)
 c.t(413,406,'128',98,LIME,True)
 c.t(92,460,'bytes',29,'white')
 c.t(92,505,'50% smaller proof component',25,'white',maxw=590)
 c.label(788,300,'LOCAL GAS RESULT')
 c.t(784,383,'150 of 150',73,bold=True,maxw=750)
 c.t(788,432,'paired compressed calls used more gas.',29,maxw=750)
 c.t(788,479,'Complete calldata fell by 6.88% to 15.31%.',25,GREY,maxw=750)
 c.foot('Pinned Rayls verifiers - Local Shanghai EVM - Verification only, not a complete Enygma payment.')
 c.save('01-enygma-banner')

def sizes():
 c=C('A 50% smaller proof is not a 50% smaller call.')
 c.label(62,55,'PROOF BYTES AND COMPLETE CALLDATA')
 c.t(58,122,'Public inputs stay in the call.',56,bold=True,maxw=1310)
 c.t(62,166,'Each profile saves 128 bytes. The public-input component grows with k.',26,GREY,maxw=1460)
 c.rect(62,204,1476,559,'white',INK,cut=18)
 c.label(88,240,'PROFILE');c.label(288,240,'SAME BYTE SCALE FOR ALL BARS')
 c.t(1507,240,'REDUCTION',19,PURPLE,True,True,anchor='end')
 scale=920/1860
 for i,p in enumerate(S['profiles']):
  y=287+i*87;k=p['k'];inputs=32*p['public_inputs']
  c.t(88,y+19,'k='+str(k),28,bold=True)
  c.t(88,y+48,str(p['public_inputs'])+' public inputs',19,GREY)
  for dy,proof,total,color in [(0,256,p['uncompressed_calldata_bytes'],LILAC),(30,128,p['compressed_calldata_bytes'],LIME)]:
   x=288;c.rect(x,y+dy,4*scale,20,INK);x+=4*scale
   c.rect(x,y+dy,proof*scale,20,color);x+=proof*scale
   c.rect(x,y+dy,inputs*scale,20,'#C8CAD8')
   c.t(288+total*scale+14,y+dy+17,f'{total:,} B',20,INK,mono=True,maxw=200)
  c.t(1507,y+33,f'{p["calldata_reduction_pct"]:.2f}%',28,PURPLE,True,anchor='end')
  if i<4:c.line(88,y+69,1510,y+69)
 c.rect(62,781,20,20,LILAC);c.t(94,799,'Uncompressed proof',21)
 c.rect(396,781,20,20,LIME);c.t(428,799,'Compressed proof',21)
 c.rect(698,781,20,20,'#C8CAD8');c.t(730,799,'Public inputs',21)
 c.rect(966,781,20,20,INK);c.t(998,799,'4-byte selector',21)
 c.foot('Complete calldata = selector + proof + 32 bytes per public input. These profiles have 8k + 2 public inputs.')
 c.save('02-proof-versus-calldata')

def gas():
 c=C('Less calldata, more gas in every recorded pair.')
 c.label(62,55,'PAIRED TRANSACTIONS - SAME PROOF AND PUBLIC INPUTS')
 c.t(58,122,'Smaller calls. Higher local gas.',55,bold=True,maxw=1310)
 c.t(62,166,'150 paired increases under the recorded Shanghai configuration.',26,GREY)
 c.rect(62,211,730,548,'white',INK,cut=18);c.rect(62,211,730,53,INK)
 c.t(87,247,'MEDIANS ACROSS 30 PROOFS PER PROFILE',20,'white',True,True,maxw=680)
 c.label(90,305,'k');c.label(203,305,'DIRECT');c.label(414,305,'COMPRESSED')
 c.t(759,305,'PAIRED %',18,PURPLE,True,True,anchor='end')
 for i,p in enumerate(S['profiles']):
  y=368+i*68
  c.t(90,y,str(p['k']),29,bold=True,mono=True)
  c.t(203,y,f'{p["gas"]["direct_uncompressed"]["median"]:,.0f}',25,mono=True)
  val=p['gas']['compressed']['median'];label=f'{val:,.1f}' if val%1 else f'{val:,.0f}'
  c.t(414,y,label,25,mono=True)
  c.t(759,y,f'+{p["paired_compression_gas_change_pct"]["median"]:.2f}%',26,PURPLE,True,anchor='end')
  c.line(90,y+22,763,y+22)
 c.t(89,741,'Gas units; paired percentages are computed per proof.',20,GREY,maxw=680)
 c.rect(829,211,709,548,INK,cut=18)
 c.label(858,252,'ONE k=2 PAIR - RUN 1, TRIAL 0',LILAC)
 c.t(858,311,'Extra execution gas',25,'white')
 c.t(1503,364,'+12,123',58,LIME,True,anchor='end')
 c.t(858,418,'Saved intrinsic calldata gas',25,'white',maxw=650)
 c.t(1503,471,'-2,048',58,LILAC,True,anchor='end')
 c.line(858,497,1504,497,LILAC,2)
 c.t(858,541,'Net transaction gas',25,'white')
 c.t(1503,603,'+10,075',62,LIME,True,anchor='end')
 c.t(858,658,'332,209 direct to 342,284 compressed',25,'white',maxw=650)
 c.t(858,719,'Compression evaluated by a read-only local call.',21,LILAC,maxw=650)
 c.t(62,799,'Execution difference includes both entry points; it is not isolated decompression opcode cost.',22,GREY,maxw=1470)
 c.foot('Medians are statistics; individual transactions use integer gas. No mainnet fees or full-payment cost is inferred.')
 c.save('03-paired-gas-reconciliation')

def acceptance():
 c=C('A successful receipt does not by itself establish proof acceptance.')
 c.label(62,55,'PROOF ACCEPTANCE AND TRANSACTION STATUS')
 c.t(58,122,'Check the proof result, too.',51,bold=True,maxw=1310)
 c.t(62,166,'The uncompressed boolean wrapper catches invalid-proof reverts and returns false.',25,GREY,maxw=1460)
 c.rect(62,210,1476,338,'white',INK,cut=18)
 c.rect(62,210,1476,53,INK)
 c.t(88,246,'ENTRY POINT',21,'white',True,True)
 c.t(700,246,'VALID PROOF',21,'white',True,True)
 c.t(1120,246,'ALTERED INPUT',21,'white',True,True)
 rows=[('Direct uncompressed','verifyProofInternal','Receipt 1; no revert','Receipt 0; reverted'),('Compressed','verifyCompressedProof','Receipt 1; no revert','Receipt 0; reverted'),('Uncompressed wrapper','verifyProof','Receipt 1; returns true','Receipt 1; returns false')]
 for i,(title,fn,valid,bad) in enumerate(rows):
  y=310+i*82
  if i==2:c.rect(78,y-29,1442,70,'#E8DFFF')
  c.t(88,y,title,26,bold=True);c.t(88,y+30,fn,20,PURPLE,mono=True)
  c.t(700,y+10,valid,24,maxw=400);c.t(1120,y+10,bad,24,maxw=390)
 c.rect(62,582,711,167,LILAC);c.rect(805,582,733,167,INK,cut=18)
 c.t(88,623,'Original: 48 rejected controls',27,bold=True,maxw=660)
 c.t(88,669,'33 reverted receipts',25)
 c.t(88,714,'15 successful receipts returning false',25,maxw=660)
 c.t(832,624,'Pinned caller checks the boolean',29,'white',True,maxw=680)
 c.t(832,668,'EnygmaV1 requires the wrapper result to be true.',23,'white',maxw=680)
 c.t(832,713,'Source inspected; full payment caller not executed.',22,LILAC,maxw=680)
 c.t(62,799,'450 valid verifier transactions were replayed with matching calldata and gas, plus these 48 rejection controls.',22,GREY,maxw=1470)
 c.foot('Acceptance was checked with the call result and receipt together. This is not evidence of an invalid-payment bypass.')
 c.save('04-proof-acceptance-versus-receipt')

def trace_evidence():
 assert V['traced_pairs']==15 and V['extra_modexp_calls_per_traced_compressed_call']==5
 assert V['extra_modexp_callee_gas_per_traced_call']==6701
 assert V['traced_intrinsic_saving_min']==2024 and V['traced_intrinsic_saving_max']==2060
 c=C('Fresh witnesses and call traces explain the local gas difference.')
 c.label(62,55,'FRESH WITNESSES - NATIVE PROOFS - SOLIDITY - CALL TRACES')
 c.t(58,122,'Find the cost inside the call.',56,bold=True,maxw=1310)
 c.t(62,166,'15 selected pairs: same proof and public inputs, two verifier entry points.',26,GREY,maxw=1460)
 for x,title,sub in [(62,'15 witness variants','45 new native proofs'),(566,'Native + Solidity','135 accepted calls'),(1070,'15 paired traces','30 traced transactions')]:
  c.rect(x,207,468,100,'white',INK,cut=15)
  c.t(x+24,247,title,28,bold=True,maxw=420)
  c.t(x+24,285,sub,24,PURPLE,maxw=420)
 c.rect(62,346,711,423,'white',INK,cut=18)
 c.t(88,389,'COMPRESSED ROUTE: EXTRA WORK',20,PURPLE,True,True,maxw=660)
 c.t(88,441,'Five modexp calls',28,bold=True)
 c.t(744,441,'6,701 gas',36,PURPLE,True,anchor='end')
 scale=610/7000
 c.rect(88,467,610,30,'#E6E4EF');c.rect(88,467,6701*scale,30,PURPLE)
 c.t(88,553,'Saved intrinsic gas',27,bold=True)
 c.t(88,605,'2,024 to 2,060',44,bold=True,maxw=650)
 c.rect(88,634,610,30,'#E6E4EF');c.rect(88,634,2060*scale,30,LIME)
 c.t(88,721,'Same scale; saving bar shows 2,060 gas.',22,GREY,maxw=650)
 c.rect(805,346,733,423,INK,cut=18)
 c.t(833,391,'BOTH ROUTES: SHARED WORK',21,LILAC,True,True,maxw=670)
 c.t(833,448,'8k + 2 EC additions',30,'white',maxw=650)
 c.t(833,496,'8k + 2 EC multiplications',30,'white',maxw=650)
 c.t(833,544,'1 pairing-precompile call',30,'white',maxw=650)
 c.line(833,575,1507,575,LILAC,2)
 c.t(833,624,'Extra exponentiation alone',30,LIME,True,maxw=650)
 c.t(833,666,'exceeds the calldata saving.',29,'white',maxw=650)
 c.t(833,724,'Callee gas excludes other entry-point overhead.',22,LILAC,maxw=650)
 c.foot('Supplemental trial-0 traces only - Local Shanghai EVM - Not full-payment cost or a production fee quote.')
 c.save('05-fresh-proof-trace-evidence')

cover();sizes();gas();acceptance();trace_evidence()
(ROOT/'figure-text-bounds.json').write_text(json.dumps(ALL,indent=2)+'\n')
(ROOT/'figure-data.json').write_text(json.dumps({'original':S,'supplemental':V},indent=2)+'\n')
