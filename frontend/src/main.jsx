import React from 'react';
import {createRoot} from 'react-dom/client';
import {BrowserRouter} from 'react-router-dom';
import {AuthProvider} from './contexts/AuthContext';
import {UIProvider} from './contexts/UIContext';
import App from './App';
import './styles/tokens.css';
import './styles/app.css';
import './styles/enterprise.css';
import './styles/organization.css';
import './styles/accounts.css';
import './styles/automations.css';
import './styles/page-layout.css';
import './styles/scrollbars.css';
import './styles/pagination.css';
import './styles/page-filters.css';

createRoot(document.getElementById('root')).render(<React.StrictMode><BrowserRouter><UIProvider><AuthProvider><App/></AuthProvider></UIProvider></BrowserRouter></React.StrictMode>);
