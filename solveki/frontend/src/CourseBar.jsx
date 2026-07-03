import { useState, useEffect } from 'react';
import './CourseBar.css';

function CourseBar(props) {
    const [displayedTopics, setDisplayedTopics] = useState(props.topics);
    const isOpen = props.topics.length > 0;

    useEffect(() => {
        if (props.topics.length > 0) {
            setDisplayedTopics(props.topics);
        }
    }, [props.topics]);

    return (
        <div
            className={`course-bar${isOpen ? ' open' : ''}`}
            onClick={() => props.onItemClick(props.id)}
        >
            <div className="course-bar-header">
                <div className="course-bar-info">
                    <span className="course-bar-name">{props.courseName}</span>
                    <span className="course-bar-grade">Grade {props.gradeLevel}</span>
                </div>
                <svg className="course-bar-chevron" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
            </div>

            <div className="course-bar-topics">
                <div className="course-bar-topics-inner">
                    <ul>
                        {displayedTopics.map((topic, i) => (
                            <li key={i}>{topic}</li>
                        ))}
                    </ul>
                </div>
            </div>
        </div>
    );
}

export default CourseBar;
