const BASE = "http://127.0.0.1:8000";
const TIMEOUT_MS = 15000;

async function http<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(BASE + path, {
      ...opts,
      headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
      signal: ctrl.signal,
    });
    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status} ${res.statusText} — ${txt}`);
    }
    return (await res.json()) as T;
  } finally {
    clearTimeout(t);
  }
}

/* ---------- Types ---------- */
export type Client = { id: number; name: string; cell?: string|null; email?: string|null; office_addr?: string|null; delivery_addr?: string|null; };
export type Vehicle = { id: number; name: string; capacity_m3: number; plate?: string|null; driver_name?: string|null; };
export type Mat = { cement:number; sand:number; agg1:number; agg2:number; water:number; admix:number };
export type Recipe = { id:number; name:string; setpoints: Mat };
export type OrderRow = { id:number; seq_no:number; planned_m3:number; state:string; actual?:Mat|null; car_run_id?:number|null };
export type Order = { id:number; client:{id:number; name:string}; recipe:{id:number; name:string; setpoints:Mat}; total_m3:number; status:string; rows:OrderRow[]; };
export type LiteOrder = { id:number; client:{id:number; name:string}; recipe:{id:number; name:string}; total_m3:number; status:string; created_at:string };
export type CarRun = { id:number; load_seq:number; vehicle?:{id:number; name:string}|null; row_start_seq:number; row_end_seq:number; volume_m3:number; note?:string };

/* ---------- Clients ---------- */
export async function listClients(){ return http<Client[]>("/api/clients"); }
export async function createClient(p:{name:string; cell?:string; email?:string; office_addr?:string; delivery_addr?:string}){ return http<{id:number}>("/api/clients",{method:"POST",body:JSON.stringify(p)}); }
export async function updateClient(id:number, p:{name?:string; cell?:string|null; email?:string|null; office_addr?:string|null; delivery_addr?:string|null}){ return http<{ok:boolean}>(`/api/clients/${id}`,{method:"PUT",body:JSON.stringify(p)}); }
export async function deleteClient(id:number){ return http<{ok:boolean}>(`/api/clients/${id}`,{method:"DELETE"}); }

/* ---------- Vehicles ---------- */
export async function listVehicles(){ return http<Vehicle[]>("/api/vehicles"); }
export async function createVehicle(name:string, capacity_m3=15, plate?:string, driver_name?:string){ return http<{id:number}>("/api/vehicles",{method:"POST",body:JSON.stringify({name,capacity_m3,plate,driver_name})}); }
export async function updateVehicle(id:number, p:Partial<Pick<Vehicle,"name"|"capacity_m3"|"plate"|"driver_name">>){ return http<{ok:boolean}>(`/api/vehicles/${id}`,{method:"PUT",body:JSON.stringify(p)}); }
export async function deleteVehicle(id:number){ return http<{ok:boolean}>(`/api/vehicles/${id}`,{method:"DELETE"}); }

/* ---------- Recipes ---------- */
export async function listRecipes(){ return http<Recipe[]>("/api/recipes"); }
export async function createRecipe(name:string, setpoints:Mat){ return http<{id:number}>("/api/recipes",{method:"POST",body:JSON.stringify({name,setpoints})}); }
export async function updateRecipe(id:number, p:{name?:string; setpoints?:Mat}){ return http<{ok:boolean}>(`/api/recipes/${id}`,{method:"PUT",body:JSON.stringify(p)}); }
export async function deleteRecipe(id:number){ return http<{ok:boolean}>(`/api/recipes/${id}`,{method:"DELETE"}); }

/* ---------- Settings ---------- */
export async function getSettings(){ return http<any>("/api/settings"); }
export async function updateSettings(p:{tolerance_pct?:number; mixer_capacity_m3?:number; default_recipe_id?:number|null}){ return http<any>("/api/settings",{method:"PUT",body:JSON.stringify(p)}); }

/* ---------- Orders ---------- */
export async function createOrder(clientId:number, recipeId:number, totalM3:number){ return http<{id:number}>("/api/orders",{method:"POST",body:JSON.stringify({clientId,recipeId,totalM3})}); }
export async function getOrder(id:number){ return http<Order>(`/api/orders/${id}`); }
export async function listOrders(limit=100){ return http<LiteOrder[]>(`/api/orders?${new URLSearchParams({limit:String(limit)})}`); }
export async function updateOrder(id:number, p:{clientId?:number; recipeId?:number; totalM3?:number; status?:string}){ return http<{ok:boolean; id:number}>(`/api/orders/${id}`,{method:"PUT",body:JSON.stringify(p)}); }
export async function deleteOrder(id:number){ return http<{ok:boolean}>(`/api/orders/${id}`,{method:"DELETE"}); }
export async function startNextRow(orderId:number){ return http<{rowId:number; seq_no:number}>(`/api/orders/${orderId}/start-next`,{method:"POST"}); }
export async function markDone(orderId:number, rowId:number){ return http<any>(`/api/orders/${orderId}/rows/${rowId}/mark-done`,{method:"POST",body:JSON.stringify({simulate:true})}); }

/* ---- Pause/Resume/Stop + Summary ---- */
export async function pauseOrder(id:number){ return http<{ok:boolean; status:string}>(`/api/orders/${id}/pause`,{method:"POST"}); }
export async function resumeOrder(id:number){ return http<{ok:boolean; status:string}>(`/api/orders/${id}/resume`,{method:"POST"}); }
export async function stopOrder(id:number){ return http<{ok:boolean; status:string}>(`/api/orders/${id}/stop`,{method:"POST"}); }
export async function orderSummary(id:number){ return http<any>(`/api/orders/${id}/summary`); }

/* ---------- Runs ---------- */
export async function runsByOrder(orderId:number){ return http<CarRun[]>(`/api/runs/by-order/${orderId}`); }
/** next 15 unassigned */ export async function createRun(orderId:number, vehicleId:number, note?:string){ return http<{id:number;load_seq:number;row_start_seq:number;row_end_seq:number}>(`/api/vehicles/${vehicleId}/runs`,{method:"POST",body:JSON.stringify({orderId,note})}); }
/** precise batch */ export async function createRunForRange(orderId:number, vehicleId:number, row_start_seq:number, row_end_seq:number, note?:string){ return http<{id:number;load_seq:number;row_start_seq:number;row_end_seq:number}>(`/api/vehicles/${vehicleId}/runs`,{method:"POST",body:JSON.stringify({orderId,note,row_start_seq,row_end_seq})}); }
