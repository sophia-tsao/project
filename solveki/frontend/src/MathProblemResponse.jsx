import { useState, useEffect } from 'react';

function MathProblemResponse(props) {
    const [response, setResponse] = useState("");
    const [boxColor, setBoxColor] = useState('black');
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
            props.genNext();
        }else{
            console.log('incorrect response');
            console.log(props.solution);
            setBoxColor('red');
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
            <button className="math-problem-submit" onClick={submitResponse}>
                Submit
            </button>
        </div>
    );
}

export default MathProblemResponse;
