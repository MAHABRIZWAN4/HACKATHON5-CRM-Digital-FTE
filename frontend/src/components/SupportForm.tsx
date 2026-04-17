'use client';

import { useState, useEffect, FormEvent, ChangeEvent, CSSProperties } from 'react';

interface FormData {
  name: string;
  email: string;
  subject: string;
  category: string;
  message: string;
}

interface ApiResponse {
  status: string;
  ticket_id?: string;
  message?: string;
}

export default function SupportForm() {
  const [formData, setFormData] = useState<FormData>({
    name: '',
    email: '',
    subject: '',
    category: 'general',
    message: ''
  });

  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [ticketId, setTicketId] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [focusedField, setFocusedField] = useState<string>('');
  const [isButtonHovered, setIsButtonHovered] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleChange = (
    e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setStatus('loading');
    setErrorMessage('');

    try {
      const response = await fetch('http://localhost:8001/support', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: formData.name,
          email: formData.email,
          subject: formData.subject,
          message: `[${formData.category}] ${formData.message}`
        }),
      });

      const data: ApiResponse = await response.json();

      if (response.ok && data.status === 'success') {
        setStatus('success');
        setTicketId(data.ticket_id || '');
        setFormData({
          name: '',
          email: '',
          subject: '',
          category: 'general',
          message: ''
        });
      } else {
        setStatus('error');
        setErrorMessage(data.message || 'Failed to submit support request');
      }
    } catch (error) {
      setStatus('error');
      setErrorMessage('Network error. Please check if the API server is running on port 8001.');
    }
  };

  const messageLength = formData.message.length;
  const maxLength = 500;

  // Styles
  const containerStyle: CSSProperties = {
    display: 'flex',
    minHeight: '100vh',
    fontFamily: "'Poppins', sans-serif",
    flexDirection: isMobile ? 'column' : 'row'
  };

  const leftSideStyle: CSSProperties = {
    width: isMobile ? '100%' : '40%',
    background: 'linear-gradient(135deg, #1a1a2e, #16213e, #0f3460)',
    padding: isMobile ? '40px 20px' : '60px 40px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    backgroundSize: '400% 400%',
    minHeight: isMobile ? '300px' : 'auto'
  };

  const logoStyle: CSSProperties = {
    fontSize: '24px',
    fontWeight: 'bold',
    color: 'white',
    marginBottom: '60px'
  };

  const headingStyle: CSSProperties = {
    fontSize: isMobile ? '32px' : '36px',
    fontWeight: 'bold',
    color: 'white',
    marginBottom: '12px'
  };

  const subheadingStyle: CSSProperties = {
    fontSize: '18px',
    color: '#00d9ff',
    marginBottom: '40px'
  };

  const badgesContainerStyle: CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    marginBottom: '40px'
  };

  const badgeStyle: CSSProperties = {
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    color: 'white',
    padding: '8px 16px',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '500',
    display: 'inline-block',
    width: 'fit-content'
  };

  const aiBadgeStyle: CSSProperties = {
    ...badgeStyle
  };

  const bottomTextStyle: CSSProperties = {
    color: 'rgba(255, 255, 255, 0.7)',
    fontSize: '14px',
    marginTop: 'auto'
  };

  const rightSideStyle: CSSProperties = {
    width: isMobile ? '100%' : '60%',
    background: '#f8fafc',
    padding: isMobile ? '40px 20px' : '60px 40px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  };

  const cardStyle: CSSProperties = {
    background: 'white',
    borderRadius: '20px',
    boxShadow: '0 20px 60px rgba(0,0,0,0.1)',
    padding: '40px',
    maxWidth: '500px',
    width: '100%'
  };

  const cardTitleStyle: CSSProperties = {
    fontSize: '28px',
    color: '#1a1a2e',
    fontWeight: '700',
    marginBottom: '30px',
    textAlign: 'center'
  };

  const formGroupStyle: CSSProperties = {
    marginBottom: '20px',
    position: 'relative'
  };

  const labelStyle: CSSProperties = {
    fontSize: '14px',
    fontWeight: '600',
    color: '#4a5568',
    marginBottom: '6px',
    display: 'block'
  };

  const inputBaseStyle: CSSProperties = {
    width: '100%',
    padding: '12px 16px',
    borderWidth: '2px',
    borderStyle: 'solid',
    borderColor: '#e2e8f0',
    borderRadius: '10px',
    fontSize: '16px',
    fontFamily: "'Poppins', sans-serif",
    transition: 'border-color 0.3s, box-shadow 0.3s',
    outline: 'none',
    color: '#2d3748',
    boxSizing: 'border-box'
  };

  const getInputStyle = (fieldName: string): CSSProperties => {
    if (focusedField === fieldName) {
      return {
        ...inputBaseStyle,
        borderColor: '#667eea',
        boxShadow: '0 0 0 3px rgba(102,126,234,0.15)'
      };
    }
    return inputBaseStyle;
  };

  const textareaStyle: CSSProperties = {
    ...inputBaseStyle,
    minHeight: '100px',
    resize: 'vertical',
    fontFamily: "'Poppins', sans-serif"
  };

  const getTextareaStyle = (): CSSProperties => {
    if (focusedField === 'message') {
      return {
        ...textareaStyle,
        borderColor: '#667eea',
        boxShadow: '0 0 0 3px rgba(102,126,234,0.15)'
      };
    }
    return textareaStyle;
  };

  const characterCounterStyle: CSSProperties = {
    fontSize: '12px',
    color: messageLength > 400 ? '#ed8936' : '#718096',
    marginTop: '4px',
    textAlign: 'right'
  };

  const buttonBaseStyle: CSSProperties = {
    background: 'linear-gradient(135deg, #667eea, #764ba2)',
    color: 'white',
    padding: '14px',
    borderRadius: '10px',
    borderWidth: '0',
    borderStyle: 'none',
    width: '100%',
    fontSize: '16px',
    fontWeight: '600',
    cursor: status === 'loading' ? 'not-allowed' : 'pointer',
    transition: 'all 0.3s',
    fontFamily: "'Poppins', sans-serif",
    opacity: status === 'loading' ? 0.8 : 1
  };

  const getButtonStyle = (): CSSProperties => {
    if (isButtonHovered && status !== 'loading') {
      return {
        ...buttonBaseStyle,
        transform: 'translateY(-2px)',
        boxShadow: '0 10px 30px rgba(102,126,234,0.4)'
      };
    }
    return buttonBaseStyle;
  };

  const errorBoxStyle: CSSProperties = {
    background: '#fff5f5',
    borderWidth: '1px',
    borderStyle: 'solid',
    borderColor: '#fc8181',
    borderRadius: '8px',
    padding: '12px',
    color: '#c53030',
    fontSize: '14px',
    marginBottom: '20px'
  };

  const successContainerStyle: CSSProperties = {
    textAlign: 'center',
    padding: '20px'
  };

  const successCheckmarkStyle: CSSProperties = {
    fontSize: '60px',
    marginBottom: '20px'
  };

  const successHeadingStyle: CSSProperties = {
    fontSize: '24px',
    fontWeight: '700',
    color: '#38a169',
    marginBottom: '20px'
  };

  const successLabelStyle: CSSProperties = {
    fontSize: '14px',
    color: '#4a5568',
    marginBottom: '10px',
    fontWeight: '600'
  };

  const ticketBoxStyle: CSSProperties = {
    background: '#f0fff4',
    borderWidth: '2px',
    borderStyle: 'solid',
    borderColor: '#68d391',
    borderRadius: '8px',
    padding: '12px',
    fontFamily: 'monospace',
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#276749',
    marginBottom: '20px',
    wordBreak: 'break-all'
  };

  const successSubtextStyle: CSSProperties = {
    fontSize: '14px',
    color: '#718096'
  };

  const secondaryButtonStyle: CSSProperties = {
    background: 'linear-gradient(135deg, #667eea, #764ba2)',
    color: 'white',
    padding: '12px 24px',
    borderRadius: '10px',
    borderWidth: '0',
    borderStyle: 'none',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    marginTop: '20px',
    fontFamily: "'Poppins', sans-serif"
  };

  return (
    <>
      <style>{`
        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(30px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes gradientShift {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }

        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-8px); }
          75% { transform: translateX(8px); }
        }

        .slide-up {
          animation: slideUp 0.6s ease-out;
        }

        .gradient-shift {
          animation: gradientShift 8s ease infinite;
        }

        .pulse {
          animation: pulse 2s infinite;
        }

        .shake {
          animation: shake 0.4s ease;
        }
      `}</style>
      <div style={containerStyle}>
        {/* Left Side */}
        <div style={leftSideStyle} className="gradient-shift">
          <div>
            <div style={logoStyle}>TechCorp</div>
          <h1 style={headingStyle}>Get Support</h1>
          <p style={subheadingStyle}>We typically reply in &lt; 2 minutes</p>

          <div style={badgesContainerStyle}>
            <div style={aiBadgeStyle} className="pulse">🤖 AI Powered</div>
            <div style={badgeStyle}>⚡ Instant Response</div>
            <div style={badgeStyle}>🔒 Secure</div>
          </div>
        </div>

        <div style={bottomTextStyle}>
          Trusted by 10,000+ customers
        </div>
      </div>

      {/* Right Side */}
      <div style={rightSideStyle}>
        <div style={cardStyle} className="slide-up">
          {status === 'success' ? (
            <div style={successContainerStyle} className="slide-up">
              <div style={successCheckmarkStyle}>✅</div>
              <h2 style={successHeadingStyle}>Request Submitted!</h2>
              <p style={successLabelStyle}>Your Ticket ID:</p>
              <div style={ticketBoxStyle}>{ticketId}</div>
              <p style={successSubtextStyle}>We'll respond within 2 minutes</p>
              <button
                onClick={() => setStatus('idle')}
                style={secondaryButtonStyle}
              >
                Submit Another Request
              </button>
            </div>
          ) : (
            <>
              <h2 style={cardTitleStyle}>Submit a Request</h2>

              {status === 'error' && (
                <div style={errorBoxStyle} className="shake">
                  {errorMessage}
                </div>
              )}

              <form onSubmit={handleSubmit}>
                <div style={formGroupStyle}>
                  <label htmlFor="name" style={labelStyle}>
                    Name *
                  </label>
                  <input
                    type="text"
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    onFocus={() => setFocusedField('name')}
                    onBlur={() => setFocusedField('')}
                    required
                    style={getInputStyle('name')}
                  />
                </div>

                <div style={formGroupStyle}>
                  <label htmlFor="email" style={labelStyle}>
                    Email *
                  </label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    onFocus={() => setFocusedField('email')}
                    onBlur={() => setFocusedField('')}
                    required
                    style={getInputStyle('email')}
                  />
                </div>

                <div style={formGroupStyle}>
                  <label htmlFor="subject" style={labelStyle}>
                    Subject *
                  </label>
                  <input
                    type="text"
                    id="subject"
                    name="subject"
                    value={formData.subject}
                    onChange={handleChange}
                    onFocus={() => setFocusedField('subject')}
                    onBlur={() => setFocusedField('')}
                    required
                    style={getInputStyle('subject')}
                  />
                </div>

                <div style={formGroupStyle}>
                  <label htmlFor="category" style={labelStyle}>
                    Category *
                  </label>
                  <select
                    id="category"
                    name="category"
                    value={formData.category}
                    onChange={handleChange}
                    onFocus={() => setFocusedField('category')}
                    onBlur={() => setFocusedField('')}
                    required
                    style={getInputStyle('category')}
                  >
                    <option value="general">General Inquiry</option>
                    <option value="technical">Technical Support</option>
                    <option value="billing">Billing Issue</option>
                    <option value="feature">Feature Request</option>
                    <option value="bug">Bug Report</option>
                  </select>
                </div>

                <div style={formGroupStyle}>
                  <label htmlFor="message" style={labelStyle}>
                    Message *
                  </label>
                  <textarea
                    id="message"
                    name="message"
                    value={formData.message}
                    onChange={handleChange}
                    onFocus={() => setFocusedField('message')}
                    onBlur={() => setFocusedField('')}
                    required
                    maxLength={maxLength}
                    style={getTextareaStyle()}
                  />
                  <div style={characterCounterStyle}>
                    {messageLength}/{maxLength} characters
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={status === 'loading'}
                  onMouseEnter={() => setIsButtonHovered(true)}
                  onMouseLeave={() => setIsButtonHovered(false)}
                  style={getButtonStyle()}
                >
                  {status === 'loading' ? 'Sending...' : 'Submit Request'}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
      </div>
    </>
  );
}
