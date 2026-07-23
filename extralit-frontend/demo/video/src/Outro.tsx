import { AbsoluteFill, Easing, Interactive, interpolate, useCurrentFrame } from "remotion";
import { demo } from "./data";
import { theme } from "./theme";

const EASE = Easing.bezier(0.16, 1, 0.3, 1);

const PROVEN = [
  "Workspace-wide projection renders as one flat grid",
  "Response beats suggestion in every coalesced cell",
  "Un-annotated schemas still contribute coverage-gap columns",
  "Table questions fan out; reference banding survives virtualized scroll",
  "Workspace swap reloads the projection in place — no stale columns",
  "Empty and no-workspace states are explicit, never a blank grid",
];

export const Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const allGreen = demo.failures.length === 0 && demo.pageErrors.length === 0;

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(1100px 700px at 70% 30%, #17203c 0%, ${theme.bg} 70%)`,
        fontFamily: theme.font,
        justifyContent: "center",
        paddingLeft: 140,
        paddingRight: 140,
      }}
    >
      <Interactive.Div
        name="Verdict"
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 26,
          opacity: interpolate(frame, [0, 16], [0, 1], { extrapolateRight: "clamp", easing: EASE }),
          translate: interpolate(frame, [0, 22], ["0px 30px", "0px 0px"], { extrapolateRight: "clamp", easing: EASE }),
        }}
      >
        <div style={{ color: allGreen ? theme.ok : theme.bad, fontSize: 112, fontWeight: 800, fontFamily: theme.mono }}>
          {demo.totalChecks - demo.failures.length}/{demo.totalChecks}
        </div>
        <div style={{ color: theme.text, fontSize: 44, fontWeight: 700 }}>assertions passed</div>
      </Interactive.Div>

      <div
        style={{
          color: theme.muted,
          fontFamily: theme.mono,
          fontSize: 26,
          marginTop: 14,
          opacity: interpolate(frame, [10, 28], [0, 1], { extrapolateRight: "clamp", easing: EASE }),
        }}
      >
        {demo.pageErrors.length} page errors · {demo.consoleErrors.length} console errors · live backend, zero mocks
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 15, marginTop: 52 }}>
        {PROVEN.map((line, i) => (
          <div
            key={line}
            style={{
              display: "flex",
              gap: 16,
              alignItems: "center",
              opacity: interpolate(frame, [20 + i * 7, 34 + i * 7], [0, 1], { extrapolateRight: "clamp", easing: EASE }),
              translate: interpolate(frame, [20 + i * 7, 38 + i * 7], ["-24px 0px", "0px 0px"], {
                extrapolateRight: "clamp",
                easing: EASE,
              }),
            }}
          >
            <div style={{ color: theme.ok, fontSize: 30, fontWeight: 800 }}>✓</div>
            <div style={{ color: theme.text, fontSize: 31 }}>{line}</div>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
