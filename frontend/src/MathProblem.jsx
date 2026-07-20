import { useState, useEffect, useMemo, useCallback } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import './MathProblem.css';
import MathProblemDisplay from './MathProblemDisplay.jsx'
import MathProblemResponse from './MathProblemResponse.jsx'
import { apiFetch } from './auth.js';
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
  const [solution, setSolution] = useState(null);
  const [currentNumber, setCurrentNumber] = useState(null);
  const [total, setTotal] = useState(null);
  const [status, setStatus] = useState('loading'); // loading | active | no_topics | completed
  const [error, setError] = useState(null);
  const [showCorrect, setShowCorrect] = useState(false);
  const [attempt, setAttempt] = useState(1);
  const [showConfetti, setShowConfetti] = useState(false);
  const MAX_ATTEMPTS = 2;

  // Fire confetti at most once per day, the first time the deck is completed.
  const maybeCelebrate = useCallback(() => {
    const key = `solveki-confetti-${new Date().toLocaleDateString('en-CA')}`;
    if (localStorage.getItem(key)) return;
    localStorage.setItem(key, '1');
    setShowConfetti(true);
    setTimeout(() => setShowConfetti(false), 3500);
  }, []);

  const applyDeck = useCallback((result) => {
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
      maybeCelebrate();
      return;
    }
    log.debug(`Showing question ${result.current_number} of ${result.total}`);
    setProblem(result.problem);
    setSolution(result.solution?.replace(/\$/g, ''));
    setCurrentNumber(result.current_number);
    setTotal(result.total);
    setAttempt(1);
    setStatus('active');
  }, [maybeCelebrate]);

  const fetchDeck = useCallback(async () => {
    try {
      const response = await apiFetch(`/deck/`);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      applyDeck(await response.json());
    } catch (err) {
      log.error('Failed to load deck:', err.message);
      setError(err.message);
    }
  }, [applyDeck]);

  const advanceDeck = useCallback(async () => {
    try {
      const response = await apiFetch(`/deck/advance/`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      applyDeck(await response.json());
    } catch (err) {
      log.error('Failed to advance deck:', err.message);
      setError(err.message);
    }
  }, [applyDeck]);

  // Load the deck once on mount.
  useEffect(() => {
    fetchDeck();
  }, [fetchDeck]);

  const handleCorrect = () => {
    setShowCorrect(true);
    setTimeout(() => {
      advanceDeck();
      setShowCorrect(false);
    }, 900);
  };

  const handleIncorrect = () => {
    if (attempt < MAX_ATTEMPTS) {
      setAttempt(attempt + 1);
    } else {
      // Out of attempts: move on to the next problem.
      advanceDeck();
    }
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

  if (showCorrect) {
    return (
      <div className="math-problem-stack">
        {behindCards}
        <div className="math-problem-card math-problem-correct">
          <svg className="math-problem-correct-icon" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="11" stroke="#16a34a" strokeWidth="1.5" />
            <path d="M7 12.5l3.2 3.2L17 9" stroke="#16a34a" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="math-problem-correct-text">Correct!</span>
        </div>
      </div>
    );
  }

  return (
    <div className="math-problem-stack">
      {behindCards}
      <div className="math-problem-card">
        <div className="math-problem-meta">
          <span className="math-problem-progress">{currentNumber} of {total} questions</span>
          <span className="math-problem-attempt">Attempt {attempt} of {MAX_ATTEMPTS}</span>
        </div>
        <MathProblemDisplay problem={renderMixedLatex(problem)} />
        <MathProblemResponse solution={solution} onCorrect={handleCorrect} onIncorrect={handleIncorrect} />
      </div>
    </div>
  );
}

export default MathProblem;
