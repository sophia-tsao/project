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
  const [error, setError] = useState(null);
  const [showCorrect, setShowCorrect] = useState(false);
  const [attempt, setAttempt] = useState(1);
  const MAX_ATTEMPTS = 2;
  const fetchMathProblem = async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/problem/`);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const result = await response.json();
      if (result.no_topics) {
        setProblem('no_topics');
        setSolution(null);
        return;
      }
      setProblem(result.problem);
      setSolution(result.solution?.replace(/\$/g, ''));
      setAttempt(1);
    } catch (err) {
      setError(err.message);
    }
  };
  useEffect(() => {
    fetchMathProblem();
  }, []);

  const handleCorrect = () => {
    setShowCorrect(true);
    setTimeout(() => {
      fetchMathProblem();
      setShowCorrect(false);
    }, 900);
  };

  const handleIncorrect = () => {
    if (attempt < MAX_ATTEMPTS) {
      setAttempt(attempt + 1);
    } else {
      // Out of attempts: move on to the next problem.
      fetchMathProblem();
    }
  };

  if (error) return <div>Error: {error}</div>;

  if (problem === null && solution === null) return null;

  if (problem === 'no_topics') {
    return (
      <div className="math-problem-card">
        <span className="math-problem-display">Select topics from the Courses page to get started.</span>
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
      <span className="math-problem-attempt">Attempt {attempt} of {MAX_ATTEMPTS}</span>
      <MathProblemDisplay problem={renderMixedLatex(problem)} />
      <MathProblemResponse solution={solution} onCorrect={handleCorrect} onIncorrect={handleIncorrect} />
    </div>
  );
}

export default MathProblem;
