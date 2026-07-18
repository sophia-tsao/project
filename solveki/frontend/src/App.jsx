import { useState, useEffect } from 'react';
import CourseList from './CourseList.jsx';
import MathProblem from './MathProblem.jsx';
import Header from './Header.jsx';
import Settings from './Settings.jsx';
function App() {
  const [currentPage, setCurrentPage]=useState("math");
  function changeVisibility(page){
    if(page==="math" || page==="courses" || page==="settings"){
      setCurrentPage(page);
    }
  }
  return(
    <div>
      <Header linkClicked={(page)=>changeVisibility(page)}/>
      <div style={{paddingTop: '32px'}}>
        {currentPage==="math" && <MathProblem />}
        {currentPage==="courses" && <CourseList />}
        {currentPage==="settings" && <Settings />}
      </div>
    </div>
  );
}

export default App;
