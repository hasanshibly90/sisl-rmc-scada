import React, { useEffect, useState } from "react";
import { Vehicle, listVehicles, createVehicle, updateVehicle, deleteVehicle } from "../api";

export default function Vehicles(){
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [name, setName] = useState(""); const [cap, setCap] = useState<number>(15);
  const [plate, setPlate] = useState(""); const [driver, setDriver] = useState("");

  const [editId, setEditId] = useState<number|null>(null);
  const [eName, setEName] = useState(""); const [eCap, setECap] = useState<number>(15);
  const [ePlate, setEPlate] = useState(""); const [eDriver, setEDriver] = useState("");

  const refresh = async ()=> setVehicles(await listVehicles());
  useEffect(()=>{ refresh(); },[]);

  const beginEdit = (v: Vehicle)=>{
    setEditId(v.id); setEName(v.name); setECap(v.capacity_m3);
    setEPlate(v.plate || ""); setEDriver(v.driver_name || "");
  };
  const cancelEdit = ()=>{ setEditId(null); };

  const saveEdit = async ()=>{
    if(editId==null) return;
    if(!eName.trim()) return alert("Name required");
    try{
      await updateVehicle(editId, { name: eName.trim(), capacity_m3: eCap, plate: ePlate || undefined, driver_name: eDriver || undefined });
      cancelEdit(); refresh();
    }catch(e:any){ alert(e.message || "Update failed"); }
  };

  const doDelete = async (id:number)=>{
    if(!confirm("Delete this vehicle? This cannot be undone.")) return;
    try{
      await deleteVehicle(id); refresh();
    }catch(e:any){ alert(e.message || "Delete failed. Vehicle may be used by delivery runs."); }
  };

  const doCreate = async ()=>{
    if(!name.trim()) return alert("Enter name");
    await createVehicle(name.trim(), cap || 15, plate || undefined, driver || undefined);
    setName(""); setCap(15); setPlate(""); setDriver(""); refresh();
  };

  return (
    <div className="space-y-6">
      <div className="panel p-4">
        <h3 className="font-semibold mb-2">Vehicles</h3>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 max-w-5xl">
          <input className="input" placeholder="Truck-XX" value={name} onChange={e=>setName(e.target.value)} />
          <input className="input" type="number" step="0.1" value={cap} onChange={e=>setCap(Number(e.target.value)||0)} />
          <input className="input" placeholder="Plate (optional)" value={plate} onChange={e=>setPlate(e.target.value)} />
          <input className="input" placeholder="Driver (optional)" value={driver} onChange={e=>setDriver(e.target.value)} />
          <button className="btn btn-primary" onClick={doCreate}>Add</button>
        </div>

        <div className="mt-4 overflow-auto">
          <table className="table">
            <thead>
              <tr>
                <th style={{width:60}}>ID</th><th>Name</th><th style={{width:120}}>Capacity (m³)</th>
                <th>Plate</th><th>Driver</th><th style={{width:200}}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {vehicles.map(v=>(
                <tr key={v.id}>
                  <td>{v.id}</td>
                  <td>{editId===v.id ? <input className="input" value={eName} onChange={e=>setEName(e.target.value)} /> : v.name}</td>
                  <td>{editId===v.id ? <input className="input" type="number" step="0.1" value={eCap} onChange={e=>setECap(Number(e.target.value)||0)} /> : v.capacity_m3}</td>
                  <td>{editId===v.id ? <input className="input" value={ePlate} onChange={e=>setEPlate(e.target.value)} /> : (v.plate || "-")}</td>
                  <td>{editId===v.id ? <input className="input" value={eDriver} onChange={e=>setEDriver(e.target.value)} /> : (v.driver_name || "-")}</td>
                  <td className="flex gap-2">
                    {editId===v.id ? (
                      <>
                        <button className="btn btn-primary" onClick={saveEdit}>Save</button>
                        <button className="btn" onClick={cancelEdit}>Cancel</button>
                      </>
                    ) : (
                      <>
                        <button className="btn" onClick={()=>beginEdit(v)}>Edit</button>
                        <button className="btn" onClick={()=>doDelete(v.id)}>Delete</button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
              {vehicles.length===0 && <tr><td colSpan={6} className="text-center text-slate-500">No vehicles yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
