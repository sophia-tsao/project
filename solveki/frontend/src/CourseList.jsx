import { useState, useEffect } from 'react';
import CourseBar from './CourseBar.jsx'
function CourseList() {
  const [courses, setCourses] = useState([]);
  const [topicsMap, setTopicsMap] = useState({});
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const response = await fetch('/courses/');
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const result = await response.json();
        console.log('result', result);
        setCourses(result.courses);
      } catch (err) {
        setError(err.message);
      }
    };
    fetchCourses();
  }, []);

  console.log('Render courses', courses);
  const handleCourseBarClick = (courseID) =>{
    const fetchTopics = async () => {
        try{
            const response = await fetch(`/courses/${courseID}/topics`)
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const result = await response.json();
            console.log('result', result);
            setTopicsMap(prev => ({ ...prev, [courseID]: result.topics.map(t => t.topic_name) }));
            console.log('topicsMap', topicsMap);
            console.log('key', topicsMap[courseID]);
            console.log('value', result.topics.topic_name);
        } catch (err) {
            setError(err.message);
        }
    }
    if(courseID in topicsMap && topicsMap[courseID].length>0){
        setTopicsMap(prev => ({ ...prev, [courseID]: [] }));
        console.log('set empty', topicsMap);
    }else{
        fetchTopics();
    }
  }
  return (
    <div>
      {error && <p>Error: {error}</p>}
      {courses.map((course) => (
        <CourseBar key={course.id} id={course.id} courseName={course.course_name} gradeLevel={course.grade_level} onItemClick={()=>handleCourseBarClick(course.id)} topics={topicsMap[course.id] ?? []} />
      ))}
    </div>
  );
}

export default CourseList;