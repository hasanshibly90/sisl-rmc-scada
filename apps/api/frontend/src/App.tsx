import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";

/* Minimal placeholder pages (no API calls yet) */
import Dashboard from "./pages/Dashboard";
import Clients from "./pages/Clients";
import Vehicles from "./pages/Vehicles";
import Recipes from "./pages/Recipes";
import Settings from "./pages/Settings";
import Orders from "./pages/Orders";
import Production from "./pages/Production";
import Reports from "./pages/Reports";

export default function App(){
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/clients" element={<Clients />} />
          <Route path="/vehicles" element={<Vehicles />} />
          <Route path="/recipes" element={<Recipes />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/orders" element={<Orders />} />
          <Route path="/production" element={<Production />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
