import { cn } from "@/lib/utils";

type SectionHeaderProps = {
  label: string;
  title: string;
  description?: string;
  labelTone?: "emerald" | "sky";
  trailing?: React.ReactNode;
};

export function SectionHeader({
  label,
  title,
  description,
  labelTone = "emerald",
  trailing,
}: SectionHeaderProps) {
  return (
    <div className="flex items-end justify-between gap-4">
      <div>
        <p
          className={cn(
            "text-[14px] uppercase tracking-widest",
            labelTone === "emerald" ? "text-emerald-400" : "text-sky-400",
          )}
        >
          {label}
        </p>
        <h2 className="mt-1.5 text-[21px] font-semibold">{title}</h2>
        {description && (
          <p className="mt-1 text-[14px] text-zinc-500">{description}</p>
        )}
      </div>
      {trailing}
    </div>
  );
}
