function Metric({ label, value, color }) {
  const raw = typeof value === "object" && value !== null
    ? value.score
    : value;
  const number = raw == null ? null : Number(raw);
  const validNumber = Number.isFinite(number);
  const percentage = validNumber
    ? Math.max(0, Math.min(100, number * 100))
    : 0;

  return (
    <div className="meter">
      <span className="name">{label}</span>
      <span className="track">
        <span
          className={`fill ${color}`}
          style={{ width: `${percentage}%` }}
        />
      </span>
      <span className="val">
        {validNumber ? number.toFixed(2) : "–"}
      </span>
    </div>
  );
}

export default function HumanStatePanel({ state }) {
  const observationValid = state?._temporal?.observation_valid !== false;
  const emotion = observationValid
    ? state?.emotion?.label || state?.emotion || "–"
    : "Not measured";

  return (
    <>
      <div className="chips">
        <span
          className="chip"
          style={{ background: "#eceffa", color: "var(--ink)" }}
        >
          Emotion: {emotion}
        </span>
      </div>

      {observationValid ? (
        <div className="meters">
          <Metric label="Confidence" value={state?.confidence} color="teal" />
          <Metric label="Hesitation" value={state?.hesitation} color="amber" />
          <Metric label="Engagement" value={state?.engagement} color="violet" />
          <Metric label="Cognitive load" value={state?.cognitive_load} color="coral" />
        </div>
      ) : (
        <p className="desc" role="status">
          Emotion and human-state measurements are unavailable for this interaction.
        </p>
      )}
    </>
  );
}
