export function Stars({ value = 0, size = "text-base" }) {
  const full = Math.round(value);
  return (
    <span className={size} role="img" aria-label={`${value} out of 5 stars`}>
      {[1, 2, 3, 4, 5].map(n => (
        <span key={n} className={n <= full ? "text-amber-500" : "text-gray-300"}>★</span>
      ))}
    </span>
  );
}