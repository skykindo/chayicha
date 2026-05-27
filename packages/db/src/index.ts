import { PrismaClient } from "@prisma/client";

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined;
};

export const prisma =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: process.env.NODE_ENV === "development" ? ["error", "warn"] : ["error"],
  });

if (process.env.NODE_ENV !== "production") {
  globalForPrisma.prisma = prisma;
}

export * from "@prisma/client";
export {
  PLATFORM_LABELS,
  formatPlatformLabel,
  formatPlatformSeriesKey,
} from "./platform";
export {
  TRACK_TYPE_LABELS,
  formatTrackTypeLabel,
} from "./track-type";
export {
  GRADING_COMPANY_LABELS,
  formatAssetGradeLabel,
  buildGradeLabel,
  parseGradeLabelFromTitle,
  matchesGradeSpec,
} from "./grading";
