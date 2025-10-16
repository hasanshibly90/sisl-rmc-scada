import React from "react";
import { NavLink } from "react-router-dom";
import {
  Gauge,          // Dashboard
  ClipboardList,  // Orders
  FlaskConical,   // Production
  FileText,       // Reports
  Users,          // Clients
  Beaker,         // Recipes
  Truck,          // Vehicles
  SlidersHorizontal // Settings
} from "lucide-react";

const links = [
  { to: "/",           label: "Dashboard",  icon: Gauge },
  { to: "/orders",     label: "Orders",     icon: ClipboardList },
  { to: "/production", label: "Production", icon: FlaskConical },
  { to: "/reports",    label: "Reports",    icon: FileText },
  { to: "/clients",    label: "Clients",    icon: Users },
  { to: "/recipes",    label: "Recipes",    icon: Beaker },
  { to: "/vehicles",   label: "Vehicles",   icon: Truck },
  { to: "/settings",   label: "Settings",   icon: SlidersHorizontal },
];

export default function Sidebar(){
  return (
    <aside className="sidebar p-4">
      <div className="flex items-center gap-3 px-2 py-3">
        <div className="h-9 w-9 rounded-lg bg-sisl-primary/20 grid place-items-center text-blue-400 font-bold">S</div>
        <div className="text-white font-semibold leading-tight">
          SISL<br/><span className="text-xs text-slate-300">RMC SCADA</span>
        </div>
      </div>

      <nav className="mt-4 space-y-1">
        {links.map(({to,label,icon:Icon})=>(
          <NavLink
            key={to}
            to={to}
            className={({isActive})=>`nav-link ${isActive?'active':''}`}
            end={to === "/"}
          >
            <Icon size={18} /><span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="mt-6 text-[11px] text-slate-400 px-4">© SISL • Professional Build</div>
    </aside>
  );
}
