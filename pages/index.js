const { useState, useEffect } = require('react');
const styles = require('../styles/Home.module.css');

function Home() {
  const [verifications, setVerifications] = useState([]);
  const [form, setForm] = useState({
    mac_address: '',
    start_datetime: '',
    expiry_datetime: '',
    api_key: '',
  });

  const fetchVerifications = async () => {
    const res = await fetch('/api/verifications');
    const data = await res.json();
    setVerifications(data);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    await fetch('/api/verifications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    fetchVerifications();
    setForm({ mac_address: '', start_datetime: '', expiry_datetime: '', api_key: '' });
  };

  const handleDelete = async (id) => {
    await fetch(`/api/verifications/${id}`, { method: 'DELETE' });
    fetchVerifications();
  };

  useEffect(() => {
    fetchVerifications();
  }, []);

  return (
    <div className={styles.container}>
      <h1>Verification Dashboard</h1>
      <form onSubmit={handleSubmit} className={styles.form}>
        <input
          type="text"
          placeholder="MAC Address"
          value={form.mac_address}
          onChange={(e) => setForm({ ...form, mac_address: e.target.value })}
          required
        />
        <input
          type="datetime-local"
          value={form.start_datetime}
          onChange={(e) => setForm({ ...form, start_datetime: e.target.value })}
          required
        />
        <input
          type="datetime-local"
          value={form.expiry_datetime}
          onChange={(e) => setForm({ ...form, expiry_datetime: e.target.value })}
          required
        />
        <input
          type="text"
          placeholder="API Key"
          value={form.api_key}
          onChange={(e) => setForm({ ...form, api_key: e.target.value })}
          required
        />
        <button type="submit">Add Verification</button>
      </form>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>MAC Address</th>
            <th>Start Datetime</th>
            <th>Expiry Datetime</th>
            <th>API Key</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {verifications.map((v) => (
            <tr key={v.id}>
              <td>{v.mac_address}</td>
              <td>{v.start_datetime}</td>
              <td>{v.expiry_datetime}</td>
              <td>{v.api_key}</td>
              <td>
                <button onClick={() => handleDelete(v.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

module.exports = Home;