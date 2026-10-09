import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "bootstrap/dist/css/bootstrap.min.css";
import {
  Sun,
  LayoutDashboard,
  CalendarDays,
  MapPin,
  BatteryCharging,
  Users,
  ShieldCheck,
  ScanLine,
  LogOut,
  ArrowUpRight,
  Plus,
  RefreshCw,
  Search,
  X,
  ChevronRight,
  Zap,
  Menu,
  UserRound,
  CheckCircle2,
} from "lucide-react";
import { request, date, localInput } from "./api";
import "./styles.css";

const names = {
  dashboard: "Overview",
  bookings: "Energy reservations",
  nodes: "Microgrid nodes",
  slots: "Trading slots",
  accounts: "User management",
  activations: "Account activation",
  verify: "Verify transfer",
  profile: "My profile",
};
const navigation = [
  ["dashboard", LayoutDashboard],
  ["bookings", CalendarDays],
  ["nodes", MapPin],
  ["slots", BatteryCharging],
  ["accounts", Users],
  ["activations", ShieldCheck],
  ["verify", ScanLine],
  ["profile", UserRound],
];
const labelRole = (role) => (role === "GridOperator" ? "Grid Operator" : role);
const numeric = new Set([
  "latitude",
  "longitude",
  "capacityKw",
  "batterySlots",
  "capacityKwh",
  "maxBookings",
  "energyKwh",
  "transferredKwh",
]);
// Render a status label with shared semantic styling.
function Badge({ children }) {
  return (
    <span className={`status status-${String(children).toLowerCase()}`}>
      {children}
    </span>
  );
}
// Explain an empty result and expose an optional next action.
function Empty({
  title = "Nothing here yet",
  text = "New records will appear here as your microgrid grows.",
}) {
  return (
    <div className="empty">
      <Sun size={32} />
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}
// Render accessible table headings and row content.
function Table({ headings, children }) {
  return (
    <div className="table-responsive">
      <table className="table align-middle mb-0">
        <thead>
          <tr>
            {headings.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
// Choose the native form control for a field specification.
function Field({ spec, initial }) {
  const [name, label, type = "text", options] = spec;
  const isCoordinate = name === "latitude" || name === "longitude";
  return (
    <label className={type === "textarea" ? "field wide" : "field"}>
      <span>{label}</span>
      {type === "select" ? (
        <select
          name={name}
          defaultValue={initial ?? ""}
          required
          className="form-select"
        >
          <option value="" disabled>
            Select {label.toLowerCase()}
          </option>
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      ) : type === "textarea" ? (
        <textarea
          name={name}
          defaultValue={initial ?? ""}
          required
          maxLength={500}
          className="form-control"
        />
      ) : (
        <input
          name={name}
          type={type}
          defaultValue={initial ?? ""}
          required
          className="form-control"
          step={type === "number" ? (isCoordinate ? "any" : "1") : undefined}
          min={type === "number" && !isCoordinate ? "1" : undefined}
          minLength={type === "password" ? 10 : undefined}
          maxLength={type === "password" ? 128 : undefined}
        />
      )}
    </label>
  );
}
// Validate and submit dialog fields while retaining API errors.
function Modal({ title, fields, initial = {}, onSubmit, close, children }) {
  const dialogRef = useRef(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    const previous = document.activeElement;
    const focusable = () => [
      ...dialogRef.current.querySelectorAll(
        "button:not(:disabled), input, select, textarea",
      ),
    ];
    focusable()[0]?.focus();
    const fn = (e) => {
      if (e.key === "Escape" && !busy) close();
      if (e.key === "Tab") {
        const elements = focusable(),
          first = elements[0],
          last = elements.at(-1);
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", fn);
    return () => {
      document.removeEventListener("keydown", fn);
      previous?.focus();
    };
  }, [busy, close]);
  // Submit form values and retain actionable validation feedback.
  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const data = Object.fromEntries(new FormData(e.currentTarget));
    for (const key of Object.keys(data))
      if (numeric.has(key)) data[key] = Number(data[key]);
    try {
      await onSubmit(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="dialog-backdrop">
      <section
        ref={dialogRef}
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header>
          <h2>{title}</h2>
          <button
            type="button"
            className="icon-btn"
            aria-label="Close dialog"
            disabled={busy}
            onClick={close}
          >
            <X />
          </button>
        </header>
        <form onSubmit={submit}>
          {children}
          <div className="form-grid">
            {fields?.map((f) => (
              <Field key={f[0]} spec={f} initial={initial[f[0]]} />
            ))}
          </div>
          {error && (
            <div className="alert alert-danger mt-3" role="alert">
              {error}
            </div>
          )}
          <footer>
            <button
              type="button"
              className="btn btn-light"
              onClick={close}
              disabled={busy}
            >
              Cancel
            </button>
            <button className="btn btn-primary" disabled={busy}>
              {busy ? "Saving…" : "Save changes"}
            </button>
          </footer>
        </form>
      </section>
    </div>
  );
}
// Authenticate staff through the API and return the resulting session.
function Login({ onLogin }) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  // Submit form values and retain actionable validation feedback.
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await request("/auth/login", {
        method: "POST",
        body: Object.fromEntries(new FormData(e.currentTarget)),
      });
      if (data.user.role === "Prosumer")
        throw new Error(
          "Please use the native Android application for your prosumer account.",
        );
      onLogin(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login-page">
      <section className="login-story">
        <div className="brand">
          <Sun />
          <span>
            solara<span className="brand-dot">.</span>
          </span>
        </div>
        <div>
          <span className="eyebrow">SMART SOLAR MICROGRID</span>
          <h1>
            Local energy.
            <br />
            Shared possibility.
          </h1>
          <p>
            A connected workspace for the people powering a cleaner community.
          </p>
          <div className="energy-graphic">
            <Sun size={64} />
            <div className="energy-line" />
            <BatteryCharging size={64} />
            <div className="energy-line" />
            <Zap size={64} />
          </div>
        </div>
        <small>Microgrid operations · Backoffice & Grid Operators</small>
      </section>
      <section className="login-form">
        <div>
          <span className="eyebrow">OPERATIONS PORTAL</span>
          <h2>Welcome back</h2>
          <p className="muted">Sign in to manage your solar network.</p>
          <form onSubmit={submit}>
            <Field spec={["email", "Email address", "email"]} />
            <Field spec={["password", "Password", "password"]} />
            {error && (
              <div className="alert alert-danger" role="alert">
                {error}
              </div>
            )}
            <button className="btn btn-primary w-100" disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
              <ArrowUpRight size={18} />
            </button>
          </form>
          <p className="login-note">
            <ShieldCheck size={16} /> Access is restricted to authorized staff.
          </p>
          <div className="account-guidance">
            <h3>Need an account?</h3>
            <p>
              <strong>Backoffice & Grid Operators:</strong> Contact an existing
              Backoffice officer to create your staff account. Grid Operators can
              use the same account on the web and Android app.
            </p>
            <p>
              <strong>Solar Prosumers:</strong> Create your account in the Android
              app using your NIC. A Backoffice officer must activate it before
              you can sign in on Android.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
// Coordinate authenticated navigation, server data and staff operations.
function App() {
  const [session, setSession] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem("solara.session"));
    } catch {
      return null;
    }
  });
  const [page, setPage] = useState("dashboard"),
    [menu, setMenu] = useState(false),
    [revision, setRevision] = useState(0);
  const [data, setData] = useState({}),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  const [modal, setModal] = useState(null),
    [toast, setToast] = useState(""),
    [summary, setSummary] = useState(null);
  const [filters, setFilters] = useState({
    status: "",
    search: "",
    from: "",
    to: "",
    page: 1,
  });
  const admin = session?.user.role === "Backoffice";
  const logout = () => {
    sessionStorage.removeItem("solara.session");
    setSession(null);
    setData({});
    setPage("dashboard");
  };
  const login = (s) => {
    sessionStorage.setItem("solara.session", JSON.stringify(s));
    setSession(s);
  };
  const api = (path, method = "GET", body) =>
    request(path, { method, body, token: session?.token });
  const refresh = () => setRevision((r) => r + 1);
  // Apply a server mutation and refresh the affected portal data.
  async function act(
    path,
    method,
    body,
    message = "Changes saved",
    showSummary = false,
  ) {
    const result = await api(path, method, body);
    setModal(null);
    setToast(message);
    if (showSummary) setSummary(result);
    refresh();
    return result;
  }
  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(""), 4500);
    return () => clearTimeout(id);
  }, [toast]);
  useEffect(() => {
    if (!session) return;
    let active = true;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    // Fetch the datasets needed by the current role and screen.
    async function load() {
      try {
        const call = (path) =>
          request(path, { token: session.token, signal: controller.signal });
        const [me, nodes, slots, users, dashboard, bookings] =
          await Promise.all([
            call("/auth/me"),
            call("/stations?includeInactive=true"),
            call("/slots"),
            call("/users"),
            call("/reservations/dashboard"),
            call(
              "/reservations?" +
                new URLSearchParams({
                  ...filters,
                  from: filters.from
                    ? new Date(filters.from).toISOString()
                    : "",
                  to: filters.to
                    ? new Date(filters.to + "T23:59:59").toISOString()
                    : "",
                  pageSize: "15",
                }).toString(),
            ),
          ]);
        if (active) setData({ me, nodes, slots, users, dashboard, bookings });
      } catch (err) {
        if (active && err.name !== "AbortError") {
          if (err.status === 401) logout();
          else setError(err.message);
        }
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => {
      active = false;
      controller.abort();
    };
  }, [session?.token, revision, filters]);
  if (!session) return <Login onLogin={login} />;
  const nodes = data.nodes || [],
    slots = data.slots || [],
    users = data.users || [],
    bookings = data.bookings?.items || [];
  const nodeName = (id) => nodes.find((n) => n.id === id)?.name || id;
  const options = (rows) => rows.map((x) => ({ value: x.id, label: x.name }));
  const nodeFields = [
    ["name", "Node name"],
    ["address", "Address"],
    ["latitude", "Latitude", "number"],
    ["longitude", "Longitude", "number"],
    ["capacityKw", "Capacity (kW)", "number"],
    ["batterySlots", "Battery storage slots", "number"],
    ["schedule", "Operating schedule", "textarea"],
  ];
  const slotFields = [
    ["start", "Starts at", "datetime-local"],
    ["end", "Ends at", "datetime-local"],
    ["capacityKwh", "Energy capacity (kWh)", "number"],
    ["maxBookings", "Maximum bookings", "number"],
  ];
  const profileFields = [
    ["name", "Full name"],
    ["phone", "Phone"],
    ["address", "Address", "textarea"],
  ];
  // Prepare a booking form using active prosumers and published slots.
  function bookModal(booking) {
    const available = slots.map((s) => ({
      value: s.id,
      label: `${nodeName(s.stationId)} · ${date(s.start)} · ${(s.capacityKwh - s.reservedKwh).toFixed(1)} kWh free`,
    }));
    setModal({
      title: booking ? "Modify reservation" : "Create reservation",
      fields: [
        ...(!booking
          ? [
              [
                "prosumerId",
                "Prosumer",
                "select",
                options(
                  users.filter(
                    (u) => u.role === "Prosumer" && u.status === "Active",
                  ),
                ),
              ],
            ]
          : []),
        ["slotId", "Trading slot", "select", available],
        ["energyKwh", "Energy (kWh)", "number"],
        [
          "direction",
          "Transfer type",
          "select",
          [
            { value: "DropOff", label: "Drop off energy" },
            { value: "Charging", label: "Charge / collect energy" },
          ],
        ],
      ],
      initial: booking || {},
      submit: (body) =>
        act(
          "/reservations" + (booking ? "/" + booking.id : ""),
          booking ? "PUT" : "POST",
          body,
          "Reservation saved",
          true,
        ),
    });
  }
  // Confirm the selected state change before sending it to the API.
  function confirmAction(
    title,
    path,
    message,
    isBooking = false,
    method = "POST",
  ) {
    setModal({
      title,
      fields: [],
      children: (
        <p>
          This action is checked against the current server rules before it is
          applied.
        </p>
      ),
      submit: () => act(path, method, undefined, message, isBooking),
    });
  }
  const changePage = (p) => {
    setPage(p);
    setMenu(false);
  };
  return (
    <div className="app-shell">
      <aside className={`sidebar ${menu ? "open" : ""}`}>
        <div className="brand">
          <Sun />
          <span>
            solara<span className="brand-dot">.</span>
          </span>
        </div>
        <span className="nav-label">WORKSPACE</span>
        <nav>
          {navigation
            .filter(
              ([key]) => admin || !["accounts", "activations"].includes(key),
            )
            .map(([key, Icon]) => (
              <button
                key={key}
                className={page === key ? "active" : ""}
                onClick={() => changePage(key)}
              >
                <Icon size={19} />
                {names[key]}
                {key === "activations" &&
                  users.filter((u) => u.status === "Pending").length > 0 && (
                    <span className="nav-count">
                      {users.filter((u) => u.status === "Pending").length}
                    </span>
                  )}
              </button>
            ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="network-note">
            <span className="live-dot" /> Connected energy community
          </div>
          <button className="logout" onClick={logout}>
            <LogOut size={18} /> Sign out
          </button>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div className="d-flex align-items-center gap-3">
            <button
              className="icon-btn mobile-menu"
              aria-label="Toggle navigation"
              onClick={() => setMenu(!menu)}
            >
              <Menu />
            </button>
            <span className="breadcrumb-text">
              Workspace <ChevronRight size={14} /> {names[page]}
            </span>
          </div>
          <div className="topbar-user">
            <span className="role-chip">{labelRole(session.user.role)}</span>
            <span className="avatar">{session.user.name.slice(0, 1)}</span>
          </div>
        </header>
        <div className="workspace">
          <div className="page-heading">
            <div>
              <span className="eyebrow">MICROGRID OPERATIONS</span>
              <h1>{names[page]}</h1>
              <p className="muted">
                {page === "dashboard"
                  ? `Welcome back, ${session.user.name.split(" ")[0]}. Here's your network at a glance.`
                  : "Live information from your connected solar network."}
              </p>
            </div>
            <button
              className="btn btn-outline-secondary"
              onClick={refresh}
              disabled={loading}
            >
              <RefreshCw size={16} className={loading ? "spin" : ""} /> Refresh
            </button>
          </div>
          {error && (
            <div className="alert alert-danger" role="alert">
              {error}{" "}
              <button className="btn btn-sm btn-light ms-2" onClick={refresh}>
                Retry
              </button>
            </div>
          )}
          {loading && (
            <div
              className="loading-bar"
              role="status"
              aria-label="Loading network data"
            />
          )}
          {page === "dashboard" && (
            <>
              <section className="overview-banner">
                <div>
                  <span className="eyebrow">ENERGY, IN BALANCE</span>
                  <h2>A brighter grid starts here.</h2>
                  <p>
                    Coordinate local generation, storage and energy exchange.
                  </p>
                  <button
                    className="btn btn-banner"
                    onClick={() => changePage("bookings")}
                  >
                    View reservations <ArrowUpRight size={18} />
                  </button>
                </div>
                <div className="banner-sun">
                  <Sun size={105} strokeWidth={1} />
                </div>
              </section>
              <div className="stats-grid">
                {[
                  ["Pending requests", data.dashboard?.pending, CalendarDays],
                  [
                    "Approved upcoming",
                    data.dashboard?.approvedFuture,
                    ShieldCheck,
                  ],
                  ["Completed transfers", data.dashboard?.completed, Zap],
                  [
                    "Active microgrid nodes",
                    data.dashboard?.activeNodes,
                    MapPin,
                  ],
                ].map(([label, value, Icon]) => (
                  <section className="stat" key={label}>
                    <span className="stat-icon">
                      <Icon size={20} />
                    </span>
                    <span className="muted">{label}</span>
                    <strong>{value ?? "—"}</strong>
                    <small>Live network data</small>
                  </section>
                ))}
              </div>
              <section className="panel">
                <div className="panel-header">
                  <div>
                    <h2>Latest reservations</h2>
                    <p>Recent activity across your microgrid</p>
                  </div>
                  <button
                    className="text-btn"
                    onClick={() => changePage("bookings")}
                  >
                    View all <ArrowUpRight size={16} />
                  </button>
                </div>
                {bookings.length ? (
                  <Table
                    headings={[
                      "Prosumer",
                      "Microgrid node",
                      "Scheduled start",
                      "Energy",
                      "Status",
                    ]}
                  >
                    {bookings.slice(0, 5).map((b) => (
                      <tr key={b.id}>
                        <td className="fw-semibold">{b.prosumerName}</td>
                        <td>{b.stationName}</td>
                        <td>{date(b.start)}</td>
                        <td>{b.energyKwh} kWh</td>
                        <td>
                          <Badge>{b.status}</Badge>
                        </td>
                      </tr>
                    ))}
                  </Table>
                ) : (
                  <Empty title="Your first energy exchange awaits" />
                )}
              </section>
            </>
          )}
          {page === "bookings" && (
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>Reservation directory</h2>
                  <p>Review, approve and coordinate energy transfers.</p>
                </div>
                <button className="btn btn-primary" onClick={() => bookModal()}>
                  <Plus size={17} /> New reservation
                </button>
              </div>
              <form
                className="filters"
                onSubmit={(e) => {
                  e.preventDefault();
                  setFilters({
                    ...Object.fromEntries(new FormData(e.currentTarget)),
                    page: 1,
                  });
                }}
              >
                <label className="search-field">
                  <Search size={17} />
                  <input
                    name="search"
                    placeholder="Search booking ID, NIC or node"
                    defaultValue={filters.search}
                  />
                </label>
                <select
                  className="form-select"
                  name="status"
                  defaultValue={filters.status}
                >
                  <option value="">All statuses</option>
                  {[
                    "Pending",
                    "Approved",
                    "Completed",
                    "Cancelled",
                    "Rejected",
                    "Expired",
                  ].map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
                <input
                  className="form-control"
                  type="date"
                  name="from"
                  aria-label="From date"
                />
                <input
                  className="form-control"
                  type="date"
                  name="to"
                  aria-label="To date"
                />
                <button className="btn btn-light">Apply</button>
              </form>
              {bookings.length ? (
                <Table
                  headings={[
                    "Booking / prosumer",
                    "Node / schedule",
                    "Energy",
                    "Status",
                    "Actions",
                  ]}
                >
                  {bookings.map((b) => (
                    <tr key={b.id}>
                      <td>
                        <strong>{b.prosumerName}</strong>
                        <small className="cell-sub">
                          {b.id.slice(0, 8)} · {b.prosumerId}
                        </small>
                      </td>
                      <td>
                        {b.stationName}
                        <small className="cell-sub">{date(b.start)}</small>
                      </td>
                      <td>
                        {b.energyKwh} kWh
                        <small className="cell-sub">
                          {b.direction === "DropOff" ? "Drop off" : "Charging"}
                        </small>
                      </td>
                      <td>
                        <Badge>{b.status}</Badge>
                      </td>
                      <td>
                        <div className="action-group">
                          {b.status === "Pending" && (
                            <>
                              <button
                                onClick={() =>
                                  confirmAction(
                                    "Approve reservation",
                                    "/reservations/" + b.id + "/approve",
                                    "Reservation approved",
                                    true,
                                  )
                                }
                              >
                                Approve
                              </button>
                              <button
                                onClick={() =>
                                  confirmAction(
                                    "Reject reservation",
                                    "/reservations/" + b.id + "/reject",
                                    "Reservation rejected",
                                    true,
                                  )
                                }
                              >
                                Reject
                              </button>
                            </>
                          )}
                          {["Pending", "Approved"].includes(b.status) && (
                            <>
                              <button onClick={() => bookModal(b)}>Edit</button>
                              <button
                                className="danger"
                                onClick={() =>
                                  confirmAction(
                                    "Cancel reservation",
                                    "/reservations/" + b.id + "/cancel",
                                    "Reservation cancelled",
                                    true,
                                  )
                                }
                              >
                                Cancel
                              </button>
                            </>
                          )}
                          <button onClick={() => setSummary(b)}>Details</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </Table>
              ) : (
                <Empty
                  title="No matching reservations"
                  text="Try changing the filters or create a new reservation."
                />
              )}
              <div className="pagination-row">
                <span>{data.bookings?.total || 0} reservations</span>
                <div>
                  <button
                    className="btn btn-light btn-sm"
                    disabled={filters.page <= 1}
                    onClick={() =>
                      setFilters({ ...filters, page: filters.page - 1 })
                    }
                  >
                    Previous
                  </button>
                  <span className="mx-3">Page {filters.page}</span>
                  <button
                    className="btn btn-light btn-sm"
                    disabled={filters.page * 15 >= (data.bookings?.total || 0)}
                    onClick={() =>
                      setFilters({ ...filters, page: filters.page + 1 })
                    }
                  >
                    Next
                  </button>
                </div>
              </div>
            </section>
          )}
          {page === "nodes" && (
            <>
              <div className="section-toolbar">
                <p>{nodes.length} registered microgrid nodes</p>
                {admin && (
                  <button
                    className="btn btn-primary"
                    onClick={() =>
                      setModal({
                        title: "Register microgrid node",
                        fields: nodeFields,
                        submit: (body) =>
                          act("/stations", "POST", body, "Node registered"),
                      })
                    }
                  >
                    <Plus size={17} /> Register node
                  </button>
                )}
              </div>
              <div className="node-grid">
                {nodes.map((n) => (
                  <section className="node-card" key={n.id}>
                    <div className="node-card-top">
                      <span className="node-icon">
                        <MapPin />
                      </span>
                      <Badge>{n.active ? "Active" : "Inactive"}</Badge>
                    </div>
                    <h2>{n.name}</h2>
                    <p className="muted">{n.address}</p>
                    <div className="node-metrics">
                      <div>
                        <strong>
                          {n.capacityKw} <small>kW</small>
                        </strong>
                        <span>Generation capacity</span>
                      </div>
                      <div>
                        <strong>{n.batterySlots}</strong>
                        <span>Battery slots</span>
                      </div>
                    </div>
                    <p className="node-schedule">{n.schedule}</p>
                    <small className="muted">
                      GPS {n.latitude.toFixed(5)}, {n.longitude.toFixed(5)}
                    </small>
                    <footer>
                      <button
                        className="text-btn"
                        onClick={() =>
                          setModal({
                            title: "Edit node",
                            fields: nodeFields,
                            initial: n,
                            submit: (body) =>
                              act("/stations/" + n.id, "PUT", body),
                          })
                        }
                      >
                        Edit node <ArrowUpRight size={15} />
                      </button>
                      {admin && (
                        <button
                          className="text-btn"
                          onClick={() =>
                            confirmAction(
                              n.active ? "Deactivate node" : "Activate node",
                              "/stations/" +
                                n.id +
                                (n.active ? "/deactivate" : "/activate"),
                              "Node status updated",
                            )
                          }
                        >
                          {n.active ? "Deactivate" : "Activate"}
                        </button>
                      )}
                      {admin && n.active && (
                        <button
                          className="text-btn"
                          onClick={() => confirmAction(
                            "Delete node from active listings (retain booking history)",
                            "/stations/" + n.id,
                            "Node removed from active listings; booking history retained",
                            false,
                            "DELETE",
                          )}
                        >
                          Delete node
                        </button>
                      )}
                    </footer>
                  </section>
                ))}
              </div>
              {!nodes.length && (
                <Empty title="Connect your first microgrid node" />
              )}
            </>
          )}
          {page === "slots" && (
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>Published trading windows</h2>
                  <p>
                    Available energy and battery capacity for upcoming slots.
                  </p>
                </div>
                <button
                  className="btn btn-primary"
                  onClick={() =>
                    setModal({
                      title: "Publish trading slot",
                      fields: [
                        [
                          "stationId",
                          "Node",
                          "select",
                          options(nodes.filter((n) => n.active)),
                        ],
                        ...slotFields,
                      ],
                      submit: ({ stationId, ...body }) =>
                        act(
                          "/stations/" + stationId + "/slots",
                          "POST",
                          {
                            ...body,
                            start: new Date(body.start).toISOString(),
                            end: new Date(body.end).toISOString(),
                          },
                          "Slot published",
                        ),
                    })
                  }
                >
                  <Plus size={17} /> Publish slot
                </button>
              </div>
              {slots.length ? (
                <Table
                  headings={[
                    "Node",
                    "Trading window",
                    "Energy available",
                    "Battery slots",
                    "Actions",
                  ]}
                >
                  {slots.map((s) => (
                    <tr key={s.id}>
                      <td className="fw-semibold">{nodeName(s.stationId)}</td>
                      <td>
                        {date(s.start)}
                        <small className="cell-sub">Until {date(s.end)}</small>
                      </td>
                      <td>
                        {(s.capacityKwh - s.reservedKwh).toFixed(2)} /{" "}
                        {s.capacityKwh} kWh
                      </td>
                      <td>
                        {s.maxBookings - s.reservedCount} / {s.maxBookings} free
                      </td>
                      <td>
                        <div className="action-group">
                          <button
                            onClick={() =>
                              setModal({
                                title: "Edit trading slot",
                                fields: slotFields,
                                initial: {
                                  ...s,
                                  start: localInput(s.start),
                                  end: localInput(s.end),
                                },
                                submit: (body) =>
                                  act("/slots/" + s.id, "PUT", {
                                    ...body,
                                    start: new Date(body.start).toISOString(),
                                    end: new Date(body.end).toISOString(),
                                  }),
                              })
                            }
                          >
                            Edit
                          </button>
                          <button
                            className="danger"
                            onClick={() =>
                              confirmAction(
                                "Archive trading slot",
                                "/slots/" + s.id,
                                "Slot archived",
                                false,
                                "DELETE",
                              )
                            }
                          >
                            Archive
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </Table>
              ) : (
                <Empty
                  title="No future trading slots"
                  text="Publish a slot to let prosumers reserve energy capacity."
                />
              )}
            </section>
          )}
          {["accounts", "activations"].includes(page) && (
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>
                    {page === "activations"
                      ? "Pending activation"
                      : "People in your network"}
                  </h2>
                  <p>
                    {page === "activations"
                      ? "Activate prosumer registrations from Android before they can sign in."
                      : "Manage staff access and prosumer profiles."}
                  </p>
                </div>
                {page === "accounts" && (
                  <div className="d-flex gap-2">
                    <button
                      className="btn btn-light"
                      onClick={() =>
                        setModal({
                          title: "Create prosumer",
                          fields: [
                            ["nic", "National Identity Card"],
                            ...profileFields,
                            ["email", "Email", "email"],
                            ["password", "Initial password", "password"],
                          ],
                          submit: (body) =>
                            act(
                              "/users/prosumers",
                              "POST",
                              body,
                              "Prosumer created",
                            ),
                        })
                      }
                    >
                      New prosumer
                    </button>
                    <button
                      className="btn btn-primary"
                      onClick={() =>
                        setModal({
                          title: "Create Backoffice or Grid Operator account",
                          fields: [
                            ["name", "Full name"],
                            ["email", "Email", "email"],
                            ["password", "Initial password", "password"],
                            [
                              "role",
                              "Role",
                              "select",
                              [
                                { value: "Backoffice", label: "Backoffice" },
                                {
                                  value: "GridOperator",
                                  label: "Grid Operator",
                                },
                              ],
                            ],
                          ],
                          submit: (body) =>
                            act(
                              "/users/staff",
                              "POST",
                              body,
                              "Staff account created",
                            ),
                        })
                      }
                    >
                      <Plus size={17} /> New staff
                    </button>
                  </div>
                )}
              </div>
              {users.filter(
                (u) => page !== "activations" || u.status === "Pending",
              ).length ? (
                <Table
                  headings={[
                    "Name / NIC",
                    "Email",
                    "Role",
                    "Status",
                    "Actions",
                  ]}
                >
                  {users
                    .filter(
                      (u) => page !== "activations" || u.status === "Pending",
                    )
                    .map((u) => (
                      <tr key={u.id}>
                        <td>
                          <strong>{u.name}</strong>
                          <small className="cell-sub">
                            {u.nic || "Staff account"}
                          </small>
                        </td>
                        <td>{u.email}</td>
                        <td>{labelRole(u.role)}</td>
                        <td>
                          <Badge>{u.status}</Badge>
                        </td>
                        <td>
                          <div className="action-group">
                            {u.role === "Prosumer" && (
                              <button
                                onClick={() =>
                                  setModal({
                                    title: "Edit prosumer",
                                    fields: profileFields,
                                    initial: u,
                                    submit: (body) =>
                                      act("/users/" + u.id, "PUT", body),
                                  })
                                }
                              >
                                Edit
                              </button>
                            )}
                            {u.id !== session.user.id && (
                              <button
                                onClick={() =>
                                  confirmAction(
                                    u.status === "Active"
                                      ? "Deactivate account"
                                      : "Activate account",
                                    "/users/" +
                                      u.id +
                                      (u.status === "Active"
                                        ? "/deactivate"
                                        : "/activate"),
                                    "Account updated",
                                  )
                                }
                              >
                                {u.status === "Active"
                                  ? "Deactivate"
                                  : "Activate"}
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                </Table>
              ) : (
                <Empty title="No accounts awaiting activation" />
              )}
            </section>
          )}
          {page === "profile" && (
            <section className="panel profile-panel">
              <div className="panel-header">
                <div>
                  <h2>Account details</h2>
                  <p>Your role and access are managed by Backoffice.</p>
                </div>
              </div>
              <dl>
                <dt>Name</dt>
                <dd>{data.me?.name}</dd>
                <dt>Email</dt>
                <dd>{data.me?.email}</dd>
                <dt>Role</dt>
                <dd>{labelRole(session.user.role)}</dd>
                <dt>Phone</dt>
                <dd>{data.me?.phone || "Not provided"}</dd>
                <dt>Address</dt>
                <dd>{data.me?.address || "Not provided"}</dd>
              </dl>
              <button
                className="btn btn-primary"
                onClick={() =>
                  setModal({
                    title: "Edit my profile",
                    fields: profileFields,
                    initial: data.me,
                    submit: (body) => act("/auth/me", "PUT", body),
                  })
                }
              >
                Edit profile
              </button>
            </section>
          )}
          {page === "verify" && (
            <Verify
              api={api}
              onComplete={(b) => {
                setSummary(b);
                setToast("Energy transfer completed");
                refresh();
              }}
            />
          )}
          <footer className="workspace-footer">
            Solara · Smart Solar Microgrid Trading System{" "}
            <span>All times shown in your local timezone</span>
          </footer>
        </div>
      </main>
      {toast && (
        <div className="toast-message" role="status">
          <CheckCircle2 size={18} />
          {toast}
        </div>
      )}
      {modal && (
        <Modal
          key={modal.title}
          title={modal.title}
          fields={modal.fields}
          initial={modal.initial}
          onSubmit={modal.submit}
          close={() => setModal(null)}
        >
          {modal.children}
        </Modal>
      )}
      {summary && (
        <div className="dialog-backdrop">
          <section
            className="dialog"
            role="dialog"
            aria-modal="true"
            aria-label="Reservation summary"
          >
            <header>
              <h2>Reservation summary</h2>
              <button
                className="icon-btn"
                aria-label="Close summary"
                onClick={() => setSummary(null)}
              >
                <X />
              </button>
            </header>
            <Badge>{summary.status}</Badge>
            <dl className="summary">
              <dt>Booking ID</dt>
              <dd>{summary.id}</dd>
              <dt>Prosumer</dt>
              <dd>{summary.prosumerName}</dd>
              <dt>Node</dt>
              <dd>{summary.stationName}</dd>
              <dt>Trading window</dt>
              <dd>
                {date(summary.start)} – {date(summary.end)}
              </dd>
              <dt>Energy</dt>
              <dd>
                {summary.energyKwh} kWh · {summary.direction}
              </dd>
              {summary.transferredKwh && (
                <>
                  <dt>Transferred</dt>
                  <dd>{summary.transferredKwh} kWh</dd>
                </>
              )}
            </dl>
            <button
              className="btn btn-primary"
              onClick={() => setSummary(null)}
            >
              Done
            </button>
          </section>
        </div>
      )}
    </div>
  );
}
// Verify transaction payloads and record operator-confirmed transfers.
function Verify({ api, onComplete }) {
  const [code, setCode] = useState(""),
    [booking, setBooking] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  // Check the entered QR payload against the current server record.
  async function verify(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setBooking(null);
    try {
      setBooking(
        await api("/reservations/verify", "POST", { qrCode: code.trim() }),
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  // Submit measured energy to the server for one-time transfer completion.
  async function complete(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const b = await api("/reservations/complete", "POST", {
        qrCode: code.trim(),
        transferredKwh: Number(
          new FormData(e.currentTarget).get("transferredKwh"),
        ),
      });
      setBooking(null);
      setCode("");
      onComplete(b);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel verify-panel">
      <span className="node-icon">
        <ScanLine size={30} />
      </span>
      <h2>Verify an energy transfer</h2>
      <p className="muted">
        Use the Android operator app to scan a QR code, or enter its transaction
        payload here.
      </p>
      <form onSubmit={verify}>
        <label className="field">
          <span>Transaction QR payload</span>
          <textarea
            className="form-control"
            value={code}
            onChange={(e) => {
              setCode(e.target.value);
              setBooking(null);
            }}
            required
          />
        </label>
        <button className="btn btn-primary" disabled={busy}>
          {busy ? "Checking…" : "Verify with server"}
        </button>
      </form>
      {error && (
        <div className="alert alert-danger mt-3" role="alert">
          {error}
        </div>
      )}
      {booking && (
        <form className="verified-booking" onSubmit={complete}>
          <Badge>{booking.status}</Badge>
          <h3>{booking.prosumerName}</h3>
          <p>
            {booking.stationName} · {date(booking.start)}
          </p>
          <p>Reserved energy: {booking.energyKwh} kWh</p>
          <Field
            spec={[
              "transferredKwh",
              "Actual transferred energy (kWh)",
              "number",
            ]}
            initial={booking.energyKwh}
          />
          <button className="btn btn-primary" disabled={busy}>
            Complete transfer
          </button>
        </form>
      )}
    </section>
  );
}
createRoot(document.getElementById("root")).render(<App />);
