
import { useState } from "react";

const API = "http://127.0.0.1:8000";

export default function Auth({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setMessage("");

    try {
      if (mode === "register") {
        const registerResponse = await fetch(`${API}/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        });

        const registered = await registerResponse.json();

        if (!registerResponse.ok) {
          throw new Error(
            registered.detail || "Registration failed."
          );
        }
      }

      const body = new URLSearchParams();
      body.set("username", username);
      body.set("password", password);

      const response = await fetch(`${API}/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Login failed.");
      }

      onLogin(data.access_token);
    } catch (error) {
      setMessage(
        error.message || "Unable to connect. Please try again."
      );
    } finally {
      setBusy(false);
    }
  }

  const styles = {
    page: {
      minHeight: "100vh",
      boxSizing: "border-box",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "24px",
      background:
        "linear-gradient(135deg, #e8f8f5 0%, #f3f7ff 55%, #e9efff 100%)",
      fontFamily:
        "Inter, Segoe UI, Arial, sans-serif",
      color: "#172b4d",
    },
    card: {
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 300px), 1fr))",
      width: "100%",
      maxWidth: "940px",
      overflow: "hidden",
      borderRadius: "24px",
      background: "#ffffff",
      boxShadow: "0 24px 70px rgba(26, 55, 90, 0.14)",
    },
    panel: {
      boxSizing: "border-box",
      padding: "clamp(28px, 5vw, 54px)",
    },
    brandPanel: {
      background: "linear-gradient(145deg, #073b4c, #087f8c)",
      color: "#ffffff",
      display: "flex",
      flexDirection: "column",
      justifyContent: "space-between",
      gap: "40px",
    },
    logo: {
      display: "flex",
      alignItems: "center",
      gap: "12px",
      fontSize: "25px",
      fontWeight: 800,
      letterSpacing: "-0.7px",
    },
    logoIcon: {
      width: "44px",
      height: "44px",
      borderRadius: "14px",
      background: "#ffffff",
      color: "#087f8c",
      display: "grid",
      placeItems: "center",
      fontSize: "27px",
    },
    eyebrow: {
      fontSize: "12px",
      fontWeight: 800,
      letterSpacing: "2px",
      color: "#75e6d0",
      textTransform: "uppercase",
    },
    heading: {
      fontSize: "clamp(30px, 4vw, 42px)",
      lineHeight: 1.15,
      letterSpacing: "-1.3px",
      margin: "14px 0",
    },
    description: {
      color: "#d5eeee",
      lineHeight: 1.8,
      fontSize: "15px",
      margin: 0,
    },
    features: {
      display: "grid",
      gap: "18px",
      marginTop: "28px",
    },
    feature: {
      display: "flex",
      alignItems: "center",
      gap: "12px",
      fontSize: "14px",
      color: "#efffff",
    },
    featureIcon: {
      width: "32px",
      height: "32px",
      borderRadius: "10px",
      background: "rgba(255,255,255,0.13)",
      display: "grid",
      placeItems: "center",
      flexShrink: 0,
    },
    formPanel: {
      boxSizing: "border-box",
      padding: "clamp(28px, 5vw, 54px)",
    },
    formHeading: {
      fontSize: "29px",
      letterSpacing: "-0.8px",
      margin: "8px 0",
      color: "#172b4d",
    },
    subtext: {
      color: "#718096",
      fontSize: "14px",
      lineHeight: 1.6,
      marginBottom: "26px",
    },
    tabs: {
      display: "flex",
      padding: "5px",
      borderRadius: "12px",
      background: "#f0f5f8",
      marginBottom: "25px",
      gap: "5px",
    },
    field: {
      display: "block",
      marginBottom: "19px",
      color: "#344563",
      fontSize: "13px",
      fontWeight: 700,
    },
    input: {
      display: "block",
      boxSizing: "border-box",
      width: "100%",
      marginTop: "8px",
      padding: "14px 15px",
      border: "1px solid #dce5ec",
      borderRadius: "10px",
      outlineColor: "#078b91",
      background: "#fbfdff",
      color: "#172b4d",
      fontSize: "15px",
    },
    primaryButton: {
      width: "100%",
      padding: "15px",
      border: "none",
      borderRadius: "11px",
      background: "linear-gradient(100deg, #087f8c, #06a69a)",
      color: "#ffffff",
      fontSize: "15px",
      fontWeight: 800,
      cursor: "pointer",
      marginTop: "5px",
    },
    secondaryButton: {
      flex: 1,
      padding: "11px 8px",
      border: "none",
      borderRadius: "9px",
      fontSize: "14px",
      fontWeight: 700,
      cursor: "pointer",
    },
    error: {
      background: "#fff0f0",
      color: "#b42318",
      border: "1px solid #ffd4d4",
      padding: "12px",
      borderRadius: "9px",
      fontSize: "13px",
      lineHeight: 1.5,
      marginBottom: "16px",
    },
    footer: {
      marginTop: "24px",
      textAlign: "center",
      color: "#8492a6",
      fontSize: "12px",
    },
  };

  const isLogin = mode === "login";

  return (
    <main style={styles.page}>
      <section style={styles.card}>
        <div style={{ ...styles.panel, ...styles.brandPanel }}>
          <div>
            <div style={styles.logo}>
              <span style={styles.logoIcon}>+</span>
              <span>Pulsecare</span>
            </div>

            <div style={{ marginTop: "65px" }}>
              <div style={styles.eyebrow}>YOUR HEALTH, CONNECTED</div>
              <h1 style={styles.heading}>
                Take control of your health journey.
              </h1>
              <p style={styles.description}>
                Your personal space to stay informed, monitor
                your health, and build healthier habits.
              </p>
            </div>

            <div style={styles.features}>
              <div style={styles.feature}>
                <span style={styles.featureIcon}>♥</span>
                <span>Personal health monitoring</span>
              </div>
              <div style={styles.feature}>
                <span style={styles.featureIcon}>✓</span>
                <span>Your health information in one place</span>
              </div>
              <div style={styles.feature}>
                <span style={styles.featureIcon}>↗</span>
                <span>Make informed health decisions</span>
              </div>
            </div>
          </div>

          <p style={{ ...styles.description, fontSize: "12px" }}>
            Your wellbeing matters. Every single day.
          </p>
        </div>

        <div style={{ ...styles.panel, ...styles.formPanel }}>
          <div style={styles.eyebrow && { ...styles.eyebrow, color: "#078b91" }}>
            WELCOME TO PULSECARE
          </div>

          <h2 style={styles.formHeading}>
            {isLogin ? "Welcome back!" : "Create your account"}
          </h2>

          <p style={styles.subtext}>
            {isLogin
              ? "Sign in to access your personal health workspace."
              : "Join Pulsecare to get started with your health workspace."}
          </p>

          <div style={styles.tabs}>
            <button
              type="button"
              onClick={() => {
                setMode("login");
                setMessage("");
              }}
              style={{
                ...styles.secondaryButton,
                background: isLogin ? "#ffffff" : "transparent",
                color: isLogin ? "#087f8c" : "#718096",
                boxShadow: isLogin
                  ? "0 2px 8px rgba(20, 50, 70, 0.08)"
                  : "none",
              }}
            >
              Sign in
            </button>

            <button
              type="button"
              onClick={() => {
                setMode("register");
                setMessage("");
              }}
              style={{
                ...styles.secondaryButton,
                background: !isLogin ? "#ffffff" : "transparent",
                color: !isLogin ? "#087f8c" : "#718096",
                boxShadow: !isLogin
                  ? "0 2px 8px rgba(20, 50, 70, 0.08)"
                  : "none",
              }}
            >
              Register
            </button>
          </div>

          <form onSubmit={submit}>
            <label style={styles.field}>
              Username
              <input
                style={styles.input}
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="Enter your username"
                minLength={3}
                maxLength={50}
                autoComplete="username"
                required
              />
            </label>

            <label style={styles.field}>
              Password
              <div style={{ position: "relative" }}>
                <input
                  style={{ ...styles.input, paddingRight: "75px" }}
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Enter your password"
                  minLength={8}
                  maxLength={128}
                  autoComplete={
                    isLogin ? "current-password" : "new-password"
                  }
                  required
                />

                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: "absolute",
                    right: "10px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    border: "none",
                    background: "transparent",
                    color: "#087f8c",
                    fontSize: "12px",
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </label>

            {message && (
              <p role="alert" style={styles.error}>
                {message}
              </p>
            )}

            <button
              type="submit"
              disabled={busy}
              style={{
                ...styles.primaryButton,
                opacity: busy ? 0.7 : 1,
                cursor: busy ? "wait" : "pointer",
              }}
            >
              {busy
                ? "Please wait..."
                : isLogin
                  ? "Sign in to Pulsecare →"
                  : "Create account →"}
            </button>
          </form>

          <div style={styles.footer}>
            Secure access to your personal health workspace
          </div>
        </div>
      </section>
    </main>
  );
}
