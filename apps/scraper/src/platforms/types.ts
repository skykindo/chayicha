export type ListItem = {
  title: string;
  price: number;
  tradeType: "AUCTION" | "FLOOR";
  cardCondition?: string;
  gradeLabel?: string;
  info?: string;
  bidCount?: number | null;
  bidderCount?: number | null;
  watchCount?: number | null;
  isDelayed?: boolean;
  capturedAt?: Date;
};

export type ChannelContext = {
  asset: import("@everyasset/db").StandardAsset;
  channel: import("@everyasset/db").AssetChannel;
};
