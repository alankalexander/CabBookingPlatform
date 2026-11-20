
"use client";

import { useEffect, useRef, useState } from "react";

import Login from "../components/Login";
import TopBar from "../components/TopBar";
import Chooser from "../components/Chooser";
import RideView from "../components/RideView";
import RatingForm from "../components/RatingForm";

import { api, connectSocket, downloadReceipt } from "../lib/api";
import { toast } from "../lib/toast";

const btn2 =
  "border px-4 py-2 rounded mb-2 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-black";

function Tick() {
  return (
    <svg
      className="tick-circle mx-auto"
      width="72"
      height="72"
      viewBox="0 0 72 72"
      aria-hidden="true"
    >
      <circle cx="36" cy="36" r="34" fill="#16a34a" />

      <path
        className="tick-path"
        d="M20 37 L31 48 L53 25"
        fill="none"
        stroke="white"
        strokeWidth="6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between py-1 border-b last:border-0 text-sm">
      <span className="text-gray-500">{label}</span>

      <span className="font-medium text-right break-all ml-4">
        {value ?? "-"}
      </span>
    </div>
  );
}

export default function Rider() {
  const [user, setUser] = useState(null);
  const [ride, setRide] = useState(null);
  const [receipt, setReceipt] = useState(null);
  const [driverPos, setDriverPos] = useState(null);
  const [tripKey, setTripKey] = useState(0);

  const socket = useRef(null);
  const rideRef = useRef(null);
  const paidIdRef = useRef(null);
  const firstLoad = useRef(true);
  const loadSeq = useRef(0);

  // Load the currently active ride
  async function loadActive() {
    const requestNumber = ++loadSeq.current;

    try {
      const response = await api("/api/rides/active", {
        silent: true,
      });

      if (requestNumber !== loadSeq.current) return;

      const found = response?.ride ?? null;

      const activeRide =
        found && found.id !== paidIdRef.current
          ? found
          : null;

      const previousRide = rideRef.current;

      if (
        activeRide &&
        !previousRide &&
        firstLoad.current
      ) {
        toast(
          `Resumed your ongoing ride #${activeRide.id}`,
          "info"
        );
      }

      if (!activeRide && previousRide) {
        toast(
          "Your ride ended or was cancelled.",
          "info"
        );

        setDriverPos(null);
        setTripKey(key => key + 1);
      }

      firstLoad.current = false;

      rideRef.current = activeRide;
      setRide(activeRide);

      if (
        activeRide &&
        activeRide.status !== "requested"
      ) {
        socket.current?.emit("join_ride", {
          ride_id: activeRide.id,
        });
      }
    } catch (error) {
      console.error("Loading active ride:", error);
    }
  }

  // Connect socket and restore active ride
  useEffect(() => {
    if (!user) return;

    let mounted = true;

    loadActive();

    connectSocket()
      .then(s => {
        if (!mounted) {
          s.disconnect();
          return;
        }

        socket.current = s;

        s.on("connect_error", error => {
          console.error("Socket connection error:", error);
        });

        s.on("ride_update", () => {
          loadActive();
        });

        s.on("driver_location", position => {
          setDriverPos(position);
        });
      })
      .catch(error => {
        console.error("Socket setup error:", error);
      });

    const interval = setInterval(() => {
      loadActive();
    }, 4000);

    return () => {
      mounted = false;

      clearInterval(interval);

      if (socket.current) {
        socket.current.disconnect();
        socket.current = null;
      }
    };
  }, [user]);

  // Handle successful payment
  function paymentDone(data) {
    paidIdRef.current = data.ride_id;

    rideRef.current = null;

    setRide(null);
    setDriverPos(null);

    setReceipt({
      ...data,
      time: new Date().toLocaleString(),
    });
  }

  // Handle cancellation
  function cancelled() {
    rideRef.current = null;

    setRide(null);
    setDriverPos(null);

    setTripKey(key => key + 1);
  }

  // Start another trip
  function newTrip() {
    setReceipt(null);
    setTripKey(key => key + 1);
  }

  // Handle newly booked ride
  async function handleBooked() {
    await loadActive();
  }

  if (!user) {
    return (
      <Login
        role="rider"
        onDone={setUser}
      />
    );
  }

  return (
    <div>
      <TopBar user={user} />

      {receipt ? (
        <div className="bg-white p-4 rounded shadow max-w-sm mx-auto text-center">

          <Tick />

          <h1 className="text-xl font-bold mt-3">
            Payment successful
          </h1>

          <p className="text-3xl font-bold text-green-600 mb-3">
            &#8377;{receipt.amount}
          </p>

          <div className="text-left bg-gray-50 rounded p-3 mb-3">
            <Row
              label="Ride"
              value={`#${receipt.ride_id}`}
            />

            <Row
              label="Distance"
              value={`${receipt.distance_km} km`}
            />

            <Row
              label="Paid by"
              value={
                receipt.method === "cash"
                  ? "Cash"
                  : "Online (Razorpay)"
              }
            />

            <Row
              label="Transaction ID"
              value={receipt.reference}
            />

            <Row
              label="Date"
              value={receipt.time}
            />

            <Row
              label="Status"
              value="Paid"
            />
          </div>

          <button
            className={btn2}
            onClick={() =>
              downloadReceipt(receipt.ride_id)
            }
          >
            Download receipt
          </button>

          <div className="text-left mt-4 border-t pt-4">
            <RatingForm
              rideId={receipt.ride_id}
              target="driver"
              onDone={newTrip}
            />
          </div>

          <div>
            <button
              className="underline text-sm mt-3"
              onClick={newTrip}
            >
              Skip and book another ride
            </button>
          </div>
        </div>
      ) : ride ? (
        <RideView
          ride={ride}
          driverPos={driverPos}
          onPaid={paymentDone}
          onCancelled={cancelled}
        />
      ) : (
        <Chooser
          key={tripKey}
          onBooked={handleBooked}
        />
      )}

      <p className="mt-6 text-sm">
        <a className="underline" href="/history">
          View all rides &rarr;
        </a>
      </p>

      <p className="mt-2 text-xs text-gray-400">
        UI build: fresh-state v5
      </p>
    </div>
  );
}
