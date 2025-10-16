import React from "react";

export default function KPI({ label, value, hint }: {label:string; value:string; hint?:string}){
  return (
    <div className="soft p-4">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-2xl font-semibold mt-1">{value}</div>
      {hint && <div className="text-[11px] text-slate-500 mt-1">{hint}</div>}
    </div>
  );
}
