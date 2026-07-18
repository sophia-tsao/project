import { useState, useEffect } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import './MathProblem.css';
import MathProblemDisplay from './MathProblemDisplay.jsx'
import MathProblemResponse from './MathProblemResponse.jsx'

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

function MathProblem() {
  const [problem, setProblem] = useState(null);
  const [solution, setSolution] = useState(null);
  const [currentNumber, setCurrentNumber] = useState(null);
  const [total, setTotal] = useState(null);
  const [status, setStatus] = useState('loading'); // loading | active | no_topics | completed
  const [error, setError] = useState(null);
  const [showCorrect, setShowCorrect] = useState(false);
  const [attempt, setAttempt] = useState(1);
  const MAX_ATTEMPTS = 2;

  const applyDeck = (result) => {
    if (result.no_topics) {
      setStatus('no_topics');
      return;
    }
    if (result.completed) {
      setTotal(result.total ?? total);
      setStatus('completed');
      return;
    }
    setProblem(result.problem);
    setSolution(result.solution?.replace(/\$/g, ''));
    setCurrentNumber(result.current_number);
    setTotal(result.total);
    setAttempt(1);
    setStatus('active');
  };

  const fetchDeck = async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/deck/`);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      applyDeck(await response.json());
    } catch (err) {
      setError(err.message);
    }
  };

  const advanceDeck = async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/deck/advance/`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      applyDeck(await response.json());
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    fetchDeck();
  }, []);

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
      <div className="math-problem-card">
        <span className="math-problem-display">Select topics from the Courses page to get started.</span>
      </div>
    );
  }

  if (status === 'completed') {
    return (
      <div className="math-problem-card">
        <span className="math-problem-display">
          You've finished all {total} question{total === 1 ? '' : 's'} for today. Come back tomorrow for a new set!
        </span>
      </div>
    );
  }

  if (showCorrect) {
    return (
      <div className="math-problem-card math-problem-correct">
        <svg className="math-problem-correct-icon" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="11" stroke="#16a34a" strokeWidth="1.5" />
          <path d="M7 12.5l3.2 3.2L17 9" stroke="#16a34a" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="math-problem-correct-text">Correct!</span>
      </div>
    );
  }

  return (
    <div className="math-problem-card">
      <div className="math-problem-meta">
        <span className="math-problem-progress">{currentNumber} of {total} questions</span>
        <span className="math-problem-attempt">Attempt {attempt} of {MAX_ATTEMPTS}</span>
      </div>
      <MathProblemDisplay problem={renderMixedLatex(problem)} />
      <MathProblemResponse solution={solution} onCorrect={handleCorrect} onIncorrect={handleIncorrect} />
    </div>
  );
}

export default MathProblem;
