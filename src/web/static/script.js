let chartInstance = null;
let currentData = [];
let forecastData = [];

const marketTypeSelect = document.getElementById('marketType');
const marketSelect = document.getElementById('market');
const startDateInput = document.getElementById('startDate');
const endDateInput = document.getElementById('endDate');
const forecastDaysSelect = document.getElementById('forecastDays');
const btnFetch = document.getElementById('btnFetch');
const btnForecast = document.getElementById('btnForecast');
const btnExport = document.getElementById('btnExport');
const tableBody = document.getElementById('tableBody');
const loadingOverlay = document.getElementById('loadingOverlay');
const dataStats = document.getElementById('dataStats');

document.addEventListener('DOMContentLoaded', () => {
    console.log('GME Market Analytics - Application starting...');
    
    const today = new Date();
    const sevenDaysAgo = new Date(today);
    sevenDaysAgo.setDate(today.getDate() - 7);
    
    const formatDate = (date) => {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    };
    
    startDateInput.value = formatDate(sevenDaysAgo);
    endDateInput.value = formatDate(today);
    endDateInput.max = formatDate(new Date(today.getFullYear() + 10, 11, 31));
    
    console.log('Loading markets...');
    loadMarkets();
    
    marketTypeSelect.addEventListener('change', () => {
        console.log('Market type changed to:', marketTypeSelect.value);
        loadMarkets();
    });
    btnFetch.addEventListener('click', fetchData);
    btnForecast.addEventListener('click', generateForecast);
    btnExport.addEventListener('click', exportToExcel);
});

async function loadMarkets() {
    console.log('loadMarkets() called');
    marketSelect.innerHTML = '<option value="">Loading markets...</option>';
    
    try {
        console.log('Fetching from /api/markets...');
        const response = await fetch('/api/markets');
        
        console.log('Response status:', response.status, response.statusText);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const markets = await response.json();
        console.log('Markets received:', markets);
        
        const type = marketTypeSelect.value;
        console.log('Current market type:', type);
        
        const availableMarkets = markets[type] || [];
        console.log('Available markets for type:', availableMarkets);
        
        if (availableMarkets.length === 0) {
            marketSelect.innerHTML = '<option value="">No markets available</option>';
            console.warn('No markets available for type:', type);
            return;
        }
        
        marketSelect.innerHTML = availableMarkets
            .map(m => `<option value="${m.id}">${m.name}</option>`)
            .join('');
        
        console.log('Markets loaded successfully, total:', availableMarkets.length);
    } catch (e) {
        console.error('Failed to load markets:', e);
        marketSelect.innerHTML = '<option value="">Error loading markets</option>';
        showError('Failed to load markets: ' + e.message);
    }
}

async function fetchData() {
    const type = marketTypeSelect.value;
    const market = marketSelect.value;
    const startDate = startDateInput.value;
    const endDate = endDateInput.value;
    
    if (!market || !startDate || !endDate) {
        showError('Please select all fields');
        return;
    }
    
    setLoading(true);
    try {
        const response = await fetch('/api/price-data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type, market, start_date: startDate, end_date: endDate })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to fetch data');
        }
        
        const result = await response.json();
        processAndRenderData(result.data);
        btnForecast.disabled = false;
        btnExport.disabled = false;
    } catch (e) {
        showError('Error fetching data: ' + e.message);
    } finally {
        setLoading(false);
    }
}

function processAndRenderData(rawData) {
    if (!rawData || rawData.length === 0) {
        showError('No data available');
        return;
    }
    
    const normalized = rawData.map(item => {
        const keys = Object.keys(item);
        const dateKey = keys.find(k => /date|data/i.test(k));
        const intervalKey = keys.find(k => /hour|interval|ora/i.test(k));
        const priceKey = keys.find(k => /price|pun|prezzo/i.test(k));
        const volumeKey = keys.find(k => /volume|quantit/i.test(k));
        
        let intervalValue = item[intervalKey] || item.interval || item.hour;
        if (typeof intervalValue === 'string') {
            intervalValue = parseInt(intervalValue.replace(/\D/g, '')) || 1;
        }
        intervalValue = parseInt(intervalValue) || 1;
        
        return {
            date: item[dateKey] || item.date,
            interval: intervalValue,
            price: parseFloat(item[priceKey] || item.price || 0),
            volume: parseFloat(item[volumeKey] || item.volume || 0),
            type: 'actual'
        };
    });
    
    currentData = normalized.sort((a, b) => {
        const dateA = new Date(a.date);
        const dateB = new Date(b.date);
        if (dateA.getTime() !== dateB.getTime()) {
            return dateA - dateB;
        }
        return (a.interval || 0) - (b.interval || 0);
    });
    
    forecastData = [];
    
    renderChart();
    renderTable();
    updateStats();
}

function renderChart() {
    const ctx = document.getElementById('priceChart').getContext('2d');
    
    const allData = [...currentData, ...forecastData];
    
    const labels = allData.map(d => {
        const hour = (d.interval || 1) - 1;
        return `${d.date} ${String(hour).padStart(2, '0')}:00`;
    });
    
    const actualPrices = currentData.map(d => d.price);
    const forecastPrices = forecastData.map(d => d.price);
    
    if (chartInstance) {
        chartInstance.destroy();
    }
    
    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Actual Price',
                    data: actualPrices,
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 2,
                    pointHoverRadius: 5
                },
                {
                    label: 'Forecast Price',
                    data: [...Array(currentData.length).fill(null), ...forecastPrices],
                    borderColor: 'rgb(139, 92, 246)',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    fill: true,
                    tension: 0.4,
                    pointRadius: 2,
                    pointHoverRadius: 5
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#94a3b8',
                        font: {
                            size: 12,
                            family: 'Inter'
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleColor: '#f8fafc',
                    bodyColor: '#f8fafc',
                    borderColor: 'rgba(148, 163, 184, 0.2)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#94a3b8',
                        maxRotation: 45,
                        minRotation: 45,
                        autoSkip: true,
                        maxTicksLimit: 20
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#94a3b8',
                        callback: function(value) {
                            return '€' + value.toFixed(2);
                        }
                    }
                }
            }
        }
    });
}

function renderTable() {
    const allData = [...currentData, ...forecastData];
    
    if (allData.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="5" class="empty-state">No data available</td></tr>';
        return;
    }
    
    tableBody.innerHTML = allData.map(d => {
        const typeLabel = d.type === 'forecast' 
            ? '<span class="forecast-badge">Forecast</span>' 
            : 'Actual';
        
        return `
            <tr>
                <td>${d.date}</td>
                <td>${d.interval || '-'}</td>
                <td>€${d.price.toFixed(2)}</td>
                <td>${d.volume ? d.volume.toFixed(2) : '-'} MWh</td>
                <td>${typeLabel}</td>
            </tr>
        `;
    }).join('');
}

function updateStats() {
    const total = currentData.length + forecastData.length;
    const actual = currentData.length;
    const forecast = forecastData.length;
    
    dataStats.textContent = `Total: ${total} records (${actual} actual, ${forecast} forecast)`;
}

async function generateForecast() {
    if (currentData.length === 0) {
        showError('Please fetch data first');
        return;
    }
    
    const days = parseInt(forecastDaysSelect.value);
    
    setLoading(true);
    try {
        const response = await fetch('/api/forecast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                history: currentData,
                days: days
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Forecast failed');
        }
        
        const result = await response.json();
        forecastData = result.forecast || [];
        
        renderChart();
        renderTable();
        updateStats();
    } catch (e) {
        showError('Error generating forecast: ' + e.message);
    } finally {
        setLoading(false);
    }
}

async function exportToExcel() {
    const allData = [...currentData, ...forecastData];
    
    if (allData.length === 0) {
        showError('No data to export');
        return;
    }
    
    const exportData = allData.map(d => ({
        Date: d.date,
        Hour: d.interval || '-',
        Price: d.price,
        Volume: d.volume || 0,
        Type: d.type
    }));
    
    try {
        const response = await fetch('/api/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                rows: exportData,
                filename: `gme_data_${new Date().toISOString().split('T')[0]}.xlsx`
            })
        });
        
        if (!response.ok) {
            throw new Error('Export failed');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `gme_data_${new Date().toISOString().split('T')[0]}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (e) {
        showError('Error exporting data: ' + e.message);
    }
}

function setLoading(isLoading) {
    if (isLoading) {
        loadingOverlay.classList.add('active');
        btnFetch.disabled = true;
        btnForecast.disabled = true;
        btnExport.disabled = true;
    } else {
        loadingOverlay.classList.remove('active');
        btnFetch.disabled = false;
        if (currentData.length > 0) {
            btnForecast.disabled = false;
            btnExport.disabled = false;
        }
    }
}

function showError(message) {
    const alertDiv = document.createElement('div');
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: rgba(239, 68, 68, 0.95);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        z-index: 10000;
        max-width: 400px;
        animation: slideIn 0.3s ease;
    `;
    alertDiv.textContent = message;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => alertDiv.remove(), 300);
    }, 5000);
    
    console.error(message);
}