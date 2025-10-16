// frontend/src/pages/Orders.tsx
import React, { useEffect, useMemo, useState } from "react";
import {
  listClients, listRecipes, listOrders, createOrder, getOrder,
  startNextRow, markDone,
  updateOrder, deleteOrder
} from "../api";
import type {
  Client as TClient,
  Recipe as TRecipe,
  Order as TOrder,
  LiteOrder
} from "../api";
import {
  Card, Panel, Button, Input, Select,
  Table, THead, TBody, TR, TH, TD,
  useToast, Modal, Pagination
} from "../components/ui";
import { useNavigate } from "react-router-dom";
import { Play, Eye, Pencil, Trash2, MoreHorizontal } from "lucide-react";

type LoadedOrder = TOrder;

export default function Orders() {
  const toast = useToast();
  const nav = useNavigate();

  // master
  const [clients, setClients] = useState<TClient[]>([]);
  const [recipes, setRecipes] = useState<TRecipe[]>([]);

  // create form
  const [clientId, setClientId] = useState<number | "">("");
  const [recipeId, setRecipeId] = useState<number | "">("");
  const [totalM3, setTotalM3] = useState<number>(45);

  // active (details)
  const [orderId, setOrderId] = useState<number | "">("");
  const [order, setOrder] = useState<LoadedOrder | null>(null);
  const [countdown, setCountdown] = useState(0);
  const [autoRunning, setAutoRunning] = useState(false);

  // list
  const [orders, setOrders] = useState<LiteOrder[]>([]);
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const PAGE = 10;

  // Details modal state
  const [infoOpen, setInfoOpen] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editClient, setEditClient] = useState<number | "">("");
  const [editRecipe, setEditRecipe] = useState<number | "">("");
  const [editTotal, setEditTotal] = useState<number>(0);

  // Row modal
  const [rowModal, setRowModal] = useState<{ open: boolean; row?: any }>({ open: false });

  useEffect(() => {
    (async () => {
      try {
        const [cs, rs] = await Promise.all([listClients(), listRecipes()]);
        setClients(cs); setRecipes(rs);
      } catch {
        toast.push({ title: "Failed to load master data", tone: "error" });
      }
      await refreshOrderList();
    })();
  }, []);

  const refreshOrderList = async () => {
    try { setOrders(await listOrders(100)); }
    catch { toast.push({ title: "Failed to load orders", tone: "error" }); }
  };

  const refreshOrder = async (id: number) => {
    try { setOrder(await getOrder(id)); }
    catch { setOrder(null); toast.push({ title: "Order not found", tone: "error" }); }
  };

  const progress = useMemo(() => {
    if (!order) return { done: 0, total: 0, pct: 0 };
    const done = order.rows.filter(r => r.state === "done").length;
    const total = order.rows.length;
    return { done, total, pct: total ? Math.round(done * 100 / total) : 0 };
  }, [order]);

  // Create
  const onCreate = async () => {
    try {
      if (!clientId || !recipeId || totalM3 <= 0) {
        toast.push({ title: "Select Client, Recipe and Total m³", tone: "error" });
        return;
      }
      const created = await createOrder(Number(clientId), Number(recipeId), totalM3);
      setOrderId(created.id);
      await Promise.all([refreshOrder(created.id), refreshOrderList()]);
      toast.push({ title: `Order #${created.id} created`, tone: "success" });
    } catch {
      toast.push({ title: "Failed to create order", tone: "error" });
    }
  };

  // Detail actions
  const onStartNext = async () => {
    try {
      if (!orderId) return toast.push({ title: "Enter Order ID", tone: "error" });
      const res = await startNextRow(Number(orderId));
      setCountdown(5);
      const timer = setInterval(async () => {
        setCountdown(c => {
          if (c <= 1) {
            clearInterval(timer);
            markDone(Number(orderId), res.rowId)
              .then(() => refreshOrder(Number(orderId)))
              .then(() => toast.push({ title: `Row ${res.seq_no} done`, tone: "success" }))
              .catch(() => toast.push({ title: "Mark done failed", tone: "error" }));
            return 0;
          }
          return c - 1;
        });
      }, 1000);
    } catch (e:any) {
      toast.push({ title: e?.message || "Start-next failed", tone: "error" });
    }
  };

  const onAutoRun = async () => {
    try {
      if (!orderId) return toast.push({ title: "Enter Order ID", tone: "error" });
      setAutoRunning(true);
      for (let i = 0; i < 15; i++) {
        const latest = await getOrder(Number(orderId));
        const pending = latest.rows.find((r: any) => r.state === "pending");
        if (!pending) break;
        const started = await startNextRow(Number(orderId));
        await new Promise(r => setTimeout(r, 5000));
        await markDone(Number(orderId), started.rowId);
        await refreshOrder(Number(orderId));
      }
      setAutoRunning(false);
      toast.push({ title: "Auto-run complete", tone: "success" });
    } catch {
      setAutoRunning(false);
      toast.push({ title: "Auto-run failed", tone: "error" });
    }
  };

  // View
  const onView = async (id: number) => {
    await refreshOrder(id);
    setOrderId(id);
    // preload edit fields
    setTimeout(() => {
      if (order) {
        setEditClient(order.client.id);
        setEditRecipe(order.recipe.id);
        setEditTotal(order.total_m3);
      }
    }, 0);
    setEditMode(false);
    setInfoOpen(true);
  };

  const onSaveEdit = async () => {
    if (!order) return;
    try {
      await updateOrder(order.id, {
        clientId: editClient ? Number(editClient) : undefined,
        recipeId: editRecipe ? Number(editRecipe) : undefined,
        totalM3: editTotal > 0 ? Number(editTotal) : undefined,
      });
      toast.push({ title: "Order updated", tone: "success" });
      setEditMode(false);
      await Promise.all([refreshOrder(order.id), refreshOrderList()]);
    } catch (e:any) {
      toast.push({ title: e?.message || "Update failed", tone: "error" });
    }
  };

  const onDelete = async (id?: number) => {
    const targetId = id ?? order?.id;
    if (!targetId) return;
    if (!confirm("Delete this order? This cannot be undone.")) return;
    try {
      await deleteOrder(targetId);
      toast.push({ title: "Order deleted", tone: "success" });
      setInfoOpen(false);
      setOrder(null);
      await refreshOrderList();
    } catch (e:any) {
      toast.push({ title: e?.message || "Delete failed", tone: "error" });
    }
  };

  // Filter + paginate
  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return orders;
    return orders.filter(o =>
      `${o.id} ${o.client.name} ${o.recipe.name} ${o.status}`.toLowerCase().includes(s)
    );
  }, [orders, q]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE));
  const pageRows = filtered.slice((page - 1) * PAGE, page * PAGE);

  // Reversed Sl across filtered results
  const slAt = (indexOnPage: number) =>
    filtered.length - ((page - 1) * PAGE + indexOnPage);

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
          <div>
            <h1>Orders</h1>
            <p className="text-sm text-slate-600">
              Create, view, edit or delete orders; run production per 1 m³ (5s sim).
            </p>
          </div>
          <div className="flex gap-2">
            <Input
              placeholder="Load Order ID"
              value={orderId ?? ""}
              onChange={(e) => setOrderId(e.target.value ? Number(e.target.value) : "")}
            />
            <Button onClick={() => orderId ? refreshOrder(Number(orderId)) : toast.push({title:"Enter Order ID", tone:"error"})}>
              Load
            </Button>
          </div>
        </div>
      </Card>

      {/* Create */}
      <Panel>
        <h2 className="mb-3">Create Order</h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          <div className="md:col-span-2">
            <label className="text-sm">Client</label>
            <Select value={clientId} onChange={(e)=>setClientId(Number(e.target.value)||"")}>
              <option value="">-- Select --</option>
              {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </Select>
          </div>
          <div className="md:col-span-2">
            <label className="text-sm">Recipe</label>
            <Select value={recipeId} onChange={(e)=>setRecipeId(Number(e.target.value)||"")}>
              <option value="">-- Select --</option>
              {recipes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
            </Select>
          </div>
          <div>
            <label className="text-sm">Total (m³)</label>
            <Input type="number" step="0.001" value={totalM3} onChange={(e)=>setTotalM3(Number(e.target.value)||0)} />
          </div>
          <div className="md:col-span-5">
            <Button variant="primary" onClick={onCreate}>Create</Button>
          </div>
        </div>
      </Panel>

      {/* Created Orders list */}
      <Panel>
        <div className="flex items-center justify-between mb-3">
          <h2>Created Orders</h2>
          <div className="flex items-center gap-2">
            <Input placeholder="Search…" value={q} onChange={(e)=>{setQ(e.target.value); setPage(1);}} />
            <Button onClick={refreshOrderList}>Refresh</Button>
          </div>
        </div>

        <div className="flex items-center justify-between mb-2">
          <div className="text-sm text-slate-600">Showing {pageRows.length} of {filtered.length}</div>
          <Pagination page={page} totalPages={totalPages} onChange={setPage} />
        </div>

        <div className="overflow-auto">
          <Table className="min-w-[1080px]">
            <THead>
              <TR>
                <TH style={{width:60}}>Sl</TH>
                <TH style={{width:90}}>ID</TH>
                <TH>Client</TH>
                <TH>Recipe</TH>
                <TH style={{width:120}}>Total (m³)</TH>
                <TH style={{width:120}}>Status</TH>
                <TH style={{width:200}}>Created</TH>
                <TH style={{width:240}}>Actions</TH>
              </TR>
            </THead>
            <TBody>
              {pageRows.map((o, i) => (
                <TR key={o.id}>
                  <TD>{slAt(i)}</TD>
                  <TD>#{o.id}</TD>
                  <TD>{o.client.name}</TD>
                  <TD>{o.recipe.name}</TD>
                  <TD>{o.total_m3}</TD>
                  <TD>
                    <span className={`badge ${o.status==="done"?"badge-green":o.status==="running"?"badge-amber":"badge"}`}>
                      {o.status}
                    </span>
                  </TD>
                  <TD>{new Date(o.created_at).toLocaleString()}</TD>

                  {/* Actions (Run + More) */}
                  <TD className="relative">
                    <div className="flex items-center gap-2">
                      <Button
                        variant="primary"
                        onClick={() => nav(`/production?orderId=${o.id}`)}
                        className="rounded-full px-3 h-9"
                        title="Run production"
                      >
                        <Play size={14}/> <span className="hidden sm:inline">&nbsp;Run</span>
                      </Button>

                      <details className="relative">
                        <summary className="btn btn-ghost list-none cursor-pointer rounded-full px-3 h-9 flex items-center gap-1">
                          <MoreHorizontal size={16}/> <span className="hidden sm:inline">More</span>
                        </summary>
                        <div className="absolute right-0 z-20 mt-2 w-44 rounded-xl border border-slate-200 bg-white shadow-card p-1">
                          <button
                            className="w-full text-left btn btn-ghost justify-start rounded-lg h-9"
                            onClick={() => onView(o.id)}
                          >
                            <Eye size={14}/> <span className="ml-2">View</span>
                          </button>
                          <button
                            className="w-full text-left btn btn-ghost justify-start rounded-lg h-9"
                            onClick={async ()=>{ await onView(o.id); setEditMode(true); }}
                          >
                            <Pencil size={14}/> <span className="ml-2">Edit</span>
                          </button>
                          <button
                            className="w-full text-left btn btn-ghost justify-start rounded-lg h-9"
                            onClick={()=> onDelete(o.id)}
                          >
                            <Trash2 size={14}/> <span className="ml-2">Delete</span>
                          </button>
                        </div>
                      </details>
                    </div>
                  </TD>
                </TR>
              ))}
              {pageRows.length===0 && <TR><TD colSpan={8} className="text-center text-slate-500">No orders</TD></TR>}
            </TBody>
          </Table>
        </div>
      </Panel>

      {/* Active order summary + controls */}
      {order && (
        <Panel>
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="space-y-1">
              <div className="text-sm">
                Order <b>#{order.id}</b> — <b>{order.client.name}</b> — {order.recipe.name} — {order.total_m3} m³
              </div>
              <div className="text-sm">Rows planned: {order.rows.length}</div>
              <div className="w-full h-2 bg-slate-200 rounded-full">
                <div className="h-2 rounded-full bg-sisl-accent transition-all" style={{ width: `${progress.pct}%` }} />
              </div>
              <div className="text-xs text-slate-600">
                Progress: {progress.done} / {progress.total} rows ({progress.pct}%)
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="primary" onClick={onStartNext}>Start Next (1 m³)</Button>
              <Button onClick={onAutoRun} disabled={autoRunning}>Auto-run Load (15 rows)</Button>
              <Button onClick={() => nav(`/production?orderId=${order.id}`)}>Open in Production</Button>
              {countdown > 0 && <span className="badge badge-amber">Discharge in {countdown}s</span>}
            </div>
          </div>
        </Panel>
      )}

      {/* Rows (unchanged) */}
      {order && (
        <Panel>
          <h2 className="mb-3">Rows</h2>
          <div className="overflow-auto">
            <Table className="min-w-[860px]">
              <THead>
                <TR><TH>Seq</TH><TH>m³</TH><TH>State</TH><TH>Assigned Load</TH><TH>Actual?</TH><TH>Actions</TH></TR>
              </THead>
              <TBody>
                {order.rows.map((r:any)=>(
                  <TR key={r.id}>
                    <TD>{r.seq_no}</TD>
                    <TD>{Number(r.planned_m3).toFixed(3)}</TD>
                    <TD><span className={`badge ${r.state==='done'?'badge-green': r.state==='running'?'badge-amber':'badge'}`}>{r.state}</span></TD>
                    <TD>{r.car_run_id ?? '-'}</TD>
                    <TD>{r.actual? 'yes':'-'}</TD>
                    <TD className="flex gap-2">
                      <Button onClick={()=>setRowModal({open:true,row:r})}>View</Button>
                    </TD>
                  </TR>
                ))}
                {order.rows.length===0 && (
                  <TR><TD colSpan={6} className="text-center text-slate-500">No rows</TD></TR>
                )}
              </TBody>
            </Table>
          </div>
        </Panel>
      )}

      {/* Order Details / Edit modal */}
      <Modal open={infoOpen} onClose={()=>{ setInfoOpen(false); setEditMode(false); }} title={editMode? "Edit Order" : "Order Details"}>
        {!order ? null : (
          <div className="space-y-4">
            {!editMode ? (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div><div className="text-xs text-slate-500">ID</div><div className="font-medium">#{order.id}</div></div>
                  <div><div className="text-xs text-slate-500">Status</div><div className="font-medium">{order.status}</div></div>
                  <div><div className="text-xs text-slate-500">Client</div><div className="font-medium">{order.client.name}</div></div>
                  <div><div className="text-xs text-slate-500">Recipe</div><div className="font-medium">{order.recipe.name}</div></div>
                  <div><div className="text-xs text-slate-500">Total (m³)</div><div className="font-medium">{order.total_m3}</div></div>
                  <div><div className="text-xs text-slate-500">Rows</div><div className="font-medium">{order.rows.length}</div></div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button onClick={()=>setEditMode(true)}>Edit</Button>
                  <Button variant="primary" onClick={()=>nav(`/production?orderId=${order.id}`)}>Run</Button>
                  <Button onClick={()=> onDelete(order.id)}>Delete</Button>
                </div>
              </>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div>
                    <label className="text-sm">Client</label>
                    <Select value={editClient} onChange={(e)=>setEditClient(Number(e.target.value)||"")}>
                      <option value="">-- Select --</option>
                      {clients.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}
                    </Select>
                  </div>
                  <div>
                    <label className="text-sm">Recipe</label>
                    <Select value={editRecipe} onChange={(e)=>setEditRecipe(Number(e.target.value)||"")}>
                      <option value="">-- Select --</option>
                      {recipes.map(r=><option key={r.id} value={r.id}>{r.name}</option>)}
                    </Select>
                  </div>
                  <div>
                    <label className="text-sm">Total (m³)</label>
                    <Input type="number" step="0.001" value={editTotal} onChange={(e)=>setEditTotal(Number(e.target.value)||0)} />
                    <div className="text-xs text-slate-500 mt-1">Changing total is allowed only before production starts.</div>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button variant="primary" onClick={onSaveEdit}>Save</Button>
                  <Button onClick={()=>setEditMode(false)}>Cancel</Button>
                </div>
              </>
            )}
          </div>
        )}
      </Modal>

      {/* Row modal */}
      <Modal
        open={rowModal.open}
        onClose={()=>setRowModal({open:false})}
        title={rowModal.row ? `Row #${rowModal.row.seq_no}` : "Row"}
      >
        {!rowModal.row ? null : (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div><div className="text-xs text-slate-500">m³</div><div className="font-medium">{Number(rowModal.row.planned_m3).toFixed(3)}</div></div>
              <div><div className="text-xs text-slate-500">State</div><div className="font-medium">{rowModal.row.state}</div></div>
              <div><div className="text-xs text-slate-500">Assigned Load</div><div className="font-medium">{rowModal.row.car_run_id ?? '-'}</div></div>
              <div><div className="text-xs text-slate-500">Has Actual</div><div className="font-medium">{rowModal.row.actual ? 'yes' : 'no'}</div></div>
            </div>
            {rowModal.row.actual && (
              <div className="panel">
                <h3 className="mb-2">Actual (materials)</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {Object.entries(rowModal.row.actual).map(([k, v]: any) => (
                    <div key={k}><div className="text-xs text-slate-500">{k}</div><div className="font-medium">{Number(v).toFixed(3)}</div></div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
