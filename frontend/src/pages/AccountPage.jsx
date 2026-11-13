import { useState } from "react";
import { useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import { clearLocalUserSession } from "../services/localSession";

function readStoredData(key) {
  try {
    return JSON.parse(localStorage.getItem(key) || "null");
  } catch {
    return null;
  }
}

export default function AccountPage() {
  const navigate = useNavigate();

  const [account, setAccount] = useState(
    () => readStoredData("hsif-account")
  );

  const [user, setUser] = useState(
    () => readStoredData("hsif-user")
  );

  const [name, setName] = useState(
    () => account?.name || user?.name || ""
  );

  const [email, setEmail] = useState(
    () => account?.email || user?.email || ""
  );

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const [profileStatus, setProfileStatus] = useState("");
  const [passwordStatus, setPasswordStatus] = useState("");

  function handleProfileSave(event) {
    event.preventDefault();

    const trimmedName = name.trim();
    const trimmedEmail = email.trim().toLowerCase();

    if (trimmedName.length < 2) {
      setProfileStatus("Name must contain at least 2 characters.");
      return;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {      setProfileStatus("Enter a valid email address.");
      return;
    }

    const updatedAccount = {
      ...(account || {}),
      name: trimmedName,
      email: trimmedEmail,
    };

    const updatedUser = {
      ...(user || {}),
      name: trimmedName,
      email: trimmedEmail,
    };

    localStorage.setItem(
      "hsif-account",
      JSON.stringify(updatedAccount)
    );

    localStorage.setItem(
      "hsif-user",
      JSON.stringify(updatedUser)
    );

    setAccount(updatedAccount);
    setUser(updatedUser);
    setProfileStatus("Profile updated successfully.");
  }

  function handlePasswordSave(event) {
    event.preventDefault();
    setPasswordStatus("");

    const storedAccount = readStoredData("hsif-account");

    if (!storedAccount?.password) {
      setPasswordStatus("No demo account password was found.");
      return;
    }

    if (currentPassword !== storedAccount.password) {
      setPasswordStatus("Current password is incorrect.");
      return;
    }

    if (newPassword.length < 8) {
      setPasswordStatus("New password must contain at least 8 characters.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordStatus("New passwords do not match.");
      return;
    }

    const updatedAccount = {
      ...storedAccount,
      password: newPassword,
    };

    localStorage.setItem(
      "hsif-account",
      JSON.stringify(updatedAccount)
    );

    setAccount(updatedAccount);
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setPasswordStatus("Password updated successfully.");
  }

  function handleDeleteAccount() {
    const confirmed = window.confirm(
      "Delete your local HSIF demo account? This removes the account and login session from this browser. Saved PostgreSQL conversations will not be deleted."
    );

    if (!confirmed) return;

    localStorage.removeItem("hsif-account");
    clearLocalUserSession();

    navigate("/signup", { replace: true });
  }

  return (
    <AppShell
      title="Account"
      subtitle="Manage your profile and password"
    >
      <div className="narrow">
        <section className="panel" aria-labelledby="profile-heading">
          <h2 id="profile-heading">Profile</h2>

          <div className="profile" style={{ marginTop: 16 }}>
            <span className="avatar" aria-hidden="true">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="8" r="4" />
                <path d="M4 21a8 8 0 0 1 16 0" />
              </svg>
            </span>
            <span className="desc">
              {name || "HSIF User"}
            </span>
          </div>

          <form onSubmit={handleProfileSave}>
            <div className="field">
              <label htmlFor="a-name">Full name</label>
              <input
                id="a-name"
                type="text"
                value={name}
                onChange={(event) => {
                  setName(event.target.value);
                  setProfileStatus("");
                }}
                autoComplete="name"
                required
              />
            </div>

            <div className="field">
              <label htmlFor="a-email">Email address</label>
              <input
                id="a-email"
                type="email"
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value);
                  setProfileStatus("");
                }}
                autoComplete="email"
                required
              />
            </div>

            <div>
              <button className="btn btn-primary" type="submit">
                Save changes
              </button>
              <span className="save-note" role="status">
                {profileStatus}
              </span>
            </div>
          </form>
        </section>

        <section className="panel" aria-labelledby="password-heading">
          <h2 id="password-heading">Password</h2>

          <form onSubmit={handlePasswordSave} style={{ marginTop: 16 }}>
            <div className="field">
              <label htmlFor="p-old">Current password</label>
              <input
                id="p-old"
                type="password"
                value={currentPassword}
                onChange={(event) => {
                  setCurrentPassword(event.target.value);
                  setPasswordStatus("");
                }}
                autoComplete="current-password"
                required
              />
            </div>

            <div className="field">
              <label htmlFor="p-new">New password</label>
              <div className="pw">
                <input
                  id="p-new"
                  type={showPassword ? "text" : "password"}
                  value={newPassword}
                  onChange={(event) => {
                    setNewPassword(event.target.value);
                    setPasswordStatus("");
                  }}
                  autoComplete="new-password"
                  minLength={8}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
              <p className="hint">Use at least 8 characters.</p>
            </div>

            <div className="field">
              <label htmlFor="p-confirm">Confirm new password</label>
              <input
                id="p-confirm"
                type={showPassword ? "text" : "password"}
                value={confirmPassword}
                onChange={(event) => {
                  setConfirmPassword(event.target.value);
                  setPasswordStatus("");
                }}
                autoComplete="new-password"
                required
              />
            </div>

            <div>
              <button className="btn btn-primary" type="submit">
                Update password
              </button>
              <span className="save-note" role="status">
                {passwordStatus}
              </span>
            </div>
          </form>
        </section>

        <section className="panel" aria-labelledby="session-heading">
          <h2 id="session-heading">Session</h2>
          <p className="desc">
            Log out on this device or remove your local demo account.
          </p>

          <div className="btn-row">
            <button
              className="btn btn-ghost"
              type="button"
              onClick={() => {
                clearLocalUserSession();
                navigate("/login", { replace: true });
              }}
            >
              Log out
            </button>

            <button
              className="btn btn-danger"
              type="button"
              onClick={handleDeleteAccount}
            >
              Delete account
            </button>
          </div>

          <p className="hint">
            Account management is currently browser-local. Deleting this
            demo account does not delete saved conversations in PostgreSQL.
          </p>
        </section>
      </div>
    </AppShell>
  );
}
