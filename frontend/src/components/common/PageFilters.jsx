import {useContext} from 'react';
import {createPortal} from 'react-dom';
import {PageChromeContext} from '../../contexts/PageChromeContext';

export default function PageFilters({label='Filtros da página',children}){
  const chrome=useContext(PageChromeContext);
  const filters=<section className="page-filters" aria-label={label}>{children}</section>;
  return chrome?.filters?createPortal(filters,chrome.filters):filters;
}
