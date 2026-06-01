/** 业务主键 → 详情页路径（含 / 的 key 按路径段编码） */
export function assetDetailHref(assetKey: string): string {
  return `/asset/${assetKey.split("/").map(encodeURIComponent).join("/")}`;
}

/** catch-all 路由 params → 业务主键 */
export function parseAssetKeyParam(segments: string | string[]): string {
  const parts = Array.isArray(segments) ? segments : [segments];
  return parts.map(decodeURIComponent).join("/");
}
