import { useEffect, useState } from "react";
const BASE = import.meta.env.VITE_API_URL || "";
const api = (p, o) => fetch(BASE + "/api" + p, o).then(r => r.json());
const post = (p, b) => api(p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b) });
const LABEL = { ok: "Healthy", stockout: "Running low", expiry: "Likely to expire unsold" };

export default function App() {
  const [items, setItems] = useState([]); const [budget, setBudget] = useState(1000); const [plan, setPlan] = useState(null);
  const [sim, setSim] = useState({ medicine: "", buy_qty: 200, delay_days: 7 }); const [res, setRes] = useState(null);
  const [q, setQ] = useState(""); const [chat, setChat] = useState([]);
  const [inv, setInv] = useState(""); const [rows, setRows] = useState([]); const [msg, setMsg] = useState(""); const [tick, setTick] = useState(0);
  const SAMPLE = "Paracetamol 500mg  B901  600  2027-06-30\nMetformin 500mg  B455  300  2027-02-28\nUnknown Syrup  Z12  50  2027-01-31";
  const upload = async e => { const f = new FormData(); f.append("file", e.target.files[0]); setRows(await fetch(BASE + "/api/invoice/upload", { method: "POST", body: f }).then(r => r.json())); };
  const confirm = async () => { await post("/invoice/confirm", rows); setMsg("Stock updated."); setRows([]); setInv(""); load(); setTick(t => t + 1); };
  const load = () => api("/inventory").then(d => { setItems(d.items); setSim(s => ({ ...s, medicine: s.medicine || d.items[0]?.medicine })); });
  useEffect(() => { load(); }, []);
  useEffect(() => { api("/recommendations?budget=" + budget).then(setPlan); }, [budget, tick]);
  const ask = async e => { e.preventDefault(); if (!q) return; const r = await post("/chat", { question: q }); setChat(c => [...c, { q, a: r.answer }]); setQ(""); };
  const n = s => items.filter(i => i.status === s).length;
  return (<main>
    <header><h1>PharmaOpt</h1><p>Know what to buy, how much, and when. Cut expired stock and empty shelves.</p></header>
    <section className="kpis">
      <div className="kpi danger"><b>{n("stockout")}</b> medicines running low</div>
      <div className="kpi warn"><b>{n("expiry")}</b> medicines likely to expire unsold</div>
      <div className="kpi good"><b>{n("ok")}</b> healthy</div>
    </section>
    <section><h2>Your stock</h2><div className="scroll"><table><thead><tr><th>Medicine</th><th>In stock</th><th>Days of cover</th><th>May expire unsold</th><th>Status</th></tr></thead>
      <tbody>{items.map(i => <tr key={i.medicine}><td>{i.medicine}</td><td>{i.in_stock}</td><td>{i.days_cover} <span className="bar" style={{ width: Math.min(120, i.days_cover * 2) }} /></td><td>{i.at_risk_of_expiry}</td><td><span className={"tag " + i.status}>{LABEL[i.status]}</span></td></tr>)}</tbody></table></div></section>
    <section><h2>What to buy next</h2><label>My purchase budget <input type="number" value={budget} onChange={e => setBudget(+e.target.value)} /></label>
      {plan && <><p className="muted">Spending {plan.spent} of {plan.budget}</p>
        {plan.orders.length ? plan.orders.map(o => <div className="card" key={o.medicine}><b>Buy {o.order_qty} × {o.medicine}</b> <span>({o.cost})</span><p>{o.reason}</p></div>) : <p>Nothing needs ordering within this budget.</p>}</>}</section>
    <section><h2>Try it before you buy</h2><div className="row">
      <select value={sim.medicine} onChange={e => setSim({ ...sim, medicine: e.target.value })}>{items.map(i => <option key={i.medicine}>{i.medicine}</option>)}</select>
      <label>Quantity <input type="number" value={sim.buy_qty} onChange={e => setSim({ ...sim, buy_qty: +e.target.value })} /></label>
      <label>Delay (days) <input type="number" value={sim.delay_days} onChange={e => setSim({ ...sim, delay_days: +e.target.value })} /></label>
      <button onClick={() => post("/simulate", sim).then(setRes)}>Compare options</button></div>
      {res && <div className="scroll"><table><thead><tr><th>Option</th><th>Days out of stock</th><th>Units expired</th><th>Cost</th></tr></thead><tbody>
        {["Don't buy", "Buy now", `Buy in ${sim.delay_days} days`].map((l, i) => <tr key={l}><td>{l}</td><td>{res[i].stockout_days}</td><td>{res[i].expired_units}</td><td>{res[i].spend}</td></tr>)}</tbody></table></div>}</section>
    <section><h2>Add stock from a supplier invoice</h2>
      <p className="muted">Paste the invoice lines or upload a photo. Check them, then confirm.</p>
      <textarea className="area" rows="4" value={inv} onChange={e => setInv(e.target.value)} placeholder="Medicine   Batch   Qty   Expiry" />
      <div className="row"><input type="file" accept=".txt,.png,.jpg,.jpeg" onChange={upload} /><button onClick={() => setInv(SAMPLE)}>Use sample invoice</button><button onClick={() => post("/invoice/parse", { text: inv }).then(setRows)}>Read invoice</button></div>
      {rows.length > 0 && <><div className="scroll"><table><thead><tr><th>Medicine</th><th>Batch</th><th>Qty</th><th>Expiry</th><th>Check</th></tr></thead><tbody>
        {rows.map((r, i) => <tr key={i}><td>{r.medicine}</td><td>{r.batch}</td><td>{r.qty}</td><td>{r.expiry}</td><td><span className={"tag " + (r.matched ? "ok" : "stockout")}>{r.matched ? "Matched" : "Not in your catalogue, will be skipped"}</span></td></tr>)}</tbody></table></div>
        <button onClick={confirm}>Add {rows.filter(r => r.matched).length} lines to stock</button></>}
      {msg && <p className="muted">{msg}</p>}</section>
    <section><h2>Ask PharmaOpt</h2>{chat.map((c, i) => <div className="card" key={i}><b>{c.q}</b><p>{c.a}</p></div>)}
      <form className="row" onSubmit={ask}><input className="wide" value={q} onChange={e => setQ(e.target.value)} placeholder="e.g. What will expire soon? What should I buy with 800?" /><button>Ask</button></form></section>
    <footer>Decision support only. A pharmacist makes the final call.</footer></main>);
}
