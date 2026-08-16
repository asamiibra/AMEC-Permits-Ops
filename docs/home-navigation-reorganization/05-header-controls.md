# Global header

The header retains environment and persona context and adds:

- bounded global-search guidance linking to canonical workspaces;
- restrained Quick Create entries that do not bypass prerequisites;
- a notification bell and drawer backed by `/api/notifications` and `/api/notifications/summary`;
- acknowledgement through the existing `/acknowledge` endpoint before notification deep-link navigation.

There is no persistent Notifications sidebar item.
