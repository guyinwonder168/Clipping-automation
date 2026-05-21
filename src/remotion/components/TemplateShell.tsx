import React from "react";
import { AbsoluteFill, Html5Audio, interpolate, Sequence, staticFile, useCurrentFrame } from "remotion";
import type { CSSProperties } from "react";
import { CTACard } from "./CTACard";
import { WordCaption } from "./WordCaption";
import { BackgroundLayer } from "./BackgroundLayer";
import { ProgressBar } from "./ProgressBar";
import type { ResolvedScene, WordTiming } from "../../state";

type TemplateShellProps = {
  backgroundStyle: CSSProperties;
  voiceoverSrc?: string;
  backgroundMusic?: string | null;
  scenes?: ResolvedScene[];
  wordTimings?: WordTiming[];
  totalFrames: number;
  hookFrames: number;
  ctaStart: number;
  ctaText: string;
  accentColor: string;
  textColor: string;
  children: React.ReactNode;
};

export const TemplateShell: React.FC<TemplateShellProps> = ({
  backgroundStyle,
  voiceoverSrc,
  backgroundMusic,
  scenes,
  wordTimings,
  totalFrames,
  hookFrames,
  ctaStart,
  ctaText,
  accentColor,
  textColor,
  children,
}) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={backgroundStyle}>
      {voiceoverSrc && <Html5Audio src={staticFile(voiceoverSrc)} volume={1} />}
      {backgroundMusic && (
        <Html5Audio src={staticFile(backgroundMusic)} volume={0.12} />
      )}

      {scenes && scenes.length > 0 && (
        <BackgroundLayer
          scenes={scenes}
          totalDurationFrames={totalFrames}
          hookFrames={hookFrames}
          ctaStartFrame={ctaStart}
        />
      )}

      {children}

      <Sequence from={ctaStart} durationInFrames={totalFrames - ctaStart}>
        <CTACard
          ctaText={ctaText}
          accentColor={accentColor}
          textColor={textColor}
          totalDurationFrames={totalFrames - ctaStart}
        />
      </Sequence>

      {wordTimings && wordTimings.length > 0 && <WordCaption wordTimings={wordTimings} />}

      <ProgressBar totalDurationFrames={totalFrames} accentColor={accentColor} />

      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: 1080,
          height: 1920,
          backgroundColor: "#000",
          opacity: 1 - interpolate(
            frame,
            [totalFrames - 30, totalFrames],
            [1, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          ),
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
