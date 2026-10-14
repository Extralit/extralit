import { AbsoluteFill, Sequence } from "remotion";
import { Intro } from "./Intro";
import { Outro } from "./Outro";
import { Screencast } from "./Screencast";
import { demo } from "./data";
import { FPS, INTRO_FRAMES, theme } from "./theme";

export const SCREEN_FRAMES = Math.floor(demo.videoDurationSec * FPS);

export const Demo: React.FC<{ commit: string }> = ({ commit }) => (
  <AbsoluteFill style={{ background: theme.bg }}>
    <Sequence name="Intro" durationInFrames={INTRO_FRAMES}>
      <Intro commit={commit} />
    </Sequence>
    <Sequence name="Screencast" from={INTRO_FRAMES} durationInFrames={SCREEN_FRAMES}>
      <Screencast />
    </Sequence>
    <Sequence name="Outro" from={INTRO_FRAMES + SCREEN_FRAMES}>
      <Outro />
    </Sequence>
  </AbsoluteFill>
);
