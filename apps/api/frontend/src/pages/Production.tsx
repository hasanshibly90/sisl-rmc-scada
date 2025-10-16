// frontend/src/pages/Production.tsx
import React, { useEffect, useMemo, useState } from "react";
import {
  getOrder, startNextRow, markDone,
  listVehicles, runsByOrder, createRunForRange,
  pauseOrder, resumeOrder, stopOrder, orderSummary
} from "../api";
import {
  Card, Panel, Button, Input, Select,
  Table, THead, TBody, TR, TH, TD, useToast
} from "../components/ui";
import { useLocation } from "react-router-dom";

const LOAD_CAP_M3 = 15;
type LoadedOrder = Awaited<ReturnType<typeof getOrder>>;
type Vehicle = Awaited<ReturnType<typeof listVehicles>>[number];
type RunRow = Awaited<ReturnType<typeof runsByOrder>>[number];
type BatchView = { no:number; startSeq:number; endSeq:number; rows:any[]; done:number; total:number; plannedM3:number; status:"running"|"done"|"queued"; };

export default function Production(){
  const toast = useToast();
  const loc = useLocation(); const qs = new URLSearchParams(loc.search);
  const qsId = qs.get("orderId");

  const [orderIdInput, setOrderIdInput] = useState("");
  const [orderId, setOrderId] = useState<number|null>(null);
  const [order, setOrder] = useState<LoadedOrder|null>(null);
  const [countdown, setCountdown] = useState(0);
  const [batchAutoRun, setBatchAutoRun] = useState(false);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [selectedVehicleId, setSelectedVehicleId] = useState<number| "">("");
  const [summary, setSummary] = useState<any>(null);

  useEffect(()=>{ (async()=>{ try{ setVehicles(await listVehicles()); }catch{} })(); },[]);
  useEffect(()=>{ if(qsId){ const id = parseInt(qsId,10); if(!Number.isNaN(id)){ setOrderIdInput(String(id)); setOrderId(id); refreshAll(id); } } },[qsId]);

  const refreshAll = async(id:number)=>{ await Promise.all([refreshOrder(id), refreshRuns(id), refreshSummary(id)]); };
  const refreshOrder = async(id:number)=>{ try{ setOrder(await getOrder(id)); }catch{ setOrder(null); toast.push({title:"Order not found", tone:"error"}); } };
  const refreshRuns = async(id:number)=>{ try{ setRuns(await runsByOrder(id)); }catch{ setRuns([]); } };
  const refreshSummary = async(id:number)=>{ try{ setSummary(await orderSummary(id)); }catch{ setSummary(null); } };

  const onLoadOrder = ()=>{ const id = parseInt(orderIdInput.trim(),10); if(Number.isNaN(id)||id<=0){ toast.push({title:"Enter a valid Order ID",tone:"error"}); return; } setOrderId(id); refreshAll(id); };

  const rows = order?.rows ?? [];
  const batches = useMemo<BatchView[]>(()=>{
    if(!order || rows.length===0) return [];
    const totalM3 = rows.reduce((a,r)=>a+Number(r.planned_m3||0),0);
    const totalB = Math.max(1, Math.ceil(totalM3/LOAD_CAP_M3));
    const perB = 15; const out:BatchView[] = [];
    for(let i=0;i<totalB;i++){
      const slice = rows.slice(i*perB, i*perB+perB);
      if(!slice.length) break;
      const done = slice.filter(r=>r.state==="done").length;
      const total = slice.length;
      const plannedM3 = slice.reduce((a,r)=>a+Number(r.planned_m3||0),0);
      const status = done===total ? "done" : (slice.some((r:any)=>r.state==="running")||slice.some((r:any)=>r.state==="done")) ? "running" : "queued";
      out.push({no:i+1,startSeq:slice[0]?.seq_no??0,endSeq:slice[slice.length-1]?.seq_no??0,rows:slice,done,total,plannedM3,status});
    }
    return out;
  },[order, rows]);

  const current = useMemo(()=>{ if(!batches.length) return undefined; const i=batches.findIndex(b=>b.status!=="done"); return i>=0?batches[i]:batches[batches.length-1]; },[batches]);
  const previousDone = useMemo(()=> batches.filter(b=> current ? b.no<current.no : false),[batches,current]);

  const runForBatch = (b:BatchView)=> runs.find(r=> r.row_start_seq===b.startSeq && r.row_end_seq===b.endSeq);
  const vehicleNameForRun = (r?:RunRow)=> r? r.vehicle?.name : undefined;

  useEffect(()=>{
    if(!current) return;
    const existing = runForBatch(current);
    if(existing?.vehicle?.id){ setSelectedVehicleId(existing.vehicle.id); return; }
    if(vehicles.length>0){ const idx=(current.no-1)%vehicles.length; setSelectedVehicleId(vehicles[idx].id); } else setSelectedVehicleId("");
  // eslint-disable-next-line
  },[current?.no, vehicles.length]);

  const onStartNext = async ()=>{
    if(!orderId) return toast.push({title:"Load an order first",tone:"error"});
    try{
      const started = await startNextRow(orderId);
      setCountdown(5);
      const t=setInterval(()=>{ setCountdown(c=>{ if(c<=1){ clearInterval(t); markDone(orderId, started.rowId).then(()=>refreshAll(orderId)); return 0;} return c-1;}); },1000);
    }catch(e:any){ toast.push({title:e?.message||"Start-next failed",tone:"error"}); }
  };

  const logRunForBatch = async(batch:BatchView)=>{
    if(!orderId) return;
    if(runForBatch(batch)) return;
    const v = vehicles.find(x=>x.id===selectedVehicleId) ?? (vehicles.length? vehicles[(batch.no-1)%vehicles.length] : null);
    if(!v){ toast.push({title:"Select a vehicle",tone:"error"}); return; }
    const note = `Auto-log: Batch-${batch.no} (${batch.startSeq}..${batch.endSeq})`;
    await createRunForRange(orderId, v.id, batch.startSeq, batch.endSeq, note);
    toast.push({title:`Logged run: Batch-${batch.no} → ${v.name}`,tone:"success"});
    await refreshRuns(orderId);
  };

  const onRunThisBatch = async ()=>{
    if(!orderId || !current){ toast.push({title:"Load an order first",tone:"error"}); return; }
    setBatchAutoRun(true);
    try{
      while(true){
        const latest = await getOrder(orderId);
        const slice = (latest.rows||[]).filter((r:any)=> r.seq_no>=current.startSeq && r.seq_no<=current.endSeq);
        const pendingInBatch = slice.find((r:any)=> r.state==="pending");
        const anyPending = (latest.rows||[]).find((r:any)=> r.state==="pending");
        if(!pendingInBatch || !anyPending) break;
        const started = await startNextRow(orderId);
        await new Promise(r=>setTimeout(r,5000));
        await markDone(orderId, started.rowId);
        await refreshAll(orderId);
      }
      const verify = await getOrder(orderId);
      const doneAll = (verify.rows||[]).filter((r:any)=> r.seq_no>=current.startSeq && r.seq_no<=current.endSeq).every((r:any)=>r.state==="done");
      if(doneAll) await logRunForBatch(current);
      toast.push({title:`Batch-${current.no} processed`,tone:"success"});
    }catch{ toast.push({title:`Batch-${current?.no} failed`,tone:"error"}); }
    finally{ setBatchAutoRun(false); if(orderId) refreshAll(orderId); }
  };

  // Pause / Resume / Stop + Summary
  const onPause = async()=>{ if(!orderId) return; await pauseOrder(orderId); toast.push({title:"Paused",tone:"success"}); await refreshAll(orderId); };
  const onResume= async()=>{ if(!orderId) return; await resumeOrder(orderId); toast.push({title:"Resumed",tone:"success"}); await refreshAll(orderId); };
  const onStop  = async()=>{ if(!orderId) return; await stopOrder(orderId); toast.push({title:"Stopped",tone:"success"}); await refreshAll(orderId); };
  const overallPct = useMemo(()=>{ const total=order?.rows?.length??0; const done=order?.rows?.filter((r:any)=>r.state==="done").length??0; return total? Math.round(done*100/total):0; },[order]);

  // === Dynamic button tones by status ===
  const status = order?.status ?? "stopped";
  const isRunning = status==="running";
  const isPaused  = status==="paused";
  const isStopped = status==="stopped";
  const isDone    = status==="done";

  // utility to join classes
  const cx = (...a:(string|false|undefined)[]) => a.filter(Boolean).join(" ");

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-center">
          <div>
            <h1 className="leading-tight">Production</h1>
            <p className="text-sm text-slate-600 mt-1">
              Select a vehicle for the current batch. You can pause / resume / stop safely. Summary shows produced totals.
            </p>
          </div>
          <form className="flex items-center gap-3" onSubmit={(e)=>{e.preventDefault(); onLoadOrder();}}>
            <label htmlFor="orderId" className="text-sm font-medium text-slate-600">Order ID</label>
            <Input id="orderId" placeholder="e.g., 1" value={orderIdInput} onChange={e=>setOrderIdInput(e.target.value)} className="h-10 w-48 rounded-full px-4" />
            <Button type="submit" variant="primary" className="h-10 rounded-full px-5">Load</Button>
          </form>
        </div>
      </Card>

      {!order && (
        <Panel><div className="text-sm text-slate-600">No order loaded. Use Order ID above or the Orders page “Run”.</div></Panel>
      )}

      {order && (
        <Panel>
          <div className="flex items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="text-sm">Order <b>#{order.id}</b> — <b>{order.client?.name ?? "-"}</b> — {order.recipe?.name ?? "-"} — {order.total_m3} m³</div>
              <div className="text-sm">Rows planned: {rows.length} • Status: <b>{status}</b></div>
              <div className="w-full h-2 bg-slate-200 rounded-full">
                <div className="h-2 rounded-full bg-sisl-accent" style={{width:`${overallPct}%`}}/>
              </div>
              <div className="text-xs text-slate-600">Progress: {overallPct}%</div>
            </div>

            {/* ====== STATUS-AWARE CONTROLS ====== */}
            <div className="flex flex-wrap items-center gap-2">
              {/* Start Next */}
              <Button
                onClick={onStartNext}
                disabled={!isRunning || !orderId}
                variant={isRunning ? "primary" : "default"}
                className={cx("rounded-full px-4 h-9",
                  !isRunning && "opacity-60 cursor-not-allowed")}
              >
                Start Next (1 m³)
              </Button>

              {/* Run batch */}
              <Button
                onClick={onRunThisBatch}
                disabled={!isRunning || batchAutoRun || !orderId}
                className={cx("rounded-full px-4 h-9",
                  isRunning ? "bg-blue-50 border-slate-300 hover:bg-blue-100" : "opacity-60 cursor-not-allowed")}
              >
                Run batch
              </Button>

              {/* Pause (amber when running) */}
              <Button
                onClick={onPause}
                disabled={!isRunning || !orderId}
                className={cx("rounded-full px-4 h-9",
                  isRunning ? "bg-amber-500 text-white border-transparent hover:bg-amber-600" : "opacity-60 cursor-not-allowed")}
              >
                Pause
              </Button>

              {/* Resume (green when paused or stopped) */}
              <Button
                onClick={onResume}
                disabled={!(isPaused || isStopped) || !orderId}
                className={cx("rounded-full px-4 h-9",
                  (isPaused || isStopped) ? "bg-emerald-600 text-white border-transparent hover:bg-emerald-700" : "opacity-60 cursor-not-allowed")}
              >
                Resume
              </Button>

              {/* Stop (red when running/paused) */}
              <Button
                onClick={onStop}
                disabled={!(isRunning || isPaused) || !orderId}
                className={cx("rounded-full px-4 h-9",
                  (isRunning || isPaused) ? "bg-red-600 text-white border-transparent hover:bg-red-700" : "opacity-60 cursor-not-allowed")}
              >
                Stop
              </Button>
            </div>
          </div>

          {/* Summary */}
          {summary && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
              <div className="kpi"><div className="text-xs text-slate-500">Produced</div><div className="text-2xl font-semibold">{summary.produced_m3} m³</div></div>
              <div className="kpi"><div className="text-xs text-slate-500">Remaining</div><div className="text-2xl font-semibold">{summary.remaining_m3} m³</div></div>
              <div className="kpi"><div className="text-xs text-slate-500">Water ACT</div><div className="text-xl font-semibold">{summary.act_totals.water}</div></div>
              <div className="kpi"><div className="text-xs text-slate-500">Δ materials</div>
                <div className="text-xl font-semibold">
                  {Object.values(summary.delta_totals).reduce((a:any,b:any)=>a+Number(b),0).toFixed(3)}
                </div>
              </div>
            </div>
          )}
        </Panel>
      )}

      {/* Batches */}
      {order && current && (
        <Panel>
          <h2 className="mb-3">Batches</h2>
          {/* current */}
          <div className="rounded-2xl border border-slate-200 p-4 mb-2">
            <div className="flex items-center justify-between">
              <div className="text-sm"><b>Batch-{current.no}</b> ({current.startSeq} … {current.endSeq}) • Planned: {current.plannedM3.toFixed(3)} m³</div>
              <div className="flex items-center gap-2">
                {(() => {
                  const r = runForBatch(current); const vName = vehicleNameForRun(r);
                  if (vName) return <span className="badge">Vehicle: <b>&nbsp;{vName}</b></span>;
                  return (
                    <>
                      <span className="text-sm text-slate-600">Vehicle</span>
                      <Select value={selectedVehicleId} onChange={e=>setSelectedVehicleId(e.target.value? Number(e.target.value):"")}>
                        <option value="">-- Select vehicle --</option>
                        {vehicles.map(v=> <option key={v.id} value={v.id}>{v.name}</option>)}
                      </Select>
                    </>
                  );
                })()}
              </div>
            </div>
            <div className="flex items-center justify-between mt-3">
              <span className="badge badge-amber">{current.done} / {current.total} running</span>
              <div className="w-full h-2 bg-slate-200 rounded-full mx-4">
                <div className="h-2 rounded-full bg-sisl-primary" style={{width:`${current.total? Math.round(current.done*100/current.total):0}%`}}/>
              </div>
              <Button onClick={onRunThisBatch} disabled={!isRunning || batchAutoRun} className={cx(isRunning? "" : "opacity-60 cursor-not-allowed")}>
                Run this batch
              </Button>
            </div>
          </div>

          {/* previous done */}
          {previousDone.map(b=>{
            const r=runForBatch(b); const vName=vehicleNameForRun(r);
            return (
              <div key={b.no} className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 mb-2">
                <div className="text-sm"><b>Batch-{b.no}</b> ({b.startSeq} … {b.endSeq}) • Planned: {b.plannedM3.toFixed(3)} m³</div>
                <div className="flex items-center gap-2">
                  {vName && <span className="badge">Vehicle: <b>&nbsp;{vName}</b></span>}
                  <span className="badge badge-green">done</span>
                </div>
              </div>
            );
          })}
        </Panel>
      )}
    </div>
  );
}
