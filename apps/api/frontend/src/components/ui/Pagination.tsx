import React from "react";
import Button from "./Button";

export default function Pagination({page,totalPages,onChange}:{page:number; totalPages:number; onChange:(p:number)=>void;}){
  return (
    <div className="flex items-center gap-2">
      <Button onClick={()=>onChange(Math.max(1,page-1))} disabled={page<=1}>Prev</Button>
      <span className="text-sm">Page {page} / {totalPages || 1}</span>
      <Button onClick={()=>onChange(Math.max(1, Math.min(totalPages, page+1)))} disabled={page>=totalPages}>Next</Button>
    </div>
  );
}
