import { Link } from "react-router-dom";

function Wave({ count = 42 }) {
  return (
    <div className="wave" aria-hidden="true">
      {Array.from({ length: count }, (_, i) => (
        <span
          key={i}
          style={{ height: `${15 + ((i * 17) % 75)}%` }}
        />
      ))}
    </div>
  );
}

function Metric({ name, color }) {
  return (
    <div className="meter">
      <span className="name">{name}</span>
      <span className="track">
        <span className={`fill ${color}`} style={{ width: "0%" }} />
      </span>
      <span className="val">0.00</span>
    </div>
  );
}

export default function LandingPage() {
  return (
    <>
      <header className="site-header">
        <div className="wrap">
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

          <nav className="nav" aria-label="Main">
            <a href="#how">How it works</a>
            <a href="#signals">What it reads</a>
            <a href="#difference">The difference</a>
          </nav>

          <div className="header-actions">
            <Link className="link" to="/login">Log in</Link>
            <Link className="btn btn-primary btn-sm" to="/signup">
              Sign up
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="hero">
          <div className="wrap">
            <div>
              <h1>Voice AI that hears how you say it.</h1>
              <p className="lead">
                HSIF reads hesitation, confidence and emotion in a person's
                voice, then tells the assistant how to reply before the
                language model answers.
              </p>
              <div className="actions">
                <Link className="btn btn-primary" to="/signup">
                  Try the live demo
                </Link>
                <a className="btn btn-ghost" href="#how">
                  See how it works
                </a>
              </div>
            </div>

            <div
              className="readout"
              id="demo-readout"
              role="group"
              aria-label="Example of HSIF reading a voice"
            >
              <div className="readout-top">
                <span className="live-dot">Example session</span>
              </div>

              <Wave />

              <p className="transcript">
                "I think I understand, but I'm not entirely sure."
              </p>

              <div className="chips">
                <span className="chip">Emotion: Calm</span>
                <span className="chip strategy">Strategy: Clarify</span>
              </div>

              <div className="meters">
                <Metric name="Confidence" color="teal" />
                <Metric name="Hesitation" color="amber" />
                <Metric name="Engagement" color="violet" />
                <Metric name="Cognitive load" color="coral" />
              </div>
            </div>
          </div>
        </section>

        <section id="how" className="band">
          <div className="wrap">
            <div className="section-head">
              <h2>One extra step between speech and the language model</h2>
              <p>
                Most voice assistants send words straight to the model.
                HSIF adds a layer that understands the speaker first.
              </p>
            </div>

            <ol className="steps">
              <li>
                <h3>Listen</h3>
                <p>
                  Voice activity detection finds speech, and Whisper turns
                  it into a transcript.
                </p>
              </li>
              <li>
                <h3>Read the human state</h3>
                <p>
                  Emotion, hesitation, confidence and more are combined
                  into one Human State Representation.
                </p>
              </li>
              <li>
                <h3>Choose a strategy</h3>
                <p>
                  The dialogue policy decides how to respond, such as
                  clarify, reassure or continue.
                </p>
              </li>
              <li>
                <h3>Reply</h3>
                <p>
                  The language model answers with that strategy, so the
                  reply fits the person.
                </p>
              </li>
            </ol>
          </div>
        </section>

        <section id="signals">
          <div className="wrap">
            <div className="section-head">
              <h2>Seven signals, read in real time</h2>
              <p>
                Each one is scored from the speaker's voice and words,
                and updated as the conversation moves.
              </p>
            </div>

            <dl className="signals">
              <div>
                <span className="dot" style={{ background: "var(--coral)" }} />
                <dt>Emotion</dt>
                <dd>How the speaker feels, such as calm, confused or frustrated.</dd>
              </div>
              <div>
                <span className="dot" style={{ background: "var(--amber)" }} />
                <dt>Hesitation</dt>
                <dd>Pauses, filler words and restarts that show doubt.</dd>
              </div>
              <div>
                <span className="dot" style={{ background: "var(--teal)" }} />
                <dt>Confidence</dt>
                <dd>How sure the speaker sounds about what they are saying.</dd>
              </div>
              <div>
                <span className="dot" style={{ background: "var(--violet)" }} />
                <dt>Engagement</dt>
                <dd>Whether the speaker is following along and taking part.</dd>
              </div>
              <div>
                <span className="dot" style={{ background: "var(--coral)" }} />
                <dt>Cognitive load</dt>
                <dd>How hard the speaker is working to keep up.</dd>
              </div>
              <div>
                <span className="dot" style={{ background: "var(--teal)" }} />
                <dt>Intent continuation</dt>
                <dd>Whether the speaker has more to say or has finished.</dd>
              </div>
              <div>
                <span className="dot" style={{ background: "var(--violet)" }} />
                <dt>Interruptibility</dt>
                <dd>Whether now is a good moment for the assistant to speak.</dd>
              </div>
            </dl>
          </div>
        </section>

        <section id="difference" className="band">
          <div className="wrap">
            <div className="section-head">
              <h2>Same words, a better reply</h2>
              <p>
                A learner says, “I don't understand this concept...” in a
                slow, hesitant voice.
              </p>
            </div>

            <div className="compare">
              <div className="reply">
                <h3>Without HSIF</h3>
                <p className="said">The assistant only sees the text.</p>
                <blockquote>
                  “A concept is an abstract idea. Here are the three main
                  types, with definitions for each...”
                </blockquote>
              </div>

              <div className="reply with">
                <h3>With HSIF</h3>
                <p className="said">
                  Hesitation 0.81, confidence 0.42. Strategy: clarify.
                </p>
                <blockquote>
                  “Let's slow down. Which part feels unclear: the term
                  itself, or how it is used?”
                </blockquote>
              </div>
            </div>
          </div>
        </section>

        <section className="cta">
          <div className="wrap">
            <h2>Start a session and watch the assistant adapt.</h2>
            <div className="actions">
              <Link className="btn btn-primary" to="/signup">
                Create an account
              </Link>
              <Link className="btn btn-ghost" to="/login">
                Log in
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="wrap">
          <span>HSIF · Human State Intelligence Framework for Conversational AI</span>
          <nav aria-label="Footer">
            <a href="#how">How it works</a>
            <Link to="/login">Log in</Link>
            <Link to="/signup">Sign up</Link>
          </nav>
        </div>
      </footer>
    </>
  );
}