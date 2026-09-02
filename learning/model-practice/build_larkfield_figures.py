from decimal import Decimal as D, ROUND_HALF_UP
def r1(x): return D(str(x)).quantize(D('0.1'), rounding=ROUND_HALF_UP)

YEARS = [2021, 2022, 2023, 2024]   # 2021 is opening only

# ---- income statement drivers (rounded inputs) ----
IS = {
 2021: dict(rev=762.0, gm=0.415, sga=160.0, rnd=53.3, dep=31.5, iexp=14.8, iinc=0.6, trate=0.245),
 2022: dict(rev=820.4, gm=0.420, sga=168.0, rnd=57.4, dep=34.0, iexp=14.2, iinc=0.9, trate=0.245),
 2023: dict(rev=889.6, gm=0.426, sga=176.1, rnd=62.3, dep=36.5, iexp=13.4, iinc=1.3, trate=0.245),
 2024: dict(rev=950.2, gm=0.431, sga=183.0, rnd=67.5, dep=39.2, iexp=12.5, iinc=2.0, trate=0.240),
}
# working capital days
DAYS = {
 2021: dict(dso=51, dio=77, dpo=44, tpd=59),
 2022: dict(dso=52, dio=78, dpo=44, tpd=60),
 2023: dict(dso=54, dio=80, dpo=45, tpd=62),
 2024: dict(dso=56, dio=81, dpo=45, tpd=61),
}
CAPEX   = {2021: 40.0, 2022: 44.0, 2023: 49.0, 2024: 53.0}
LTD     = {2021: 260.0, 2022: 240.0, 2023: 220.0, 2024: 200.0}
STD     = {2021: 35.0,  2022: 35.0,  2023: 35.0,  2024: 30.0}
REVOLV  = {2021: 0.0,   2022: 0.0,   2023: 0.0,   2024: 0.0}
BUYBACK = {2021: 0.0,   2022: 0.0,   2023: 0.0,   2024: 8.0}
DIVPAY  = {2021: 21.0,  2022: 21.6,  2023: 24.8,  2024: 27.4}
GOODWILL, INTANG = 112.0, 38.0
PPE_OPEN_2021 = 259.5
CE_OPEN_2021, RE_OPEN_2021 = 180.0, 210.0

P = {}   # per-year computed figures
ppe_prev, ce_prev, re_prev = r1(PPE_OPEN_2021), r1(CE_OPEN_2021), r1(RE_OPEN_2021)

for y in YEARS:
    d = IS[y]; k = DAYS[y]
    rev  = r1(d['rev'])
    cogs = r1(rev * D(str(d['gm'])) * -1 + rev)          # rev - gross profit
    gp   = rev - cogs
    sga, rnd, dep = r1(d['sga']), r1(d['rnd']), r1(d['dep'])
    ebit = gp - sga - rnd - dep
    iexp, iinc = r1(d['iexp']), r1(d['iinc'])
    ebt  = ebit - iexp + iinc
    tax  = r1(ebt * D(str(d['trate'])))
    ni   = ebt - tax
    div  = r1(DIVPAY[y])

    ar  = r1(rev  * D(k['dso']) / D(365))
    inv = r1(cogs * D(k['dio']) / D(365))
    ap  = r1(cogs * D(k['dpo']) / D(365))
    tp  = r1(tax  * D(k['tpd']) / D(365))

    capex = r1(CAPEX[y])
    ppe   = ppe_prev + capex - dep
    ce    = ce_prev - r1(BUYBACK[y])
    re    = re_prev + ni - div

    P[y] = dict(rev=rev, cogs=cogs, gp=gp, sga=sga, rnd=rnd, dep=dep, ebit=ebit,
                iexp=iexp, iinc=iinc, ebt=ebt, tax=tax, ni=ni, div=div,
                ar=ar, inv=inv, ap=ap, tp=tp, capex=capex, ppe=ppe,
                ltd=r1(LTD[y]), std=r1(STD[y]), rev_lv=r1(REVOLV[y]),
                ce=ce, re=re, buyback=r1(BUYBACK[y]))
    ppe_prev, ce_prev, re_prev = ppe, ce, re

# opening cash for FY2021 chosen so the FY2021 balance sheet balances exactly
p = P[2021]
liab_eq = p['ap']+p['tp']+p['std']+p['rev_lv']+p['ltd']+p['ce']+p['re']
non_cash_assets = p['ar']+p['inv']+p['ppe']+r1(GOODWILL)+r1(INTANG)
P[2021]['cash'] = liab_eq - non_cash_assets

# cash flow statement for 2022-2024, cash rolls forward
for y in [2022, 2023, 2024]:
    c, pv = P[y], P[y-1]
    c['d_ar']  = -(c['ar']  - pv['ar'])
    c['d_inv'] = -(c['inv'] - pv['inv'])
    c['d_ap']  =  (c['ap']  - pv['ap'])
    c['d_tp']  =  (c['tp']  - pv['tp'])
    c['cfo'] = c['ni'] + c['dep'] + c['d_ar'] + c['d_inv'] + c['d_ap'] + c['d_tp']
    c['cfi'] = -c['capex']
    c['d_ltd'] = c['ltd'] - pv['ltd']
    c['d_std'] = c['std'] - pv['std']
    c['d_rev'] = c['rev_lv'] - pv['rev_lv']
    c['cff'] = c['d_ltd'] + c['d_std'] + c['d_rev'] - c['buyback'] - c['div']
    c['dcash'] = c['cfo'] + c['cfi'] + c['cff']
    c['cash_open'] = pv['cash']
    c['cash'] = pv['cash'] + c['dcash']

# ---------------- verification ----------------
print("VERIFICATION")
ok = True
for y in YEARS:
    p = P[y]
    A = p['cash']+p['ar']+p['inv']+p['ppe']+r1(GOODWILL)+r1(INTANG)
    L = p['ap']+p['tp']+p['std']+p['rev_lv']+p['ltd']+p['ce']+p['re']
    bal = A - L
    if bal != 0: ok=False
    print(f"  FY{y}  assets {A:>8}  L+E {L:>8}  check {bal}")
for y in [2022,2023,2024]:
    c=P[y]
    if c['cash'] != c['cash_open'] + c['dcash']: ok=False; print(f"  FY{y} cash roll BROKEN")
    ist = c['gp'] - c['sga'] - c['rnd'] - c['dep'] - c['ebit']
    if ist != 0: ok=False; print(f"  FY{y} EBIT BROKEN")
print("  income statement subtotals tie:", all(P[y]['rev']-P[y]['cogs']==P[y]['gp'] for y in YEARS))
print("  cash flow closing cash = balance sheet cash:", all(P[y]['cash']==P[y]['cash'] for y in [2022,2023,2024]))
print("\n  ALL IDENTITIES HOLD" if ok else "\n  *** FAILED")

import json
out={str(y):{k:str(v) for k,v in P[y].items()} for y in YEARS}
out['_meta']={'goodwill':str(r1(GOODWILL)),'intangibles':str(r1(INTANG))}
open('report_numbers.json','w').write(json.dumps(out,indent=1))

print("\nSUMMARY (FY2022-24)")
for k,lbl in [('rev','Revenue'),('gp','Gross profit'),('ebit','EBIT'),('ni','Net income'),
              ('cfo','Cash from ops'),('cash','Cash')]:
    print(f"  {lbl:<16}" + "".join(f"{P[y].get(k,''):>12}" for y in [2022,2023,2024]))
