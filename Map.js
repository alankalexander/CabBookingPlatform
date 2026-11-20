"use client";
import { useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Polyline, Tooltip, useMap, useMapEvents } from "react-leaflet";

function Clicker({ onClick }) {
  useMapEvents({ click: e => onClick && onClick([e.latlng.lat, e.latlng.lng]) });
  return null;
}
function FlyTo({ focus }) {
  const map = useMap();
  useEffect(() => { if (focus) map.flyTo(focus, 15); }, [focus]);
  return null;
}
function Fit({ route }) {
  const map = useMap();
  useEffect(() => {
    if (route && route.length > 1) map.fitBounds(route, { padding: [60, 60] });
  }, [route]);
  return null;
}

// markers: [{ pos: [lat, lng], color, label }]   route: [[lat, lng], ...]
export default function Map({ markers = [], route, onClick, focus, center = [9.9312, 76.2673] }) {
  return (
    <div className="h-[26rem] sm:h-[32rem] w-full rounded overflow-hidden" role="application" aria-label="Map">
      <MapContainer center={center} zoom={13} style={{ height: "100%", width: "100%" }}>
        <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="(c) OpenStreetMap" />
        <Clicker onClick={onClick} />
        <FlyTo focus={focus} />
        <Fit route={route} />
        {route && route.length > 1 && <Polyline positions={route} pathOptions={{ color: "#2563eb", weight: 5, opacity: 0.8 }} />}
        {markers.map((m, i) => m.pos && (
          <CircleMarker key={i} center={m.pos} radius={m.label ? 10 : 7} pathOptions={{ color: m.color, fillOpacity: 0.9 }}>
            {m.label && <Tooltip permanent direction="top" offset={[0, -8]}>{m.label}</Tooltip>}
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}