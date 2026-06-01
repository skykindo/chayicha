"use client";

import { useCallback, useEffect, useState } from "react";
import { ImageOff, X } from "lucide-react";
import { cn } from "@/lib/utils";

type AssetCardThumbProps = {
  imageUrl?: string | null;
  name: string;
  variant?: "list" | "detail";
  className?: string;
};

const SIZES = {
  /** 原 40×56，放大 15% → 46×64 */
  list: { w: "w-[46px]", h: "h-16", wPx: 46, hPx: 64 },
  /** 原 120×168，放大 25% → 150×210 */
  detail: { w: "w-[150px]", h: "h-[210px]", wPx: 150, hPx: 210 },
} as const;

function CardPlaceholder({
  name,
  compact,
}: {
  name: string;
  compact?: boolean;
}) {
  return (
    <div
      className="flex h-full w-full flex-col items-center justify-center gap-1 bg-gradient-to-b from-zinc-800 to-zinc-900"
      title={name}
    >
      <ImageOff
        className={cn("text-zinc-500", compact ? "h-4 w-4" : "h-8 w-8")}
        strokeWidth={1.5}
      />
      {!compact && (
        <span className="max-w-[120px] truncate px-1 text-[10px] text-zinc-600">
          {name}
        </span>
      )}
      {compact && (
        <span className="max-w-[38px] truncate text-[8px] leading-tight text-zinc-600">
          {name.slice(0, 4)}
        </span>
      )}
    </div>
  );
}

function CardImage({
  src,
  alt,
  width,
  height,
  className,
  onError,
}: {
  src: string;
  alt: string;
  width: number;
  height: number;
  className?: string;
  onError: () => void;
}) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt}
      width={width}
      height={height}
      className={cn("h-full w-full object-cover object-top", className)}
      loading="lazy"
      decoding="async"
      referrerPolicy="no-referrer"
      onError={onError}
    />
  );
}

function CardLightbox({
  src,
  alt,
  open,
  onClose,
}: {
  src: string;
  alt: string;
  open: boolean;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/90 p-6 backdrop-blur-md"
      role="dialog"
      aria-modal="true"
      aria-label={`${alt} 大图预览`}
      onClick={onClose}
    >
      <button
        type="button"
        onClick={onClose}
        className="absolute right-5 top-5 rounded-full border border-zinc-600 bg-zinc-900/90 p-2 text-zinc-300 transition hover:bg-zinc-800 hover:text-white"
        aria-label="关闭"
      >
        <X className="h-5 w-5" />
      </button>

      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={alt}
        className="max-h-[92vh] max-w-[min(92vw,480px)] rounded-lg object-contain shadow-2xl shadow-black/60"
        referrerPolicy="no-referrer"
        onClick={(e) => e.stopPropagation()}
      />
    </div>
  );
}

export function AssetCardThumb({
  imageUrl,
  name,
  variant = "list",
  className,
}: AssetCardThumbProps) {
  const [failed, setFailed] = useState(false);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const showImage = Boolean(imageUrl?.trim()) && !failed;
  const src = imageUrl?.trim() ?? "";
  const size = SIZES[variant];
  const isList = variant === "list";

  const openLightbox = useCallback(() => {
    if (showImage) setLightboxOpen(true);
  }, [showImage]);

  const closeLightbox = useCallback(() => setLightboxOpen(false), []);

  return (
    <>
      <button
        type="button"
        disabled={!showImage}
        onClick={openLightbox}
        className={cn(
          "relative shrink-0 overflow-hidden rounded border border-zinc-700/80 bg-zinc-900 shadow-sm",
          size.w,
          size.h,
          showImage &&
            "cursor-zoom-in transition hover:border-zinc-500 hover:shadow-md hover:shadow-black/40",
          !showImage && "cursor-default",
          className,
        )}
        aria-label={showImage ? `查看 ${name} 大图` : name}
      >
        {showImage ? (
          <CardImage
            src={src}
            alt={name}
            width={size.wPx}
            height={size.hPx}
            onError={() => setFailed(true)}
          />
        ) : (
          <CardPlaceholder name={name} compact={isList} />
        )}
      </button>

      {showImage && (
        <CardLightbox
          src={src}
          alt={name}
          open={lightboxOpen}
          onClose={closeLightbox}
        />
      )}
    </>
  );
}
