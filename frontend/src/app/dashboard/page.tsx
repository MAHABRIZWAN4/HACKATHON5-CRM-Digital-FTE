'use client';

import { useState, useEffect, CSSProperties } from 'react';

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

  const getUrgencyBadge = (urgency: string) => {
    const baseStyle: CSSProperties = {
      padding: '4px 12px',
      borderRadius: '6px',
      fontSize: '12px',
      fontWeight: '600',
      textTransform: 'uppercase',
      display: 'inline-block'
    };

    switch (urgency.toLowerCase()) {
      case 'high':
        return <span style={{ ...baseStyle, background: '#dc2626', color: 'white' }}>High</span>;
      case 'medium':
        return <span style={{ ...baseStyle, background: '#ea580c', color: 'white' }}>Medium</span>;
      case 'low':
        return <span style={{ ...baseStyle, background: '#6b7280', color: 'white' }}>Low</span>;
      default:
        return <span style={{ ...baseStyle, background: '#6b7280', color: 'white' }}>{urgency}</span>;
    }
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

  const containerStyle: CSSProperties = {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #1a1a2e, #16213e, #0f3460)',
    padding: '40px 20px',
    fontFamily: "'Poppins', sans-serif"
  };

  const headerStyle: CSSProperties = {
    maxWidth: '1400px',
    margin: '0 auto 30px',
    color: 'white'
  };

  const titleStyle: CSSProperties = {
    fontSize: '36px',
    fontWeight: 'bold',
    marginBottom: '8px'
  };

  const subtitleStyle: CSSProperties = {
    fontSize: '16px',
    color: '#00d9ff',
    marginBottom: '20px'
  };

  const statsStyle: CSSProperties = {
    display: 'flex',
    gap: '20px',
    marginBottom: '20px'
  };

  const statBoxStyle: CSSProperties = {
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    padding: '15px 25px',
    borderRadius: '10px',
    color: 'white'
  };

  const statNumberStyle: CSSProperties = {
    fontSize: '28px',
    fontWeight: 'bold',
    marginBottom: '4px'
  };

  const statLabelStyle: CSSProperties = {
    fontSize: '14px',
    color: 'rgba(255, 255, 255, 0.7)'
  };

  const cardStyle: CSSProperties = {
    maxWidth: '1400px',
    margin: '0 auto',
    background: 'rgba(255, 255, 255, 0.95)',
    borderRadius: '20px',
    boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
    overflow: 'hidden'
  };

  const tableContainerStyle: CSSProperties = {
    overflowX: 'auto'
  };

  const tableStyle: CSSProperties = {
    width: '100%',
    borderCollapse: 'collapse'
  };

  const thStyle: CSSProperties = {
    background: '#1a1a2e',
    color: 'white',
    padding: '16px',
    textAlign: 'left',
    fontSize: '14px',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  };

  const tdStyle: CSSProperties = {
    padding: '16px',
    borderBottom: '1px solid #e5e7eb',
    fontSize: '14px',
    color: '#374151'
  };

  const buttonStyle: CSSProperties = {
    background: 'linear-gradient(135deg, #667eea, #764ba2)',
    color: 'white',
    padding: '8px 16px',
    borderRadius: '6px',
    border: 'none',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.3s',
    fontFamily: "'Poppins', sans-serif"
  };

  const emptyStateStyle: CSSProperties = {
    textAlign: 'center',
    padding: '60px 20px',
    color: '#6b7280'
  };

  const errorBoxStyle: CSSProperties = {
    maxWidth: '1400px',
    margin: '0 auto',
    background: '#fee2e2',
    border: '1px solid #ef4444',
    borderRadius: '10px',
    padding: '16px',
    color: '#991b1b',
    fontSize: '14px'
  };

  const loadingStyle: CSSProperties = {
    textAlign: 'center',
    padding: '60px 20px',
    color: 'white',
    fontSize: '18px'
  };

  if (loading) {
    return (
      <div style={containerStyle}>
        <div style={loadingStyle}>Loading escalations...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={containerStyle}>
        <div style={headerStyle}>
          <h1 style={titleStyle}>🚨 Escalation Dashboard</h1>
        </div>
        <div style={errorBoxStyle}>{error}</div>
      </div>
    );
  }

  const totalEscalations = escalations.length;
  const highUrgency = escalations.filter(e => e.urgency.toLowerCase() === 'high').length;
  const escalatedStatus = escalations.filter(e => e.status === 'escalated').length;

  return (
    <>
      <link
        href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap"
        rel="stylesheet"
      />
      <div style={containerStyle}>
        <div style={headerStyle}>
          <h1 style={titleStyle}>🚨 Escalation Dashboard</h1>
          <p style={subtitleStyle}>Real-time monitoring of escalated support tickets</p>

          <div style={statsStyle}>
            <div style={statBoxStyle}>
              <div style={statNumberStyle}>{totalEscalations}</div>
              <div style={statLabelStyle}>Total Escalations</div>
            </div>
            <div style={statBoxStyle}>
              <div style={statNumberStyle}>{highUrgency}</div>
              <div style={statLabelStyle}>High Urgency</div>
            </div>
            <div style={statBoxStyle}>
              <div style={statNumberStyle}>{escalatedStatus}</div>
              <div style={statLabelStyle}>Pending</div>
            </div>
          </div>
        </div>

        <div style={cardStyle}>
          {escalations.length === 0 ? (
            <div style={emptyStateStyle}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>✅</div>
              <div style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px' }}>
                No Escalations
              </div>
              <div style={{ fontSize: '14px' }}>
                All tickets are being handled smoothly!
              </div>
            </div>
          ) : (
            <div style={tableContainerStyle}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Ticket ID</th>
                    <th style={thStyle}>Customer</th>
                    <th style={thStyle}>Reason</th>
                    <th style={thStyle}>Urgency</th>
                    <th style={thStyle}>Created At</th>
                    <th style={thStyle}>Status</th>
                    <th style={thStyle}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {escalations.map((escalation) => (
                    <tr key={escalation.ticket_id}>
                      <td style={tdStyle}>
                        <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                          {escalation.ticket_id.substring(0, 8)}...
                        </span>
                      </td>
                      <td style={tdStyle}>
                        <div style={{ fontWeight: '600' }}>{escalation.customer_name}</div>
                        <div style={{ fontSize: '12px', color: '#6b7280' }}>
                          {escalation.customer_email}
                        </div>
                      </td>
                      <td style={tdStyle}>{escalation.reason}</td>
                      <td style={tdStyle}>{getUrgencyBadge(escalation.urgency)}</td>
                      <td style={tdStyle}>{formatDate(escalation.escalated_at)}</td>
                      <td style={tdStyle}>
                        <span
                          style={{
                            padding: '4px 12px',
                            borderRadius: '6px',
                            fontSize: '12px',
                            fontWeight: '600',
                            background: escalation.status === 'escalated' ? '#fef3c7' : '#d1fae5',
                            color: escalation.status === 'escalated' ? '#92400e' : '#065f46'
                          }}
                        >
                          {escalation.status}
                        </span>
                      </td>
                      <td style={tdStyle}>
                        {escalation.status === 'escalated' && (
                          <button
                            onClick={() => handleResolve(escalation.ticket_id)}
                            disabled={resolvingId === escalation.ticket_id}
                            style={{
                              ...buttonStyle,
                              opacity: resolvingId === escalation.ticket_id ? 0.6 : 1,
                              cursor: resolvingId === escalation.ticket_id ? 'not-allowed' : 'pointer'
                            }}
                          >
                            {resolvingId === escalation.ticket_id ? 'Resolving...' : 'Mark as Resolved'}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
