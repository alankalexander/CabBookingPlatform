
"use client";

import { useState } from "react";

export default function DemoPayment({ amount = 0, onSuccess, onCancel, onFailure }) {
  const [method, setMethod] = useState("upi");
  const [upiId, setUpiId] = useState("demo@upi");
  const [cardNumber, setCardNumber] = useState("4111 1111 1111 1111");
  const [cardName, setCardName] = useState("Demo User");
  const [expiry, setExpiry] = useState("12/29");
  const [cvv, setCvv] = useState("123");
  const [bank, setBank] = useState("Demo Bank");
  const [processing, setProcessing] = useState(false);

  const paymentAmount = Number(amount || 0);

  function simulateSuccess() {
    if (processing) return;

    setProcessing(true);

    const payment = {
      status: "paid",
      method,
      reference: `DEMO_${Date.now()}`,
      amount: paymentAmount,
      simulated: true
    };

    setTimeout(() => {
      setProcessing(false);
      onSuccess?.(payment);
    }, 1000);
  }

  function simulateFailure() {
    if (processing) return;

    const payment = {
      status: "failed",
      method,
      reference: `DEMO_${Date.now()}`,
      amount: paymentAmount,
      reason: "Demo payment was declined",
      simulated: true
    };

    onFailure?.(payment);
  }

  const tabStyle = (selected) => ({
    flex: 1,
    padding: "11px 5px",
    border: selected ? "1px solid #2563eb" : "1px solid #e5e7eb",
    background: selected ? "#eff6ff" : "#fff",
    color: selected ? "#1d4ed8" : "#374151",
    borderRadius: 9,
    cursor: "pointer",
    fontWeight: 600,
    fontSize: 13
  });

  const fieldStyle = {
    width: "100%",
    padding: "12px",
    border: "1px solid #d1d5db",
    borderRadius: 8,
    marginTop: 6,
    marginBottom: 14,
    boxSizing: "border-box",
    fontSize: 14,
    color: "#111827",
    background: "#fff"
  };

  return (
    <div style={{
      position: "fixed",
      inset: 0,
      zIndex: 9999,
      background: "rgba(15, 23, 42, 0.65)",
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      padding: 16
    }}>
      <div style={{
        width: "100%",
        maxWidth: 440,
        background: "#fff",
        borderRadius: 16,
        overflow: "hidden",
        boxShadow: "0 20px 60px rgba(0,0,0,.25)",
        color: "#111827",
        fontFamily: "Arial, sans-serif"
      }}>
        <div style={{
          background: "#172554",
          color: "#fff",
          padding: "20px 22px"
        }}>
          <div style={{ fontSize: 12, opacity: 0.8 }}>
            CAB BOOKING · DEMO CHECKOUT
          </div>
          <div style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: 9
          }}>
            <strong style={{ fontSize: 20 }}>Complete payment</strong>
            <strong style={{ fontSize: 21 }}>
              ₹{paymentAmount.toFixed(2)}
            </strong>
          </div>
        </div>

        <div style={{ padding: 22 }}>
          <div style={{
            background: "#fff7ed",
            border: "1px solid #fed7aa",
            color: "#9a3412",
            padding: 10,
            borderRadius: 8,
            fontSize: 12,
            marginBottom: 18
          }}>
            Demo mode — no real money will be charged.
          </div>

          <div style={{
            display: "flex",
            gap: 7,
            marginBottom: 20
          }}>
            <button type="button" style={tabStyle(method === "upi")}
              onClick={() => setMethod("upi")}>UPI</button>
            <button type="button" style={tabStyle(method === "card")}
              onClick={() => setMethod("card")}>Card</button>
            <button type="button" style={tabStyle(method === "netbanking")}
              onClick={() => setMethod("netbanking")}>Net Banking</button>
          </div>

          {method === "upi" && (
            <div>
              <label style={{ fontSize: 13, fontWeight: 600 }}>UPI ID</label>
              <input
                style={fieldStyle}
                value={upiId}
                onChange={(e) => setUpiId(e.target.value)}
                placeholder="example@upi"
              />
              <div style={{ fontSize: 12, color: "#6b7280" }}>
                Enter any demo UPI ID to continue.
              </div>
            </div>
          )}

          {method === "card" && (
            <div>
              <label style={{ fontSize: 13, fontWeight: 600 }}>Card number</label>
              <input style={fieldStyle} value={cardNumber}
                onChange={(e) => setCardNumber(e.target.value)}
                placeholder="Card number" />

              <label style={{ fontSize: 13, fontWeight: 600 }}>Cardholder name</label>
              <input style={fieldStyle} value={cardName}
                onChange={(e) => setCardName(e.target.value)}
                placeholder="Name on card" />

              <div style={{ display: "flex", gap: 10 }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: 13, fontWeight: 600 }}>Expiry</label>
                  <input style={fieldStyle} value={expiry}
                    onChange={(e) => setExpiry(e.target.value)}
                    placeholder="MM/YY" />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: 13, fontWeight: 600 }}>CVV</label>
                  <input style={fieldStyle} value={cvv}
                    onChange={(e) => setCvv(e.target.value)}
                    placeholder="CVV" />
                </div>
              </div>
            </div>
          )}

          {method === "netbanking" && (
            <div>
              <label style={{ fontSize: 13, fontWeight: 600 }}>Select bank</label>
              <select style={fieldStyle} value={bank}
                onChange={(e) => setBank(e.target.value)}>
                <option>Demo Bank</option>
                <option>State Bank of India</option>
                <option>HDFC Bank</option>
                <option>ICICI Bank</option>
                <option>Axis Bank</option>
              </select>
            </div>
          )}

          <button
            type="button"
            disabled={processing}
            onClick={simulateSuccess}
            style={{
              width: "100%",
              padding: 14,
              border: 0,
              borderRadius: 9,
              background: processing ? "#93c5fd" : "#2563eb",
              color: "#fff",
              fontWeight: 700,
              fontSize: 15,
              cursor: processing ? "wait" : "pointer"
            }}
          >
            {processing ? "Processing demo payment..." : `Pay ₹${paymentAmount.toFixed(2)}`}
          </button>

          <button
            type="button"
            disabled={processing}
            onClick={simulateFailure}
            style={{
              width: "100%",
              marginTop: 9,
              padding: 11,
              border: "1px solid #fecaca",
              borderRadius: 9,
              background: "#fff",
              color: "#b91c1c",
              fontWeight: 600,
              cursor: "pointer"
            }}
          >
            Simulate payment failure
          </button>

          <button
            type="button"
            disabled={processing}
            onClick={onCancel}
            style={{
              width: "100%",
              marginTop: 8,
              padding: 10,
              border: 0,
              background: "transparent",
              color: "#6b7280",
              cursor: "pointer"
            }}
          >
            Cancel
          </button>

          <div style={{
            textAlign: "center",
            color: "#9ca3af",
            fontSize: 11,
            marginTop: 8
          }}>
            This is a locally simulated payment, not an official Razorpay checkout.
          </div>
        </div>
      </div>
    </div>
  );
}
