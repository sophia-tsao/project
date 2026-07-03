import { useState, useEffect } from 'react';
import CourseList from './CourseList.jsx';
import MathProblem from './MathProblem.jsx';
import Header from './Header.jsx';
function App() {
  const [currentPage, setCurrentPage]=useState("math");
  function changeVisibility(page){
    if(page==="math"){
      setCurrentPage("math");
    }
    if(page==="courses"){
      setCurrentPage("courses");
    }
  }
  return(
    <div>
      <Header linkClicked={(page)=>changeVisibility(page)}/>
      <div style={{paddingTop: '32px'}}>
        {currentPage==="math" && <MathProblem />}
        {currentPage==="courses" && <CourseList />}
      </div>
    </div>
  );
}

export default App;
