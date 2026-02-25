import { Link } from "react-router";

import { municipalities } from "../../data";

export default function Index() {
  return (
    <>
      <h1>市町村一覧</h1>

      <ul>
        {municipalities.map(({ slug, type, name }) => (
          <li key={`${slug}/${type}`}>
            <Link to={`${slug}/${type}`}>
              {name}
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
