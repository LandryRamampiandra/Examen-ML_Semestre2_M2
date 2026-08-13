import { useCallback, useEffect, useState } from 'react';
import './App.css';

const API_BASE = 'http://localhost:8000';

const initialRegister = {
  nom: '',
  email: '',
  mot_de_passe: '',
};

function App() {
  const [token, setToken] = useState('');
  const [user, setUser] = useState(null);
  const [health, setHealth] = useState({ statut: 'inconnu' });
  const [tickets, setTickets] = useState([]);
  const [pendingTickets, setPendingTickets] = useState([]);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [ticketText, setTicketText] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');

  const [loginData, setLoginData] = useState({
    email: 'admin@example.com',
    password: 'admin123',
  });
  const [registerData, setRegisterData] = useState(initialRegister);
  const [loading, setLoading] = useState({ login: false, register: false, ticket: false, tickets: false });

  const apiRequest = useCallback(async (path, options = {}, isProtected = false) => {
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    };

    if (isProtected) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    const contentType = response.headers.get('content-type') || '';
    const payload = contentType.includes('application/json') ? await response.json() : await response.text();

    if (!response.ok) {
      throw new Error(typeof payload === 'string' ? payload : payload.detail || 'Erreur backend');
    }

    return payload;
  }, [token]);

  const loadDashboard = useCallback(async () => {
    if (!token) return;

    setLoading((prev) => ({ ...prev, tickets: true }));
    try {
      const [healthData, meData, ticketList, pendingList] = await Promise.all([
        apiRequest('/health'),
        apiRequest('/auth/me', {}, true),
        apiRequest('/tickets', {}, true),
        apiRequest('/tickets-en-attente', {}, true),
      ]);

      setHealth(healthData);
      setUser(meData);
      setTickets(ticketList || []);
      setPendingTickets(pendingList || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading((prev) => ({ ...prev, tickets: false }));
    }
  }, [token]);

  useEffect(() => {
    if (!token) {
      setUser(null);
      setTickets([]);
      setPendingTickets([]);
      setSelectedTicket(null);
      setResult(null);
      return;
    }

    loadDashboard();
  }, [token, loadDashboard]);

  async function handleLogin(event) {
    event.preventDefault();
    setError('');
    setInfo('');
    setLoading((prev) => ({ ...prev, login: true }));

    try {
      const params = new URLSearchParams();
      params.append('username', loginData.email);
      params.append('password', loginData.password);

      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params.toString(),
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Connexion impossible');

      setToken(data.access_token);
      setInfo('Connexion réussie.');
      setLoginData({ email: '', password: '' });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading((prev) => ({ ...prev, login: false }));
    }
  }

  async function handleRegister(event) {
    event.preventDefault();
    setError('');
    setInfo('');
    setLoading((prev) => ({ ...prev, register: true }));

    try {
      const payload = await apiRequest('/auth/register', {
        method: 'POST',
        body: JSON.stringify(registerData),
      });

      setInfo(`Compte créé pour ${payload.nom}. Vous pouvez maintenant vous connecter.`);
      setRegisterData(initialRegister);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading((prev) => ({ ...prev, register: false }));
    }
  }

  async function handleSubmitTicket(event) {
    event.preventDefault();
    setError('');
    setInfo('');

    if (!token) {
      setError('Merci de vous connecter avant d’envoyer un ticket.');
      return;
    }

    if (!ticketText.trim()) {
      setError('Le texte du ticket est obligatoire.');
      return;
    }

    setLoading((prev) => ({ ...prev, ticket: true }));

    try {
      const payload = await apiRequest('/tickets', {
        method: 'POST',
        body: JSON.stringify({
          ticket_id: `ticket-${Date.now()}`,
          texte: ticketText.trim(),
          horodatage: new Date().toISOString(),
        }),
      }, true);

      setResult(payload);
      setTicketText('');
      setInfo('Ticket soumis avec succès.');
      await loadDashboard();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading((prev) => ({ ...prev, ticket: false }));
    }
  }

  async function openTicket(ticketId) {
    try {
      const data = await apiRequest(`/tickets/${ticketId}`, {}, true);
      setSelectedTicket(data);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar panel">
        <div className="brand-block">
          <span className="brand-kicker">Support IT</span>
          <h1>mAIntenance</h1>
        </div>

        <div className="mini-card status-card">
          <span className="mini-label">Système</span>
          <strong>{health.statut === 'ok' ? 'Backend en ligne' : 'Vérification...'}</strong>
          <small>{health.statut}</small>
        </div>

        <div className="stack-block">
          <h3>Connexion</h3>
          <form onSubmit={handleLogin} className="auth-form">
            <label>
              Email
              <input
                type="email"
                value={loginData.email}
                onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
                placeholder="nom@entreprise.fr"
              />
            </label>

            <label>
              Mot de passe
              <input
                type="password"
                value={loginData.password}
                onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                placeholder="••••••••"
              />
            </label>

            <button type="submit" className="secondary-button" disabled={loading.login}>
              {loading.login ? 'Connexion...' : 'Se connecter'}
            </button>
          </form>
        </div>

        <div className="stack-block">
          <h3>Créer un compte</h3>
          <form onSubmit={handleRegister} className="auth-form">
            <label>
              Nom
              <input
                type="text"
                value={registerData.nom}
                onChange={(e) => setRegisterData({ ...registerData, nom: e.target.value })}
                placeholder="Nom complet"
              />
            </label>

            <label>
              Email
              <input
                type="email"
                value={registerData.email}
                onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })}
                placeholder="prenom@entreprise.fr"
              />
            </label>

            <label>
              Mot de passe
              <input
                type="password"
                value={registerData.mot_de_passe}
                onChange={(e) => setRegisterData({ ...registerData, mot_de_passe: e.target.value })}
                placeholder="••••••••"
              />
            </label>

            <button type="submit" className="secondary-button" disabled={loading.register}>
              {loading.register ? 'Création...' : 'S’inscrire'}
            </button>
          </form>
        </div>

        {user && (
          <div className="mini-card user-card">
            <span className="mini-label">Utilisateur</span>
            <strong>{user.nom}</strong>
            <small>{user.email}</small>
          </div>
        )}

        {info && <div className="info-box">{info}</div>}
        {error && <div className="error-box">{error}</div>}
      </aside>

      <main className="content panel">
        <div className="header-row">
          <div>
            <p className="eyebrow">Assistant technique</p>
            <h2>Gestion des tickets</h2>
          </div>
          <span className="badge">{token ? 'Session active' : 'Déconnecté'}</span>
        </div>

        <div className="workspace-grid">
          <section className="ticket-panel">
            <form onSubmit={handleSubmitTicket} className="ticket-form">
              <label htmlFor="ticket-text" className="label-text">Description du problème</label>
              <textarea
                id="ticket-text"
                value={ticketText}
                onChange={(e) => setTicketText(e.target.value)}
                placeholder="Exemple : Le VPN ne se connecte pas depuis le bureau 2, le service réseau est lent depuis ce matin..."
                rows="8"
              />

              <div className="footer-actions">
                <span>{ticketText.trim().length} caractères</span>
                <button type="submit" className="primary-button" disabled={loading.ticket || !token}>
                  {loading.ticket ? 'Analyse en cours...' : 'Envoyer le ticket'}
                </button>
              </div>
            </form>
          </section>

          <section className="result-panel">
            <div className="result-header">
              <h3>Décision de traitement</h3>
            </div>

            {!result ? (
              <p className="empty-state">Aucune analyse récente. Soumettez un ticket pour générer une décision.</p>
            ) : (
              <div className="result-grid">
                <div className="meta-card">
                  <span>Catégorie</span>
                  <strong>{result.categorie || '—'}</strong>
                </div>
                <div className="meta-card">
                  <span>Priorité</span>
                  <strong>{result.priorite || '—'}</strong>
                </div>
                <div className="meta-card">
                  <span>Confiance</span>
                  <strong>{result.confiance ? `${(result.confiance * 100).toFixed(0)}%` : '—'}</strong>
                </div>
                <div className="meta-card">
                  <span>Action</span>
                  <strong>{result.action || '—'}</strong>
                </div>

                <div className="result-block wide">
                  <h4>Diagnostic</h4>
                  <p>{result.diagnostic || 'Aucun diagnostic disponible.'}</p>
                </div>

                <div className="result-block wide">
                  <h4>Étapes de résolution</h4>
                  <ul>
                    {result.etapes_resolution && result.etapes_resolution.length > 0 ? (
                      result.etapes_resolution.map((step, index) => <li key={index}>{step}</li>)
                    ) : (
                      <li>Aucune étape fournie.</li>
                    )}
                  </ul>
                </div>

                <div className="result-block wide">
                  <h4>Sources</h4>
                  <ul>
                    {result.sources && result.sources.length > 0 ? (
                      result.sources.map((source, index) => <li key={index}>{source}</li>)
                    ) : (
                      <li>Aucune source associée.</li>
                    )}
                  </ul>
                </div>
              </div>
            )}
          </section>
        </div>

        <div className="dashboard-grid">
          <section className="list-panel">
            <div className="section-header">
              <h3>Tickets récents</h3>
              <span>{tickets.length}</span>
            </div>

            {loading.tickets ? (
              <p className="empty-state">Chargement des tickets...</p>
            ) : tickets.length === 0 ? (
              <p className="empty-state">Aucun ticket disponible.</p>
            ) : (
              <ul className="ticket-list">
                {tickets.map((ticket) => (
                  <li key={ticket.ticket_id} className="ticket-item" onClick={() => openTicket(ticket.ticket_id)}>
                    <div>
                      <strong>{ticket.ticket_id}</strong>
                      <p>{ticket.texte.slice(0, 90)}{ticket.texte.length > 90 ? '...' : ''}</p>
                    </div>
                    <span className="status-pill">{ticket.statut}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="list-panel">
            <div className="section-header">
              <h3>Validation humaine</h3>
              <span>{pendingTickets.length}</span>
            </div>

            {pendingTickets.length === 0 ? (
              <p className="empty-state">Aucun ticket en attente de validation.</p>
            ) : (
              <ul className="ticket-list compact-list">
                {pendingTickets.map((decision) => (
                  <li key={decision.id} className="ticket-item pending-item">
                    <div>
                      <strong>{decision.ticket_id}</strong>
                      <p>{decision.categorie} · {decision.priorite}</p>
                    </div>
                    <span className="status-pill warn">{decision.action}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        {selectedTicket && (
          <section className="detail-panel">
            <div className="section-header">
              <h3>Détail du ticket</h3>
            </div>
            <div className="detail-grid">
              <div>
                <p><strong>ID :</strong> {selectedTicket.ticket_id}</p>
                <p><strong>Statut :</strong> {selectedTicket.statut}</p>
                <p><strong>Équipe :</strong> {selectedTicket.equipe_affectee || 'non affectée'}</p>
              </div>
              <div>
                <p><strong>Utilisateur :</strong> {selectedTicket.utilisateur_id || 'inconnu'}</p>
                <p><strong>Créé le :</strong> {selectedTicket.horodatage}</p>
              </div>
            </div>

            <div className="detail-text">
              <h4>Texte du ticket</h4>
              <p>{selectedTicket.texte}</p>
            </div>

            {selectedTicket.decisions && selectedTicket.decisions.length > 0 && (
              <div className="detail-text">
                <h4>Décision enregistrée</h4>
                <pre>{JSON.stringify(selectedTicket.decisions[0], null, 2)}</pre>
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
