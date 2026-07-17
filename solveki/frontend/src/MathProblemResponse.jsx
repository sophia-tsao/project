import { useState, useEffect } from 'react';

function MathProblemResponse(props) {
    const [response, setResponse] = useState("");
    const [boxColor, setBoxColor] = useState('black');
    const [showIncorrect, setShowIncorrect] = useState(false);
    function updateResponse(event) {
        setResponse(event.target.value);
    }
    function submitResponse() {
        const numResponse = parseFloat(response);
        const numSolution = parseFloat(props.solution);
        const isCorrect = response === props.solution ||
            (!isNaN(numResponse) && !isNaN(numSolution) && numResponse === numSolution);
        if(isCorrect){
            console.log('correct response');
            setResponse("");
            setBoxColor('black');
            props.onCorrect();
        }else{
            console.log('incorrect response');
            console.log(props.solution);
            setBoxColor('red');
            setShowIncorrect(true);
            setTimeout(() => setShowIncorrect(false), 900);
        }
    }
    function inputKeyPress(event){
        if(event.key==="Enter"){
            submitResponse();
        }
    }
    return (
        <div style={{width: '100%', display: 'flex', gap: '8px'}}>
            <input
                className={`math-problem-input${boxColor === 'red' ? ' incorrect' : ''}`}
                value={response}
                onChange={updateResponse}
                onKeyPress={inputKeyPress}
            />
            <button
                className={`math-problem-submit${showIncorrect ? ' math-problem-submit-incorrect' : ''}`}
                onClick={submitResponse}
            >
                {showIncorrect ? 'Incorrect!' : 'Submit'}
            </button>
        </div>
    );
}

export default MathProblemResponse;
