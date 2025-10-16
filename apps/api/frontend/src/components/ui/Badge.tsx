import React from "react";
type Tone = "default" | "green" | "amber";
export default function Badge({ tone="default", className="", children }:{
  tone?:Tone; className?:string; children:React.ReactNode;
}){
  const map = { default:"badge", green:"badge badge-green", amber:"badge badge-amber" };
  return <span className={`${map[tone]} ${className}`}>{children}</span>;
}
