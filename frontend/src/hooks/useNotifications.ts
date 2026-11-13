import { useState, useEffect, useRef, useCallback } from 'react';
import { AppNotification, User } from '../services/types';
import { api } from '../services/api';

export function useNotifications(currentUser: User | null) {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryCountRef = useRef<number>(0);
  const isRefreshingRef = useRef<boolean>(false);
  const isMountedRef = useRef<boolean>(true);

  // Fetch / re-sync notifications from database
  const refreshNotifications = useCallback(async () => {
    if (!currentUser || !isMountedRef.current) {
      setNotifications([]);
      setUnreadCount(0);
      return;
    }

    if (isRefreshingRef.current) {
      return;
    }
    isRefreshingRef.current = true;

    try {
      const data = await api.getNotifications();
      if (!isMountedRef.current) return;

      setNotifications((prev) => {
        // Build map by ID preserving existing read status if updated locally
        const map = new Map<string, AppNotification>();
        
        // Add fresh persistent records first
        for (const item of data) {
          map.set(item.id, item);
        }

        // Overlay any in-flight local state changes (e.g. marked as read locally)
        for (const existing of prev) {
          const fromDb = map.get(existing.id);
          if (fromDb) {
            map.set(existing.id, {
              ...fromDb,
              is_read: existing.is_read || fromDb.is_read,
            });
          } else {
            // Keep any real-time notification not yet in DB page window
            map.set(existing.id, existing);
          }
        }

        const merged = Array.from(map.values()).sort((a, b) => {
          const tA = a.created_at ? new Date(a.created_at).getTime() : 0;
          const tB = b.created_at ? new Date(b.created_at).getTime() : 0;
          return tB - tA;
        });

        // Compute unread count from merged list to guarantee consistency
        setUnreadCount(merged.filter((n) => !n.is_read).length);
        return merged;
      });
    } catch (err) {
      console.error('Failed to fetch/refresh notifications:', err);
      // Refresh failure must not crash or terminate SSE connection
    } finally {
      isRefreshingRef.current = false;
    }
  }, [currentUser]);

  // Mark single notification as read
  const markAsRead = useCallback(async (id: string) => {
    try {
      await api.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      console.error('Failed to mark notification as read:', err);
    }
  }, []);

  // Connect to SSE stream
  useEffect(() => {
    if (!currentUser) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      setIsConnected(false);
      setNotifications([]);
      setUnreadCount(0);
      return;
    }

    refreshNotifications();

    isMountedRef.current = true;

    const connectSSE = () => {
      if (!isMountedRef.current) return;

      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      // Native EventSource carries session cookies ({ withCredentials: true } ensures cross-origin cookies work if direct API URL is set)
      const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
      const es = new EventSource(`${apiBase}/api/v1/auth/notifications/stream`, { withCredentials: true });
      eventSourceRef.current = es;

      es.addEventListener('connected', () => {
        if (!isMountedRef.current) return;
        setIsConnected(true);
        retryCountRef.current = 0;
        // Re-sync persistent notifications upon successful (re)connection
        refreshNotifications();
      });

      es.addEventListener('notification', (e: MessageEvent) => {
        if (!isMountedRef.current) return;
        try {
          const newNotif: AppNotification = JSON.parse(e.data);
          setNotifications((prev) => {
            // Avoid duplicate by ID if already present
            if (prev.some((n) => n.id === newNotif.id)) {
              return prev;
            }
            const updated = [newNotif, ...prev];
            setUnreadCount(updated.filter((n) => !n.is_read).length);
            return updated;
          });
        } catch (err) {
          console.error('Failed to parse SSE notification message:', err);
        }
      });

      es.addEventListener('ping', () => {
        // Heartbeat received, connection is healthy
      });

      es.onerror = () => {
        if (!isMountedRef.current) return;
        setIsConnected(false);
        es.close();
        eventSourceRef.current = null;

        // Exponential backoff reconnect: 2s, 4s, 8s, up to 16s max
        const backoff = Math.min(16000, 2000 * Math.pow(2, retryCountRef.current));
        retryCountRef.current += 1;

        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }
        reconnectTimeoutRef.current = setTimeout(() => {
          if (isMountedRef.current && currentUser) {
            connectSSE();
          }
        }, backoff);
      };
    };

    connectSSE();

    return () => {
      isMountedRef.current = false;
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      setIsConnected(false);
    };
  }, [currentUser, refreshNotifications]);

  // Delete single notification
  const deleteNotification = useCallback(async (id: string) => {
    try {
      await api.deleteNotification(id);
      setNotifications((prev) => {
        const item = prev.find((n) => n.id === id);
        if (item && !item.is_read) {
          setUnreadCount((c) => Math.max(0, c - 1));
        }
        return prev.filter((n) => n.id !== id);
      });
    } catch (err) {
      console.error('Failed to delete notification:', err);
    }
  }, []);

  return {
    notifications,
    unreadCount,
    isConnected,
    markAsRead,
    deleteNotification,
    refreshNotifications,
  };
}
