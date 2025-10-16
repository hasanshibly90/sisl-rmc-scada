import React, { useEffect, useState } from "react";
import { Recipe, Mat, listRecipes, createRecipe, updateRecipe, deleteRecipe, getSettings } from "../api";

const emptyMat: Mat = {cement:0,sand:0,agg1:0,agg2:0,water:0,admix:0};
const mats: (keyof Mat)[] = ["cement","sand","agg1","agg2","water","admix"];

export default function Recipes(){
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [name, setName] = useState("");
  const [sp, setSp] = useState<Mat>({...emptyMat});

  const [editId, setEditId] = useState<number|null>(null);
  const [eName, setEName] = useState("");
  const [eSp, setESp] = useState<Mat>({...emptyMat});

  const refresh = async ()=>{
    setRecipes(await listRecipes());
    const st = await getSettings();
    if(st?.default_recipe) setSp(st.default_recipe.setpoints);
  };
  useEffect(()=>{ refresh(); },[]);

  const beginEdit = (r: Recipe)=>{
    setEditId(r.id); setEName(r.name); setESp({...r.setpoints});
  };
  const cancelEdit = ()=>{ setEditId(null); };

  const saveEdit = async ()=>{
    if(editId==null) return;
    if(!eName.trim()) return alert("Name required");
    try{
      await updateRecipe(editId, { name: eName.trim(), setpoints: eSp });
      cancelEdit(); refresh();
    }catch(e:any){ alert(e.message || "Update failed"); }
  };

  const doDelete = async (id:number)=>{
    if(!confirm("Delete this recipe? This cannot be undone.")) return;
    try{
      await deleteRecipe(id); refresh();
    }catch(e:any){ alert(e.message || "Delete failed. Recipe may be used by orders."); }
  };

  const doCreate = async ()=>{
    if(!name.trim()) return alert("Enter recipe name");
    await createRecipe(name.trim(), sp); setName("");
    setSp({...emptyMat}); refresh();
  };

  return (
    <div className="space-y-6">
      <div className="panel p-4">
        <h3 className="font-semibold mb-2">Recipes (per-m³ setpoints)</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 max-w-5xl">
          <input className="input md:col-span-3" placeholder="Name (e.g., M25 DEFAULT)" value={name} onChange={e=>setName(e.target.value)} />
          {mats.map(k=>(
            <div key={k} className="flex items-center gap-2">
              <label className="w-20 capitalize">{k}</label>
              <input className="input" type="number" step="0.001"
                     value={sp[k]} onChange={e=>setSp({...sp, [k]: Number(e.target.value)})}/>
            </div>
          ))}
          <div className="md:col-span-3">
            <button className="btn btn-primary" onClick={doCreate}>Save Recipe</button>
          </div>
        </div>

        <div className="mt-6 overflow-auto">
          <table className="table">
            <thead>
              <tr>
                <th style={{width:60}}>ID</th>
                <th style={{minWidth:180}}>Name</th>
                {mats.map(m=> <th key={m} className="capitalize">{m}</th>)}
                <th style={{width:200}}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {recipes.map(r=>(
                <tr key={r.id}>
                  <td>{r.id}</td>
                  <td>
                    {editId===r.id
                      ? <input className="input" value={eName} onChange={e=>setEName(e.target.value)} />
                      : r.name}
                  </td>
                  {mats.map(m=>(
                    <td key={m}>
                      {editId===r.id
                        ? <input className="input" type="number" step="0.001"
                                 value={eSp[m]} onChange={e=>setESp({...eSp, [m]: Number(e.target.value)})}/>
                        : r.setpoints[m]}
                    </td>
                  ))}
                  <td className="flex gap-2">
                    {editId===r.id ? (
                      <>
                        <button className="btn btn-primary" onClick={saveEdit}>Save</button>
                        <button className="btn" onClick={cancelEdit}>Cancel</button>
                      </>
                    ) : (
                      <>
                        <button className="btn" onClick={()=>beginEdit(r)}>Edit</button>
                        <button className="btn" onClick={()=>doDelete(r.id)}>Delete</button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
              {recipes.length===0 && <tr><td colSpan={2 + mats.length + 1} className="text-center text-slate-500">No recipes yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
