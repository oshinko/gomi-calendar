import municipalityCalendarList from "./data/calendars.json";
import municipalityList from "./data/municipalities.json";

const MAP_KEY_SEP = "/";

console.debug("######## import utils.ts");

type MunicipalityBase = (typeof municipalityList.municipalities)[number];
type MunicipalityCalendar = (typeof municipalityCalendarList)[number]["calendars"][number];
type Municipality = MunicipalityBase & { calendars: MunicipalityCalendar[] };

const municipalityBaseMap = new Map<string, MunicipalityBase>();
for (const item of municipalityList.municipalities) {
  municipalityBaseMap.set(item.slug + MAP_KEY_SEP + item.type, item);
}

const municipalityCalendarMap = new Map<string, MunicipalityCalendar[]>();
for (const item of municipalityCalendarList) {
  const k = item.municipality.slug + MAP_KEY_SEP + item.municipality.type;
  municipalityCalendarMap.set(k, item.calendars);
}

const copy = structuredClone(municipalityList.municipalities);
export const municipalities = copy.map<Municipality>(x => ({
  ...x,
  calendars: municipalityCalendarMap.get(x.slug + MAP_KEY_SEP + x.type) ?? []
}));
