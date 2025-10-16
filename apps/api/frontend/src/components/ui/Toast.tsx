import React, { createContext, useContext, useState, useCallback, useEffect } from "react";

type Toast = { id:number; title:string; tone?:"default"|"success"|"error" };
const Ctx = createContext<{ push:(t:Omit<Toast,"id">)=>void }>({ push: ()=>{} });

export function ToastProvider({ children }:{children:React.ReactNode}){
  const [items,setItems] = useState<Toast[]>([]);
  const push = useCallback((t:Omit<Toast,"id">)=>{
    const id = Date.now() + Math.random();
    setItems(s=>[...s, {id, ...t}]);
    setTimeout(()=> setItems(s=>s.filter(x=>x.id!==id)), 3000);
  },[]);
  return (
    <Ctx.Provider value={{push}}>
      {children}
      <div className="fixed bottom-4 right-4 space-y-2 z-50">
        {items.map(i=>(
          <div key={i.id}
            className={`rounded-xl px-4 py-2 shadow-card border text-sm
            ${i.tone==="error" ? "bg-red-50 border-red-200 text-red-800" :
              i.tone==="success" ? "bg-emerald-50 border-emerald-200 text-emerald-800" :
              "bg-white border-slate-200 text-slate-900"}`}>
            {i.title}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
export function useToast(){ return useContext(Ctx); }
