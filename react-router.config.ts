import type { Config } from "@react-router/dev/config";

import { municipalities } from "./data";

export default {
  ssr: false,
  async prerender({ getStaticPaths }) {
    return [
      ...getStaticPaths(),
      ...municipalities.map(({ slug, type }) => `/${slug}/${type}`),
    ];
  },
} satisfies Config;
