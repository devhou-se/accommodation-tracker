const express = require('express');
const app = express();
const port = process.env.PORT || 8082;

// Middleware to parse JSON bodies
app.use(express.json({ limit: '10mb' }));

// Store received notifications for inspection
const notifications = [];

// CORS headers
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization');
  
  if (req.method === 'OPTIONS') {
    res.sendStatus(200);
  } else {
    next();
  }
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
    notifications_received: notifications.length
  });
});

// Main notification endpoint
app.post('/notify', (req, res) => {
  const notification = {
    ...req.body,
    received_at: new Date().toISOString(),
    headers: req.headers
  };
  
  notifications.push(notification);
  
  console.log('🔔 NOTIFICATION RECEIVED:');
  console.log('='.repeat(50));
  console.log('Time:', notification.received_at);
  console.log('Accommodation:', req.body.accommodation_name || 'Unknown');
  console.log('Available Dates:', req.body.available_dates || []);
  console.log('Location:', req.body.location || 'Unknown');
  console.log('Link:', req.body.link || 'No link');
  console.log('Discovered At:', req.body.discovered_at || 'Unknown');
  console.log('Price Info:', req.body.price_info || 'None');
  console.log('='.repeat(50));
  
  // Simulate different response scenarios for testing
  if (req.body._test === true) {
    console.log('🧪 Test notification detected');
  }
  
  // Always return success for this mock
  res.json({ 
    status: 'success',
    message: 'Notification received',
    notification_id: notifications.length,
    timestamp: notification.received_at
  });
});

// Get all received notifications (for debugging)
app.get('/notifications', (req, res) => {
  res.json({
    count: notifications.length,
    notifications: notifications
  });
});

// Clear all notifications
app.delete('/notifications', (req, res) => {
  const cleared = notifications.length;
  notifications.length = 0;
  res.json({ 
    message: `Cleared ${cleared} notifications`,
    count: 0
  });
});

// Catch-all for other paths
app.all('*', (req, res) => {
  console.log(`📥 Received ${req.method} request to ${req.path}`);
  console.log('Headers:', req.headers);
  if (req.body && Object.keys(req.body).length > 0) {
    console.log('Body:', JSON.stringify(req.body, null, 2));
  }
  
  res.json({
    status: 'received',
    method: req.method,
    path: req.path,
    timestamp: new Date().toISOString()
  });
});

// Error handling
app.use((error, req, res, next) => {
  console.error('❌ Error:', error.message);
  res.status(500).json({
    status: 'error',
    message: error.message,
    timestamp: new Date().toISOString()
  });
});

// Start server
app.listen(port, '0.0.0.0', () => {
  console.log(`🚀 Mock Notification Service running on port ${port}`);
  console.log(`📍 Health check: http://localhost:${port}/health`);
  console.log(`📨 Notification endpoint: http://localhost:${port}/notify`);
  console.log(`🔍 View notifications: http://localhost:${port}/notifications`);
});