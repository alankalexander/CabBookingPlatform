
"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { toast } from "../lib/toast";

const Map = dynamic(() => import("./Map"), { ssr: false });

const btn =
  "bg-black text-white px-4 py-2 rounded mr-2 mb-2 disabled:opacity-50";

const btn2 =
  "border px-4 py-2 rounded mb-2 disabled:opacity-50";

export default function RideView({
  ride,
  driverPos,
  onPaid,
  onCancelled
}) {
  const [route, setRoute] = useState(null);
  const [routeInfo, setRouteInfo] = useState(null);
  const [busy, setBusy] = useState(false);

  const [showCheckout, setShowCheckout] = useState(false);
  const [method, setMethod] = useState("upi");

  const from = [ride.pickup_lat, ride.pickup_lng];
  const to = [ride.drop_lat, ride.drop_lng];

  const key = from.join(",") + "|" + to.join(",");
  const st = ride.status;

  const amount = Number(
    ride.fare_actual ?? ride.fare_estimate ?? 0
  );

  useEffect(() => {
    setRoute(null);
    setRouteInfo(null);

    let cancelled = false;

    fetch(
      `https://router.project-osrm.org/route/v1/driving/${from[1]},${from[0]};${to[1]},${to[0]}?overview=full&geometries=geojson`
    )
      .then(r => r.json())
      .then(d => {
        if (cancelled) return;

        const rt = d.routes && d.routes[0];

        if (!rt) throw new Error("No route");

        setRoute(
          rt.geometry.coordinates.map(([lng, lat]) => [lat, lng])
        );

        setRouteInfo({
          km: rt.distance / 1000,
          min: Math.max(1, Math.round(rt.duration / 60))
        });
      })
      .catch(() => {
        if (!cancelled) {
          setRoute([from, to]);
          setRouteInfo(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [key]);

  async function run(fn) {
    setBusy(true);

    try {
      await fn();
    } catch {
      // API helper already displays errors.
    } finally {
      setBusy(false);
    }
  }

  const cancel = () => run(async () => {
    if (!window.confirm("Cancel this ride?")) return;

    await api(`/api/rides/${ride.id}/cancel`, {
      method: "POST",
      body: { reason: "Cancelled by rider" }
    });

    toast("Ride cancelled", "success");
    onCancelled();
  });

  // Open demo checkout
  function payOnline() {
    setShowCheckout(true);
  }

  // Send payment result to FastAPI
  async function processDemoPayment(outcome) {
    if (busy) return;

    setBusy(true);

    try {
      const result = await api(
        `/api/payments/demo/${ride.id}`,
        {
          method: "POST",
          body: {
            method,
            outcome
          }
        }
      );

      if (outcome === "failure") {
        toast("Demo payment failed. Please try again.", "error");
        return;
      }

      setShowCheckout(false);

      toast("Demo payment successful!", "success");

      onPaid(result);

    } catch (error) {
      console.error("Demo payment error:", error);
    } finally {
      setBusy(false);
    }
  }

  const payCash = () => run(async () => {
    const result = await api(
      `/api/payments/cash/${ride.id}`,
      { method: "POST" }
    );

    onPaid(result);
  });

  const markers = [
    { pos: from, color: "green", label: "From" },
    { pos: to, color: "red", label: "To" },
    {
      pos: driverPos && [driverPos.lat, driverPos.lng],
      color: "blue",
      label: "Driver"
    }
  ];

  return (
    <>
      <div>
        <Map markers={markers} route={route} />

        <div
          className="bg-white p-4 rounded shadow mt-3"
          aria-live="polite"
        >
          <p className="text-xs text-gray-500 mb-1">
            Ride #{ride.id}
          </p>

          {routeInfo && (
            <p className="text-sm text-blue-700 mb-2">
              Trip route: {routeInfo.km.toFixed(1)} km
              {" · "}
              about {routeInfo.min} min
            </p>
          )}

          {st === "requested" && (
            <>
              <p>
                Finding a driver... nearby drivers are being asked.
              </p>

              <button
                className={btn2 + " mt-2"}
                disabled={busy}
                onClick={cancel}
              >
                Cancel request
              </button>
            </>
          )}

          {st === "accepted" && (
            <>
              <p>
                <b>{ride.driver_name}</b>
                {" "}({ride.driver_vehicle || "vehicle"})
                {" "}is on the way
                {ride.driver_rating
                  ? ` - rating ${ride.driver_rating}`
                  : ""}.

                <a
                  className="underline text-sm ml-2"
                  href={`/reviews?user=${ride.driver_id}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  See reviews
                </a>
              </p>

              {ride.driver_phone && (
                <p className="text-sm">
                  Phone: {ride.driver_phone}
                </p>
              )}

              <button
                className={btn2 + " mt-2"}
                disabled={busy}
                onClick={cancel}
              >
                Cancel ride
              </button>
            </>
          )}

          {st === "arrived" && (
            <>
              <p>
                Your driver has <b>arrived</b>.
                Please head to the pickup point.
              </p>

              <button
                className={btn2 + " mt-2"}
                disabled={busy}
                onClick={cancel}
              >
                Cancel ride
              </button>
            </>
          )}

          {st === "started" && (
            <p>Trip in progress to your destination...</p>
          )}

          {st === "completed" && (
            <>
              <p className="text-gray-500 text-sm">
                Ride complete
              </p>

              <p className="text-3xl font-bold mb-3">
                ₹{amount.toFixed(2)}
              </p>

              <button
                className={btn}
                disabled={busy}
                onClick={payOnline}
              >
                Pay online
              </button>

              <button
                className={btn2}
                disabled={busy}
                onClick={payCash}
              >
                Pay cash
              </button>

              <p className="text-xs text-gray-500 mt-2">
                Online payment is currently in demo mode.
              </p>
            </>
          )}
        </div>
      </div>

      {/* DEMO PAYMENT CHECKOUT */}
      {showCheckout && (
        <div className="fixed inset-0 z-[9999] bg-black/60 flex items-center justify-center p-3">

          <div className="bg-white w-full max-w-md rounded-xl shadow-2xl overflow-hidden text-gray-900">

            {/* Checkout header */}
            <div className="bg-[#172554] text-white p-5">

              <p className="text-xs tracking-widest text-blue-200">
                CABGO SECURE CHECKOUT
              </p>

              <div className="flex justify-between items-center mt-3">
                <h2 className="text-xl font-bold">
                  Complete payment
                </h2>

                <span className="text-xl font-bold">
                  ₹{amount.toFixed(2)}
                </span>
              </div>

            </div>

            <div className="p-5">

              <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 mb-5 text-xs text-orange-800">
                Demo payment mode. No real money will be charged.
                This is not the official Razorpay checkout.
              </div>

              <p className="font-semibold text-sm mb-3">
                Select payment method
              </p>

              {/* Payment methods */}
              <div className="grid grid-cols-3 gap-2 mb-5">

                {[
                  { id: "upi", name: "UPI", icon: "📱" },
                  { id: "card", name: "Cards", icon: "💳" },
                  { id: "netbanking", name: "Net Banking", icon: "🏦" }
                ].map(item => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setMethod(item.id)}
                    className={`border rounded-lg p-3 text-sm ${
                      method === item.id
                        ? "border-blue-600 bg-blue-50 text-blue-700"
                        : "border-gray-200"
                    }`}
                  >
                    <div className="text-xl mb-1">
                      {item.icon}
                    </div>

                    {item.name}
                  </button>
                ))}

              </div>

              {/* Selected method details */}
              {method === "upi" && (
                <div className="border rounded-lg p-4 mb-5">
                  <p className="font-semibold text-sm">
                    UPI payment
                  </p>

                  <p className="text-sm text-gray-500 mt-2">
                    Demo UPI ID: demo@upi
                  </p>

                  <p className="text-xs text-gray-400 mt-2">
                    No real UPI transaction will occur.
                  </p>
                </div>
              )}

              {method === "card" && (
                <div className="border rounded-lg p-4 mb-5">
                  <p className="font-semibold text-sm">
                    Card payment
                  </p>

                  <p className="text-sm text-gray-500 mt-2">
                    Demo card: **** **** **** 4242
                  </p>

                  <p className="text-xs text-gray-400 mt-2">
                    No actual card information is collected.
                  </p>
                </div>
              )}

              {method === "netbanking" && (
                <div className="border rounded-lg p-4 mb-5">
                  <p className="font-semibold text-sm">
                    Net Banking
                  </p>

                  <p className="text-sm text-gray-500 mt-2">
                    Selected bank: Demo Bank
                  </p>

                  <p className="text-xs text-gray-400 mt-2">
                    Bank authentication is simulated.
                  </p>
                </div>
              )}

              {/* Successful demo payment */}
              <button
                type="button"
                disabled={busy}
                onClick={() => processDemoPayment("success")}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg disabled:opacity-50"
              >
                {busy
                  ? "Processing..."
                  : `Pay ₹${amount.toFixed(2)}`}
              </button>

              {/* Failed demo payment */}
              <button
                type="button"
                disabled={busy}
                onClick={() => processDemoPayment("failure")}
                className="w-full border border-red-300 text-red-600 py-3 rounded-lg mt-2 disabled:opacity-50"
              >
                Simulate payment failure
              </button>

              {/* Cancel checkout */}
              <button
                type="button"
                disabled={busy}
                onClick={() => setShowCheckout(false)}
                className="w-full text-gray-500 text-sm py-3 mt-1"
              >
                Cancel
              </button>

              <p className="text-center text-xs text-gray-400 mt-2">
                CabGo Demo Payment Gateway
              </p>

            </div>
          </div>
        </div>
      )}
    </>
  );
}
