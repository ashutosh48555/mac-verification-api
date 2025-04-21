import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.POSTGRES_URL,
});

export default async function handler(req, res) {
  if (req.method === 'GET') {
    const result = await pool.query('SELECT * FROM verifications');
    res.json(result.rows);
  } else if (req.method === 'POST') {
    const { mac_address, start_datetime, expiry_datetime, api_key } = req.body;
    await pool.query(
      'INSERT INTO verifications (mac_address, start_datetime, expiry_datetime, api_key) VALUES ($1, $2, $3, $4)',
      [mac_address, start_datetime, expiry_datetime, api_key]
    );
    res.status(201).json({ success: true });
  } else if (req.method === 'DELETE') {
    const id = req.query.id;
    await pool.query('DELETE FROM verifications WHERE id = $1', [id]);
    res.status(200).json({ success: true });
  } else {
    res.status(405).json({ message: 'Method not allowed' });
  }
}