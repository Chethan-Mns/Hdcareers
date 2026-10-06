#!/usr/bin/env python3
import argparse, json, sys, time
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from job_verifier_v2 import verify_url, now_utc

def score(job,state):
    state_bonus={"LIVE":1000,"UNCONFIRMED":200,"EXPIRED":-10000}[state]
    category_bonus={"Fresher":80,"Non-IT":35,"Experienced":20}.get(job.get("category"),0)
    return state_bonus+category_bonus+int(job.get("priority",0))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--jobs",default=str(ROOT/"tests/fixtures/v2_final_fresh_30.json"))
    ap.add_argument("--output",default=str(ROOT/"shadow-final-gate-report.json"))
    ap.add_argument("--top",type=int,default=10)
    args=ap.parse_args()
    jobs=json.loads(Path(args.jobs).read_text())
    rows=[]
    for i,j in enumerate(jobs,1):
        v=verify_url(j["apply"])
        row={**j,"initial":asdict(v),"score":score(j,v.state)}
        rows.append(row)
        print(f'[{i:02}/{len(jobs)}] {j["company"]} / {j["role"]}: {v.state} ({v.provider or "unknown"})')
    eligible=[r for r in rows if r["initial"]["state"]!="EXPIRED"]
    eligible.sort(key=lambda r:(r["score"],r.get("priority",0)),reverse=True)
    picked=[]; per_company=defaultdict(int)
    for r in eligible:
        if per_company[r["company"]]>=2: continue
        picked.append(r); per_company[r["company"]]+=1
        if len(picked)>=args.top: break
    print("\nFresh re-verification of proposed Top 10")
    regressions=[]
    for i,r in enumerate(picked,1):
        time.sleep(.25)
        v=verify_url(r["apply"])
        r["fresh"]=asdict(v)
        before=r["initial"]["state"]
        if before=="LIVE" and v.state!="LIVE":
            regressions.append({"id":r["id"],"company":r["company"],"before":before,"after":v.state})
        print(f'TOP {i:02} {r["company"]} / {r["role"]}: {before} -> {v.state}')
    counts=Counter(r["initial"]["state"] for r in rows)
    providers=Counter((r["initial"]["provider"] or "unsupported") for r in rows)
    report={
      "shadow":True,"productionWrites":False,"publishing":False,
      "checkedAt":now_utc().isoformat(),"poolSize":len(rows),
      "verdictCounts":dict(counts),"providerCounts":dict(providers),
      "top10":[{"rank":i+1,**r} for i,r in enumerate(picked)],
      "liveRegressions":regressions,"items":rows
    }
    Path(args.output).write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print("\nSUMMARY",json.dumps({"pool":len(rows),"verdicts":dict(counts),"providers":dict(providers),"top10":len(picked),"liveRegressions":len(regressions)}))
    if regressions:
        raise SystemExit("Final gate failed: a LIVE candidate did not remain LIVE on fresh re-verification")

if __name__=="__main__":
    main()
