import React, { useEffect, useMemo, useState } from "react";
import {
  Client,
  listClients,
  createClient,
  updateClient,
  deleteClient,
} from "../api";

/* ---------- Types & defaults ---------- */
type Form = {
  name: string;
  cell: string;
  email: string;
  office_addr: string;
  delivery_addr: string;
};

const EMPTY: Form = {
  name: "",
  cell: "",
  email: "",
  office_addr: "",
  delivery_addr: "",
};

/* ---------- Tiny Modal component (no external libs) ---------- */
function Modal({
  open,
  onClose,
  children,
  title,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="absolute inset-0 flex items-center justify-center p-4">
        <div className="w-full max-w-2xl rounded-2xl bg-white shadow-lg border border-slate-200">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
            <h3 className="font-semibold">{title}</h3>
            <button className="btn" onClick={onClose}>
              Close
            </button>
          </div>
          <div className="p-4">{children}</div>
        </div>
      </div>
    </div>
  );
}

/* ---------- Page ---------- */
export default function Clients() {
  const [items, setItems] = useState<Client[]>([]);
  const [creating, setCreating] = useState<Form>({ ...EMPTY });

  // Search & simple pagination
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 10;

  // Details modal
  const [viewItem, setViewItem] = useState<Client | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [edit, setEdit] = useState<Form>({ ...EMPTY });

  const refresh = async () => setItems(await listClients());
  useEffect(() => {
    refresh();
  }, []);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return items;
    return items.filter((c) => {
      const hay = `${c.name ?? ""} ${c.cell ?? ""} ${c.email ?? ""}`.toLowerCase();
      return hay.includes(s);
    });
  }, [items, q]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [totalPages, page]);

  /* ---------- Create ---------- */
  const doCreate = async () => {
    if (!creating.name.trim()) {
      alert("Client name is required.");
      return;
    }
    await createClient({
      name: creating.name.trim(),
      cell: creating.cell || undefined,
      email: creating.email || undefined,
      office_addr: creating.office_addr || undefined,
      delivery_addr: creating.delivery_addr || undefined,
    });
    setCreating({ ...EMPTY });
    setPage(1);
    refresh();
  };

  /* ---------- View / Edit in Modal ---------- */
  const openView = (c: Client) => {
    setViewItem(c);
    setEditMode(false);
    setEdit({
      name: c.name || "",
      cell: c.cell || "",
      email: c.email || "",
      office_addr: c.office_addr || "",
      delivery_addr: c.delivery_addr || "",
    });
  };

  const saveEdit = async () => {
    if (!viewItem) return;
    if (!edit.name.trim()) return alert("Name is required.");
    await updateClient(viewItem.id, {
      name: edit.name.trim(),
      cell: edit.cell || null,
      email: edit.email || null,
      office_addr: edit.office_addr || null,
      delivery_addr: edit.delivery_addr || null,
    });
    setEditMode(false);
    setViewItem(null);
    refresh();
  };

  const doDelete = async (id: number) => {
    if (!confirm("Delete this client? This cannot be undone.")) return;
    try {
      await deleteClient(id);
      // if we deleted from modal, close it
      if (viewItem?.id === id) setViewItem(null);
      refresh();
    } catch (e: any) {
      alert(e.message || "Delete failed. Client may have related orders.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Search */}
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-xl font-semibold">Clients</h2>
          <p className="text-sm text-slate-600">
            Compact list (Sl, Name, Cell, Email). Click <b>View</b> to see full
            details or edit.
          </p>
        </div>
        <div className="flex gap-2">
          <input
            className="input"
            placeholder="Search name, cell, email…"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
          />
        </div>
      </div>

      {/* Add client (compact) */}
      <div className="panel">
        <h3 className="font-semibold mb-3">Add Client</h3>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          <input
            className="input md:col-span-2"
            placeholder="Name *"
            value={creating.name}
            onChange={(e) => setCreating({ ...creating, name: e.target.value })}
          />
          <input
            className="input"
            placeholder="Cell"
            value={creating.cell}
            onChange={(e) => setCreating({ ...creating, cell: e.target.value })}
          />
          <input
            className="input"
            type="email"
            placeholder="Email"
            value={creating.email}
            onChange={(e) => setCreating({ ...creating, email: e.target.value })}
          />
          <button className="btn btn-primary" onClick={doCreate}>
            Add
          </button>
        </div>

        {/* Advanced fields collapsed link */}
        <details className="mt-3">
          <summary className="cursor-pointer text-sm text-slate-600">
            Advanced fields (Office / Delivery address)
          </summary>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-2">
            <textarea
              className="input"
              rows={2}
              placeholder="Office Address"
              value={creating.office_addr}
              onChange={(e) =>
                setCreating({ ...creating, office_addr: e.target.value })
              }
            />
            <textarea
              className="input"
              rows={2}
              placeholder="Delivery Address"
              value={creating.delivery_addr}
              onChange={(e) =>
                setCreating({ ...creating, delivery_addr: e.target.value })
              }
            />
          </div>
        </details>
      </div>

      {/* Table: Sl, Name, Cell, Email (+ Actions) */}
      <div className="panel overflow-auto">
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm text-slate-600">
            Showing {current.length} of {filtered.length}
          </div>
          {/* Pagination */}
          <div className="flex items-center gap-2">
            <button
              className="btn"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
            >
              Prev
            </button>
            <span className="text-sm">
              Page {page} / {totalPages}
            </span>
            <button
              className="btn"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
            >
              Next
            </button>
          </div>
        </div>

        <table className="table min-w-[720px]">
          <thead>
            <tr>
              <th style={{ width: 70 }}>Sl</th>
              <th style={{ minWidth: 240 }}>Name</th>
              <th style={{ minWidth: 160 }}>Cell</th>
              <th style={{ minWidth: 240 }}>Email</th>
              <th style={{ width: 220 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {current.map((c, idx) => (
              <tr key={c.id}>
                <td>{(page - 1) * PAGE_SIZE + idx + 1}</td>
                <td>{c.name}</td>
                <td>{c.cell || "-"}</td>
                <td>{c.email || "-"}</td>
                <td className="flex gap-2">
                  <button className="btn" onClick={() => openView(c)}>
                    View
                  </button>
                  <button className="btn" onClick={() => doDelete(c.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {current.length === 0 && (
              <tr>
                <td colSpan={5} className="text-center text-slate-500">
                  No clients found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Details / Edit Modal */}
      <Modal
        open={!!viewItem}
        onClose={() => setViewItem(null)}
        title={editMode ? "Edit Client" : "Client Details"}
      >
        {!viewItem ? null : (
          <div className="space-y-4">
            {!editMode ? (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-xs text-slate-500">Name</div>
                    <div className="font-medium">{viewItem.name}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">Cell</div>
                    <div className="font-medium">{viewItem.cell || "-"}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">Email</div>
                    <div className="font-medium">{viewItem.email || "-"}</div>
                  </div>
                </div>

                <div>
                  <div className="text-xs text-slate-500">Office Address</div>
                  <div className="font-medium whitespace-pre-wrap">
                    {viewItem.office_addr || "-"}
                  </div>
                </div>

                <div>
                  <div className="text-xs text-slate-500">Delivery Address</div>
                  <div className="font-medium whitespace-pre-wrap">
                    {viewItem.delivery_addr || "-"}
                  </div>
                </div>

                <div className="flex gap-2 pt-2">
                  <button
                    className="btn btn-primary"
                    onClick={() => setEditMode(true)}
                  >
                    Edit
                  </button>
                  <button
                    className="btn"
                    onClick={() => doDelete(viewItem.id)}
                  >
                    Delete
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="text-sm">Name *</label>
                    <input
                      className="input"
                      value={edit.name}
                      onChange={(e) => setEdit({ ...edit, name: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="text-sm">Cell</label>
                    <input
                      className="input"
                      value={edit.cell}
                      onChange={(e) => setEdit({ ...edit, cell: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="text-sm">Email</label>
                    <input
                      className="input"
                      type="email"
                      value={edit.email}
                      onChange={(e) =>
                        setEdit({ ...edit, email: e.target.value })
                      }
                    />
                  </div>
                  <div className="md:col-span-2">
                    <label className="text-sm">Office Address</label>
                    <textarea
                      className="input"
                      rows={2}
                      value={edit.office_addr}
                      onChange={(e) =>
                        setEdit({ ...edit, office_addr: e.target.value })
                      }
                    />
                  </div>
                  <div className="md:col-span-2">
                    <label className="text-sm">Delivery Address</label>
                    <textarea
                      className="input"
                      rows={2}
                      value={edit.delivery_addr}
                      onChange={(e) =>
                        setEdit({ ...edit, delivery_addr: e.target.value })
                      }
                    />
                  </div>
                </div>

                <div className="flex gap-2 pt-2">
                  <button className="btn btn-primary" onClick={saveEdit}>
                    Save
                  </button>
                  <button
                    className="btn"
                    onClick={() => {
                      setEditMode(false);
                      // reset edits back to current viewItem
                      if (viewItem) {
                        setEdit({
                          name: viewItem.name || "",
                          cell: viewItem.cell || "",
                          email: viewItem.email || "",
                          office_addr: viewItem.office_addr || "",
                          delivery_addr: viewItem.delivery_addr || "",
                        });
                      }
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
