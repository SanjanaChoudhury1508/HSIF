
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

function Wave() {
  return (
    <div className="wave" aria-hidden="true">
      {Array.from({ length: 36 }, (_, i) => (
        <span key={i} style={{ height: `${12 + ((i * 17) % 27)}px` }} />
      ))}
    </div>
  );
}

export default function SignupPage() {
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [terms, setTerms] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (name.trim().length < 2) {
      setError("Please enter your full name.");
      return;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setError("Please enter a valid email address.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    if (!terms) {
      setError("Please accept the terms of use and privacy policy.");
      return;
    }

    localStorage.setItem("hsif-account", JSON.stringify({
      name: name.trim(),
      email: email.trim().toLowerCase(),
      password,
    }));

    navigate("/login", { state: { registered: true } });
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

          <h1>Create your account</h1>
          <p className="sub">
            It takes a minute. Then you can start your first voice session.
          </p>

          {error && <p className="error" role="alert">{error}</p>}

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="name">Full name</label>
              <input
                id="name"
                type="text"
                autoComplete="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

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
                  autoComplete="new-password"
                  aria-describedby="pw-hint"
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
              <p className="hint" id="pw-hint">Use at least 8 characters.</p>
            </div>

            <div className="field">
              <label className="check">
                <input
                  type="checkbox"
                  checked={terms}
                  onChange={(e) => setTerms(e.target.checked)}
                />
                <span>
                  I agree to the <a href="#" onClick={(e) => e.preventDefault()}>terms of use</a>
                  {" "}and{" "}
                  <a href="#" onClick={(e) => e.preventDefault()}>privacy policy</a>.
                </span>
              </label>
            </div>

            <button className="btn btn-primary btn-block" type="submit">
              Create account
            </button>
          </form>

          <p className="switch">
            Already have an account? <Link to="/login">Log in</Link>
          </p>
        </div>
      </main>

      <aside className="auth-side" aria-hidden="true">
        <h2>An assistant that notices when you're unsure.</h2>
        <p>
          HSIF listens for hesitation and low confidence, then changes how
          the assistant explains things.
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