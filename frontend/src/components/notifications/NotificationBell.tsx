import React, { useState, useRef, useEffect } from 'react';
import { Bell, Check, Radio, Trash2, ArrowRight } from 'lucide-react';
import { AppNotification } from '../../services/types';

interface NotificationBellProps {
  notifications: AppNotification[];
  unreadCount: number;
  isConnected: boolean;
  onMarkAsRead: (id: string) => void;
  onDelete?: (id: string) => void;
  onNavigateToRequest?: (refType: string, refId: string) => void;
}

export const NotificationBell: React.FC<NotificationBellProps> = ({
  notifications,
  unreadCount,
  isConnected,
  onMarkAsRead,
  onDelete,
  onNavigateToRequest,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const formatTimestamp = (dateStr?: string) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000);
    if (diffSec < 60) return 'Just now';
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  };

  return (
    <div className="relative z-50" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="relative p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
        title={isConnected ? 'Real-time notifications connected' : 'Connecting to notification stream...'}
      >
        <Bell className="w-4 h-4" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex items-center justify-center min-w-[16px] h-4 px-1 rounded-full bg-rose-600 text-[10px] font-bold text-white shadow-xs">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
        {/* SSE Live status indicator dot */}
        <span
          className={`absolute bottom-1 right-1 w-2 h-2 rounded-full border border-white ${
            isConnected ? 'bg-emerald-500' : 'bg-amber-400 animate-pulse'
          }`}
          title={isConnected ? 'SSE Live Stream Active' : 'Connecting...'}
        />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white border border-slate-200 rounded-xl shadow-2xl z-[100] overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-xs text-slate-800">Notifications</span>
              {unreadCount > 0 && (
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200">
                  {unreadCount} new
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
              <Radio className={`w-3 h-3 ${isConnected ? 'text-emerald-500' : 'text-amber-500 animate-pulse'}`} />
              <span>{isConnected ? 'Real-time' : 'Reconnecting...'}</span>
            </div>
          </div>

          <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
            {notifications.length === 0 ? (
              <div className="px-4 py-8 text-center text-xs text-slate-400">
                No notifications received yet
              </div>
            ) : (
              notifications.map((item) => (
                <div
                  key={item.id}
                  className={`p-3.5 flex items-start justify-between gap-3 transition-colors ${
                    item.is_read ? 'bg-white hover:bg-slate-50' : 'bg-indigo-50/40 hover:bg-indigo-50/70'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold text-slate-800 truncate">
                        {item.title}
                      </span>
                      {!item.is_read && (
                        <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 shrink-0" />
                      )}
                    </div>
                    <p className="text-[11px] text-slate-600 leading-relaxed break-words">
                      {item.message}
                    </p>
                    
                    {/* Actionable Request Status Context */}
                    <div className="mt-2 flex items-center justify-between gap-2">
                      <span className="text-[10px] text-slate-400 block">
                        {formatTimestamp(item.created_at)}
                      </span>

                      {item.reference_type && item.reference_id && (
                        <div>
                          {item.request_status === 'PENDING' ? (
                            <button
                              onClick={() => {
                                setIsOpen(false);
                                onNavigateToRequest?.(item.reference_type!, item.reference_id!);
                              }}
                              className="px-2 py-0.5 rounded bg-indigo-600 hover:bg-indigo-700 text-white text-[10px] font-semibold flex items-center gap-1 cursor-pointer transition-colors"
                            >
                              <span>Review</span>
                              <ArrowRight className="w-2.5 h-2.5" />
                            </button>
                          ) : item.request_status ? (
                            <span
                              className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${
                                item.request_status === 'APPROVED' || item.request_status === 'IMPLEMENTED' || item.request_status === 'ROSTER_PENDING'
                                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                  : item.request_status === 'REJECTED'
                                  ? 'bg-rose-50 text-rose-700 border border-rose-200'
                                  : 'bg-amber-50 text-amber-700 border border-amber-200'
                              }`}
                            >
                              {item.request_status === 'APPROVED' || item.request_status === 'IMPLEMENTED' || item.request_status === 'ROSTER_PENDING'
                                ? 'ACCEPTED'
                                : item.request_status === 'REJECTED'
                                ? 'REJECTED'
                                : 'UNDER REVIEW'}
                            </span>
                          ) : null}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Actions: Mark read or Delete */}
                  <div className="flex flex-col items-center gap-1 shrink-0">
                    {!item.is_read ? (
                      <button
                        onClick={() => onMarkAsRead(item.id)}
                        className="p-1 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
                        title="Mark as read"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                    ) : (
                      onDelete && (
                        <button
                          onClick={() => onDelete(item.id)}
                          className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-colors"
                          title="Delete notification"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

