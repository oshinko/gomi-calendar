import { Link, useParams } from "react-router";

import { municipalities } from "../../data";

export default function Municipality() {
  const { municipality: slug, type } = useParams();
  const municipality = municipalities.find(x => x.slug === slug && x.type === type)!;

  return <>
    <h1>{municipality.name}</h1>

    {municipality.calendars.length === 0 ? (
      <p>カレンダーはありません。</p>
    ) : (
      <ul>
        {municipality.calendars.map(calendar => (
          <li>
            {calendar.name}
            <ul>
              {calendar.iCalendar && (
                <li>
                  <Link to={calendar.iCalendar}>
                    iCalendar
                  </Link>
                </li>
              )}
              {calendar.googleCalendar && (
                <li>
                  <Link to={calendar.googleCalendar}>
                    Google カレンダー
                  </Link>
                </li>
              )}
            </ul>
          </li>
        ))}
      </ul>
    )}
  </>;
}
