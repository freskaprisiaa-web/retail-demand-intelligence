from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTING = ROOT / "data" / "reporting"


def read_csv(name: str) -> list[dict[str, str]]:
    with (REPORTING / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


monthly = read_csv("monthly_report.csv")
branches = read_csv("branch_scorecard.csv")
forecast_store = read_csv("forecast_by_store.csv")
actions = read_csv("action_register.csv")
with (ROOT / "validation" / "model_summary.json").open(encoding="utf-8") as handle:
    model = json.load(handle)

data = {
    "monthly": monthly,
    "branches": branches,
    "forecastStore": forecast_store,
    "actions": actions,
    "model": model,
}

html = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Retail Demand Intelligence</title>
<style>
:root{--navy:#173b57;--teal:#168f8b;--gold:#d9a441;--red:#c45a3a;--ink:#243746;--muted:#637382;--line:#d9e2e8;--bg:#f4f7f9;--card:#fff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);font:14px/1.45 Inter,Segoe UI,Arial,sans-serif;color:var(--ink)}
header{background:linear-gradient(115deg,var(--navy),#245d74);color:#fff;padding:28px 5vw 24px}h1{margin:0 0 6px;font-size:30px}header p{margin:0;opacity:.86}
main{max-width:1440px;margin:auto;padding:24px 4vw 48px}.notice{background:#eaf3f5;border-left:4px solid var(--teal);padding:12px 15px;margin-bottom:18px}
.cards{display:grid;grid-template-columns:repeat(5,minmax(155px,1fr));gap:12px}.card,.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:0 3px 14px #173b570b}
.card{padding:17px}.label{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}.value{font-size:25px;font-weight:750;color:var(--navy);margin-top:5px}.sub{font-size:12px;color:var(--muted);margin-top:3px}
.grid{display:grid;grid-template-columns:1.2fr .8fr;gap:16px;margin-top:16px}.panel{padding:18px}.panel h2{font-size:17px;margin:0 0 2px}.panel p{font-size:12px;color:var(--muted);margin:0 0 12px}
svg{width:100%;height:300px;overflow:visible}.axis{stroke:#aebbc5;stroke-width:1}.gridline{stroke:#e4ebef;stroke-width:1}.trend{fill:none;stroke:var(--navy);stroke-width:3}.dot{fill:var(--gold)}.bar{fill:var(--teal)}.risk{fill:var(--red)}
table{width:100%;border-collapse:collapse;font-size:12px}th{text-align:left;background:var(--navy);color:#fff;padding:9px}td{padding:8px;border-bottom:1px solid var(--line)}.pill{padding:3px 8px;border-radius:999px;background:#fff1cd;color:#7f5a00;font-weight:700}.p2{background:#ffe0d7;color:#8b321e}
footer{color:var(--muted);padding:20px 0 0;font-size:12px}@media(max-width:1000px){.cards{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}}@media(max-width:560px){.cards{grid-template-columns:1fr}h1{font-size:24px}}
</style></head>
<body><header><h1>Retail Demand Intelligence</h1><p>CRISP-DM management dashboard · aligned-period performance · leakage-safe forecast monitoring</p></header>
<main>
<div class="notice"><strong>Scope:</strong> independent Kaggle competition project. August 2017 is partial through 15 August; year-over-year KPIs use aligned dates.</div>
<section class="cards" id="cards"></section>
<section class="grid"><article class="panel"><h2>Monthly unit sales</h2><p>Last 24 observed months; the final point is a partial month.</p><svg id="trend" viewBox="0 0 760 300"></svg></article>
<article class="panel"><h2>Top stores by aligned 2017 YTD sales</h2><p>Store-level demand volume through 15 August.</p><svg id="branches" viewBox="0 0 520 300"></svg></article></section>
<section class="grid"><article class="panel"><h2>Forecast risk by store</h2><p>Stores with the highest WAPE in the fixed 16-day holdout.</p><svg id="risk" viewBox="0 0 760 300"></svg></article>
<article class="panel"><h2>Continuous-improvement backlog</h2><p>Highest-priority store–family exceptions with named owners.</p><div style="overflow:auto"><table><thead><tr><th>Store</th><th>Family</th><th>Bias</th><th>WAPE</th><th>Priority</th><th>Owner</th></tr></thead><tbody id="actions"></tbody></table></div></article></section>
<footer>Metric definitions and assumptions are documented in <code>docs/KPI_DICTIONARY.md</code>. Baseline results are transparent benchmarks and not production claims.</footer>
</main>
<script>
const DATA = __DATA__;
const num=v=>Number(v||0), pct=v=>`${(100*num(v)).toFixed(1)}%`, compact=v=>Intl.NumberFormat('en',{notation:'compact',maximumFractionDigits:1}).format(num(v));
const current=DATA.branches.reduce((s,r)=>s+num(r.current_ytd_sales),0), prior=DATA.branches.reduce((s,r)=>s+num(r.prior_ytd_sales),0);
const metrics=[
 ['Aligned 2017 YTD sales',compact(current),'1 Jan–15 Aug'],['Aligned YoY growth',pct(current/prior-1),'Like-for-like window'],
 ['Validation RMSLE',num(DATA.model.validation_rmsle).toFixed(3),'Official competition metric'],['Forecast bias',pct(DATA.model.validation_bias),'Aggregate holdout bias'],
 ['Forecast WAPE',pct(DATA.model.validation_wape),'Operational error magnitude']];
document.querySelector('#cards').innerHTML=metrics.map(m=>`<div class="card"><div class="label">${m[0]}</div><div class="value">${m[1]}</div><div class="sub">${m[2]}</div></div>`).join('');
function lineChart(id,rows,xkey,ykey){const svg=document.querySelector(id),W=760,H=300,p={l:54,r:15,t:18,b:48};const xs=rows.map((_,i)=>i),ys=rows.map(r=>num(r[ykey]));const ymin=Math.min(...ys),ymax=Math.max(...ys),x=i=>p.l+i*(W-p.l-p.r)/(rows.length-1),y=v=>H-p.b-(v-ymin)*(H-p.t-p.b)/(ymax-ymin||1);let h='';for(let i=0;i<5;i++){let yy=p.t+i*(H-p.t-p.b)/4;h+=`<line class="gridline" x1="${p.l}" x2="${W-p.r}" y1="${yy}" y2="${yy}"/><text x="${p.l-8}" y="${yy+4}" text-anchor="end" font-size="10" fill="#637382">${compact(ymax-i*(ymax-ymin)/4)}</text>`}h+=`<polyline class="trend" points="${ys.map((v,i)=>`${x(i)},${y(v)}`).join(' ')}"/>`;rows.forEach((r,i)=>{if(i%4===0||i===rows.length-1)h+=`<text x="${x(i)}" y="${H-18}" transform="rotate(-35 ${x(i)} ${H-18})" text-anchor="end" font-size="9" fill="#637382">${r[xkey].slice(0,7)}</text>`});h+=`<circle class="dot" cx="${x(rows.length-1)}" cy="${y(ys.at(-1))}" r="4"/>`;svg.innerHTML=h}
function barChart(id,rows,labelKey,valueKey,klass='bar'){const svg=document.querySelector(id),W=id==='#branches'?520:760,H=300,p={l:id==='#branches'?125:145,r:34,t:8,b:20};const max=Math.max(...rows.map(r=>num(r[valueKey])));let h='';rows.forEach((r,i)=>{const bh=(H-p.t-p.b)/rows.length-4,y=p.t+i*(H-p.t-p.b)/rows.length,w=num(r[valueKey])*(W-p.l-p.r)/(max||1);h+=`<text x="${p.l-7}" y="${y+bh*.75}" text-anchor="end" font-size="10" fill="#435563">${r[labelKey]}</text><rect class="${klass}" x="${p.l}" y="${y}" width="${w}" height="${bh}" rx="3"/><text x="${p.l+w+5}" y="${y+bh*.75}" font-size="9" fill="#637382">${id==='#risk'?pct(r[valueKey]):compact(r[valueKey])}</text>`});svg.innerHTML=h}
lineChart('#trend',DATA.monthly.slice(-24),'month_start','unit_sales');
const top=[...DATA.branches].sort((a,b)=>num(b.current_ytd_sales)-num(a.current_ytd_sales)).slice(0,10).map(r=>({...r,label:`${r.store_nbr} · ${r.city}`}));barChart('#branches',top,'label','current_ytd_sales');
const risks=[...DATA.forecastStore].sort((a,b)=>num(b.wape)-num(a.wape)).slice(0,10).map(r=>({...r,label:`${r.store_nbr} · ${r.city}`}));barChart('#risk',risks,'label','wape','risk');
document.querySelector('#actions').innerHTML=DATA.actions.slice(0,10).map(r=>`<tr><td>${r.store_nbr}</td><td>${r.family}</td><td>${pct(r.forecast_bias)}</td><td>${pct(r.wape)}</td><td><span class="pill ${r.priority.toLowerCase()}">${r.priority}</span></td><td>${r.owner}</td></tr>`).join('');
</script></body></html>'''

html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
(ROOT / "dashboard.html").write_text(html, encoding="utf-8")
print(f"Wrote {ROOT / 'dashboard.html'}")
