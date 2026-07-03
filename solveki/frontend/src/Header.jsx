import { useState, useEffect } from 'react';
import './Header.css';

function Header(props) {
    return (
        <header className="header">
            <span className="header-logo">Solveki</span>
            <nav className="header-nav">
                <button onClick={() => props.linkClicked("math")}>Practice</button>
                <button onClick={() => props.linkClicked("courses")}>Available Courses</button>
            </nav>
        </header>
    );
}

export default Header;
