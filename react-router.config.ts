import type { Config } from "@react-router/dev/config";

import municipalities from "./data/calendars.json";

export default {
  ssr: false,
  async prerender({ getStaticPaths }) {
    return [
      ...getStaticPaths(),
      ...municipalities.map(({ municipality, calendars }) => `/${municipality.slug}/${municipality.type}`),
    ];
  },
} satisfies Config;
