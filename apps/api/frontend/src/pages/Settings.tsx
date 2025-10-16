import React, { useEffect, useState } from "react";
import { getSettings, updateSettings, listRecipes } from "../api";

export default function SettingsPage(){
  const [tolerance, setTolerance] = useState<number>(2.5);
  const [mixer, setMixer] = useState<number>(1.0);
  const [defRecipeId, setDefRecipeId] = useState<number|''>('');
  const [recipes, setRecipes] = useState<{id:number; name:string}[]>([]);

  const refresh = async ()=>{
    const st = await getSettings();
    setTolerance(st.tolerance_pct ?? 2.5);
    setMixer(st.mixer_capacity_m3 ?? 1.0);
    setDefRecipeId(st.default_recipe_id ?? '');
    setRecipes(await listRecipes());
  };
  useEffect(()=>{ refresh(); },[]);

  return (
    <div className="space-y-6">
      <div className="panel p-4 max-w-2xl">
        <h3 className="font-semibold mb-3">System Settings</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="text-sm">Tolerance %</label>
            <input className="input" type="number" step="0.1" value={tolerance}
              onChange={e=>setTolerance(Number(e.target.value)||0)} />
          </div>
          <div>
            <label className="text-sm">Mixer Capacity (m³)</label>
            <input className="input" type="number" step="0.1" value={mixer}
              onChange={e=>setMixer(Number(e.target.value)||0)} />
          </div>
          <div className="md:col-span-2">
            <label className="text-sm">Default Recipe</label>
            <select className="select" value={defRecipeId} onChange={e=>setDefRecipeId(Number(e.target.value)||'')}>
              <option value="">-- None --</option>
              {recipes.map(r=><option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
          <div className="md:col-span-2">
            <button className="btn btn-primary" onClick={async ()=>{
              await updateSettings({
                tolerance_pct: tolerance,
                mixer_capacity_m3: mixer,
                default_recipe_id: defRecipeId === '' ? null : Number(defRecipeId),
              });
              alert("Settings updated.");
              refresh();
            }}>Save Settings</button>
          </div>
        </div>
      </div>

      <div className="panel p-4 max-w-2xl">
        <h3 className="font-semibold mb-2">Info</h3>
        <p className="text-sm text-slate-600">
          These settings affect production simulation (tolerance jitter), planning stats (mixer capacity),
          and default setpoints used to scale “Set” in 1 m³ rows.
        </p>
      </div>
    </div>
  );
}
