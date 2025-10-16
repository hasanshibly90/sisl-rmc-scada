import React, { useEffect, useState } from "react";
import KPI from "../components/KPI";
import { listClients, listVehicles, listRecipes, getOrder, runsByOrder } from "../api";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export default function Dashboard(){
  const [clientsCount, setClientsCount] = useState(0);
  const [vehiclesCount, setVehiclesCount] = useState(0);
  const [recipesCount, setRecipesCount] = useState(0);
  const [orderId, setOrderId] = useState<number|''>('');
  const [progress, setProgress] = useState<{done:number; total:number}>({done:0,total:0});
  const [runs, setRuns] = useState<any[]>([]);

  useEffect(()=>{
    (async()=>{
      setClientsCount((await listClients()).length);
      setVehiclesCount((await listVehicles()).length);
      setRecipesCount((await listRecipes()).length);
    })();
  },[]);

  const refreshOrder = async ()=>{
    if(!orderId) return;
    const o = await getOrder(Number(orderId));
    const done = o.rows.filter(r=>r.state==="done").length;
    setProgress({done, total:o.rows.length});
    setRuns(await runsByOrder(Number(orderId)));
  };

  const chartData = Array.from({length:7}).map((_,i)=>({ day:`D${i+1}`, m3: Math.round(20 + Math.random()*30)}));
  const pct = progress.total? Math.round(progress.done*100/progress.total): 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPI label="Clients" value={String(clientsCount)} />
        <KPI label="Vehicles" value={String(vehiclesCount)} />
        <KPI label="Recipes" value={String(recipesCount)} />
        <KPI label="Order Progress" value={`${pct}%`} hint={`${progress.done} of ${progress.total} rows`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="panel p-4 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Weekly Production (m³)</h3>
          </div>
          <div className="h-64 mt-2">
            <ResponsiveContainer>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="m3" stroke="#2563eb" strokeWidth={2} dot={false}/>
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="panel p-4">
          <h3 className="font-semibold">Current Order Snapshot</h3>
          <div className="flex gap-2 mt-3">
            <input className="input" placeholder="Order ID" value={orderId??''} onChange={e=>setOrderId(e.target.value? Number(e.target.value):'')} />
            <button className="btn btn-primary" onClick={refreshOrder}>Refresh</button>
          </div>
          <div className="mt-4">
            <div className="text-sm">Rows Done: <b>{progress.done}</b> / {progress.total}</div>
            <div className="w-full h-2 bg-slate-200 rounded-full mt-2">
              {/* FIXED: use bg-sisl-accent */}
              <div className="h-2 rounded-full bg-sisl-accent" style={{width:`${pct}%`}}/>
            </div>
          </div>
          <div className="mt-4">
            <h4 className="font-medium mb-2">Recent Loads</h4>
            <div className="max-h-40 overflow-auto">
              <table className="table">
                <thead><tr><th>#</th><th>Vehicle</th><th>Rows</th><th>Volume</th></tr></thead>
                <tbody>
                  {runs.map(r=>(
                    <tr key={r.id}>
                      <td>{r.load_seq}</td>
                      <td>{r.vehicle.name}</td>
                      <td>{r.row_start_seq} .. {r.row_end_seq}</td>
                      <td>{r.volume_m3.toFixed(3)} m³</td>
                    </tr>
                  ))}
                  {runs.length===0 && <tr><td colSpan={4} className="text-center text-slate-500">No loads logged yet.</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        </div>

      </div>

      <div className="panel p-4">
        <h3 className="font-semibold">Quick Actions</h3>
        <div className="flex flex-wrap gap-2 mt-3">
          <a className="btn" href="/orders">Create Order</a>
          <a className="btn" href="/production">Run Production</a>
          <a className="btn" href="/reports">Generate PDF Report</a>
          <a className="btn" href="/master">Manage Master Data</a>
        </div>
      </div>
    </div>
  );
}
