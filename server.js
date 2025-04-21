const express = require('express');
const { Pool } = require('pg');
const cors = require('cors');
require('dotenv').config();

const app = express();
app.use(cors());
app.use(express.json());

// Postgres connection
const pool = new Pool({
  connectionString: process.env.POSTGRES_URL,
});

// Verification endpoint
app.post('/api/verify', async (req, res) => {
  const { mac_address } = req.body;
  const now = new Date();

  try {
    const result = await pool.query(
      'SELECT * FROM verifications WHERE mac_address = $1 AND start_datetime <= $2 AND expiry_datetime >= $2',
      [mac_address, now]
    );

    if (result.rows.length > 0) {
      res.json({ success: true, api_key: result.rows[0].api_key });
    } else {
      res.status(403).json({ success: false, message: 'Invalid MAC address or time range' });
    }
  } catch (error) {
    console.error('Verification error:', error);
    res.status(500).json({ success: false, message: 'Server error' });
  }
});

module.exports = app;