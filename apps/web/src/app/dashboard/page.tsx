import { redirect } from "next/navigation";

/** 旧看板入口已合并至首页列表 + /asset/[id] */
export default function DashboardPage() {
  redirect("/");
}
