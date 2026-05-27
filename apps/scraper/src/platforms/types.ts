export type ListItem = {
  title: string;
  price: number;
  tradeType: "AUCTION" | "FLOOR";
  gradeLabel?: string;
  info?: string;
};

export type ChannelContext = {
  asset: import("@everyasset/db").StandardAsset;
  channel: import("@everyasset/db").AssetChannel;
};
