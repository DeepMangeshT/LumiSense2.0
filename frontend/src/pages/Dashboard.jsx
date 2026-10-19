import React, { useState, useEffect } from 'react';
import { 
  Sun, 
  Activity, 
  Thermometer, 
  Droplets, 
  Zap, 
  Award,
  Play, 
  Pause,
  RefreshCw
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  CartesianGrid, 
  Area, 
  ComposedChart,
  Bar
} from 'recharts';

import MetricCard from '../components/MetricCard';
import LiveGauge from '../components/LiveGauge';
import { api } from '../services/api';

export default function Dashboard({ systemStatus, setActiveTab }) {
  const [latestReading, setLatestReading] = useState(null);
  const [history, setHistory] = useState([]);
  const [efficiencyScore, setEfficiencyScore] = useState(null);
  const [isPaused, setIsPaused] = useState(false);
  const [timeWindow, setTimeWindow] = useState('5m'); // 1m, 5m, 15m, 1h
  const [errorNotice, setErrorNotice] = useState(null);

  // Determine limit from time window
  const getWindowLimit = (windowKey) => {
    switch (windowKey) {
      case '1m': return 25;
      case '5m': return 60;
      case '15m': return 150;
      case '1h': return 350;
      default: return 60;
    }
  };

  const fetchLiveTelemetry = async () => {
    try {
      const [latest, hist, eff] = await Promise.all([
        api.getLatestReading(),
        api.getHistory(getWindowLimit(timeWindow)),
        api.getEfficiencyScore().catch(() => null),
      ]);

      setLatestReading(latest);
      if (hist) setHistory(hist);
      if (eff) setEfficiencyScore(eff);
      setErrorNotice(null);
    } catch (err) {
      console.warn("Failed to fetch live telemetry:", err);
    }
  };

  useEffect(() => {
    fetchLiveTelemetry();
    if (isPaused) return;

    const interval = setInterval(fetchLiveTelemetry, 1500);
    return () => clearInterval(interval);
  }, [isPaused, timeWindow]);

  // Format historical chart data
  const chartData = history.map((item) => {
    const timeStr = item.timestamp ? new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '';
    return {
      time: timeStr,
      raw: item.light_raw,
      smoothed: item.light_smoothed,
      motion: item.motion,
      demand: item.predicted_demand || 0,
      isAnomaly: item.is_anomaly,
    };
  });

  const isMotionActive = latestReading?.motion === 1;
  const sourceLabel = latestReading?.source === 'real'
    ? 'Real Hardware'
    : latestReading?.source === 'simulated'
      ? 'Simulated Stream'
      : systemStatus?.arduino_connected
        ? 'Waiting for live data'
        : systemStatus?.simulation_mode
          ? 'Simulated Stream'
          : 'No sensor data';

  return (
    <div className="page-body">
      {/* Metrics Row */}
      <div className="stats-grid">
        {/* Metric 1: Light Level */}
        <MetricCard
          title="Relative Light Level"
          value={latestReading ? Math.round(latestReading.light_smoothed) : '--'}
          unit="ADC"
          subtext={`Raw sensor reading: ${latestReading?.light_raw ?? '--'} (10-bit)`}
          icon={Sun}
          accent="cyan"
          badgeText="LDR AO"
        />

        {/* Metric 2: PIR Occupancy */}
        <MetricCard
          title="Occupancy & Motion"
          value={latestReading ? (isMotionActive ? "Motion Detected" : "Clear / Idle") : "--"}
          subtext="HC-SR501 PIR sensor on pin D2"
          icon={Activity}
          accent={isMotionActive ? "amber" : "emerald"}
          badgeText={isMotionActive ? "OCCUPIED" : "VACANT"}
        />

        {/* Metric 3: Estimated Lighting Demand */}
        <MetricCard
          title="Estimated Lighting Demand"
          value={latestReading?.predicted_demand !== null && latestReading?.predicted_demand !== undefined 
            ? `${Math.round(latestReading.predicted_demand)}%` 
            : "--"}
          subtext="Random Forest regression estimate"
          icon={Zap}
          accent="purple"
          badgeText="ML MODEL"
        />

        {/* Metric 4: LumiSense Efficiency Score */}
        <MetricCard
          title="LumiSense Efficiency"
          value={efficiencyScore ? `${efficiencyScore.score} / 100` : "--"}
          subtext={efficiencyScore ? efficiencyScore.rating : "Analyzing usage patterns..."}
          icon={Award}
          accent={efficiencyScore?.score > 70 ? "emerald" : "amber"}
          badgeText="PROJECT SCORE"
        />

        {/* Metric 5: Live temperature from the connected DHT11 */}
        <MetricCard
          title="Ambient Temperature"
          value={latestReading?.temperature !== null && latestReading?.temperature !== undefined 
            ? `${latestReading.temperature} °C` 
            : "-- °C"}
          subtext={latestReading?.temperature !== null && latestReading?.temperature !== undefined ? "Live DHT11 reading" : "Waiting for DHT11 reading..."}
          icon={Thermometer}
          accent="cyan"
          badgeText={latestReading?.temperature !== null && latestReading?.temperature !== undefined ? "LIVE" : "DHT11 PENDING"}
        />

        {/* Metric 6: Live humidity from the connected DHT11 */}
        <MetricCard
          title="Relative Humidity"
          value={latestReading?.humidity !== null && latestReading?.humidity !== undefined 
            ? `${latestReading.humidity} %` 
            : "-- %"}
          subtext={latestReading?.humidity !== null && latestReading?.humidity !== undefined ? "Live DHT11 reading" : "Waiting for DHT11 reading..."}
          icon={Droplets}
          accent="cyan"
          badgeText={latestReading?.humidity !== null && latestReading?.humidity !== undefined ? "LIVE" : "DHT11 PENDING"}
        />
      </div>

      {/* Main Real-Time Telemetry & Gauges Section */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2.5fr) minmax(0, 1fr)', gap: '24px' }}>
        
        {/* Real-Time Chart Card */}
        <div className="glass-card chart-card">
          <div className="chart-header">
            <div className="chart-title">
              <h3>Live Environmental Telemetry</h3>
              <p>Continuous LDR relative light & PIR occupancy stream</p>
            </div>

            <div className="chart-controls">
              {/* Window selectors */}
              {['1m', '5m', '15m', '1h'].map((w) => (
                <button
                  key={w}
                  className={`pill-btn ${timeWindow === w ? 'active' : ''}`}
                  onClick={() => setTimeWindow(w)}
                >
                  {w}
                </button>
              ))}

              {/* Pause / Resume Button */}
              <button 
                className="btn btn-secondary" 
                onClick={() => setIsPaused(!isPaused)}
                style={{ padding: '6px 12px', fontSize: '0.75rem', marginLeft: '6px' }}
                title={isPaused ? "Resume Live Stream" : "Pause Live Stream"}
              >
                {isPaused ? <Play size={13} color="#10B981" /> : <Pause size={13} color="#F59E0B" />}
                <span>{isPaused ? "Resume" : "Pause"}</span>
              </button>
            </div>
          </div>

          <div style={{ width: '100%', height: 320 }}>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData}>
                  <defs>
                    <linearGradient id="lightFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#38BDF8" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#38BDF8" stopOpacity={0.0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                  <XAxis 
                    dataKey="time" 
                    stroke="var(--text-muted)" 
                    fontSize={11} 
                    tickLine={false}
                  />
                  <YAxis 
                    stroke="var(--text-muted)" 
                    fontSize={11} 
                    domain={[0, 1023]}
                    tickLine={false}
                    label={{ value: 'Light (ADC 0-1023)', angle: -90, position: 'insideLeft', fill: 'var(--text-muted)', fontSize: 11 }}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(15, 23, 42, 0.95)', 
                      borderColor: 'var(--border-strong)', 
                      borderRadius: '8px',
                      color: 'var(--text-primary)',
                      fontSize: '0.8rem'
                    }} 
                  />
                  {/* Smoothed Light Area */}
                  <Area 
                    type="monotone" 
                    dataKey="smoothed" 
                    name="Smoothed Light" 
                    stroke="#38BDF8" 
                    strokeWidth={2.5} 
                    fillOpacity={1} 
                    fill="url(#lightFill)" 
                    isAnimationActive={false}
                  />
                  {/* Raw Light Subtle Line */}
                  <Line 
                    type="monotone" 
                    dataKey="raw" 
                    name="Raw Light" 
                    stroke="#94A3B8" 
                    strokeWidth={1} 
                    strokeDasharray="2 2" 
                    dot={false}
                    isAnimationActive={false}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
                Waiting for incoming sensor telemetry...
              </div>
            )}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '14px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            <div style={{ display: 'flex', gap: '16px' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width: 12, height: 3, backgroundColor: '#38BDF8', display: 'inline-block' }} />
                Smoothed (Moving Avg N=5)
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width: 12, height: 2, backgroundColor: '#94A3B8', borderStyle: 'dashed', display: 'inline-block' }} />
                Raw ADC (0-1023)
              </span>
            </div>
            <div>
              {isPaused ? <span style={{ color: '#F59E0B' }}>Stream Paused</span> : <span style={{ color: '#10B981' }}>Live Streaming</span>}
            </div>
          </div>
        </div>

        {/* Live Gauges & System Sidebar Card */}
        <div className="glass-card chart-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div className="chart-title" style={{ marginBottom: '16px' }}>
              <h3>Current Levels</h3>
              <p>Real-time visual dial</p>
            </div>

            <div style={{ padding: '10px 0' }}>
              <LiveGauge 
                value={latestReading?.light_smoothed || 0} 
                max={1023} 
                label="Relative Light Level" 
              />
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '16px', marginTop: '16px' }}>
            <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px', textTransform: 'uppercase' }}>
              Hardware Telemetry State
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.82rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Microcontroller:</span>
                <span style={{ fontWeight: 600 }}>Arduino Uno R3</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Interface:</span>
                <span>USB Serial @ 9600 Bd</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Source:</span>
                <span style={{ color: latestReading?.source === 'real' ? '#10B981' : latestReading?.source === 'simulated' ? '#C084FC' : 'var(--text-muted)', fontWeight: 600 }}>
                  {sourceLabel}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>LDR Calibration:</span>
                <span style={{ fontStyle: 'italic' }}>Relative units (uncalibrated)</span>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* Telemetry Stream Log Table */}
      <div className="glass-card chart-card">
        <div className="chart-header">
          <div className="chart-title">
            <h3>Recent Sensor Records</h3>
            <p>Validated frames ingested into SQLite database</p>
          </div>
          <button 
            className="btn btn-secondary" 
            onClick={fetchLiveTelemetry}
            style={{ padding: '6px 12px', fontSize: '0.78rem' }}
          >
            <RefreshCw size={13} />
            <span>Refresh</span>
          </button>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="custom-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Server Timestamp</th>
                <th>Raw Light</th>
                <th>Smoothed Light</th>
                <th>Motion (PIR)</th>
                <th>Temp / Humidity</th>
                <th>Predicted Demand</th>
                <th>Status / Source</th>
              </tr>
            </thead>
            <tbody>
              {history.slice(-8).reverse().map((row) => (
                <tr key={row.id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>#{row.id}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                    {new Date(row.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </td>
                  <td><strong>{row.light_raw}</strong></td>
                  <td style={{ color: '#38BDF8', fontWeight: 600 }}>{row.light_smoothed}</td>
                  <td>
                    <span style={{ 
                      color: row.motion === 1 ? '#F59E0B' : '#10B981', 
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}>
                      <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: row.motion === 1 ? '#F59E0B' : '#10B981' }} />
                      {row.motion === 1 ? 'Detected (1)' : 'Idle (0)'}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-muted)' }}>
                    {row.temperature !== null ? `${row.temperature}°C / ${row.humidity}%` : '-- / --'}
                  </td>
                  <td style={{ color: '#C084FC', fontWeight: 600 }}>
                    {row.predicted_demand !== null ? `${Math.round(row.predicted_demand)}%` : '--'}
                  </td>
                  <td>
                    {row.is_anomaly ? (
                      <span className="badge badge-warning" style={{ fontSize: '0.7rem' }}>ANOMALY</span>
                    ) : (
                      <span style={{ fontSize: '0.75rem', color: row.source === 'real' ? '#10B981' : '#C084FC' }}>
                        {row.source === 'real' ? 'Real Uno' : 'Simulated'}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
