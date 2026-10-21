// A drawn city skyline. Built in code, so there are no image rights to worry about.
function rng(seed) {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) % 4294967296;
    return s / 4294967296;
  };
}

export default function Skyline() {
  const rand = rng(11);
  const W = 1440;
  const H = 260;
  const buildings = [];
  let x = -10;
  while (x < W) {
    const w = 38 + Math.floor(rand() * 72);
    const h = 60 + Math.floor(rand() * 175);
    const windows = [];
    for (let wy = H - h + 12; wy < H - 10; wy += 16) {
      for (let wx = x + 7; wx < x + w - 9; wx += 12) {
        if (rand() > 0.74) windows.push({ x: wx, y: wy, warm: rand() > 0.3 });
      }
    }
    buildings.push({ x, w, h, windows });
    x += w + (rand() > 0.6 ? 6 : 0);
  }
  return (
    <svg
      className="skyline"
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="xMidYMax slice"
      aria-hidden="true"
    >
      {buildings.map((b, i) => (
        <g key={i}>
          <rect x={b.x} y={H - b.h} width={b.w} height={b.h} fill="#050507" />
          {b.windows.map((w, j) => (
            <rect
              key={j}
              x={w.x}
              y={w.y}
              width="5"
              height="7"
              fill={w.warm ? "#f2a33a" : "#c8202f"}
              opacity="0.9"
            />
          ))}
        </g>
      ))}
    </svg>
  );
}
