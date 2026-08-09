import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../store/AuthContext';
import { ShieldIcon, EyeIcon, EyeOffIcon, UserIcon, MailIcon, AlertTriangleIcon, CheckCircleIcon, RefreshCwIcon, LogInIcon, UserPlusIcon, ArrowLeftIcon } from 'lucide-react';

type AuthMode = 'login' | 'register' | 'forgot' | 'reset';
type RegisterStep = 'form' | 'otp';

const RESEND_COOLDOWN_SECONDS = 60; // mirrors backend OTP_RESEND_COOLDOWN_SECONDS default

export default function LoginPage() {
  const { login, register, verifyOtp, resendOtp, forgotPassword, resetPassword, error, authEnabled } = useAuth();
  const [mode, setMode] = useState<AuthMode>('login');
  const [step, setStep] = useState<RegisterStep>('form');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [otp, setOtp] = useState('');
  const [pendingEmail, setPendingEmail] = useState('');
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resendMessage, setResendMessage] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const usernameRef = useRef<HTMLInputElement>(null);
  const otpRef = useRef<HTMLInputElement>(null);
  const [resetToken, setResetToken] = useState('');
  const [forgotEmail, setForgotEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [forgotMessage, setForgotMessage] = useState<string | null>(null);

  // If the user arrived via the emailed reset link, jump straight to the reset form
  useEffect(() => {
  const params = new URLSearchParams(window.location.search);
  const t = params.get('reset_token');
  if (t) {
    setResetToken(t);
    setMode('reset');
  }
}, []);

  // Focus username input on mount
  useEffect(() => {
    usernameRef.current?.focus();
  }, []);

  // Focus the OTP input as soon as we enter the verification step
  useEffect(() => {
    if (step === 'otp') {
      otpRef.current?.focus();
    }
  }, [step]);

  // Clear local error / reset the OTP step when switching modes
  useEffect(() => {
    setLocalError(null);
    setStep('form');
    setOtp('');
    setResendMessage(null);
  }, [mode]);

  // Tick the client-side resend cooldown down once a second (the backend
  // enforces the real cooldown regardless — this is just UX affordance).
  useEffect(() => {
    const t = setInterval(() => {
      setResendCooldown(c => (c > 0 ? c - 1 : 0));
    }, 1000);
    return () => clearInterval(t);
  }, []);

  const displayError = localError || error;

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim() || submitting) return;
    setSubmitting(true);
    setSuccess(false);
    setLocalError(null);
    const result = await login(username.trim(), password);
    if (result) {
      setSuccess(true);
    }
    setSubmitting(false);
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setLocalError(null);

    if (!username.trim() || username.trim().length < 3) {
      setLocalError('Username must be at least 3 characters.');
      return;
    }
    if (!email.trim() || !email.includes('@')) {
      setLocalError('Please enter a valid email address.');
      return;
    }
    if (!password.trim() || password.length < 6) {
      setLocalError('Password must be at least 6 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setLocalError('Passwords do not match.');
      return;
    }

    setSubmitting(true);
    setSuccess(false);
    const result = await register(username.trim(), email.trim(), password);

    if (result.success && result.otpRequired) {
      // Account is NOT created yet — move to the "enter the code" step.
      setPendingEmail(result.email || email.trim());
      setOtp('');
      setStep('otp');
      setResendCooldown(RESEND_COOLDOWN_SECONDS);
      setResendMessage(null);
      setLocalError(null);
    } else {
      setLocalError(result.error || 'Registration failed.');
    }
    setSubmitting(false);
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting || otp.trim().length < 4) return;
    setSubmitting(true);
    setLocalError(null);
    const result = await verifyOtp(pendingEmail, otp.trim());
    if (result.success) {
      setSuccess(true);
    } else {
      setLocalError(result.error || 'Verification failed.');
    }
    setSubmitting(false);
  };

  const handleResendOtp = async () => {
    if (resendCooldown > 0 || submitting) return;
    setLocalError(null);
    setResendMessage(null);
    const result = await resendOtp(pendingEmail);
    if (result.success) {
      setResendMessage(result.message || 'A new code has been sent.');
      setResendCooldown(RESEND_COOLDOWN_SECONDS);
    } else {
      setLocalError(result.error || 'Could not resend code.');
    }
  };

  const handleBackToForm = () => {
    setStep('form');
    setOtp('');
    setLocalError(null);
    setResendMessage(null);
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
  e.preventDefault();
  if (!forgotEmail.trim() || submitting) return;
  setSubmitting(true);
  setLocalError(null);
  setForgotMessage(null);
  const result = await forgotPassword(forgotEmail.trim());
  setForgotMessage(result.message || 'If an account with that email exists, a reset link has been sent.');
  setSubmitting(false);
};

const handleResetPassword = async (e: React.FormEvent) => {
  e.preventDefault();
  if (submitting) return;
  setLocalError(null);
  if (newPassword.length < 6) {
    setLocalError('Password must be at least 6 characters.');
    return;
  }
  if (newPassword !== confirmNewPassword) {
    setLocalError('Passwords do not match.');
    return;
  }
  setSubmitting(true);
  const result = await resetPassword(resetToken, newPassword);
  if (result.success) {
    setSuccess(true);
    setTimeout(() => {
      window.history.replaceState({}, '', window.location.pathname); // strip ?reset_token from the URL
      setMode('login');
      setSuccess(false);
      setNewPassword('');
      setConfirmNewPassword('');
    }, 1800);
  } else {
    setLocalError(result.error || 'Could not reset password.');
  }
  setSubmitting(false);
};

  return (
    <div className="login-page">
      <div className="login-bg-gradient" />
      <div className="login-particles">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="login-orb" style={{
            '--orb-x': `${Math.random() * 100}%`,
            '--orb-y': `${Math.random() * 100}%`,
            '--orb-size': `${80 + Math.random() * 180}px`,
            '--orb-duration': `${20 + Math.random() * 30}s`,
            '--orb-delay': `${Math.random() * 15}s`,
            '--orb-opacity': 0.02 + Math.random() * 0.05,
          } as React.CSSProperties} />
        ))}
      </div>

      <div className="login-grid" />

      <div className="login-card">
        <div className="login-card-glow" />
        <div className="login-card-inner">
          {/* Logo */}
          <div className="login-logo">
            <div className="login-logo-icon">
              <ShieldIcon size={28} />
            </div>
            <div className="login-logo-text">
              <span className="login-logo-name">TRINETRA</span>
              <span className="login-logo-subtitle">OSINT Dashboard</span>
            </div>
          </div>

          <div className="login-divider" />

          {/* Tab Switcher — hidden mid-verification so it can't be used to escape the OTP step */}
          {step === 'form' && (mode === 'login' || mode === 'register') && (
          <div className="login-tabs">
              <button
                className={`login-tab ${mode === 'login' ? 'active' : ''}`}
                onClick={() => setMode('login')}
              >
                <LogInIcon size={14} />
                Sign In
              </button>
              <button
                className={`login-tab ${mode === 'register' ? 'active' : ''}`}
                onClick={() => setMode('register')}
              >
                <UserPlusIcon size={14} />
                Register
              </button>
            </div>
          )}

          {/* Title */}
          {mode === 'login' ? (
            <>
              <h1 className="login-title">Welcome Back</h1>
              <p className="login-subtitle">
                Sign in to access the OSINT intelligence dashboard.
              </p>
            </>
          ) : step === 'form' ? (
            <>
              <h1 className="login-title">Create Account</h1>
              <p className="login-subtitle">
                Register to get started with the OSINT intelligence dashboard.
              </p>
            </>
          ) : (
            <>
              <h1 className="login-title">Verify Your Email</h1>
              <p className="login-subtitle">
                Enter the 6-digit code we sent to <strong>{pendingEmail}</strong>.
              </p>
            </>
          )}

          {/* ── Login form ── */}
          {mode === 'login' && (
            <form onSubmit={handleLogin} className="login-form">
              <div className="login-input-wrapper">
                <div className="login-input-icon">
                  <UserIcon size={16} />
                </div>
                <input
                  ref={usernameRef}
                  type="text"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  placeholder="Username"
                  className="login-input"
                  disabled={submitting || success}
                  autoComplete="username"
                  spellCheck={false}
                />
              </div>

              <div className="login-input-wrapper">
                <div className="login-input-icon">
                  <ShieldIcon size={15} />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Password"
                  className="login-input"
                  disabled={submitting || success}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="login-toggle-vis"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOffIcon size={15} /> : <EyeIcon size={15} />}
                </button>
            </div>

              <div className="login-forgot-row">
  <button
    type="button"
    className="login-link-btn"
    onClick={() => { setMode('forgot'); setLocalError(null); setForgotMessage(null); }}
  >
    Forgot password?
  </button>
</div>

              {displayError && (
                <div className="login-error">
                  <AlertTriangleIcon size={13} />
                  <span>{displayError}</span>
                </div>
              )}

              {success && (
                <div className="login-success">
                  <CheckCircleIcon size={14} />
                  <span>Signed in! Loading dashboard...</span>
                </div>
              )}

              <button
                type="submit"
                className="login-submit-btn"
                disabled={submitting || success}
              >
                {submitting ? (
                  <>
                    <RefreshCwIcon size={14} className="login-spinner" />
                    Signing in...
                  </>
                ) : success ? (
                  <>
                    <CheckCircleIcon size={14} />
                    Welcome
                  </>
                ) : (
                  <>
                    <LogInIcon size={15} />
                    Sign In
                  </>
                )}
              </button>
            </form>
          )}

          {/* ── Registration form (step 1: collect details, send OTP) ── */}
          {mode === 'register' && step === 'form' && (
            <form onSubmit={handleRegister} className="login-form">
              <div className="login-input-wrapper">
                <div className="login-input-icon">
                  <UserIcon size={16} />
                </div>
                <input
                  ref={usernameRef}
                  type="text"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  placeholder="Username"
                  className="login-input"
                  disabled={submitting || success}
                  autoComplete="username"
                  spellCheck={false}
                />
              </div>

              <div className="login-input-wrapper">
                <div className="login-input-icon">
                  <MailIcon size={16} />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="Email address"
                  className="login-input"
                  disabled={submitting || success}
                  autoComplete="email"
                />
              </div>

              <div className="login-input-wrapper">
                <div className="login-input-icon">
                  <ShieldIcon size={15} />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Password (min. 6 characters)"
                  className="login-input"
                  disabled={submitting || success}
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  className="login-toggle-vis"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOffIcon size={15} /> : <EyeIcon size={15} />}
                </button>
              </div>

              <div className="login-input-wrapper">
                <div className="login-input-icon">
                  <ShieldIcon size={15} />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={e => setConfirmPassword(e.target.value)}
                  placeholder="Confirm password"
                  className="login-input"
                  disabled={submitting || success}
                  autoComplete="new-password"
                />
              </div>

              {displayError && (
                <div className="login-error">
                  <AlertTriangleIcon size={13} />
                  <span>{displayError}</span>
                </div>
              )}

              <button
                type="submit"
                className="login-submit-btn"
                disabled={submitting || success}
              >
                {submitting ? (
                  <>
                    <RefreshCwIcon size={14} className="login-spinner" />
                    Sending code...
                  </>
                ) : (
                  <>
                    <UserPlusIcon size={15} />
                    Create Account
                  </>
                )}
              </button>
            </form>
          )}

          {/* ── Registration step 2: verify the emailed OTP ── */}
          {mode === 'register' && step === 'otp' && (
            <form onSubmit={handleVerifyOtp} className="login-form">
              <div className="login-input-wrapper">
                <div className="login-input-icon">
                  <ShieldIcon size={15} />
                </div>
                <input
                  ref={otpRef}
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  autoComplete="one-time-code"
                  value={otp}
                  onChange={e => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="6-digit code"
                  className="login-input login-otp-input"
                  disabled={submitting || success}
                  maxLength={6}
                />
              </div>

              {displayError && (
                <div className="login-error">
                  <AlertTriangleIcon size={13} />
                  <span>{displayError}</span>
                </div>
              )}

              {resendMessage && !displayError && !success && (
                <div className="login-success">
                  <CheckCircleIcon size={14} />
                  <span>{resendMessage}</span>
                </div>
              )}

              {success && (
                <div className="login-success">
                  <CheckCircleIcon size={14} />
                  <span>Email verified! Loading dashboard...</span>
                </div>
              )}

              <button
                type="submit"
                className="login-submit-btn"
                disabled={submitting || success || otp.trim().length < 4}
              >
                {submitting ? (
                  <>
                    <RefreshCwIcon size={14} className="login-spinner" />
                    Verifying...
                  </>
                ) : success ? (
                  <>
                    <CheckCircleIcon size={14} />
                    Account Created
                  </>
                ) : (
                  <>
                    <CheckCircleIcon size={15} />
                    Verify & Create Account
                  </>
                )}
              </button>

              <div className="login-otp-actions">
                <button
                  type="button"
                  className="login-link-btn"
                  onClick={handleBackToForm}
                  disabled={submitting || success}
                >
                  <ArrowLeftIcon size={12} />
                  Back
                </button>
                <button
                  type="button"
                  className="login-link-btn"
                  onClick={handleResendOtp}
                  disabled={submitting || success || resendCooldown > 0}
                >
                  {resendCooldown > 0 ? `Resend code (${resendCooldown}s)` : 'Resend code'}
                </button>
              </div>
            </form>
          )}

          {/* ── Forgot password form ── */}
{mode === 'forgot' && (
  <form onSubmit={handleForgotPassword} className="login-form">
    <p className="login-subtitle" style={{ marginTop: 0 }}>
      Enter your account email and we'll send you a password reset link.
    </p>
    <div className="login-input-wrapper">
      <div className="login-input-icon">
        <MailIcon size={16} />
      </div>
      <input
        type="email"
        value={forgotEmail}
        onChange={e => setForgotEmail(e.target.value)}
        placeholder="Email address"
        className="login-input"
        disabled={submitting}
        autoComplete="email"
      />
    </div>

    {localError && (
      <div className="login-error">
        <AlertTriangleIcon size={13} />
        <span>{localError}</span>
      </div>
    )}
    {forgotMessage && (
      <div className="login-success">
        <CheckCircleIcon size={14} />
        <span>{forgotMessage}</span>
      </div>
    )}

    <button type="submit" className="login-submit-btn" disabled={submitting}>
      {submitting ? (
        <>
          <RefreshCwIcon size={14} className="login-spinner" />
          Sending...
        </>
      ) : (
        'Send Reset Link'
      )}
    </button>

    <button
  type="button"
  className="login-link-btn"
  onClick={() => { setMode('login'); setLocalError(null); setForgotMessage(null); }}
  style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', marginTop: '10px', alignSelf: 'flex-start' }}
>
  <ArrowLeftIcon size={13} /> Back to Sign In
</button>
  </form>
)}

{/* ── Reset password form (arrived via emailed link) ── */}
{mode === 'reset' && (
  <form onSubmit={handleResetPassword} className="login-form">
    <p className="login-subtitle" style={{ marginTop: 0 }}>
      Choose a new password for your account.
    </p>
    <div className="login-input-wrapper">
      <div className="login-input-icon">
        <ShieldIcon size={15} />
      </div>
      <input
        type={showPassword ? 'text' : 'password'}
        value={newPassword}
        onChange={e => setNewPassword(e.target.value)}
        placeholder="New password"
        className="login-input"
        disabled={submitting || success}
        autoComplete="new-password"
      />
      <button
        type="button"
        className="login-toggle-vis"
        onClick={() => setShowPassword(!showPassword)}
        tabIndex={-1}
      >
        {showPassword ? <EyeOffIcon size={15} /> : <EyeIcon size={15} />}
      </button>
    </div>

    <div className="login-input-wrapper">
      <div className="login-input-icon">
        <ShieldIcon size={15} />
      </div>
      <input
        type={showPassword ? 'text' : 'password'}
        value={confirmNewPassword}
        onChange={e => setConfirmNewPassword(e.target.value)}
        placeholder="Confirm new password"
        className="login-input"
        disabled={submitting || success}
        autoComplete="new-password"
      />
    </div>

    {localError && (
      <div className="login-error">
        <AlertTriangleIcon size={13} />
        <span>{localError}</span>
      </div>
    )}
    {success && (
      <div className="login-success">
        <CheckCircleIcon size={14} />
        <span>Password reset! Redirecting to sign in...</span>
      </div>
    )}

    <button type="submit" className="login-submit-btn" disabled={submitting || success}>
      {submitting ? (
        <>
          <RefreshCwIcon size={14} className="login-spinner" />
          Resetting...
        </>
      ) : (
        'Reset Password'
      )}
    </button>
  </form>
)}
          
          {/* Switch mode link — hidden during OTP verification (use Back instead) */}
          {step === 'form' && (
            <div className="login-switch-mode">
              {mode === 'login' ? (
                <span>
                  Don't have an account?{' '}
                  <button className="login-link-btn" onClick={() => setMode('register')}>
                    Register here
                  </button>
                </span>
              ) : (
                <span>
                  Already have an account?{' '}
                  <button className="login-link-btn" onClick={() => setMode('login')}>
                    Sign in
                  </button>
                </span>
              )}
            </div>
          )}

          {/* Footer */}
          <div className="login-footer">
            <span className="login-footer-dot" />
            <span>Registration open</span>
          </div>
        </div>
      </div>
    </div>
  );
}
