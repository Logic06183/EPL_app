// Firebase Cloud Functions entry point
const functions = require('firebase-functions');
const { spawn } = require('child_process');
const path = require('path');

// Export the Python FastAPI app as a Cloud Function
exports.api = functions.https.onRequest((req, res) => {
  // Set CORS headers
  res.set('Access-Control-Allow-Origin', '*');
  res.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.set('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  
  if (req.method === 'OPTIONS') {
    res.status(200).send('');
    return;
  }

  // Run the Python FastAPI application
  const python = spawn('python3', [
    path.join(__dirname, 'api_production.py')
  ], {
    env: {
      ...process.env,
      PORT: '8080',
      NEWS_API_KEY: 'e36350769b6341bb81b832a84442e6ad',
      PAYSTACK_PUBLIC_KEY: 'pk_test_0f6e3092te89f0f4ad18268d1f3884258afc37bc'
    }
  });

  let output = '';
  let errorOutput = '';

  python.stdout.on('data', (data) => {
    output += data.toString();
  });

  python.stderr.on('data', (data) => {
    errorOutput += data.toString();
  });

  python.on('close', (code) => {
    if (code === 0) {
      try {
        const result = JSON.parse(output);
        res.status(200).json(result);
      } catch (e) {
        res.status(200).send(output);
      }
    } else {
      console.error('Python error:', errorOutput);
      res.status(500).json({
        error: 'Internal server error',
        details: errorOutput
      });
    }
  });

  // Handle timeout
  setTimeout(() => {
    python.kill();
    res.status(408).json({ error: 'Request timeout' });
  }, 55000); // Firebase functions timeout at 60s
});

// Simple health check
exports.health = functions.https.onRequest((req, res) => {
  res.set('Access-Control-Allow-Origin', '*');
  res.status(200).json({
    status: 'healthy',
    service: 'FPL AI Pro',
    version: '1.0.0',
    timestamp: new Date().toISOString()
  });
});