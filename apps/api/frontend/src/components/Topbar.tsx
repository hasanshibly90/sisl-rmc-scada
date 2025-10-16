import React from "react";
import { Bell } from "lucide-react";
import { useLocation } from "react-router-dom";

const titles: Record<string,string> = {
  "/": "Dashboard",
  "/clients": "Clients",
  "/vehicles": "Vehicles",
  "/recipes": "Recipes",
  "/settings": "Settings",
  "/orders": "Orders",
  "/production": "Production",
  "/reports": "Reports",
};

export default function Topbar(){
  const path = useLocation().pathname;
  const title = titles[path] ?? "SISL — RMC SCADA";
  return (
    <header className="topbar">
      <div className="font-semibold">{title}</div>
      <div className="flex items-center gap-2">
        <button className="btn-ghost rounded-full p-2" title="Notifications">
          <Bell size={18}/>
        </button>
      </div>
    </header>
  );
}
