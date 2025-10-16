import React, { useEffect } from "react";
import Button from "./Button";

export default function Modal({ open, title, onClose, children }:{
  open:boolean; title?:string; onClose:()=>void; children:React.ReactNode;
}){
  useEffect(()=>{
    const onEsc=(e:KeyboardEvent)=>{ if(e.key==="Escape") onClose(); };
    document.addEventListener("keydown", onEsc);
    return ()=>document.removeEventListener("keydown", onEsc);
  },[onClose]);

  if(!open) return null;
  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="absolute inset-0 flex items-center justify-center p-4">
        <div className="w-full max-w-2xl rounded-2xl bg-white shadow-card border border-slate-200">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
            <h3 className="font-semibold">{title}</h3>
            <Button onClick={onClose}>Close</Button>
          </div>
          <div className="p-4">{children}</div>
        </div>
      </div>
    </div>
  );
}
