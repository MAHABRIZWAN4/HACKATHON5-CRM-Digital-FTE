'use client';

import { useState, useEffect } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

interface Escalation {
  ticket_id: string;
  customer_email: string;
  customer_name: string;
  title: string;
  reason: string;
  urgency: string;
  status: string;
  created_at: string;
  escalated_at: string;
}

export default function Dashboard() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  // Check authentication on mount
  useEffect(() => {
    const auth = sessionStorage.getItem('dashboard_auth');
    if (auth === 'authenticated') {
      setIsAuthenticated(true);
    } else {
      setLoading(false);
    }
  }, []);

  // Handle login
  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();

    // Simple password check (in production, this should be server-side)
    const correctPassword = 'admin123'; // Default password

    if (password === correctPassword) {
      sessionStorage.setItem('dashboard_auth', 'authenticated');
      setIsAuthenticated(true);
      setAuthError('');
      setPassword('');
    } else {
      setAuthError('Incorrect password. Please try again.');
      setPassword('');
    }
  };

  // Handle logout
  const handleLogout = () => {
    sessionStorage.removeItem('dashboard_auth');
    setIsAuthenticated(false);
    setPassword('');
  };

  const fetchEscalations = async () => {
    if (!isAuthenticated) return;

    try {
      const response = await fetch(`${API_URL}/dashboard/escalations`);
      const data = await response.json();

      if (data.success) {
        setEscalations(data.escalations);
        setError('');
      } else {
        setError(data.error || 'Failed to fetch escalations');
      }
    } catch (err) {
      setError('Network error. Please check if the API server is running.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchEscalations();
      const interval = setInterval(fetchEscalations, 30000);
      return () => clearInterval(interval);
    }
  }, [isAuthenticated]);

  const handleResolve = async (ticketId: string) => {
    setResolvingId(ticketId);
    try {
      const response = await fetch(`${API_URL}/dashboard/escalations/${ticketId}/resolve`, {
        method: 'POST',
      });
      const data = await response.json();

      if (data.success) {
        await fetchEscalations();
      } else {
        alert('Failed to resolve ticket: ' + data.error);
      }
    } catch (err) {
      alert('Network error while resolving ticket');
    } finally {
      setResolvingId(null);
    }
  };

  const getUrgencyColor = (urgency: string) => {
    const colors: { [key: string]: { bg: string; text: string } } = {
      high: { bg: '#dc2626', text: 'white' },
      medium: { bg: '#ea580c', text: 'white' },
      low: { bg: '#6b7280', text: 'white' }
    };
    return colors[urgency.toLowerCase()] || colors.low;
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet" />
        <div className="container">
          <div className="loading">Loading escalations...</div>
        </div>
        <style jsx>{styles}</style>
      </>
    );
  }

  // Show login form if not authenticated
  if (!isAuthenticated) {
    return (
      <>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet" />
        <div className="container">
          <div className="login-container">
            <div className="login-card">
              <div className="login-header">
                <h1 className="login-title">🔒 Dashboard Login</h1>
                <p className="login-subtitle">Enter password to access escalation dashboard</p>
              </div>
              <form onSubmit={handleLogin} className="login-form">
                <div className="form-group">
                  <label htmlFor="password" className="form-label">Password</label>
                  <input
                    type="password"
                    id="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter dashboard password"
                    className="form-input"
                    autoFocus
                  />
                </div>
                {authError && (
                  <div className="auth-error">{authError}</div>
                )}
                <button type="submit" className="login-btn">
                  Login
                </button>
                <div className="login-hint">
                  Default password: admin123
                </div>
              </form>
            </div>
          </div>
        </div>
        <style jsx>{styles}</style>
      </>
    );
  }

  if (error) {
    return (
      <>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet" />
        <div className="container">
          <div className="header">
            <h1 className="title">🚨 Escalation Dashboard</h1>
          </div>
          <div className="error-box">{error}</div>
        </div>
        <style jsx>{styles}</style>
      </>
    );
  }

  const totalEscalations = escalations.length;
  const highUrgency = escalations.filter(e => e.urgency.toLowerCase() === 'high').length;
  const escalatedStatus = escalations.filter(e => e.status === 'escalated').length;

  return (
    <>
      <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet" />
      <div className="container">
        <div className="header">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <h1 className="title">🚨 Escalation Dashboard</h1>
            <button onClick={handleLogout} className="logout-btn">
              Logout
            </button>
          </div>
          <p className="subtitle">Real-time monitoring of escalated support tickets</p>

          <div className="stats-grid">
            <div className="stat-box">
              <div className="stat-number">{totalEscalations}</div>
              <div className="stat-label">Total</div>
            </div>
            <div className="stat-box">
              <div className="stat-number">{highUrgency}</div>
              <div className="stat-label">High Urgency</div>
            </div>
            <div className="stat-box">
              <div className="stat-number">{escalatedStatus}</div>
              <div className="stat-label">Pending</div>
            </div>
          </div>
        </div>

        {escalations.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">✅</div>
            <div className="empty-title">No Escalations</div>
            <div className="empty-text">All tickets are being handled smoothly!</div>
          </div>
        ) : (
          <>
            {/* Desktop Table View */}
            <div className="desktop-view">
              <div className="card">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Ticket ID</th>
                      <th>Customer</th>
                      <th>Reason</th>
                      <th>Urgency</th>
                      <th>Created At</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {escalations.map((escalation) => {
                      const urgencyColor = getUrgencyColor(escalation.urgency);
                      return (
                        <tr key={escalation.ticket_id}>
                          <td>
                            <span className="ticket-id">
                              {escalation.ticket_id.substring(0, 8)}...
                            </span>
                          </td>
                          <td>
                            <div className="customer-name">{escalation.customer_name}</div>
                            <div className="customer-email">{escalation.customer_email}</div>
                          </td>
                          <td>{escalation.reason}</td>
                          <td>
                            <span className="urgency-badge" style={{ background: urgencyColor.bg, color: urgencyColor.text }}>
                              {escalation.urgency}
                            </span>
                          </td>
                          <td>{formatDate(escalation.escalated_at)}</td>
                          <td>
                            <span className={`status-badge ${escalation.status}`}>
                              {escalation.status}
                            </span>
                          </td>
                          <td>
                            {escalation.status === 'escalated' && (
                              <button
                                onClick={() => handleResolve(escalation.ticket_id)}
                                disabled={resolvingId === escalation.ticket_id}
                                className="resolve-btn"
                              >
                                {resolvingId === escalation.ticket_id ? 'Resolving...' : 'Resolve'}
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Mobile Card View */}
            <div className="mobile-view">
              {escalations.map((escalation) => {
                const urgencyColor = getUrgencyColor(escalation.urgency);
                return (
                  <div key={escalation.ticket_id} className="escalation-card">
                    <div className="card-header">
                      <span className="ticket-id-mobile">
                        {escalation.ticket_id.substring(0, 8)}...
                      </span>
                      <span className="urgency-badge-mobile" style={{ background: urgencyColor.bg, color: urgencyColor.text }}>
                        {escalation.urgency}
                      </span>
                    </div>

                    <div className="card-body">
                      <div className="card-row">
                        <div className="card-label">Customer</div>
                        <div>
                          <div className="customer-name-mobile">{escalation.customer_name}</div>
                          <div className="customer-email-mobile">{escalation.customer_email}</div>
                        </div>
                      </div>

                      <div className="card-row">
                        <div className="card-label">Reason</div>
                        <div className="card-value">{escalation.reason}</div>
                      </div>

                      <div className="card-row">
                        <div className="card-label">Created</div>
                        <div className="card-value">{formatDate(escalation.escalated_at)}</div>
                      </div>

                      <div className="card-row">
                        <div className="card-label">Status</div>
                        <span className={`status-badge-mobile ${escalation.status}`}>
                          {escalation.status}
                        </span>
                      </div>
                    </div>

                    {escalation.status === 'escalated' && (
                      <div className="card-footer">
                        <button
                          onClick={() => handleResolve(escalation.ticket_id)}
                          disabled={resolvingId === escalation.ticket_id}
                          className="resolve-btn-mobile"
                        >
                          {resolvingId === escalation.ticket_id ? 'Resolving...' : 'Mark as Resolved'}
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
      <style jsx>{styles}</style>
    </>
  );
}

const styles = `
  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  html, body {
    overflow-x: hidden;
    width: 100%;
    max-width: 100vw;
  }

  .container {
    min-height: 100vh;
    background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460);
    padding: 15px;
    font-family: 'Poppins', sans-serif;
    width: 100%;
    max-width: 100vw;
    overflow-x: hidden;
  }

  .header {
    max-width: 100%;
    margin: 0 0 20px 0;
    color: white;
    width: 100%;
  }

  .title {
    font-size: 28px;
    font-weight: bold;
    margin-bottom: 8px;
    word-wrap: break-word;
  }

  .subtitle {
    font-size: 14px;
    color: #00d9ff;
    margin-bottom: 15px;
    word-wrap: break-word;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
    margin-bottom: 20px;
    width: 100%;
  }

  .stat-box {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    padding: 15px;
    border-radius: 12px;
    color: white;
    text-align: center;
    width: 100%;
  }

  .stat-number {
    font-size: 28px;
    font-weight: bold;
    margin-bottom: 5px;
  }

  .stat-label {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.8);
  }

  /* Desktop Table View */
  .desktop-view {
    display: none;
  }

  .mobile-view {
    display: block;
    width: 100%;
  }

  .card {
    max-width: 100%;
    margin: 0 auto;
    background: rgba(255, 255, 255, 0.95);
    border-radius: 16px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    overflow: hidden;
    width: 100%;
  }

  .table {
    width: 100%;
    border-collapse: collapse;
  }

  .table thead {
    background: #1a1a2e;
    color: white;
  }

  .table th {
    padding: 16px;
    text-align: left;
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .table td {
    padding: 16px;
    border-bottom: 1px solid #e5e7eb;
    font-size: 14px;
    color: #374151;
  }

  .table tbody tr:hover {
    background: #f9fafb;
  }

  .ticket-id {
    font-family: monospace;
    font-size: 12px;
    background: #f3f4f6;
    padding: 4px 8px;
    border-radius: 4px;
  }

  .customer-name {
    font-weight: 600;
    margin-bottom: 4px;
  }

  .customer-email {
    font-size: 12px;
    color: #6b7280;
  }

  .urgency-badge {
    padding: 4px 12px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    display: inline-block;
  }

  .status-badge {
    padding: 4px 12px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    display: inline-block;
  }

  .status-badge.escalated {
    background: #fef3c7;
    color: #92400e;
  }

  .status-badge.resolved {
    background: #d1fae5;
    color: #065f46;
  }

  .resolve-btn {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    padding: 8px 16px;
    border-radius: 6px;
    border: none;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s;
    font-family: 'Poppins', sans-serif;
  }

  .resolve-btn:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }

  .resolve-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  /* Mobile Card View */
  .escalation-card {
    width: 100%;
    max-width: 100%;
    margin: 0 0 12px 0;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    overflow: hidden;
  }

  .card-header {
    background: #1a1a2e;
    padding: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .ticket-id-mobile {
    font-family: monospace;
    font-size: 11px;
    color: white;
    background: rgba(255,255,255,0.1);
    padding: 4px 8px;
    border-radius: 4px;
    word-break: break-all;
  }

  .urgency-badge-mobile {
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .card-body {
    padding: 12px;
    width: 100%;
  }

  .card-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 10px;
    gap: 10px;
    width: 100%;
  }

  .card-row:last-child {
    margin-bottom: 0;
  }

  .card-label {
    font-size: 11px;
    font-weight: 600;
    color: #6b7280;
    min-width: 60px;
    flex-shrink: 0;
  }

  .card-value {
    font-size: 12px;
    color: #374151;
    text-align: right;
    flex: 1;
    word-wrap: break-word;
    overflow-wrap: break-word;
  }

  .customer-name-mobile {
    font-size: 12px;
    font-weight: 600;
    color: #374151;
    text-align: right;
    word-wrap: break-word;
    overflow-wrap: break-word;
  }

  .customer-email-mobile {
    font-size: 10px;
    color: #6b7280;
    text-align: right;
    margin-top: 2px;
    word-wrap: break-word;
    overflow-wrap: break-word;
  }

  .status-badge-mobile {
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 10px;
    font-weight: 600;
    white-space: nowrap;
  }

  .status-badge-mobile.escalated {
    background: #fef3c7;
    color: #92400e;
  }

  .status-badge-mobile.resolved {
    background: #d1fae5;
    color: #065f46;
  }

  .card-footer {
    padding: 0 12px 12px;
    width: 100%;
  }

  .resolve-btn-mobile {
    width: 100%;
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    padding: 12px;
    border-radius: 8px;
    border: none;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    font-family: 'Poppins', sans-serif;
  }

  .resolve-btn-mobile:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .empty-state {
    max-width: 100%;
    margin: 0;
    background: white;
    border-radius: 16px;
    text-align: center;
    padding: 40px 20px;
    color: #6b7280;
    width: 100%;
  }

  .empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
  }

  .empty-title {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 8px;
  }

  .empty-text {
    font-size: 14px;
  }

  .error-box {
    max-width: 100%;
    margin: 0;
    background: #fee2e2;
    border: 1px solid #ef4444;
    border-radius: 10px;
    padding: 15px;
    color: #991b1b;
    font-size: 13px;
    width: 100%;
    word-wrap: break-word;
  }

  .loading {
    text-align: center;
    padding: 60px 20px;
    color: white;
    font-size: 18px;
  }

  /* Login Form Styles */
  .login-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 80vh;
    width: 100%;
  }

  .login-card {
    background: white;
    border-radius: 16px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    padding: 40px;
    width: 100%;
    max-width: 400px;
  }

  .login-header {
    text-align: center;
    margin-bottom: 30px;
  }

  .login-title {
    font-size: 28px;
    font-weight: bold;
    color: #1a1a2e;
    margin-bottom: 8px;
  }

  .login-subtitle {
    font-size: 14px;
    color: #6b7280;
  }

  .login-form {
    width: 100%;
  }

  .form-group {
    margin-bottom: 20px;
  }

  .form-label {
    display: block;
    font-size: 14px;
    font-weight: 600;
    color: #374151;
    margin-bottom: 8px;
  }

  .form-input {
    width: 100%;
    padding: 12px 16px;
    border: 2px solid #e5e7eb;
    border-radius: 8px;
    font-size: 14px;
    font-family: 'Poppins', sans-serif;
    transition: border-color 0.3s;
  }

  .form-input:focus {
    outline: none;
    border-color: #667eea;
  }

  .auth-error {
    background: #fee2e2;
    border: 1px solid #ef4444;
    color: #991b1b;
    padding: 12px;
    border-radius: 8px;
    font-size: 13px;
    margin-bottom: 20px;
  }

  .login-btn {
    width: 100%;
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    padding: 14px;
    border-radius: 8px;
    border: none;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    font-family: 'Poppins', sans-serif;
    transition: transform 0.2s;
  }

  .login-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }

  .login-hint {
    text-align: center;
    margin-top: 20px;
    font-size: 12px;
    color: #6b7280;
    padding: 10px;
    background: #f9fafb;
    border-radius: 6px;
  }

  .logout-btn {
    background: rgba(255, 255, 255, 0.1);
    color: white;
    padding: 8px 16px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    font-family: 'Poppins', sans-serif;
    transition: all 0.3s;
  }

  .logout-btn:hover {
    background: rgba(255, 255, 255, 0.2);
    border-color: rgba(255, 255, 255, 0.3);
  }

  /* Desktop - 1024px and above */
  @media (min-width: 1024px) {
    .container {
      padding: 40px 20px;
    }

    .header {
      max-width: 1400px;
      margin: 0 auto 30px;
    }

    .title {
      font-size: 36px;
    }

    .subtitle {
      font-size: 16px;
    }

    .stats-grid {
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
    }

    .stat-box {
      padding: 20px;
    }

    .stat-number {
      font-size: 32px;
    }

    .stat-label {
      font-size: 14px;
    }

    .desktop-view {
      display: block;
    }

    .mobile-view {
      display: none;
    }

    .card {
      max-width: 1400px;
    }

    .empty-state {
      max-width: 1400px;
      margin: 0 auto;
      padding: 60px 20px;
    }

    .error-box {
      max-width: 1400px;
      margin: 0 auto;
    }
  }

  /* Tablet - 768px to 1023px */
  @media (min-width: 768px) and (max-width: 1023px) {
    .container {
      padding: 25px 15px;
    }

    .title {
      font-size: 32px;
    }

    .subtitle {
      font-size: 15px;
    }

    .stats-grid {
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
    }

    .stat-box {
      padding: 18px;
    }

    .stat-number {
      font-size: 30px;
    }
  }
`;
