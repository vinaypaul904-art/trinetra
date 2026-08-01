import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../../store/AuthContext';
import { getStoredApiKey } from '../../utils/api';
import { ShieldIcon, ChevronRightIcon, CheckIcon, CreditCardIcon, LogOutIcon } from '../Icons/Icons';
import "./PaymentPage.css";

interface Plan {
  id: string;
  name: string;
  amount: number;
  credits: number;
  description: string;
}

interface PaymentPageProps {
  onPaymentComplete: () => void;
  onSkip?: () => void;
}

interface CashfreeInstance {
  checkout: (options: { paymentSessionId: string; redirectTarget: string }) => Promise<{
    error?: { message: string };
    paymentDetails?: { paymentMessage: string };
  }>;
}

type CashfreeFactory = (options: { mode: string }) => CashfreeInstance;

declare global {
  interface Window {
    Cashfree?: CashfreeFactory;
  }
}

export default function PaymentPage({ onPaymentComplete, onSkip }: PaymentPageProps) {
  const { username, credits, refreshCredits, logout } = useAuth();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const processingRef = useRef(false);

  // Handle redirect-back from Cashfree after payment
  // When checkout uses redirectTarget '_self', Cashfree redirects back with ?order_id=
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const orderId = params.get('order_id');
    if (!orderId || processingRef.current) return;

    // Clear the query param from URL
    const cleanUrl = window.location.pathname;
    window.history.replaceState({}, '', cleanUrl);    setProcessing('redirect');
    processingRef.current = true;

    const verifyAfterRedirect = async () => {
      try {
        const token = getStoredApiKey();
        if (!token) throw new Error('Session expired. Please log in again.');

        // Poll frequently so credits appear as soon as Cashfree marks the order PAID.
        // (In local dev the webhook can't reach localhost, so this poll is the
        // primary credit-adding path — keep the interval tight.)
        let verified = false;
        for (let attempt = 0; attempt < 10; attempt++) {
          const verifyRes = await fetch('/api/payment/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ order_id: orderId }),
          });
          if (verifyRes.ok) {
            const data = await verifyRes.json();
            if (data.status === 'PAID') { verified = true; break; }
          }
          if (attempt < 9) await new Promise(r => setTimeout(r, 1000));
        }

        if (verified) {
          setSuccess(true);
          await refreshCredits();
          setTimeout(() => onPaymentComplete(), 900);
        } else {
          setError('Payment is still processing. Please check your credits shortly.');
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Verification failed.';
        setError(message);
      } finally {
        setProcessing(null);
        processingRef.current = false;
      }
    };
    verifyAfterRedirect();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Load available plans
  useEffect(() => {
    const loadPlans = async () => {
      try {
        const res = await fetch('/api/payment/plans');
        if (res.ok) {
          const data = await res.json();
          setPlans(data.plans || []);
        }
      } catch {
        setError('Failed to load payment plans');
      } finally {
        setLoading(false);
      }
    };
    loadPlans();
  }, []);

  const handlePurchase = useCallback(async (planId: string) => {
    setProcessing(planId);
    setError(null);

    try {
      // Create order
      const token = getStoredApiKey();
      if (!token) {
        throw new Error('Please log in again to complete your purchase.');
      }

      const res = await fetch('/api/payment/create-order', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ plan_id: planId }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail?.error || data.error || 'Failed to create order');
      }

      const orderData = await res.json();
      const cashfreeEnv = orderData.env || 'sandbox';

      // Open Cashfree checkout
      if (!orderData.payment_session_id) {
        throw new Error('Order created but no payment session received. Please try again.');
      }

      if (typeof window.Cashfree !== 'function') {
        throw new Error('Payment SDK failed to load. Please disable ad blockers and try again.');
      }

      const cashfree = window.Cashfree({
        mode: cashfreeEnv,
      });

      // Redirect to Cashfree checkout in the same window
      // After payment, Cashfree redirects back to return_url with ?order_id=
      // The redirect-back useEffect above will handle verification
      const checkoutResult = await cashfree.checkout({
        paymentSessionId: orderData.payment_session_id,
        redirectTarget: '_self',
      });

      // Check if the payment was completed inside the modal
      if (checkoutResult && checkoutResult.error) {
        throw new Error(checkoutResult.error.message || 'Payment was cancelled or failed inside the checkout. Please try again.');
      }

      // If checkout returned payment details, check the message
      if (checkoutResult && checkoutResult.paymentDetails && checkoutResult.paymentDetails.paymentMessage !== 'Success') {
        throw new Error(checkoutResult.paymentDetails.paymentMessage || 'Payment was not successful. Please try again.');
      }

      // Verify payment status with our backend — retry quickly until PAID
      // because Cashfree sandbox may take a moment to update order status
      let verifyData = null;
      for (let attempt = 0; attempt < 6; attempt++) {
        const verifyRes = await fetch('/api/payment/verify', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({ order_id: orderData.order_id }),
        });

        if (!verifyRes.ok) {
          const errData = await verifyRes.json().catch(() => ({}));
          throw new Error(errData.detail?.error || errData.error || 'Payment verification failed');
        }

        verifyData = await verifyRes.json();
        if (verifyData.status === 'PAID') {
          break; // Payment confirmed!
        }

        // Not PAID yet — wait briefly and retry
        if (attempt < 5) {
          await new Promise(r => setTimeout(r, 1000));
        }
      }

      if (verifyData && verifyData.status === 'PAID') {
        setSuccess(true);
        await refreshCredits();
        setTimeout(() => onPaymentComplete(), 900);
      } else {
        // Payment was completed in the modal but verify still didn't pick it up
        throw new Error('Payment confirmed but still processing. Please click "Continue to Dashboard" to check your credits.');
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Payment failed. Please try again.';
      setError(message);
    } finally {
      setProcessing(null);
    }
  }, [refreshCredits, onPaymentComplete]);

  if (success) {
    return (
      <div className="payment-page">
        <div className="payment-success-card">
          <div className="payment-success-icon">
            <CheckIcon size={40} color="var(--accent-green)" />
          </div>
          <h2>Payment Successful!</h2>
          <p>Your credits have been added to your account.</p>
          <p className="payment-success-credits">Current balance: <strong>{credits}</strong> credits</p>
          <button className="payment-btn-primary" onClick={onPaymentComplete}>
            Continue to Dashboard <ChevronRightIcon size={14} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="payment-page">
      <div className="payment-bg-gradient" />
      
      <div className="payment-container">
        <div className="payment-header">
          <div className="payment-logo">
            <ShieldIcon size={24} color="white" />
          </div>
          <h1>Choose Your Plan</h1>
          <p>Select a credit package to start using TRINETRA OSINT tools</p>
          {credits !== null && credits > 0 && (
            <div className="payment-current-credits">
              Current balance: <strong>{credits}</strong> credits
            </div>
          )}

          {username && (
            <div className="payment-user-info">
              <span>Logged in as <strong>{username}</strong></span>
            </div>
          )}
        </div>

        {loading ? (
          <div className="payment-loading">
            <div className="payment-loading-spinner" />
            <span>Loading plans...</span>
          </div>
        ) : (
          <div className="payment-plans-grid">
            {plans.map((plan) => (
              <div 
                key={plan.id}
                className={`payment-plan-card ${plan.id === 'pro' ? 'payment-plan-featured' : ''}`}
              >
                {plan.id === 'pro' && (
                  <div className="payment-plan-badge">Most Popular</div>
                )}
                <h3 className="payment-plan-name">{plan.name}</h3>
                <div className="payment-plan-price">
                  <span className="payment-plan-currency">₹</span>
                  <span className="payment-plan-amount">{plan.amount}</span>
                </div>
                <div className="payment-plan-credits">
                  <CreditCardIcon size={14} />
                  <span>{plan.credits} credits</span>
                </div>
                <p className="payment-plan-desc">{plan.description}</p>
                <ul className="payment-plan-features">
                  <li><CheckIcon size={12} /> {Math.floor(plan.credits / 10)} OSINT scan{Math.floor(plan.credits / 10) === 1 ? '' : 's'}</li>
                  <li><CheckIcon size={12} /> 10 credits per search</li>
                  <li><CheckIcon size={12} /> All 15 plugins included</li>
                  <li><CheckIcon size={12} /> Live threat feed</li>
                  <li><CheckIcon size={12} /> AI chatbot access</li>
                </ul>
                <button
                  className={`payment-plan-btn ${plan.id === 'pro' ? 'payment-plan-btn-featured' : ''}`}
                  onClick={() => handlePurchase(plan.id)}
                  disabled={processing !== null}
                >
                  {processing === plan.id ? (
                    <>
                      <div className="payment-btn-spinner" />
                      Processing...
                    </>
                  ) : (
                    <>
                      Get {plan.name} <ChevronRightIcon size={14} />
                    </>
                  )}
                </button>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="payment-error">
            {error}
          </div>
        )}

        {onSkip && credits !== null && credits > 0 && (
          <div className="payment-skip">
            <button className="payment-skip-btn" onClick={onSkip}>
              Continue with existing credits ({credits} remaining)
            </button>
          </div>
        )}

        <div className="payment-test-info">
          <p><strong>🧪 Sandbox Testing</strong></p>
          <p>When the Cashfree checkout opens, use these test details:</p>
          <ul>
            <li><strong>Card:</strong> 4111 1111 1111 1111</li>
            <li><strong>Expiry:</strong> Any future date (e.g. 12/25)</li>
            <li><strong>CVV:</strong> 123</li>
            <li><strong>Name:</strong> Any name</li>
          </ul>
          <p className="payment-test-info-note">Complete the payment inside the modal — do not close it until done!</p>
        </div>

        <div className="payment-footer-actions">
          <button className="payment-logout-btn" onClick={logout}>
            <LogOutIcon size={12} />
            <span>Switch Account</span>
          </button>
        </div>
      </div>
    </div>
  );
}
