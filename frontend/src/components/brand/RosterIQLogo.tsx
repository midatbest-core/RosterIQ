import React from 'react';

interface RosterIQLogoProps {
  variant?: 'icon' | 'full' | 'wordmark';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showTagline?: boolean;
  className?: string;
}

export const RosterIQLogo: React.FC<RosterIQLogoProps> = ({
  variant = 'full',
  size = 'md',
  showTagline = false,
  className = '',
}) => {
  const iconDimensions = {
    sm: { box: 28, text: 'text-sm', tag: 'text-[9px]' },
    md: { box: 36, text: 'text-base', tag: 'text-[10px]' },
    lg: { box: 44, text: 'text-xl', tag: 'text-xs' },
    xl: { box: 56, text: 'text-2xl', tag: 'text-sm' },
  }[size];

  const IconSVG = (
    <svg
      width={iconDimensions.box}
      height={iconDimensions.box}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="shrink-0"
    >
      <defs>
        <linearGradient id="logo-bg" x1="4" y1="4" x2="44" y2="44" gradientUnits="userSpaceOnUse">
          <stop stopColor="#312e81" />
          <stop offset="0.5" stopColor="#1e1b4b" />
          <stop offset="1" stopColor="#0f172a" />
        </linearGradient>
        <linearGradient id="logo-check" x1="18" y1="20" x2="36" y2="34" gradientUnits="userSpaceOnUse">
          <stop stopColor="#10b981" />
          <stop offset="1" stopColor="#059669" />
        </linearGradient>
      </defs>

      <rect x="2" y="2" width="44" height="44" rx="12" fill="url(#logo-bg)" stroke="#4f46e5" strokeWidth="1.5" />
      <path d="M2 14C2 8.47715 6.47715 4 12 4H36C41.5228 4 46 8.47715 46 14V16H2V14Z" fill="#4338ca" fillOpacity="0.45" />

      {/* Binder rings */}
      <rect x="13" y="1" width="3" height="6" rx="1.5" fill="#a5b4fc" />
      <rect x="32" y="1" width="3" height="6" rx="1.5" fill="#a5b4fc" />

      {/* Calendar shift grid */}
      <circle cx="12" cy="22" r="2.2" fill="#6366f1" fillOpacity="0.8" />
      <circle cx="20" cy="22" r="2.2" fill="#818cf8" />
      <circle cx="28" cy="22" r="2.2" fill="#6366f1" fillOpacity="0.8" />
      <circle cx="36" cy="22" r="2.2" fill="#818cf8" />

      <circle cx="12" cy="30" r="2.2" fill="#818cf8" />
      <circle cx="12" cy="38" r="2.2" fill="#6366f1" fillOpacity="0.8" />

      {/* Dynamic Optimal Checkmark */}
      <path
        d="M19 31.5L25.5 38L37 25"
        stroke="url(#logo-check)"
        strokeWidth="4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );

  if (variant === 'icon') {
    return <div className={`inline-flex items-center ${className}`}>{IconSVG}</div>;
  }

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {IconSVG}
      <div className="flex flex-col">
        <div className="flex items-center gap-1.5 leading-none">
          <span className={`font-black tracking-tight text-white ${iconDimensions.text}`}>
            Roster<span className="text-indigo-400">IQ</span>
          </span>
          <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-mono">
            WFM
          </span>
        </div>
        {showTagline ? (
          <span className={`text-slate-400 font-medium tracking-wide mt-1 ${iconDimensions.tag}`}>
            Smart Rostering. Better Teams.
          </span>
        ) : (
          <span className="text-[10px] text-slate-400 font-medium">Smart Rostering</span>
        )}
      </div>
    </div>
  );
};
