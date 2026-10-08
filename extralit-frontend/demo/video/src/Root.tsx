import { Composition } from "remotion";
import { Demo, SCREEN_FRAMES } from "./Demo";
import { demo } from "./data";
import { FPS, INTRO_FRAMES, OUTRO_FRAMES } from "./theme";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="ExtractionsDemo"
    component={Demo}
    durationInFrames={INTRO_FRAMES + SCREEN_FRAMES + OUTRO_FRAMES}
    fps={FPS}
    width={1920}
    height={1080}
    // Stamped by build-timeline.mjs from the commit the recording was made against.
    defaultProps={{ commit: demo.commit }}
  />
);
