import React, { useState, useEffect } from 'react';
import { 
  Sliders, 
  Cpu, 
  Activity, 
  RefreshCw, 
  Save, 
  CheckCircle, 
  AlertCircle,
  HardDrive,
  Info
} from 'lucide-react';
import { api } from '../services/api';

export default function Settings({ systemStatus, refreshStatus }) {
  const [ports, setPorts] = useState([]);
  const [selectedPort, setSelectedPort] = useState('AUTO');
  const [baudRate, setBaudRate] = useState(9600);
  const [smoothingWindow, setSmoothingWindow] = useState(5);
  const [simulationMode, setSimulationMode] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const fetchPorts = async () => {
    try {
      const data = await api.getSerialPorts();
      setPorts(data.ports || []);
      setStatusMessage(data.status_message || '');
      if (data.current_configured_port) {
        setSelectedPort(data.current_configured_port);
      }
    } catch (err) {
      console.warn("Could not fetch serial ports:", err);
    }
  };

  useEffect(() => {
    fetchPorts();
    if (systemStatus) {
      if (systemStatus.baud_rate) setBaudRate(systemStatus.baud_rate);
      if (systemStatus.smoothing_window) setSmoothingWindow(systemStatus.smoothing_window);
      if (systemStatus.simulation_mode !== undefined) setSimulationMode(systemStatus.simulation_mode);
    }
  }, [systemStatus]);

  const handleSave = async () => {
    setIsSaving(true);
    setFeedback(null);
    try {
      await api.updateSettings({
        serial_port: selectedPort,
        baud_rate: baudRate,
        smoothing_window: smoothingWindow,
        simulation_mode: simulationMode,
      });
      setFeedback({ type: 'success', message: 'Settings saved and applied successfully!' });
      if (refreshStatus) refreshStatus();
      await fetchPorts();
    } catch (err) {
      setFeedback({ type: 'error', message: err.message });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="page-body">
      <div className="glass-card" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '1.2rem', color: 'var(--text-primary)', marginBottom: '4px' }}>
          Hardware & System Configuration
        </h3>
        <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
          Configure Arduino Uno serial communication parameters, signal smoothing, and simulation behavior
        </p>

        {feedback && (
          <div style={{ 
            marginTop: '16px', 
            padding: '12px', 
            borderRadius: '8px', 
            fontSize: '0.84rem',
            background: feedback.type === 'success' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(244, 63, 94, 0.12)',
            border: `1px solid ${feedback.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
            color: feedback.type === 'success' ? '#6EE7B7' : '#FDA4AF'
          }}>
            {feedback.message}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginTop: '24px' }}>
          
          {/* Section 1: Arduino Serial Configuration */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <h4 style={{ fontSize: '0.95rem', color: 'var(--accent-cyan)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Cpu size={18} />
              USB Serial Interface (Arduino Uno)
            </h4>

            {/* COM Port Selector */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <label style={{ fontSize: '0.84rem', fontWeight: 600 }}>COM / Serial Port</label>
                <button 
                  onClick={fetchPorts} 
                  style={{ background: 'none', border: 'none', color: 'var(--accent-cyan)', cursor: 'pointer', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                >
                  <RefreshCw size={12} /> Scan Ports
                </button>
              </div>

              <select
                value={selectedPort}
                onChange={(e) => setSelectedPort(e.target.value)}
                style={{ 
                  width: '100%', 
                  padding: '10px 14px', 
                  borderRadius: '8px', 
                  background: 'var(--bg-input)', 
                  border: '1px solid var(--border-subtle)', 
                  color: 'var(--text-primary)',
                  fontSize: '0.88rem'
                }}
              >
                <option value="AUTO">AUTO (Auto-Detect Connected Arduino)</option>
                {ports.map((p) => (
                  <option key={p.device} value={p.device}>
                    {p.device} - {p.description} {p.is_arduino_candidate ? '★ [Detected Arduino]' : ''}
                  </option>
                ))}
              </select>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                {statusMessage || 'Selecting AUTO will automatically probe available COM ports.'}
              </div>
            </div>

            {/* Baud Rate */}
            <div>
              <label style={{ fontSize: '0.84rem', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                Baud Rate
              </label>
              <select
                value={baudRate}
                onChange={(e) => setBaudRate(Number(e.target.value))}
                style={{ 
                  width: '100%', 
                  padding: '10px 14px', 
                  borderRadius: '8px', 
                  background: 'var(--bg-input)', 
                  border: '1px solid var(--border-subtle)', 
                  color: 'var(--text-primary)',
                  fontSize: '0.88rem'
                }}
              >
                <option value={9600}>9600 baud (Default Arduino Sketch)</option>
                <option value={19200}>19200 baud</option>
                <option value={38400}>38400 baud</option>
                <option value={57600}>57600 baud</option>
                <option value={115200}>115200 baud</option>
              </select>
            </div>

            {/* Connection Status Box */}
            <div style={{ 
              padding: '12px 16px', 
              background: 'var(--bg-input)', 
              borderRadius: '8px', 
              border: '1px solid var(--border-subtle)',
              fontSize: '0.82rem'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Connection Status:</span>
                <span style={{ color: systemStatus?.arduino_connected ? '#10B981' : '#F43F5E', fontWeight: 600 }}>
                  {systemStatus?.arduino_connected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Active Port:</span>
                <span>{systemStatus?.serial_port || 'None'}</span>
              </div>
            </div>
          </div>

          {/* Section 2: Sensor Signal Processing & Simulation */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <h4 style={{ fontSize: '0.95rem', color: '#A855F7', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sliders size={18} />
              Signal Filtering & Simulation
            </h4>

            {/* Moving Average Smoothing Window Slider */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <label style={{ fontSize: '0.84rem', fontWeight: 600 }}>
                  LDR Smoothing Window (N)
                </label>
                <span style={{ color: 'var(--accent-cyan)', fontWeight: 700 }}>{smoothingWindow} samples</span>
              </div>
              <input
                type="range"
                min="1"
                max="20"
                value={smoothingWindow}
                onChange={(e) => setSmoothingWindow(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--accent-cyan)' }}
              />
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                Larger window (e.g. 5-10) eliminates sensor noise but introduces slight latency. Window of 1 = raw signal.
              </div>
            </div>

            {/* Simulation Mode Toggle */}
            <div style={{ 
              padding: '14px 16px', 
              background: 'var(--bg-input)', 
              borderRadius: '8px', 
              border: '1px solid var(--border-subtle)'
            }}>
              <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}>
                <div>
                  <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    Sensor Simulation Mode
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    Feeds realistic diurnal cycles & occupant motion when Arduino is unplugged
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={simulationMode}
                  onChange={(e) => setSimulationMode(e.target.checked)}
                  style={{ width: '20px', height: '20px', accentColor: '#A855F7' }}
                />
              </label>
            </div>

            {/* Hardware Note */}
            <div style={{ 
              padding: '12px 14px', 
              background: 'rgba(255, 255, 255, 0.03)', 
              borderRadius: '8px', 
              border: '1px solid var(--border-subtle)',
              fontSize: '0.78rem',
              color: 'var(--text-muted)',
              display: 'flex',
              gap: '8px'
            }}>
              <Info size={16} color="#38BDF8" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                When an Arduino Uno is plugged into the PC via USB, LumiSense seamlessly switches to real hardware telemetry 
                without restarting the software.
              </div>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div style={{ marginTop: '28px', display: 'flex', justifyContent: 'flex-end' }}>
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={isSaving}
            style={{ padding: '11px 24px' }}
          >
            <Save size={16} />
            <span>{isSaving ? 'Applying Changes...' : 'Save Settings'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
