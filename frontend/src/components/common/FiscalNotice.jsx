import {Info} from 'lucide-react';
import {Link} from 'react-router-dom';
export default function FiscalNotice(){return <div className="environment-strip" role="note"><span><Info size={14}/>Demonstração · sem validade fiscal</span><Link to="/system">Sobre o ambiente</Link></div>;}
