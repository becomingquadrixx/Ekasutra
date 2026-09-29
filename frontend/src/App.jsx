/**
 * EKASUTRA Frontend UI
 * Built by Team QuadriX
 */
import React, { useState, useEffect, useRef } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import './App.css';

const API_BASE = 'http://localhost:8000';

function App() {
  const [activeTab, setActiveTab] = useState('reviewer');
  
  return (
    <div className="container">
      <header className="header">
        <div>
          <h1>EKASUTRA <span>Common National Material Code Portal</span></h1>
        </div>
        <div className="tabs">
          <button 
            className={`tab ${activeTab === 'reviewer' ? 'active' : ''}`}
            onClick={() => setActiveTab('reviewer')}
          >
            Reviewer Dashboard
          </button>
          <button 
            className={`tab ${activeTab === 'analytics' ? 'active' : ''}`}
            onClick={() => setActiveTab('analytics')}
          >
            Analytics Dashboard
          </button>
          <button 
            className={`tab ${activeTab === 'upload' ? 'active' : ''}`}
            onClick={() => setActiveTab('upload')}
          >
            Upload CSV
          </button>
        </div>
      </header>
      <div className="content-area">
        {activeTab === 'reviewer' && <ReviewerDashboard />}
        {activeTab === 'analytics' && <AnalyticsDashboard />}
        {activeTab === 'upload' && <UploadPanel />}
      </div>
    </div>
  );
}

function ReviewerDashboard() {
  const [matches, setMatches] = useState([]);
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchMatches = async () => {
    try {
      const res = await fetch(`${API_BASE}/matches?status=pending_review`);
      const data = await res.json();
      setMatches(data.matches || []);
    } catch (err) {
      console.error("Failed to fetch matches", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/matches?status=pending_review`)
      .then((res) => res.json())
      .then((data) => {
        if (!cancelled) setMatches(data.matches || []);
      })
      .catch((err) => console.error("Failed to fetch matches", err))
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const handleAction = async (id, action) => {
    try {
      await fetch(`${API_BASE}/matches/${id}/${action}`, { method: 'POST' });
      setSelectedMatch(null);
      fetchMatches();
    } catch (err) {
      console.error(`Failed to ${action} match`, err);
    }
  };

  if (loading && matches.length === 0) {
    return <div className="empty-state">Loading matches...</div>;
  }

  return (
    <div>
      {selectedMatch ? (
        <DetailView 
          match={selectedMatch} 
          onBack={() => setSelectedMatch(null)} 
          onAction={handleAction} 
        />
      ) : (
        <MatchList matches={matches} onSelect={setSelectedMatch} />
      )}
    </div>
  );
}

function MatchList({ matches, onSelect }) {
  if (matches.length === 0) {
    return <div className="empty-state">No pending matches to review.</div>;
  }

  return (
    <div className="list-container">
      <table className="matches-table">
        <colgroup>
          <col className="col-mat" />
          <col className="col-mat" />
          <col className="col-score" />
          <col className="col-level" />
        </colgroup>
        <thead>
          <tr>
            <th>Material A</th>
            <th>Material B</th>
            <th>Sim. Score</th>
            <th>Decision Level</th>
          </tr>
        </thead>
        <tbody>
          {matches.map((m) => (
            <tr key={m.match_id} onClick={() => onSelect(m)} className="clickable-row">
              <td>
                <div className="cpse-badge">{m.material_a.cpse_name}</div>
                <div className="desc">{m.material_a.description}</div>
              </td>
              <td>
                <div className="cpse-badge">{m.material_b.cpse_name}</div>
                <div className="desc">{m.material_b.description}</div>
              </td>
              <td>
                <div className="score-badge">{(m.semantic_score * 100).toFixed(1)}%</div>
              </td>
              <td>
                <div className={`level-badge ${m.decision_level}`}>
                  {m.decision_level.replace(/_/g, ' ').toUpperCase()}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DetailView({ match, onBack, onAction }) {
  const specs = Object.entries(match.spec_agreement || {});
  const specTypes = match.spec_types || {};

  const getSpecValue = (material, specName) => {
    const raw = material.raw_specs || {};
    return raw[`spec_${specName}`] || raw[specName] || '—';
  };

  const typeBadge = (type) => {
    if (type === 'critical') return <span className="type-badge critical">CRITICAL</span>;
    if (type === 'soft') return <span className="type-badge soft">SOFT</span>;
    return <span className="type-badge irrelevant">IRRELEVANT</span>;
  };

  return (
    <div className="detail-container">
      <button className="back-btn" onClick={onBack}>← Back to List</button>

      <div className="cards-row">
        <div className="card">
          <span className="cpse-badge">{match.material_a.cpse_name}</span>
          <h2>{match.material_a.description}</h2>
          <p className="normalized"><strong>Normalized:</strong> {match.material_a.normalized_description}</p>
        </div>
        <div className="score-center">
          <div className="score-badge large">{(match.semantic_score * 100).toFixed(1)}% Match</div>
          <div className={`level-badge large ${match.decision_level}`}>
            {match.decision_level.replace(/_/g, ' ').toUpperCase()}
          </div>
        </div>
        <div className="card">
          <span className="cpse-badge">{match.material_b.cpse_name}</span>
          <h2>{match.material_b.description}</h2>
          <p className="normalized"><strong>Normalized:</strong> {match.material_b.normalized_description}</p>
        </div>
      </div>

      <div className="specs-section">
        <div className="specs-section-header">Specification Comparison</div>
        {specs.length > 0 ? (
          <table className="specs-table">
            <colgroup>
              <col className="col-spec" />
              <col className="col-val" />
              <col className="col-val" />
              <col className="col-crit" />
              <col className="col-result" />
            </colgroup>
            <thead>
              <tr>
                <th>Spec Name</th>
                <th>Value A ({match.material_a.cpse_name})</th>
                <th>Value B ({match.material_b.cpse_name})</th>
                <th>Critical?</th>
                <th>Pass / Fail</th>
              </tr>
            </thead>
            <tbody>
              {specs.map(([spec, result]) => {
                const specType = specTypes[spec] || 'irrelevant';
                const isCritical = specType === 'critical';
                return (
                  <tr key={spec} className={isCritical ? 'critical-row' : ''}>
                    <td className="spec-name">{spec.replace(/_/g, ' ')}</td>
                    <td className="spec-value">{getSpecValue(match.material_a, spec)}</td>
                    <td className="spec-value">{getSpecValue(match.material_b, spec)}</td>
                    <td>{typeBadge(specType)}</td>
                    <td>
                      <span className={`status-badge ${result}`}>
                        {result === 'agree' ? 'PASS' : result === 'disagree' ? 'FAIL' : 'N/A'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <p>No explicit specifications extracted for comparison.</p>
        )}
      </div>

      <div className="action-buttons">
        <button className="btn btn-reject" onClick={() => onAction(match.match_id, 'reject')}>
          Reject
        </button>
        <button className="btn btn-approve" onClick={() => onAction(match.match_id, 'approve')}>
          Approve &amp; Generate CNMC
        </button>
      </div>
    </div>
  );
}

function AnalyticsDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const res = await fetch(`${API_BASE}/analytics/summary`);
        const json = await res.json();
        setData(json);
      } catch (e) {
        console.error("Failed to fetch analytics", e);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  if (loading || !data) {
    return <div className="empty-state">Loading analytics...</div>;
  }

  // Format data for charts
  const duplicateRateData = Object.entries(data.duplicate_rate_by_category).map(([cat, stats]) => ({
    name: cat,
    rate: stats.rate * 100 // convert to percentage
  }));

  const pendingData = Object.entries(data.pending_reviews_by_category).map(([cat, count]) => ({
    name: cat,
    count: count
  }));

  const progressData = [
    { name: 'Mapped to CNMC', value: data.overall_progress_percent },
    { name: 'Pending/Unmapped', value: 100 - data.overall_progress_percent }
  ];
  const COLORS = ['#166534', '#9ca3af'];

  return (
    <div className="analytics-container">
      <div className="chart-row">
        <div className="chart-card">
          <h3>Duplicate / Match Rate by Category</h3>
          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={duplicateRateData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis unit="%" />
                <Tooltip formatter={(value) => `${value.toFixed(1)}%`} />
                <Bar dataKey="rate" fill="#2c5282" name="Duplicate Rate" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="chart-card">
          <h3>Pending Reviews Backlog</h3>
          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={pendingData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#92400e" name="Pending Count" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="chart-row single">
        <div className="chart-card full-width">
          <h3>Overall CNMC Mapping Progress</h3>
          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={progressData}
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                  label={({name, value}) => `${name}: ${value.toFixed(1)}%`}
                >
                  {progressData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => `${value.toFixed(1)}%`} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}

function UploadPanel() {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => setDragging(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.name.endsWith('.csv')) {
      setFile(droppedFile);
      setResult(null);
      setError(null);
    } else {
      setError('Please upload a .csv file');
    }
  };

  const handleFileSelect = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setResult(null);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API_BASE}/ingest`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Upload failed');
      }
      const data = await res.json();
      setResult(data);
      setFile(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-container">
      <div className="upload-card">
        <h2>Ingest CPSE Material Data</h2>
        <p className="upload-subtitle">
          Upload a CSV file with columns: <code>cpse_name</code>, <code>original_code</code>, <code>description</code>, and optional <code>spec_*</code> columns.
        </p>

        <div
          className={`drop-zone ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          {file ? (
            <div className="file-info">
              <span className="file-name">{file.name}</span>
              <span className="file-size">({(file.size / 1024).toFixed(1)} KB)</span>
            </div>
          ) : (
            <div className="drop-prompt">
              <p>Drop CSV here or click to browse</p>
            </div>
          )}
        </div>

        <button
          className="btn btn-upload"
          onClick={handleUpload}
          disabled={!file || uploading}
        >
          {uploading ? 'Processing...' : 'Upload & Process'}
        </button>

        {error && (
          <div className="upload-error">
            <strong>Error:</strong> {error}
          </div>
        )}

        {result && (
          <div className="upload-result">
            <h3>Ingestion Complete</h3>
            <div className="result-stats">
              <div className="stat-card">
                <div className="stat-value">{result.rows_inserted}</div>
                <div className="stat-label">Materials Inserted</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{result.matches_evaluated}</div>
                <div className="stat-label">Matches Evaluated</div>
              </div>
            </div>
            
            {result.normalization_sample && result.normalization_sample.length > 0 && (
              <div className="normalization-sample">
                <h4>Normalization Sample (Lexicon Effect)</h4>
                <table className="sample-table">
                  <thead>
                    <tr>
                      <th>Original (Raw)</th>
                      <th>Normalized</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.normalization_sample.map((s, i) => (
                      <tr key={i}>
                        <td className="raw-text">{s.raw}</td>
                        <td className="normalized-text">{s.normalized}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
