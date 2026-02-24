import type { RouteConfig } from "@react-router/dev/routes";
import { index, route } from "@react-router/dev/routes";

export default [
  index("./routes/_index.tsx"),
  route(":municipality/:type", "./routes/$municipality.$type.tsx"),
] satisfies RouteConfig;
