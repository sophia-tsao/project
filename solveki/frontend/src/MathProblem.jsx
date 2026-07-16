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
    } catch (err) {
      setError(err.message);
    }
  };
  useEffect(() => {
    fetchMathProblem();
  }, []);

  if (error) return <div>Error: {error}</div>;

  if (problem === null && solution === null) return null;

  if (problem === 'no_topics') {
    return (
      <div className="math-problem-card">
        <span className="math-problem-display">Select topics from the Courses page to get started.</span>
      </div>
    );
  }

  return (
    <div className="math-problem-card">
      <MathProblemDisplay problem={renderMixedLatex(problem)} />
      <MathProblemResponse solution={solution} genNext={fetchMathProblem} />
    </div>
  );
}

export default MathProblem;
