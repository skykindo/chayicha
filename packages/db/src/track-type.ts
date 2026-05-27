import { TrackType } from "@prisma/client";

export const TRACK_TYPE_LABELS: Record<TrackType, string> = {
  WEB: "网页爬虫",
  VISION_AI: "AI 视觉",
};

export function formatTrackTypeLabel(trackType: TrackType): string {
  return TRACK_TYPE_LABELS[trackType];
}
