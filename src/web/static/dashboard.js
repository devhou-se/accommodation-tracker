/**
 * Interactive dashboard JavaScript for the Gassho-zukuri Tracker
 * Handles real-time updates, charts, and user interactions
 */

class Gassho-zukuriDashboard {
    constructor() {
        this.charts = {};
        this.refreshInterval = 30000; // 30 seconds
        this.intervalId = null;
        
        // Initialize dashboard
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        await this.loadInitialData();
        this.startAutoRefresh();
        this.updateCurrentTime();
        
        // Update time every second
        setInterval(() => this.updateCurrentTime(), 1000);
    }
    
    setupEventListeners() {
        // Refresh button
        document.getElementById('refresh-status')?.addEventListener('click', () => {
            this.refreshData();
        });
        
        // Test notification button
        document.getElementById('test-notification')?.addEventListener('click', () => {
            this.testNotification();
        });
        
        // Check now button
        document.getElementById('check-now')?.addEventListener('click', () => {
            this.triggerManualCheck();
        });
        
        // Handle visibility change to pause/resume updates
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stopAutoRefresh();
            } else {
                this.startAutoRefresh();
                this.refreshData();
            }
        });
    }
    
    updateCurrentTime() {
        const now = new Date();
        const timeString = now.toLocaleString('en-US', {
            timeZone: 'Asia/Tokyo',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
        
        const timeElement = document.getElementById('current-time');
        if (timeElement) {
            timeElement.textContent = `${timeString} JST`;
        }
    }
    
    async loadInitialData() {
        await Promise.all([
            this.updateSystemStatus(),
            this.updateConfiguration(),
            this.updateRecentActivity(),
            this.updateAccommodations(),
            this.updateMetrics()
        ]);
    }
    
    async refreshData() {
        this.showToast('Refreshing data...', 'info');
        await this.loadInitialData();
        this.showToast('Data refreshed successfully! 🎌', 'success');
    }
    
    startAutoRefresh() {
        if (this.intervalId) return;
        
        this.intervalId = setInterval(async () => {
            try {
                await this.loadInitialData();
            } catch (error) {
                console.error('Auto-refresh failed:', error);
            }
        }, this.refreshInterval);
    }
    
    stopAutoRefresh() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }
    
    async updateSystemStatus() {
        try {
            const response = await axios.get('/api/status');
            const status = response.data;
            
            // Update status badge
            this.updateStatusBadge(status.status);
            
            // Update quick stats
            document.getElementById('checks-today').textContent = status.checks_today || 0;
            document.getElementById('accommodations-checked').textContent = status.accommodations_checked || 0;
            document.getElementById('availabilities-found').textContent = status.availabilities_found || 0;
            document.getElementById('uptime').textContent = status.uptime_human || '-';
            
            // Update status details
            document.getElementById('current-status').textContent = this.capitalizeFirst(status.status || 'unknown');
            document.getElementById('last-check').textContent = this.formatDateTime(status.last_check);
            document.getElementById('target-dates').textContent = status.target_dates?.join(', ') || 'None configured';
            document.getElementById('check-interval').textContent = `${Math.floor((status.check_interval || 0) / 60)} minutes`;
            document.getElementById('success-rate').textContent = `${status.metrics?.success_rate || 0}%`;
            
        } catch (error) {
            console.error('Failed to update system status:', error);
            this.updateStatusBadge('error');
        }
    }
    
    async updateRecentActivity() {
        try {
            const response = await axios.get('/api/history?hours=24');
            const history = response.data;
            
            const timeline = document.getElementById('activity-timeline');
            if (!timeline) return;
            
            if (history.check_runs && history.check_runs.length > 0) {
                timeline.innerHTML = history.check_runs.slice(0, 10).map(run => `
                    <div class="timeline-item">
                        <div class="timeline-dot ${this.getStatusClass(run.status)}"></div>
                        <div class="timeline-content">
                            <div class="timeline-time">${this.formatDateTime(run.timestamp)}</div>
                            <div class="timeline-message">
                                ${this.formatCheckMessage(run)}
                            </div>
                            <div class="timeline-details">
                                Duration: ${run.duration_seconds ? `${run.duration_seconds.toFixed(1)}s` : 'N/A'} • 
                                Accommodations: ${run.accommodations_checked || 0} • 
                                Availabilities: ${run.availabilities_found || 0}
                            </div>
                        </div>
                    </div>
                `).join('');
            } else {
                timeline.innerHTML = '<div class="loading">No recent activity found</div>';
            }
            
        } catch (error) {
            console.error('Failed to update recent activity:', error);
        }
    }
    
    async updateAccommodations() {
        try {
            const response = await axios.get('/api/accommodations');
            const accommodations = response.data;
            
            const grid = document.getElementById('accommodations-grid');
            if (!grid) return;
            
            if (accommodations.accommodations && accommodations.accommodations.length > 0) {
                grid.innerHTML = accommodations.accommodations.map(acc => `
                    <div class="accommodation-card">
                        <div class="accommodation-name">${acc.name}</div>
                        <div class="accommodation-status status-${acc.status.replace('_', '-')}">
                            ${acc.status === 'available' ? '✨ Available' : '😴 No Availability'}
                        </div>
                        <div class="accommodation-dates">
                            ${acc.recent_dates?.length > 0 
                                ? acc.recent_dates.map(date => `<span class="date-tag">${date}</span>`).join('')
                                : 'No recent availability'
                            }
                        </div>
                        ${acc.last_availability ? `
                            <div class="timeline-time" style="margin-top: 0.5rem;">
                                Last seen: ${this.formatDateTime(acc.last_availability)}
                            </div>
                        ` : ''}
                    </div>
                `).join('');
            } else {
                grid.innerHTML = '<div class="loading">No accommodations data available</div>';
            }
            
        } catch (error) {
            console.error('Failed to update accommodations:', error);
        }
    }
    
    async updateMetrics() {
        try {
            const [metricsResponse, historyResponse] = await Promise.all([
                axios.get('/api/metrics'),
                axios.get('/api/history?hours=24')
            ]);
            
            const metrics = metricsResponse.data;
            const history = historyResponse.data;
            
            // Update success rate chart
            this.updateSuccessRateChart(metrics.hourly_stats || []);
            
            // Update duration chart
            this.updateDurationChart(history.check_runs || []);
            
            // Update discoveries
            this.updateDiscoveries(history.discoveries || []);
            
        } catch (error) {
            console.error('Failed to update metrics:', error);
        }
    }
    
    updateSuccessRateChart(hourlyStats) {
        const ctx = document.getElementById('success-rate-chart');
        if (!ctx) return;
        
        if (this.charts.successRate) {
            this.charts.successRate.destroy();
        }
        
        const hours = Array.from({length: 24}, (_, i) => i);
        const successRates = hours.map(hour => {
            const stat = hourlyStats.find(s => s.hour === hour);
            return stat ? stat.success_rate : 0;
        });
        
        this.charts.successRate = new Chart(ctx, {
            type: 'line',
            data: {
                labels: hours.map(h => `${h.toString().padStart(2, '0')}:00`),
                datasets: [{
                    label: 'Success Rate (%)',
                    data: successRates,
                    borderColor: '#27AE60',
                    backgroundColor: 'rgba(39, 174, 96, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    },
                    x: {
                        display: true
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }
    
    updateDurationChart(checkRuns) {
        const ctx = document.getElementById('duration-chart');
        if (!ctx) return;
        
        if (this.charts.duration) {
            this.charts.duration.destroy();
        }
        
        const recentRuns = checkRuns
            .filter(run => run.status === 'success' && run.duration_seconds > 0)
            .slice(0, 12)
            .reverse();
        
        if (recentRuns.length === 0) {
            return;
        }
        
        this.charts.duration = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: recentRuns.map((_, i) => `Run ${i + 1}`),
                datasets: [{
                    label: 'Duration (seconds)',
                    data: recentRuns.map(run => run.duration_seconds),
                    backgroundColor: '#F39C12',
                    borderColor: '#E67E22',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value + 's';
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }
    
    updateDiscoveries(discoveries) {
        const container = document.getElementById('discoveries-container');
        if (!container) return;
        
        if (discoveries && discoveries.length > 0) {
            container.innerHTML = discoveries.slice(0, 5).map(discovery => `
                <div class="discovery-card">
                    <div class="discovery-header">
                        <div class="discovery-name">🏯 ${discovery.accommodation_name}</div>
                        <div class="discovery-time">${this.formatDateTime(discovery.timestamp)}</div>
                    </div>
                    <div class="discovery-dates">
                        ${discovery.available_dates.map(date => 
                            `<span class="date-tag">${date}</span>`
                        ).join('')}
                    </div>
                    <div style="margin-top: 0.5rem;">
                        <a href="${discovery.link}" target="_blank" class="discovery-link">
                            🔗 View Booking Page
                        </a>
                        ${discovery.notification_sent ? 
                            '<span style="margin-left: 1rem; color: #27AE60; font-size: 0.8rem;">📧 Notified</span>' : 
                            '<span style="margin-left: 1rem; color: #E67E22; font-size: 0.8rem;">⏳ Pending</span>'
                        }
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="loading">No recent discoveries 😴<br><small>The service is actively monitoring for availability!</small></div>';
        }
    }
    
    async updateConfiguration() {
        try {
            const response = await axios.get('/api/config');
            const config = response.data;
            
            const configDetails = document.getElementById('config-details');
            if (!configDetails) return;
            
            configDetails.innerHTML = `
                <div class="config-item">
                    <span class="label">Target Dates:</span>
                    <span class="value dates-list">${config.target_dates.join(', ')}</span>
                </div>
                <div class="config-item">
                    <span class="label">Check Interval:</span>
                    <span class="value">${Math.floor(config.check_interval_seconds / 60)} minutes</span>
                </div>
                <div class="config-item">
                    <span class="label">Timeout:</span>
                    <span class="value">${config.timeout_seconds}s</span>
                </div>
                <div class="config-item">
                    <span class="label">Retry Attempts:</span>
                    <span class="value">${config.retry_attempts}</span>
                </div>
                <div class="config-item">
                    <span class="label">Log Level:</span>
                    <span class="value">${config.log_level}</span>
                </div>
                <div class="config-item">
                    <span class="label">Notification Endpoint:</span>
                    <span class="value" style="font-family: 'Courier New', monospace; font-size: 0.8rem;">${config.notification_endpoint}</span>
                </div>
            `;
            
        } catch (error) {
            console.error('Failed to load configuration:', error);
            const configDetails = document.getElementById('config-details');
            if (configDetails) {
                configDetails.innerHTML = '<div class="loading">Failed to load configuration</div>';
            }
        }
    }

    async testNotification() {
        const button = document.getElementById('test-notification');
        if (!button) return;
        
        const originalText = button.textContent;
        button.textContent = '🔄 Sending...';
        button.disabled = true;
        
        try {
            const response = await axios.post('/api/test-notification');
            const result = response.data;
            
            if (result.success) {
                this.showToast('🎉 Test notification sent successfully!', 'success');
            } else {
                this.showToast(`❌ Test notification failed: ${result.message}`, 'error');
            }
        } catch (error) {
            console.error('Test notification failed:', error);
            this.showToast('❌ Failed to send test notification', 'error');
        } finally {
            button.textContent = originalText;
            button.disabled = false;
        }
    }

    async triggerManualCheck() {
        const button = document.getElementById('check-now');
        if (!button) return;
        
        const originalText = button.textContent;
        button.textContent = '🔄 Checking...';
        button.disabled = true;
        
        this.showToast('🔍 Manual availability check started...', 'info');
        
        try {
            const response = await axios.post('/api/check-now');
            const result = response.data;
            
            if (result.success) {
                this.showToast(`✅ ${result.message}`, 'success');
                // Refresh data to show the new check results
                setTimeout(() => this.refreshData(), 2000);
            } else {
                this.showToast(`❌ Manual check failed: ${result.message}`, 'error');
            }
        } catch (error) {
            console.error('Manual check failed:', error);
            if (error.response && error.response.data && error.response.data.message) {
                this.showToast(`❌ ${error.response.data.message}`, 'error');
            } else {
                this.showToast('❌ Failed to trigger manual check', 'error');
            }
        } finally {
            button.textContent = originalText;
            button.disabled = false;
        }
    }
    
    updateStatusBadge(status) {
        const badge = document.getElementById('system-status');
        const statusText = document.getElementById('status-text');
        const statusDot = badge?.querySelector('.status-dot');
        
        if (!badge || !statusText || !statusDot) return;
        
        // Remove existing status classes
        statusDot.classList.remove('healthy', 'warning', 'error', 'loading');
        
        // Add appropriate status class and text
        switch (status) {
            case 'running':
                statusDot.classList.add('loading');
                statusText.textContent = 'Checking...';
                break;
            case 'idle':
                statusDot.classList.add('healthy');
                statusText.textContent = 'Healthy';
                break;
            case 'error':
                statusDot.classList.add('error');
                statusText.textContent = 'Error';
                break;
            default:
                statusDot.classList.add('loading');
                statusText.textContent = 'Unknown';
        }
    }
    
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
        
        // Remove on click
        toast.addEventListener('click', () => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        });
    }
    
    formatDateTime(dateString) {
        if (!dateString) return 'Never';
        
        try {
            const date = new Date(dateString);
            const now = new Date();
            const diffMs = now - date;
            const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
            const diffMinutes = Math.floor(diffMs / (1000 * 60));
            
            if (diffMinutes < 1) return 'Just now';
            if (diffMinutes < 60) return `${diffMinutes}m ago`;
            if (diffHours < 24) return `${diffHours}h ago`;
            
            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (error) {
            return 'Invalid date';
        }
    }
    
    formatCheckMessage(run) {
        if (run.status === 'success') {
            return `✅ Check completed successfully`;
        } else if (run.error_message) {
            return `❌ Check failed: ${run.error_message}`;
        } else {
            return `❌ Check failed`;
        }
    }
    
    getStatusClass(status) {
        switch (status) {
            case 'success': return 'success';
            case 'error': return 'error';
            case 'running': return 'running';
            default: return 'error';
        }
    }
    
    capitalizeFirst(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new Gassho-zukuriDashboard();
});