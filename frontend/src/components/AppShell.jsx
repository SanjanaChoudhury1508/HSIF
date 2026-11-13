import { NavLink, Link, useNavigate } from "react-router-dom";
import { clearLocalUserSession } from "../services/localSession";

function Icon({ children }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export default function AppShell({ title, subtitle, action, children }) {
  const navigate = useNavigate();

  function handleLogout() {
    clearLocalUserSession();
    navigate("/login", { replace: true });
  }

  return (
    <div className="shell light">
      <aside className="sidebar">
        <Link className="logo" to="/dashboard" aria-label="HSIF dashboard">
          <svg viewBox="0 0 32 32" aria-hidden="true">
            <rect width="32" height="32" rx="9" fill="#3fd6c2" />
            <g fill="#101b2e">
              <rect x="6" y="13" width="3" height="6" rx="1.5" />
              <rect x="11" y="9" width="3" height="14" rx="1.5" />
              <rect x="16" y="6" width="3" height="20" rx="1.5" />
              <rect x="21" y="10" width="3" height="12" rx="1.5" />
            </g>
          </svg>
          HSIF
        </Link>

        <nav className="side-nav" aria-label="App">
          <NavLink to="/dashboard">
            <Icon>
              <rect x="3" y="3" width="7" height="9" rx="1.5" />
              <rect x="14" y="3" width="7" height="5" rx="1.5" />
              <rect x="14" y="12" width="7" height="9" rx="1.5" />
              <rect x="3" y="16" width="7" height="5" rx="1.5" />
            </Icon>
            <span>Dashboard</span>
          </NavLink>

          <NavLink to="/chat">
            <Icon>
              <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z" />
            </Icon>
            <span>Chat</span>
          </NavLink>

          <NavLink to="/history">
            <Icon>
              <circle cx="12" cy="12" r="9" />
              <path d="M12 7v5l3 2" />
            </Icon>
            <span>History</span>
          </NavLink>

          <NavLink to="/account">
            <Icon>
              <circle cx="12" cy="8" r="4" />
              <path d="M4 21a8 8 0 0 1 16 0" />
            </Icon>
            <span>Account</span>
          </NavLink>

          <NavLink to="/settings">
            <Icon>
              <circle cx="12" cy="12" r="3" />
              <path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2" />
            </Icon>
            <span>Settings</span>
          </NavLink>
        </nav>

        <button className="logout" type="button" onClick={handleLogout}>
          <Icon>
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
          </Icon>
          <span>Log out</span>
        </button>
      </aside>

      <div className="main">
        <header className="topbar">
          <div>
            <h1>{title}</h1>
            <p className="session">{subtitle}</p>
          </div>
          {action}
        </header>

        {children}
      </div>
    </div>
  );
}
