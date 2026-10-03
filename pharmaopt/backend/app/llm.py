"""LLM layer: parses the question, calls the engine for verified facts, then explains them.
Set OLLAMA_URL (e.g. http://localhost:11434) to use Qwen2.5-7B; otherwise a template explainer is used."""
import os, re, json, urllib.request
from . import engine

def facts_for(q, meds, stock):
    ql = q.lower(); nums = [int(x) for x in re.findall(r"\d+", q)]
    if re.search(r"buy|order|purchase|budget", ql):
        return "purchase_plan", engine.recommend(meds, stock, nums[0] if nums else 1000)
    rows = engine.analyze(meds, stock)
    if "expir" in ql: return "expiry_risk", [r for r in rows if r["at_risk_of_expiry"] > 0]
    if re.search(r"stock ?out|low|run out", ql): return "stockout_risk", [r for r in rows if r["status"] == "stockout"]
    return "overview", rows

def explain(q, intent, facts):
    prompt = ("You are a pharmacy inventory assistant. Answer ONLY using these verified facts; never invent numbers. "
              f"Question: {q}\nFacts: {json.dumps(facts)}")
    url = os.getenv("OLLAMA_URL")
    if url:
        try:
            req = urllib.request.Request(url + "/api/generate", method="POST", headers={"Content-Type": "application/json"},
                data=json.dumps({"model": os.getenv("LLM_MODEL", "qwen2.5:7b-instruct"), "prompt": prompt, "stream": False}).encode())
            return json.load(urllib.request.urlopen(req, timeout=60))["response"]
        except Exception: pass
    if intent == "purchase_plan":
        return f"I recommend {len(facts['orders'])} orders costing {facts['spent']} of your {facts['budget']} budget. " + " ".join(f"{o['medicine']}: buy {o['order_qty']} ({o['reason']})" for o in facts["orders"])
    if not facts: return "Nothing needs attention right now."
    return "; ".join(f"{r['medicine']}: {r['in_stock']} in stock, {r['days_cover']} days cover, {r['at_risk_of_expiry']} units likely to expire unsold" for r in facts)
