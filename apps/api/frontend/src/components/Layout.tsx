import React from "react";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

export default function Layout({ children }: { children: React.ReactNode }){
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="min-h-screen flex flex-col">
        <Topbar />
        <main className="p-4 md:p-6 lg:p-8 bg-slate-50 flex-1">
          {children}
        </main>
      </div>
    </div>
  );
}
