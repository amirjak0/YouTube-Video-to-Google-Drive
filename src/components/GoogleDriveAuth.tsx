import React, { useState } from 'react';
import { User } from 'firebase/auth';
import { googleSignIn, logout } from '../services/firebaseAuth';
import { CheckCircle2, Cloud, LogOut, RefreshCw, AlertCircle, HardDrive } from 'lucide-react';

interface Props {
  user: User | null;
  token: string | null;
  onAuthChange: (user: User | null, token: string | null) => void;
  folderId?: string;
  onRefreshDrive: () => void;
}

export const GoogleDriveAuth: React.FC<Props> = ({
  user,
  token,
  onAuthChange,
  folderId,
  onRefreshDrive,
}) => {
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSignIn = async () => {
    setIsLoggingIn(true);
    setError(null);
    try {
      const res = await googleSignIn();
      if (res) {
        onAuthChange(res.user, res.accessToken);
      }
    } catch (err: any) {
      console.error('Sign-in error:', err);
      setError(err?.message || 'خطا در اتصال به حساب گوگل');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleSignOut = async () => {
    try {
      await logout();
      onAuthChange(null, null);
    } catch (err: any) {
      console.error('Logout error:', err);
    }
  };

  if (!user || !token) {
    return (
      <div className="bg-gradient-to-r from-blue-950/40 via-neutral-900/60 to-neutral-900/60 border border-blue-600/30 rounded-xl p-4 sm:p-5 shadow-lg backdrop-blur-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-2.5 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-lg shrink-0 mt-0.5">
              <Cloud className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">اتصال مستقیم به Google Drive</h3>
                <span className="px-2 py-0.5 text-xs bg-amber-500/10 border border-amber-500/30 text-amber-300 rounded font-medium">
                  نیاز به تأیید اتصال
                </span>
              </div>
              <p className="text-xs text-neutral-300 mt-1 leading-relaxed">
                برای ذخیره خودکار ویدیوها با کیفیت کامل در گوگل درایو خود، فقط کافیست با حساب گوگل وارد شوید (بدون نیاز به ساخت API Key یا تنطیمات دستی).
              </p>
              {error && (
                <div className="flex items-center gap-1.5 text-xs text-rose-400 mt-2 bg-rose-500/10 border border-rose-500/20 px-3 py-1.5 rounded-lg">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={handleSignIn}
              disabled={isLoggingIn}
              className="gsi-material-button transition-all hover:scale-[1.02] active:scale-[0.98] shadow-md hover:shadow-blue-500/10"
              title="ورود با حساب گوگل برای دسترسی به گوگل درایو"
            >
              <div className="gsi-material-button-state"></div>
              <div className="gsi-material-button-content-wrapper">
                <div className="gsi-material-button-icon">
                  <svg version="1.1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" style={{ display: 'block' }}>
                    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"></path>
                    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"></path>
                    <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"></path>
                    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"></path>
                    <path fill="none" d="M0 0h48v48H0z"></path>
                  </svg>
                </div>
                <span className="gsi-material-button-contents font-medium">
                  {isLoggingIn ? 'در حال اتصال...' : 'ورود با حساب گوگل (Sign in with Google)'}
                </span>
              </div>
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-r from-emerald-950/40 via-neutral-900/60 to-neutral-900/60 border border-emerald-600/30 rounded-xl p-4 sm:p-5 shadow-lg backdrop-blur-sm">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {user.photoURL ? (
            <img
              src={user.photoURL}
              alt={user.displayName || 'Google User'}
              className="w-11 h-11 rounded-full border-2 border-emerald-500/40 shadow-sm shrink-0"
            />
          ) : (
            <div className="w-11 h-11 rounded-full bg-emerald-600/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 font-bold shrink-0">
              {user.email ? user.email[0].toUpperCase() : 'G'}
            </div>
          )}

          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-bold text-white">{user.displayName || 'کاربر متصل شده'}</span>
              <span className="flex items-center gap-1 px-2 py-0.5 text-xs bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-full font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" />
                متصل به Google Drive
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs text-neutral-400 mt-1 flex-wrap">
              <span>{user.email}</span>
              <span className="text-neutral-600">•</span>
              <span className="flex items-center gap-1 text-neutral-300">
                <HardDrive className="w-3.5 h-3.5 text-blue-400" />
                پوشه هدف: <code className="text-blue-300 font-mono text-[11px] bg-neutral-800 px-1.5 py-0.5 rounded">{folderId || 'YouTube-AutoSync (خودکار)'}</code>
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={onRefreshDrive}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-neutral-300 hover:text-white bg-neutral-800/80 hover:bg-neutral-700/80 border border-neutral-700 rounded-lg transition-colors"
            title="بروزرسانی فایل‌های گوگل درایو"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>بروزرسانی درایو</span>
          </button>

          <button
            onClick={handleSignOut}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-rose-300 hover:text-rose-200 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 rounded-lg transition-colors"
            title="قطع اتصال حساب گوگل"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>قطع اتصال</span>
          </button>
        </div>
      </div>
    </div>
  );
};
