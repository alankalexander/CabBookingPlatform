
"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { api } from "../lib/api";
import { toast } from "../lib/toast";

const Map = dynamic(() => import("./Map"), { ssr: false });

const vehicles = [
  { name: "Mini", price: 12 },
  { name: "Sedan", price: 15 },
  { name: "SUV", price: 20 },
];

export default function Chooser({ onBooked }) {
  const [pickupText, setPickupText] = useState("");
  const [destinationText, setDestinationText] = useState("");

  const [pickup, setPickup] = useState(null);
  const [destination, setDestination] = useState(null);

  const [pickupResults, setPickupResults] = useState([]);
  const [destinationResults, setDestinationResults] = useState([]);

  const [activeSearch, setActiveSearch] = useState("");
  const [vehicle, setVehicle] = useState("Mini");

  const [route, setRoute] = useState(null);
  const [distance, setDistance] = useState(null);
  const [loadingRoute, setLoadingRoute] = useState(false);
  const [booking, setBooking] = useState(false);

  const [focus, setFocus] = useState([9.9312, 76.2673]);

  // Search place names
  async function searchPlaces(value, type) {
    if (value.trim().length < 3) {
      if (type === "pickup") setPickupResults([]);
      else setDestinationResults([]);
      return;
    }

    try {
      const url =
        "https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5&countrycodes=in&q=" +
        encodeURIComponent(value);

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error("Place search failed");
      }

      const data = await response.json();

      if (type === "pickup") {
        setPickupResults(data);
      } else {
        setDestinationResults(data);
      }
    } catch (error) {
      console.error("Place search:", error);
      toast("Unable to search places. Please try again.", "error");
    }
  }

  // Pickup search delay
  useEffect(() => {
    if (activeSearch !== "pickup") return;

    const timer = setTimeout(() => {
      searchPlaces(pickupText, "pickup");
    }, 700);

    return () => clearTimeout(timer);
  }, [pickupText, activeSearch]);

  // Destination search delay
  useEffect(() => {
    if (activeSearch !== "destination") return;

    const timer = setTimeout(() => {
      searchPlaces(destinationText, "destination");
    }, 700);

    return () => clearTimeout(timer);
  }, [destinationText, activeSearch]);

  // Select a place
  function selectPlace(place, type) {
    const selected = {
      name: place.display_name,
      lat: Number(place.lat),
      lng: Number(place.lon),
    };

    if (type === "pickup") {
      setPickup(selected);
      setPickupText(place.display_name);
      setPickupResults([]);
    } else {
      setDestination(selected);
      setDestinationText(place.display_name);
      setDestinationResults([]);
    }

    setActiveSearch("");
    setFocus([selected.lat, selected.lng]);
  }

  // Calculate route
  useEffect(() => {
    if (!pickup || !destination) {
      setRoute(null);
      setDistance(null);
      return;
    }

    let cancelled = false;

    async function getRoute() {
      setLoadingRoute(true);

      try {
        const url =
          `https://router.project-osrm.org/route/v1/driving/` +
          `${pickup.lng},${pickup.lat};${destination.lng},${destination.lat}` +
          `?overview=full&geometries=geojson`;

        const response = await fetch(url);

        if (!response.ok) {
          throw new Error("Route request failed");
        }

        const data = await response.json();
        const result = data.routes?.[0];

        if (!result) {
          throw new Error("No route found");
        }

        if (cancelled) return;

        setRoute(
          result.geometry.coordinates.map(([lng, lat]) => [lat, lng])
        );

        setDistance(result.distance / 1000);
      } catch (error) {
        if (!cancelled) {
          console.error("Route error:", error);
          setRoute(null);
          setDistance(null);
          toast("Could not calculate route. Try other locations.", "error");
        }
      } finally {
        if (!cancelled) setLoadingRoute(false);
      }
    }

    getRoute();

    return () => {
      cancelled = true;
    };
  }, [pickup, destination]);

  const selectedVehicle = vehicles.find(
    item => item.name === vehicle
  );

  const fare =
    distance !== null && selectedVehicle
      ? Math.ceil(distance * selectedVehicle.price)
      : null;

  // Map markers
  const markers = [
    ...(pickup
      ? [
          {
            pos: [pickup.lat, pickup.lng],
            color: "green",
            label: "Pickup",
          },
        ]
      : []),

    ...(destination
      ? [
          {
            pos: [destination.lat, destination.lng],
            color: "red",
            label: "Destination",
          },
        ]
      : []),
  ];

  // Book ride
  async function bookRide() {
    if (!pickup || !destination) {
      toast("Select pickup and destination first.", "error");
      return;
    }

    if (loadingRoute || distance === null || fare === null) {
      toast("Please wait for route calculation.", "info");
      return;
    }

    setBooking(true);

    try {
      const result = await api("/api/rides/request", {
        method: "POST",
        body: {
          pickup_lat: pickup.lat,
          pickup_lng: pickup.lng,
          drop_lat: destination.lat,
          drop_lng: destination.lng,
          vehicle_type: vehicle,
        },
      });

      toast("Ride request submitted successfully!", "success");

      if (onBooked) {
        onBooked(result);
      }
    } catch (error) {
      console.error("Ride booking failed:", error);

      toast(
        error.message || "Unable to book ride.",
        "error"
      );
    } finally {
      setBooking(false);
    }
  }

  // Complete UI
  return (
    <div className="space-y-4">

      <div className="bg-white p-4 rounded shadow">
        <h1 className="text-xl font-bold mb-4">
          Book Your Ride
        </h1>

        {/* Pickup */}
        <div className="relative mb-4">
          <label className="block text-sm font-medium mb-1">
            Pickup Location
          </label>

          <input
            type="text"
            value={pickupText}
            placeholder="Enter pickup place name"
            className="border rounded p-3 w-full"
            onFocus={() => setActiveSearch("pickup")}
            onChange={e => {
              setPickupText(e.target.value);
              setPickup(null);
              setPickupResults([]);
            }}
          />

          {activeSearch === "pickup" &&
            pickupResults.length > 0 && (
              <div className="absolute z-[1000] bg-white border rounded shadow w-full max-h-60 overflow-y-auto">
                {pickupResults.map(place => (
                  <button
                    type="button"
                    key={place.place_id}
                    className="block w-full text-left p-3 text-sm hover:bg-gray-100 border-b"
                    onClick={() =>
                      selectPlace(place, "pickup")
                    }
                  >
                    📍 {place.display_name}
                  </button>
                ))}
              </div>
            )}
        </div>

        {/* Destination */}
        <div className="relative mb-4">
          <label className="block text-sm font-medium mb-1">
            Destination
          </label>

          <input
            type="text"
            value={destinationText}
            placeholder="Enter destination place name"
            className="border rounded p-3 w-full"
            onFocus={() => setActiveSearch("destination")}
            onChange={e => {
              setDestinationText(e.target.value);
              setDestination(null);
              setDestinationResults([]);
            }}
          />

          {activeSearch === "destination" &&
            destinationResults.length > 0 && (
              <div className="absolute z-[1000] bg-white border rounded shadow w-full max-h-60 overflow-y-auto">
                {destinationResults.map(place => (
                  <button
                    type="button"
                    key={place.place_id}
                    className="block w-full text-left p-3 text-sm hover:bg-gray-100 border-b"
                    onClick={() =>
                      selectPlace(place, "destination")
                    }
                  >
                    📍 {place.display_name}
                  </button>
                ))}
              </div>
            )}
        </div>

        {/* Vehicle */}
        <label className="block text-sm font-medium mb-1">
          Select Vehicle
        </label>

        <select
          value={vehicle}
          onChange={e => setVehicle(e.target.value)}
          className="border rounded p-3 w-full mb-4"
        >
          {vehicles.map(item => (
            <option key={item.name} value={item.name}>
              {item.name} - ₹{item.price}/km
            </option>
          ))}
        </select>

        {/* Location status */}
        {pickup && (
          <p className="text-sm text-green-700 mb-2">
            ✓ Pickup selected
          </p>
        )}

        {destination && (
          <p className="text-sm text-red-700 mb-2">
            ✓ Destination selected
          </p>
        )}

        {/* Route */}
        {loadingRoute && (
          <p className="text-sm text-blue-600 mb-2">
            Calculating route...
          </p>
        )}

        {/* Fare */}
        {distance !== null && (
          <div className="bg-gray-50 p-3 rounded mb-4">
            <p className="text-sm">
              Distance: <b>{distance.toFixed(2)} km</b>
            </p>

            <p className="text-xl font-bold mt-1">
              Estimated fare: ₹{fare}
            </p>

            <p className="text-xs text-gray-500">
              Final fare is determined by the backend.
            </p>
          </div>
        )}

        {/* Book button */}
        <button
          type="button"
          onClick={bookRide}
          disabled={
            booking ||
            loadingRoute ||
            !pickup ||
            !destination ||
            distance === null
          }
          className="bg-black text-white w-full p-3 rounded font-semibold disabled:opacity-50"
        >
          {booking ? "Booking..." : "Book Ride"}
        </button>
      </div>

      {/* Map */}
      <div className="bg-white p-2 rounded shadow">
        <h2 className="font-semibold p-2">
          Your Route on Map
        </h2>

        <Map
          markers={markers}
          route={route}
          focus={focus}
          center={focus}
        />
      </div>

    </div>
  );
}
