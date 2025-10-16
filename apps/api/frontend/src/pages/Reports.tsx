import React, { useEffect, useState } from "react";
import { listVehicles, runsByOrder, createRun } from "../api";

export default function Reports(){
  const [orderId,setOrderId]=useState<number|undefined>(undefined);
  const [vehicles,setVehicles]=useState<{id:number; name:string}[]>([]);
  const [vehicleId,setVehicleId]=useState<number|''>('');
  const [runs,setRuns]=useState<any[]>([]);

  useEffect(()=>{
    (async()=> setVehicles(await listVehicles()))();
  },[]);

  return (
    <div className="space-y-6">
      <div className="panel p-4">
        <h3 className="font-semibold mb-3">Deliveries — Loads (Log & Print)</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
          <div>
            <label className="text-sm">Order ID</label>
            <input className="input" placeholder="e.g., 1" value={orderId??''} onChange={e=>setOrderId(e.target.value? Number(e.target.value):undefined)} />
          </div>
          <div>
            <label className="text-sm">Vehicle</label>
            <select className="select" value={vehicleId} onChange={e=>setVehicleId(Number(e.target.value)||'')}>
              <option value="">-- Select --</option>
              {vehicles.map(v=><option key={v.id} value={v.id}>{v.name}</option>)}
            </select>
          </div>
          <div className="flex gap-2">
            <button className="btn" onClick={async ()=>{
              if(!orderId) return alert("Enter Order ID");
              setRuns(await runsByOrder(orderId));
            }}>Refresh Runs</button>
            <button className="btn btn-primary" onClick={async ()=>{
              if(!orderId || !vehicleId) return alert("Order + Vehicle required");
              const r = await createRun(orderId, Number(vehicleId), "Logged load");
              alert(`Run #${r.id} assigned rows ${r.row_start_seq}..${r.row_end_seq}`);
              setRuns(await runsByOrder(orderId));
            }}>Log Next 15 m³ → Vehicle</button>
          </div>
          <div className="flex gap-2">
            <a className="btn" target="_blank"
               href={orderId? `http://127.0.0.1:8000/api/reports3/${orderId}/loads.html${vehicleId?`?vehicleId=${vehicleId}`:''}` : '#'}>
               View HTML
            </a>
            <a className="btn btn-primary" target="_blank"
               href={orderId? `http://127.0.0.1:8000/api/reports3/${orderId}/loads.pdf${vehicleId?`?vehicleId=${vehicleId}`:''}` : '#'}>
               Download PDF
            </a>
          </div>
        </div>
      </div>

      <div className="panel p-4">
        <h3 className="font-semibold mb-2">Runs (this order)</h3>
        <div className="overflow-auto">
          <table className="table">
            <thead><tr><th>#</th><th>Vehicle</th><th>Rows</th><th>Volume</th><th>Note</th></tr></thead>
            <tbody>
              {runs.map(r=>(
                <tr key={r.id}>
                  <td>{r.load_seq}</td><td>{r.vehicle.name}</td>
                  <td>{r.row_start_seq} .. {r.row_end_seq}</td>
                  <td>{r.volume_m3.toFixed(3)} m³</td><td>{r.note}</td>
                </tr>
              ))}
              {runs.length===0 && <tr><td colSpan={5} className="text-center text-slate-500">No runs yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
