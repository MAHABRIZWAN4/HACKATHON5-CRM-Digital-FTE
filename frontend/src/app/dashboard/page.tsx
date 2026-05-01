'use client';

import { useState, useEffect } from 'react';

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
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const fetchEscalations = async () => {
    try {
      const response = await fetch('http://localhost:8001/dashboard/escalations');
      const data = await response.json();

      if (data.success) {
        setEscalations(data.escalations);
        setError('');
      } else {
        setError(data.error || 'Failed to fetch escalations');
      }
    } catch (err) {
      setError('Network error. Please check if the API server is running on port 8001.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEscalations();
    const interval = setInterval(fetchEscalations, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleResolve = async (ticketId: string) => {
    setResolvingId(ticketId);
    try {
      const response = await fetch(`http://localhost:8001/dashboard/escalations/${ticketId}/resolve`, {
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
          <h1 className="title">🚨 Escalation Dashboard</h1>
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
