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
      const response = await fetch('/problem/');
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const result = await response.json();
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

  return (
    <div className="math-problem-card">
      <MathProblemDisplay problem={renderMixedLatex(problem)} />
      <MathProblemResponse solution={solution} genNext={fetchMathProblem} />
    </div>
  );
}

export default MathProblem;
