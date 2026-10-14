import { Video } from "@remotion/media";
import { AbsoluteFill, Easing, Interactive, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { demo } from "./data";
import { theme } from "./theme";

const EASE = Easing.bezier(0.16, 1, 0.3, 1);

// The 1440x900 recording is scaled down so the browser card, the assertion rail and the
// lower-third caption each get their own band of the 1920x1080 canvas without overlapping.
const VIDEO_X = 48;
const VIDEO_Y = 124;
const VIDEO_SCALE = 0.98;
const CHROME_H = 36;
// Every scene's content lives in the top ~720px of the 900px-tall page; the rest is empty
// canvas below the grid. Cropping it lets the recording render nearly 1:1 instead of being
// shrunk to fit dead space.
const CROP_H = 720;
const VIDEO_W = Math.round(demo.width * VIDEO_SCALE);
const VIDEO_H = Math.round(demo.height * VIDEO_SCALE);
const VIEWPORT_H = Math.round(CROP_H * VIDEO_SCALE);
const RAIL_X = VIDEO_X + VIDEO_W + 40;
const RAIL_W = 1920 - RAIL_X - 48;
const CARD_BOTTOM = VIDEO_Y + CHROME_H + VIEWPORT_H;

/** The scene covering `ms`, or the last one once the recording has run past its end. */
const sceneAt = (ms: number) =>
  demo.scenes.find((s) => ms >= s.startMs && ms < s.endMs) ?? demo.scenes[demo.scenes.length - 1];

const Tick: React.FC<{ ok: boolean; visible: number }> = ({ ok, visible }) => (
  <div
    style={{
      width: 22,
      height: 22,
      borderRadius: 6,
      flexShrink: 0,
      marginTop: 3,
      display: "grid",
      placeItems: "center",
      background: ok ? "rgba(74,222,128,0.16)" : "rgba(248,113,113,0.16)",
      border: `1px solid ${ok ? theme.ok : theme.bad}`,
      color: ok ? theme.ok : theme.bad,
      fontSize: 15,
      fontWeight: 800,
      opacity: visible,
      scale: interpolate(visible, [0, 1], [0.6, 1]),
    }}
  >
    {ok ? "✓" : "✕"}
  </div>
);

export const Screencast: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ms = (frame / fps) * 1000;
  const scene = sceneAt(ms);
  const sceneIndex = demo.scenes.indexOf(scene);
  const sceneFrame = frame - (scene.startMs / 1000) * fps;

  // Checks reveal one after another across the first ~40% of the scene, so the rail reads
  // as "assertions passing live" rather than appearing all at once.
  const revealSpacing = Math.max(6, ((scene.endMs - scene.startMs) / 1000) * fps * 0.12);

  const checksSoFar =
    demo.scenes.slice(0, sceneIndex).reduce((n, s) => n + s.checks.length, 0) +
    Math.min(scene.checks.length, Math.max(0, Math.floor(sceneFrame / revealSpacing) + 1));

  return (
    <AbsoluteFill style={{ background: theme.bg, fontFamily: theme.font }}>
      {/* ── Header ─────────────────────────────────────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          inset: "0 0 auto 0",
          height: 92,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 48px",
          borderBottom: `1px solid ${theme.panelBorder}`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          <div style={{ width: 14, height: 14, borderRadius: 999, background: theme.accent }} />
          <div style={{ color: theme.text, fontSize: 27, fontWeight: 700 }}>
            Extralit <span style={{ color: theme.muted, fontWeight: 500 }}>/extractions</span>
          </div>
        </div>
        <div style={{ color: theme.muted, fontFamily: theme.mono, fontSize: 22 }}>
          scene {sceneIndex + 1}/{demo.scenes.length} · {scene.id}
        </div>
      </div>

      {/* ── Screen recording, in a browser frame ───────────────────────────────── */}
      <Interactive.Div
        name="Browser frame"
        style={{
          position: "absolute",
          left: VIDEO_X,
          top: VIDEO_Y,
          width: VIDEO_W,
          borderRadius: 16,
          overflow: "hidden",
          background: theme.panel,
          border: `1px solid ${theme.panelBorder}`,
          boxShadow: "0 40px 90px rgba(0,0,0,0.55)",
        }}
      >
        <div style={{ height: CHROME_H, display: "flex", alignItems: "center", gap: 9, padding: "0 16px" }}>
          {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
            <div key={c} style={{ width: 12, height: 12, borderRadius: 999, background: c }} />
          ))}
          <div
            style={{
              marginLeft: 14,
              flex: 1,
              height: 24,
              borderRadius: 999,
              background: "rgba(0,0,0,0.28)",
              color: theme.muted,
              fontFamily: theme.mono,
              fontSize: 14,
              display: "flex",
              alignItems: "center",
              paddingLeft: 14,
            }}
          >
            localhost:3000/extractions
          </div>
        </div>
        <div style={{ height: VIEWPORT_H, overflow: "hidden" }}>
          <Video src={staticFile("screen.mp4")} style={{ display: "block", width: VIDEO_W, height: VIDEO_H }} />
        </div>
      </Interactive.Div>

      {/* ── Live assertion rail ────────────────────────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          left: RAIL_X,
          top: VIDEO_Y,
          width: RAIL_W,
          height: CARD_BOTTOM - VIDEO_Y,
          background: theme.panel,
          border: `1px solid ${theme.panelBorder}`,
          borderRadius: 16,
          padding: 24,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div style={{ color: theme.muted, fontSize: 17, letterSpacing: 2, textTransform: "uppercase", fontWeight: 700 }}>
          Asserted live
        </div>
        <div style={{ color: theme.text, fontSize: 46, fontWeight: 800, marginTop: 8, fontFamily: theme.mono }}>
          {checksSoFar}
          <span style={{ color: theme.muted, fontSize: 26, fontWeight: 500 }}> / {demo.totalChecks}</span>
        </div>
        <div style={{ height: 1, background: theme.panelBorder, margin: "20px 0" }} />
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {scene.checks.map((check, i) => (
            <div key={check.label} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
              <Tick
                ok={check.ok}
                visible={interpolate(sceneFrame, [i * revealSpacing, i * revealSpacing + 8], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                  easing: EASE,
                })}
              />
              <div
                style={{
                  color: theme.text,
                  fontSize: 19,
                  lineHeight: 1.35,
                  opacity: interpolate(sceneFrame, [i * revealSpacing, i * revealSpacing + 8], [0.15, 1], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                    easing: EASE,
                  }),
                }}
              >
                {check.label}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Lower third: scene title + caption ─────────────────────────────────── */}
      <Interactive.Div
        name="Caption"
        style={{
          position: "absolute",
          left: VIDEO_X,
          right: 48,
          top: CARD_BOTTOM + 28,
          opacity: interpolate(sceneFrame, [0, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE }),
          translate: interpolate(sceneFrame, [0, 16], ["0px 18px", "0px 0px"], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: EASE,
          }),
        }}
      >
        <div style={{ color: theme.accent, fontSize: 34, fontWeight: 800 }}>{scene.title}</div>
        <div style={{ color: theme.muted, fontSize: 26, marginTop: 8 }}>{scene.caption}</div>
      </Interactive.Div>

      {/* ── Progress bar ───────────────────────────────────────────────────────── */}
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 6, background: "rgba(255,255,255,0.06)" }}>
        <div
          style={{
            height: "100%",
            width: `${Math.min(100, (ms / (demo.videoDurationSec * 1000)) * 100)}%`,
            background: theme.accent,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
