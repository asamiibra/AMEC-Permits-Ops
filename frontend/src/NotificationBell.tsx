import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { api } from "./api";
import type { Persona } from "./PersonaIssuesNotifications";

type NotificationItem = { id: string; subject: string; message?: string; deep_link?: string; unread?: boolean; created_at?: string; cta_label?: string };

export function NotificationBell({ persona }: { persona: Persona }) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState<number | null>(null);
  const [error, setError] = useState("");
  const headers = { "X-Dev-User": `demo:${persona.toLowerCase()}` };

  const loadSummary = () => api<{ summary?: { unread?: number } }>(`/api/notifications/summary?persona=${persona}`, { headers }).then((value) => setUnread(Number(value.summary?.unread || 0))).catch(() => setUnread(null));
  useEffect(() => { void loadSummary(); }, [persona]);
  useEffect(() => {
    if (!open) return;
    setError("");
    api<{ notifications: NotificationItem[] }>(`/api/notifications?persona=${persona}&unread=false`, { headers }).then((value) => setItems((value.notifications || []).slice(0, 6))).catch(() => setError("Notifications could not be loaded."));
  }, [open, persona]);

  const acknowledge = async (item: NotificationItem) => {
    if (!item.unread) return;
    try {
      await api(`/api/notifications/${item.id}/acknowledge?persona=${persona}`, { method: "POST", headers });
      setItems((current) => current.map((candidate) => candidate.id === item.id ? { ...candidate, unread: false } : candidate));
      setUnread((current) => current == null ? current : Math.max(0, current - 1));
    } catch { setError("This notification could not be marked as read."); }
  };

  const openNotification = async (event: MouseEvent<HTMLAnchorElement>, item: NotificationItem) => {
    event.preventDefault();
    await acknowledge(item);
    window.location.assign(item.deep_link || "/notifications");
  };

  const markVisibleRead = async () => {
    await Promise.all(visibleItems.filter((item) => item.unread).map((item) => acknowledge(item)));
  };

  const visibleItems = useMemo(() => items.slice(0, 5), [items]);
  return <div className="notification-control">
    <button className="header-control notification-bell" aria-label="Notifications" aria-expanded={open} onClick={() => setOpen((value) => !value)}><span aria-hidden="true">◌</span>{unread !== null && unread > 0 && <span className="notification-count" aria-label={`${unread} unread notifications`}>{unread > 99 ? "99+" : unread}</span>}</button>
    {open && <div className="notification-popover" role="dialog" aria-label="Notification drawer">
      <div className="notification-popover-heading"><div><span className="eyebrow">NOTIFICATIONS</span><h3>Recent updates</h3></div><button className="text-button" onClick={() => { void markVisibleRead(); }}>Mark visible read</button></div>
      {error && <p className="notification-popover-error" role="alert">{error}</p>}
      {visibleItems.length ? <div className="notification-list">{visibleItems.map((item) => <a className={`notification-popover-item ${item.unread ? "unread" : ""}`} href={item.deep_link || "/notifications"} key={item.id} onClick={(event) => { void openNotification(event, item); }}><span className="notification-popover-dot" aria-hidden="true" /> <span><b>{item.subject}</b><small>{item.message || item.cta_label || "Open notification context"}</small></span></a>)}</div> : <p className="truthful-empty">No notifications are available for this persona.</p>}
      <a className="notification-view-all" href="/notifications">View all notifications →</a>
    </div>}
  </div>;
}
