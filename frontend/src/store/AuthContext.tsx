import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { setApiKey, getStoredApiKey } from '../utils/api';

const API_BASE = '/api';

interface AuthState {
  /** null = still loading, true = authenticated, false = not authenticated */
  isAuthenticated: boolean | null;
  /** Whether the backend requires authentication */
  authEnabled: boolean;
  /** True while checking auth status with backend */
  isLoading: boolean;
  /** Error message from last action */
  error: string | null;
  /** Logged-in username (if authenticated) */
  username: string | null;
  /** User's scan credits */
  credits: number | null;
  /** Whether the payment gateway is configured */
  paymentConfigured: boolean;
}

interface AuthContextType extends AuthState {
  /** Attempt to log in with username and password */
  login: (username: string, password: string) => Promise<boolean>;
  /** Step 1 of signup: validate input and email a verification code.
   *  Does NOT create the account or log the user in yet. */
  register: (username: string, email: string, password: string) => Promise<{ success: boolean; error?: string; otpRequired?: boolean; email?: string }>;
  /** Step 2 of signup: confirm the emailed code. Creates the account and logs in on success. */
  verifyOtp: (email: string, otp: string) => Promise<{ success: boolean; error?: string }>;
  /** Resend the signup verification code to the given email. */
  resendOtp: (email: string) => Promise<{ success: boolean; error?: string; message?: string }>;
  /** Clear session token and log out */
  forgotPassword: (email: string) => Promise<{ success: boolean; message?: string; error?: string }>;
  resetPassword: (token: string, newPassword: string) => Promise<{ success: boolean; message?: string; error?: string }>;
  logout: () => void;
  /** Re-check auth status with the backend */
  checkAuth: () => Promise<void>;
  /** Refresh the user's credit balance */
  refreshCredits: () => Promise<void>;
  /** Whether registration is open */
  registrationOpen: boolean;
}

const initialState: AuthState & { registrationOpen: boolean } = {
  isAuthenticated: null,
  authEnabled: false,
  isLoading: true,
  error: null,
  username: null,
  credits: null,
  paymentConfigured: false,
  registrationOpen: true,
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/** Fetch credits and paymentConfigured from the backend after login/verify-otp */
async function fetchPaymentState(token: string): Promise<{ credits: number; paymentConfigured: boolean }> {
  let credits = 0;
  let paymentConfigured = false;
  try {
    const credRes = await fetch(`${API_BASE}/payment/credits`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (credRes.ok) { credits = (await credRes.json()).credits ?? 0; }
  } catch {}
  try {
    const planRes = await fetch(`${API_BASE}/payment/plans`);
    if (planRes.ok) { paymentConfigured = (await planRes.json()).configured ?? false; }
  } catch {}
  return { credits, paymentConfigured };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState & { registrationOpen: boolean }>(initialState);

  const checkAuth = useCallback(async () => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    try {
      const res = await fetch(`${API_BASE}/auth/status`);
      if (!res.ok) {
        setState(prev => ({
          ...prev,
          isAuthenticated: false,
          authEnabled: false,
          isLoading: false,
          error: 'Cannot connect to server. Make sure the backend is running.',
          username: null,
        }));
        return;
      }
      const data = await res.json();

      setState(prev => ({ ...prev, registrationOpen: data.registration_open ?? true }));

      if (!data.auth_enabled) {
        setState(prev => ({
          ...prev,
          isAuthenticated: true,
          authEnabled: false,
          isLoading: false,
          error: null,
          username: null,
        }));
        return;
      }

      // Check if we have a stored session token
      const storedKey = getStoredApiKey();
      if (!storedKey) {
        setState(prev => ({
          ...prev,
          isAuthenticated: false,
          authEnabled: true,
          isLoading: false,
          error: null,
          username: null,
        }));
        return;
      }

      // Verify the stored token against the backend
      try {
        const verifyRes = await fetch(`${API_BASE}/auth/verify`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: storedKey }),
        });
        const verifyData = await verifyRes.json();

        if (verifyData.valid) {
          // Token is still valid — also fetch payment status and credits
          const { credits, paymentConfigured } = await fetchPaymentState(storedKey);
          setState(prev => ({
            isAuthenticated: true,
            authEnabled: true,
            isLoading: false,
            error: null,
            username: localStorage.getItem('trinetra_username'),
            registrationOpen: prev.registrationOpen,
            credits,
            paymentConfigured,
          }));
        } else {
          // Token expired or server restarted — clear it
          setApiKey(null);
          try { localStorage.removeItem('trinetra_username'); } catch {}
          setState(prev => ({
            ...prev,
            isAuthenticated: false,
            authEnabled: true,
            isLoading: false,
            error: null,
            username: null,
          }));
        }
      } catch {
        // Can't reach server — assume token is valid (optimistic)
        setState(prev => ({
          isAuthenticated: true,
          authEnabled: true,
          isLoading: false,
          error: null,
          username: localStorage.getItem('trinetra_username'),
          registrationOpen: prev.registrationOpen,
          credits: prev.credits,
          paymentConfigured: prev.paymentConfigured,
        }));
      }
    } catch {
      setState(prev => ({
        ...prev,
        isAuthenticated: false,
        authEnabled: false,
        isLoading: false,
        error: 'Network error. Please check your connection and try again.',
        username: null,
      }));
    }
  }, []);

  const register = useCallback(async (username: string, email: string, password: string): Promise<{ success: boolean; error?: string; otpRequired?: boolean; email?: string }> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password }),
      });
      const data = await res.json();

      // Account is NOT created yet — this only sends the verification code.
      // Auth state (isAuthenticated/token) stays untouched here.
      setState(prev => ({ ...prev, isLoading: false }));

      if (data.success && data.otp_required) {
        return { success: true, otpRequired: true, email: data.email || email };
      }

      return { success: false, error: data.error || 'Registration failed.' };
    } catch {
      setState(prev => ({ ...prev, isLoading: false }));
      return { success: false, error: 'Network error. Could not connect to server.' };
    }
  }, []);

  const verifyOtp = useCallback(async (email: string, otp: string): Promise<{ success: boolean; error?: string }> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    try {
      const res = await fetch(`${API_BASE}/auth/register/verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, otp }),
      });
      const data = await res.json();

      if (data.success && data.token) {
        setApiKey(data.token);
        try {
          localStorage.setItem('trinetra_username', data.username || '');
        } catch {}
        // Fetch credits and paymentConfigured now that the account exists (mirrors login())
        const { credits, paymentConfigured } = await fetchPaymentState(data.token);
        setState(prev => ({
          isAuthenticated: true,
          authEnabled: true,
          isLoading: false,
          error: null,
          username: data.username || null,
          registrationOpen: prev.registrationOpen,
          credits,
          paymentConfigured,
        }));
        return { success: true };
      } else {
        setState(prev => ({ ...prev, isLoading: false }));
        return { success: false, error: data.error || 'Verification failed.' };
      }
    } catch {
      setState(prev => ({ ...prev, isLoading: false }));
      return { success: false, error: 'Network error. Could not connect to server.' };
    }
  }, []);

  const resendOtp = useCallback(async (email: string): Promise<{ success: boolean; error?: string; message?: string }> => {
    try {
      const res = await fetch(`${API_BASE}/auth/register/resend-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();

      if (data.success) {
        return { success: true, message: data.message };
      }
      return { success: false, error: data.error || 'Could not resend code.' };
    } catch {
      return { success: false, error: 'Network error. Could not connect to server.' };
    }
  }, []);

  const forgotPassword = useCallback(async (email: string): Promise<{ success: boolean; message?: string; error?: string }> => {
  try {
    const res = await fetch(`${API_BASE}/auth/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    const data = await res.json();
    return { success: !!data.success, message: data.message };
  } catch {
    return { success: false, error: 'Network error. Could not connect to server.' };
  }
}, []);

const resetPassword = useCallback(async (token: string, newPassword: string): Promise<{ success: boolean; message?: string; error?: string }> => {
  try {
    const res = await fetch(`${API_BASE}/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, new_password: newPassword }),
    });
    const data = await res.json();
    if (data.success) return { success: true, message: data.message };
    return { success: false, error: data.error || 'Could not reset password.' };
  } catch {
    return { success: false, error: 'Network error. Could not connect to server.' };
  }
}, []);
  
  const login = useCallback(async (username: string, password: string): Promise<boolean> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();

      if (data.success && data.token) {
        setApiKey(data.token);
        try {
          localStorage.setItem('trinetra_username', data.username || username);
        } catch {}
        // Fetch credits and paymentConfigured after successful login
        const { credits, paymentConfigured } = await fetchPaymentState(data.token);
        setState(prev => ({
          ...prev,
          isAuthenticated: true,
          authEnabled: true,
          isLoading: false,
          error: null,
          username: data.username || username,
          credits,
          paymentConfigured,
        }));
        return true;
      } else {
        setState(prev => ({
          ...prev,
          isLoading: false,
          error: data.error || 'Invalid username or password.',
          username: null,
        }));
        return false;
      }
    } catch {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: 'Network error. Could not connect to server.',
        username: null,
      }));
      return false;
    }
  }, []);

  const logout = useCallback(() => {
    setApiKey(null);
    try {
      localStorage.removeItem('trinetra_username');
    } catch {}
    setState(prev => ({
      ...prev,
      isAuthenticated: false,
      authEnabled: true,
      isLoading: false,
      error: null,
      username: null,
      credits: null,
    }));
  }, []);

  const refreshCredits = useCallback(async () => {
    const token = getStoredApiKey();
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/payment/credits`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setState(prev => ({ ...prev, credits: data.credits }));
      }
    } catch {
      // Silently fail — credits will show as null
    }
  }, []);

  // Check auth on mount
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // Fetch credits when authenticated
  useEffect(() => {
    if (state.isAuthenticated && state.username) {
      refreshCredits();
    }
  }, [state.isAuthenticated, state.username, refreshCredits]);

  return (
    <AuthContext.Provider value={{ ...state, login, register, verifyOtp, resendOtp, forgotPassword, resetPassword, logout, checkAuth, refreshCredits, registrationOpen: state.registrationOpen }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
