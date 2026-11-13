
import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";

function Wave() {
  return (
    <div className="wave" aria-hidden="true">
      {Array.from({ length: 36 }, (_, i) => (
        <span key={i} style={{ height: `${12 + ((i * 17) % 27)}px` }} />
      ))}
    </div>
  );
}

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [notice] = useState(
    location.state?.registered ? "Account created. Log in to continue." : ""
  );

  function handleSubmit(event) {
    event.preventDefault();
    setError("");

    const account = JSON.parse(localStorage.getItem("hsif-account") || "null");

    if (!email.trim() || !password) {
      setError("Please enter your email address and password.");
      return;
    }

    if (
      !account ||
      account.email !== email.trim().toLowerCase() ||
      account.password !== password
    ) {
      setError("Invalid email or password. Create an account first if you are new.");
      return;
    }

    localStorage.setItem("hsif-user", JSON.stringify({
      name: account.name,
      email: account.email,
      remember,
    }));

    navigate("/dashboard");
  }

  return (
    <div className="auth">
      <main className="auth-form">
        <Link className="back" to="/">‹ Back to home</Link>

        <div className="auth-card">
          <Link className="logo" to="/" aria-label="HSIF home">
            <svg viewBox="0 0 32 32" aria-hidden="true">
              <rect width="32" height="32" rx="9" fill="#101b2e" />
              <g fill="#3fd6c2">
                <rect x="6" y="13" width="3" height="6" rx="1.5" />
                <rect x="11" y="9" width="3" height="14" rx="1.5" />
                <rect x="16" y="6" width="3" height="20" rx="1.5" />
                <rect x="21" y="10" width="3" height="12" rx="1.5" />
              </g>
            </svg>
            HSIF
          </Link>

          <h1>Log in</h1>
          <p className="sub">Welcome back. Pick up where your last session ended.</p>

          {notice && <p className="notice" role="status">{notice}</p>}
          {error && <p className="error" role="alert">{error}</p>}

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="email">Email address</label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div className="field">
              <label htmlFor="password">Password</label>
              <div className="pw">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </div>

            <div className="row">
              <label className="check">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                />
                Keep me logged in
              </label>
              <a href="#" onClick={(e) => e.preventDefault()}>
                Forgot password?
              </a>
            </div>

            <button className="btn btn-primary btn-block" type="submit">
              Log in
            </button>
          </form>

          <p className="switch">
            New to HSIF? <Link to="/signup">Create an account</Link>
          </p>
        </div>
      </main>

      <aside className="auth-side" aria-hidden="true">
        <h2>See how the assistant read every conversation.</h2>
        <p>
          Each session keeps its scores, so you can review where a speaker
          hesitated and how the assistant responded.
        </p>
        <div className="readout">
          <Wave />
          <ul className="signal-list">
            <li><i style={{ background: "#3fd6c2" }} />Confidence</li>
            <li><i style={{ background: "#f1b24a" }} />Hesitation</li>
            <li><i style={{ background: "#9a92ff" }} />Engagement</li>
            <li><i style={{ background: "#ff8a80" }} />Cognitive load</li>
          </ul>
        </div>
      </aside>
    </div>
  );
}