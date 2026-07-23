import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import './MathProblem.css';
import MathProblemDisplay from './MathProblemDisplay.jsx'
import MathProblemResponse from './MathProblemResponse.jsx'
import { apiFetch, localDay } from './auth.js';
import { createLogger } from './logger.js';

const log = createLogger('deck');

function InlineMath({ math }) {
  const html = katex.renderToString(math, { throwOnError: false });
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

function renderMixedLatex(str) {
  if (!str) return null;
  return str.split('$').map((segment, i) =>
    i % 2 === 1
      ? <InlineMath key={i} math={segment} />
      : segment
  );
}

const CONFETTI_COLORS = ['#2563eb', '#16a34a', '#f59e0b', '#ec4899', '#8b5cf6'];

function Confetti() {
  // Generate the pieces once so they don't reshuffle on re-render.
  const pieces = useMemo(
    () =>
      Array.from({ length: 60 }, (_, i) => ({
        id: i,
        left: Math.random() * 100,
        delay: Math.random() * 0.5,
        duration: 1.8 + Math.random() * 1.2,
        color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
        rotate: Math.random() * 360,
        drift: (Math.random() - 0.5) * 80,
      })),
    []
  );
  return (
    <div className="confetti" aria-hidden="true">
      {pieces.map((p) => (
        <span
          key={p.id}
          className="confetti-piece"
          style={{
            left: `${p.left}%`,
            backgroundColor: p.color,
            animationDelay: `${p.delay}s`,
            animationDuration: `${p.duration}s`,
            '--confetti-rotate': `${p.rotate}deg`,
            '--confetti-drift': `${p.drift}px`,
          }}
        />
      ))}
    </div>
  );
}

function MathProblem() {
  const [problem, setProblem] = useState(null);
  const [topicName, setTopicName] = useState(null);
  const [solution, setSolution] = useState(null);
  const [currentNumber, setCurrentNumber] = useState(null);
  const [total, setTotal] = useState(null);
  const [status, setStatus] = useState('loading'); // loading | active | no_topics | completed
  const [error, setError] = useState(null);
  const [flipped, setFlipped] = useState(false); // true rotates the card to its back
  const [result, setResult] = useState('correct'); // 'correct' | 'incorrect' — back-face content
  const [resultAnswer, setResultAnswer] = useState(null); // solution frozen for the back face
  const [attempt, setAttempt] = useState(1);
  const [showConfetti, setShowConfetti] = useState(false);
  const MAX_ATTEMPTS = 2;

  // Fire confetti. Celebration is gated entirely by the `celebrate` flag below
  // (see applyDeck), not by a per-day token: a student who finishes their deck,
  // raises their questions-per-day, and finishes the new cards should be
  // celebrated each time they genuinely complete the deck — even twice in a day.
  const celebrate = useCallback(() => {
    setShowConfetti(true);
    setTimeout(() => setShowConfetti(false), 3500);
  }, []);

  // `celebrate` gates the confetti: only the genuine finish transition (the
  // student answering the last card, via advanceDeck) should fire it. A passive
  // load that happens to land on an already-completed deck — the mount fetch,
  // the day-rollover refetch on refocus, a reload of the completed screen, or a
  // topic change — must not, so reopening a finished deck stays quiet.
  const applyDeck = useCallback((result, { celebrating = false } = {}) => {
    if (result.no_topics) {
      log.debug('Deck has no selected topics');
      setStatus('no_topics');
      return;
    }
    if (result.completed) {
      // Fall back to the last known total when the payload omits it.
      setTotal((prev) => result.total ?? prev);
      setStatus('completed');
      log.info('Deck completed');
      if (celebrating) celebrate();
      return;
    }
    log.debug(`Showing question ${result.current_number} of ${result.total}`);
    setProblem(result.problem);
    setTopicName(result.topic_name ?? null);
    setSolution(result.solution?.replace(/\$/g, ''));
    setCurrentNumber(result.current_number);
    setTotal(result.total);
    setAttempt(1);
    setFlipped(false);
    setStatus('active');
  }, [celebrate]);

  const fetchDeck = useCallback(async () => {
    try {
      // Pass the client's local day so the deck resets at the user's midnight,
      // not the server's UTC midnight (the backend clock runs in UTC).
      const response = await apiFetch(`/deck/?today=${localDay()}`);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      applyDeck(await response.json());
    } catch (err) {
      log.error('Failed to load deck:', err.message);
      setError(err.message);
    }
  }, [applyDeck]);

  // `outcome` reports how the card being left was answered ('correct_first' |
  // 'correct_second' | 'incorrect') so the backend can update that topic's
  // spaced-repetition schedule. Omitted for a stray advance with no answer
  // (e.g. the midnight day-rollover advance), which must not grade anything.
  // `fromNumber` is the 1-based card the advance is leaving, captured at the
  // moment the advance is initiated (a click, or when a timer is scheduled).
  // The backend ignores an advance whose `from_number` no longer matches the
  // card it's showing, so a stray leftover timer — e.g. the correct-answer
  // timer from finishing yesterday's last card, firing after the deck has
  // rolled over to today's card 1 — can't step the fresh deck past card 1.
  const advanceDeck = useCallback(async (outcome, fromNumber) => {
    try {
      const body = {};
      if (typeof outcome === 'string') body.outcome = outcome;
      if (typeof fromNumber === 'number') body.from_number = fromNumber;
      const response = await apiFetch(`/deck/advance/?today=${localDay()}`, {
        method: 'POST',
        ...(Object.keys(body).length ? { body: JSON.stringify(body) } : {}),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      // Reaching `completed` here means the student just answered the last
      // card — the one moment worth celebrating.
      applyDeck(await response.json(), { celebrating: true });
    } catch (err) {
      log.error('Failed to advance deck:', err.message);
      setError(err.message);
    }
  }, [applyDeck]);

  // Load the deck on mount, and remember which local day it was built for.
  const loadedDay = useRef(localDay());
  useEffect(() => {
    loadedDay.current = localDay();
    fetchDeck();
  }, [fetchDeck]);

  // The deck resets at the start of each day, but the SPA can sit open across
  // midnight (a student leaves the tab up overnight). Fetching only on mount
  // would leave them staring at yesterday's deck — usually the "come back
  // tomorrow" completion screen. Reload when the local day has rolled over so
  // the backend can hand back the fresh deck it already builds for the new day.
  //
  // Three triggers, because no single one covers every case: refocus and
  // visibility handle a tab that was backgrounded across midnight, and a
  // periodic timer handles a tab that stays focused the whole time (e.g. left
  // open on-screen), which would otherwise never re-check and keep showing
  // yesterday's card.
  useEffect(() => {
    const reloadIfNewDay = () => {
      const today = localDay();
      if (today !== loadedDay.current) {
        log.info('Local day rolled over; reloading deck for the new day');
        loadedDay.current = today;
        fetchDeck();
      }
    };
    const onVisible = () => {
      if (document.visibilityState === 'visible') reloadIfNewDay();
    };
    window.addEventListener('focus', reloadIfNewDay);
    document.addEventListener('visibilitychange', onVisible);
    // Catch a rollover even while the tab stays focused and untouched. A minute
    // is plenty prompt for a day boundary and negligible overhead.
    const interval = setInterval(reloadIfNewDay, 60 * 1000);
    return () => {
      window.removeEventListener('focus', reloadIfNewDay);
      document.removeEventListener('visibilitychange', onVisible);
      clearInterval(interval);
    };
  }, [fetchDeck]);

  // Flip the card to reveal the result on its back, then advance once the
  // student has had a beat to read it. advanceDeck() sets `flipped` back to
  // false, flipping the fresh problem to its front. We deliberately leave
  // `result` untouched on the flip back so the back face doesn't flash the
  // other outcome while it rotates out of view.
  const handleCorrect = () => {
    // A first-attempt correct answer grades higher than a second-attempt one.
    const outcome = attempt === 1 ? 'correct_first' : 'correct_second';
    // Capture the card being answered *now*, so if this timer somehow fires
    // after a day-rollover reload, its stale from_number won't match the fresh
    // deck and the backend will ignore it (leaving the student on card 1).
    const from = currentNumber;
    setResult('correct');
    setFlipped(true);
    setTimeout(() => advanceDeck(outcome, from), 1400);
  };

  const handleIncorrect = () => {
    if (attempt < MAX_ATTEMPTS) {
      setAttempt(attempt + 1);
    } else {
      // Out of attempts: flip to show the correct answer. Unlike the correct
      // face (which auto-advances), the incorrect face waits for the student to
      // act — either accepting the miss ("Continue") or overriding it ("I got
      // this correct") if the answer box wrongly marked a correct answer wrong.
      // A timed auto-advance would give no time to read the answer or override.
      // Freeze the answer on the back face so it isn't replaced by the next
      // problem's solution while the card rotates back to the front.
      setResult('incorrect');
      setResultAnswer(solution);
      setFlipped(true);
    }
  };

  // From the incorrect back face: accept the miss and move on.
  const handleAcceptIncorrect = () => advanceDeck('incorrect', currentNumber);

  // From the incorrect back face: the student says the answer box wrongly
  // marked them wrong. Override to a clean correct grade (full credit).
  const handleOverrideCorrect = () => {
    log.info('Student overrode an incorrect grade to correct');
    setResult('correct');
    advanceDeck('correct_first', currentNumber);
  };

  if (error) return <div>Error: {error}</div>;

  if (status === 'loading') return null;

  if (status === 'no_topics') {
    return (
      <div className="math-problem-card math-problem-card-centered">
        <span className="math-problem-display">Select topics from the Courses page to get started.</span>
      </div>
    );
  }

  if (status === 'completed') {
    return (
      <div className="math-problem-stack">
        {showConfetti && <Confetti />}
        <div className="math-problem-card math-problem-card-centered">
          <span className="math-problem-display">
            You've finished all {total} question{total === 1 ? '' : 's'} for today. Come back tomorrow for a new set!
          </span>
        </div>
      </div>
    );
  }

  // Cards still remaining after the current one, capped at 3 so the stack
  // stays tidy. Shrinks as the user nears the end of the deck.
  const behindCount = Math.min(3, Math.max(0, total - currentNumber));
  const behindCards = Array.from({ length: behindCount }, (_, i) => (
    <div key={i} className={`math-problem-card math-problem-card-behind behind-${i + 1}`} />
  ));

  return (
    <div className="math-problem-stack">
      {behindCards}
      {/* The flipper rotates 180° to reveal the back face (the result) when
          `flip` is set. Front holds the problem; back holds the outcome. */}
      <div className={`math-problem-flipper${flipped ? ' flipped' : ''}`}>
        <div className="math-problem-card math-problem-face math-problem-face-front">
          <div className="math-problem-meta">
            <span className="math-problem-progress">{currentNumber} of {total} questions</span>
            <span className="math-problem-attempt">Attempt {attempt} of {MAX_ATTEMPTS}</span>
          </div>
          {topicName && <span className="math-problem-topic">{topicName}</span>}
          <MathProblemDisplay problem={renderMixedLatex(problem)} />
          <MathProblemResponse solution={solution} onCorrect={handleCorrect} onIncorrect={handleIncorrect} />
        </div>
        <div
          className={`math-problem-card math-problem-face math-problem-face-back ${
            result === 'incorrect' ? 'math-problem-incorrect' : 'math-problem-correct'
          }`}
        >
          {result === 'incorrect' ? (
            <>
              <svg className="math-problem-result-icon" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="11" stroke="#dc2626" strokeWidth="1.5" />
                <path d="M8 8l8 8M16 8l-8 8" stroke="#dc2626" strokeWidth="1.75" strokeLinecap="round" />
              </svg>
              <span className="math-problem-incorrect-text">Incorrect...</span>
              <span className="math-problem-answer">The answer is {resultAnswer}</span>
              <div className="math-problem-back-actions">
                <button
                  className="math-problem-back-button math-problem-back-continue"
                  onClick={handleAcceptIncorrect}
                >
                  Continue
                </button>
                <button
                  className="math-problem-back-button math-problem-back-override"
                  onClick={handleOverrideCorrect}
                >
                  I got this correct
                </button>
              </div>
            </>
          ) : (
            <>
              <svg className="math-problem-result-icon" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="11" stroke="#16a34a" strokeWidth="1.5" />
                <path d="M7 12.5l3.2 3.2L17 9" stroke="#16a34a" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span className="math-problem-correct-text">Correct!</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default MathProblem;
