from pathlib import Path
import csv,tempfile,subprocess,json
def write_file(path,corrupt=False):
    with path.open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['Timestamp']+[f'Array {i}' for i in range(1,15)])
        for d in range(1,31):
            for b in range(96):
                hh=b//4;mm=(b%4)*15
                if corrupt and d==15 and b==95:hh,mm=23,30
                vals=[0.5]*13+[0.47];w.writerow([f'{d}/04/16 {hh}:{mm:02d}']+vals)
with tempfile.TemporaryDirectory() as td:
    td=Path(td);good=td/'good.csv';bad=td/'bad.csv';write_file(good,False);write_file(bad,True)
    for p,expected in [(good,1),(bad,0)]:
        out=td/(p.stem+'_out');r=subprocess.run(['python',str(Path(__file__).with_name('reproduce_r20_more_eu.py')),str(p),str(out)],capture_output=True,text=True);assert r.returncode==0,r.stderr;s=json.loads((out/'R20_SUMMARY.json').read_text());assert s['complete_months']==expected,(p,s)
print('synthetic complete/fail-closed timestamp tests PASS')
