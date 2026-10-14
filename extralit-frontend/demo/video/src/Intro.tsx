import { AbsoluteFill, Easing, interpolate, Interactive, useCurrentFrame } from "remotion";
import { theme } from "./theme";
import { demo } from "./data";

const EASE = Easing.bezier(0.16, 1, 0.3, 1);

export const Intro: React.FC<{ commit: string }> = ({ commit }) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(1200px 700px at 30% 20%, #17203c 0%, ${theme.bg} 70%)`,
        fontFamily: theme.font,
        justifyContent: "center",
        paddingLeft: 140,
      }}
    >
      <Interactive.Div
        name="Eyebrow"
        style={{
          color: theme.accent,
          fontSize: 30,
          fontWeight: 700,
          letterSpacing: 6,
          textTransform: "uppercase",
          marginBottom: 26,
          opacity: interpolate(frame, [0, 18], [0, 1], { extrapolateRight: "clamp", easing: EASE }),
          translate: interpolate(frame, [0, 24], ["-30px 0px", "0px 0px"], {
            extrapolateRight: "clamp",
            easing: EASE,
          }),
        }}
      >
        Extralit · PR #234
      </Interactive.Div>

      <Interactive.Div
        name="Title"
        style={{
          color: theme.text,
          fontSize: 92,
          fontWeight: 800,
          lineHeight: 1.05,
          maxWidth: 1400,
          opacity: interpolate(frame, [6, 30], [0, 1], { extrapolateRight: "clamp", easing: EASE }),
          translate: interpolate(frame, [6, 34], ["0px 40px", "0px 0px"], {
            extrapolateRight: "clamp",
            easing: EASE,
          }),
        }}
      >
        The <span style={{ color: theme.accent }}>/extractions</span> grid
      </Interactive.Div>

      <Interactive.Div
        name="Subtitle"
        style={{
          color: theme.muted,
          fontSize: 38,
          marginTop: 30,
          maxWidth: 1300,
          opacity: interpolate(frame, [18, 42], [0, 1], { extrapolateRight: "clamp", easing: EASE }),
        }}
      >
        Every extraction in a workspace, denormalized into one Perspective datagrid.
      </Interactive.Div>

      <Interactive.Div
        name="Meta"
        style={{
          display: "flex",
          gap: 18,
          marginTop: 56,
          opacity: interpolate(frame, [30, 54], [0, 1], { extrapolateRight: "clamp", easing: EASE }),
        }}
      >
        {[
          "Live extralit-server + Nuxt — no mocks",
          "Headless Chromium (Playwright)",
          `${demo.totalChecks} assertions`,
          commit,
        ].map((chip) => (
          <div
            key={chip}
            style={{
              border: `1px solid ${theme.panelBorder}`,
              background: theme.panel,
              color: theme.muted,
              borderRadius: 999,
              padding: "12px 24px",
              fontSize: 24,
              fontFamily: theme.mono,
            }}
          >
            {chip}
          </div>
        ))}
      </Interactive.Div>
    </AbsoluteFill>
  );
};
