/**
 * Main JavaScript for OSINT Geospatial Intelligence Platform
 * Handles MapLibre map initialization, API calls, and layer management
 */

// Global variables
let map;
let refreshInterval;
let isRefreshing = false;

// API base URL
const API_BASE = '/api';

// Initialize the map
function initMap() {
    map = new maplibregl.Map({
        container: 'map',
        style: {
            version: 8,
            sources: {
                'osm': {
                    type: 'raster',
                    tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
                    tileSize: 256,
                    attribution: '© OpenStreetMap contributors'
                }
            },
            layers: [{
                id: 'osm',
                type: 'raster',
                source: 'osm',
                minzoom: 0,
                maxzoom: 19
            }]
        },
        center: [0, 20],
        zoom: 2
    });

    // Add navigation controls
    map.addControl(new maplibregl.NavigationControl(), 'top-left');

    // Add scale control
    map.addControl(new maplibregl.ScaleControl(), 'bottom-right');

    // Wait for map to load
    map.on('load', () => {
        console.log('Map loaded');
        addLayers();
        fetchInitialData();
        setupEventListeners();
        startHealthCheck();
    });

    // Refresh on viewport change
    map.on('moveend', debounce(() => {
        if (!isRefreshing) {
            fetchData();
        }
    }, 1000));
}

// Add layers to the map
function addLayers() {
    // Aircraft layer
    map.addSource('aircraft', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
    });

    map.addLayer({
        id: 'aircraft',
        type: 'circle',
        source: 'aircraft',
        paint: {
            'circle-radius': 6,
            'circle-color': '#3b82f6',
            'circle-stroke-width': 2,
            'circle-stroke-color': '#1d4ed8',
            'circle-opacity': 0.8
        }
    });

    // Vessel layer
    map.addSource('vessel', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
    });

    map.addLayer({
        id: 'vessel',
        type: 'circle',
        source: 'vessel',
        paint: {
            'circle-radius': 6,
            'circle-color': '#10b981',
            'circle-stroke-width': 2,
            'circle-stroke-color': '#059669',
            'circle-opacity': 0.8
        }
    });

    // Thermal event layer
    map.addSource('thermal', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
    });

    map.addLayer({
        id: 'thermal',
        type: 'circle',
        source: 'thermal',
        paint: {
            'circle-radius': 8,
            'circle-color': '#ef4444',
            'circle-stroke-width': 2,
            'circle-stroke-color': '#dc2626',
            'circle-opacity': 0.7
        }
    });

    // Satellite layer
    map.addSource('satellite', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
    });

    map.addLayer({
        id: 'satellite',
        type: 'circle',
        source: 'satellite',
        paint: {
            'circle-radius': 5,
            'circle-color': '#f59e0b',
            'circle-stroke-width': 2,
            'circle-stroke-color': '#d97706',
            'circle-opacity': 0.8
        }
    });

    // Radio station layer
    map.addSource('radio', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
    });

    map.addLayer({
        id: 'radio',
        type: 'circle',
        source: 'radio',
        paint: {
            'circle-radius': 8,
            'circle-color': '#a855f7',
            'circle-stroke-width': 2,
            'circle-stroke-color': '#7c3aed',
            'circle-opacity': 0.8
        }
    });

    // Oil rig layer
    map.addSource('oilrig', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
    });

    map.addLayer({
        id: 'oilrig',
        type: 'circle',
        source: 'oilrig',
        paint: {
            'circle-radius': 7,
            'circle-color': '#14b8a6',
            'circle-stroke-width': 2,
            'circle-stroke-color': '#0d9488',
            'circle-opacity': 0.8
        }
    });

    // Power grid line layer
    map.addSource('powergrid', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
    });

    map.addLayer({
        id: 'powergrid',
        type: 'line',
        source: 'powergrid',
        paint: {
            'line-width': 2,
            'line-color': '#06b6d4',
            'line-opacity': 0.6
        }
    });

    // Power substation layer
    map.addSource('substation', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
    });

    map.addLayer({
        id: 'substation',
        type: 'circle',
        source: 'substation',
        paint: {
            'circle-radius': 5,
            'circle-color': '#ec4899',
            'circle-stroke-width': 2,
            'circle-stroke-color': '#db2777',
            'circle-opacity': 0.8
        }
    });

    // FIR layer
    map.addSource('fir', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
    });

    map.addLayer({
        id: 'fir',
        type: 'fill',
        source: 'fir',
        paint: {
            'fill-color': '#6366f1',
            'fill-opacity': 0.15,
            'stroke-color': '#4f46e5',
            'stroke-width': 1
        }
    });

    // Maritime boundary layer
    map.addSource('maritime', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
    });

    map.addLayer({
        id: 'maritime',
        type: 'fill',
        source: 'maritime',
        paint: {
            'fill-color': '#3b82f6',
            'fill-opacity': 0.1,
            'stroke-color': '#2563eb',
            'stroke-width': 1
        }
    });

    // Add popups
    addPopups();
}

// Add popups for each layer
function addPopups() {
    const layers = ['aircraft', 'vessel', 'thermal', 'satellite', 'radio', 'oilrig', 'substation'];

    layers.forEach(layerId => {
        map.on('click', layerId, (e) => {
            const props = e.features[0].properties || {};
            const popupRows = [
                ['Source', props.source],
                ['Type', props.entity_type],
                ['ID', props.identifier],
                ['Time', formatTimestamp(props.timestamp)],
            ];

            let popupContent = `<div style="padding: 10px; min-width: 200px;">`;
            popupContent += `<h3 style="margin: 0 0 10px 0; font-size: 14px;">${escapeHtml(props.popup_title || getEntityTitle(props))}</h3>`;
            popupContent += `<div style="font-size: 12px;">`;

            for (const [label, value] of getPopupMetadataRows(props)) {
                if (value) {
                    popupRows.push([label, value]);
                }
            }

            // Add radio-specific controls
            if (props.entity_type === 'radio_station' && props.meta_url_resolved) {
                popupContent += `<div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #444;">`;
                popupContent += `<button onclick="playRadioStation('${escapeHtml(props.meta_url_resolved)}', '${escapeHtml(props.meta_name)}')" style="width: 100%; padding: 8px; background: #a855f7; color: white; border: none; border-radius: 4px; cursor: pointer;">📻 Play Live</button>`;
                popupContent += `</div>`;
            }

            popupContent += popupRows
                .filter(([, value]) => formatDisplayValue(value))
                .map(([label, value]) => (
                    `<div><strong>${escapeHtml(label)}:</strong> ${escapeHtml(formatDisplayValue(value))}</div>`
                ))
                .join('');
            popupContent += `</div></div>`;

            new maplibregl.Popup()
                .setLngLat(e.lngLat)
                .setHTML(popupContent)
                .addTo(map);
        });

        // Change cursor on hover
        map.on('mouseenter', layerId, () => {
            map.getCanvas().style.cursor = 'pointer';
        });

        map.on('mouseleave', layerId, () => {
            map.getCanvas().style.cursor = '';
        });
    });

    // Add click handler for FIR layer
    map.on('click', 'fir', (e) => {
        const props = e.features[0].properties || {};
        const popupContent = `<div style="padding: 10px; min-width: 200px;">
            <h3 style="margin: 0 0 10px 0; font-size: 14px;">${escapeHtml(props.popup_title)}</h3>
            <div style="font-size: 12px;">
                <div><strong>Country:</strong> ${escapeHtml(props.meta_country)}</div>
                <div><strong>ICAO Code:</strong> ${escapeHtml(props.meta_icao_code)}</div>
            </div>
        </div>`;
        new maplibregl.Popup()
            .setLngLat(e.lngLat)
            .setHTML(popupContent)
            .addTo(map);
    });

    // Add click handler for maritime layer
    map.on('click', 'maritime', (e) => {
        const props = e.features[0].properties || {};
        const popupContent = `<div style="padding: 10px; min-width: 200px;">
            <h3 style="margin: 0 0 10px 0; font-size: 14px;">${escapeHtml(props.popup_title)}</h3>
            <div style="font-size: 12px;">
                <div><strong>Water Type:</strong> ${escapeHtml(props.meta_water_type)}</div>
                <div><strong>Country:</strong> ${escapeHtml(props.meta_country)}</div>
                <div><strong>International:</strong> ${props.meta_is_international ? 'Yes' : 'No'}</div>
            </div>
        </div>`;
        new maplibregl.Popup()
            .setLngLat(e.lngLat)
            .setHTML(popupContent)
            .addTo(map);
    });
}

// Play radio station
function playRadioStation(url, name) {
    const player = document.getElementById('radio-player');
    const info = document.getElementById('radio-station-info');

    player.src = url;
    player.play();
    info.textContent = `Now playing: ${name}`;

    // Show player container
    document.getElementById('radio-player-container').style.display = 'block';
}

// Get entity title for popup
function getEntityTitle(props) {
    const metadata = parseMetadata(props.metadata);
    const type = props.entity_type || 'entity';
    const identifier = props.identifier || 'unknown';

    switch (type) {
        case 'aircraft':
            return metadata.callsign?.trim() || metadata.icao24 || `Aircraft ${identifier}`;
        case 'vessel':
            return metadata.name?.trim() || metadata.mmsi || `Vessel ${identifier}`;
        case 'thermal_event':
            return 'Thermal Event';
        case 'satellite':
            return metadata.name?.trim() || metadata.norad_id || `Satellite ${identifier}`;
        case 'radio_station':
            return metadata.name?.trim() || `Radio Station ${identifier}`;
        case 'oil_rig':
            return metadata.name?.trim() || `Oil Rig ${identifier}`;
        case 'power_substation':
            return metadata.name?.trim() || `Substation ${identifier}`;
        case 'fir':
            return metadata.name?.trim() || `FIR ${identifier}`;
        case 'maritime_boundary':
            return metadata.name?.trim() || `Maritime Boundary ${identifier}`;
        default:
            return formatKey(type);
    }
}

// Format timestamp
function formatTimestamp(timestamp) {
    if (!timestamp) return 'Unknown';

    const date = new Date(timestamp);
    return Number.isNaN(date.getTime()) ? String(timestamp) : date.toLocaleString();
}

// Format key for display
function formatKey(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function normalizeFeatureForMap(feature) {
    const properties = normalizeFeatureProperties(feature.properties);
    const metadataKeys = new Set(
        String(properties.metadata_keys || '')
            .split(',')
            .map(key => key.trim())
            .filter(Boolean)
    );
    const flatMetadata = {};

    for (const [key, value] of Object.entries(properties)) {
        if (!key.startsWith('meta_')) continue;

        const formattedValue = formatDisplayValue(value);
        if (!formattedValue) continue;

        metadataKeys.add(key.slice(5));
        flatMetadata[key] = value;
    }

    for (const [key, value] of Object.entries(properties.metadata)) {
        const formattedValue = formatDisplayValue(value);
        if (!formattedValue) continue;

        metadataKeys.add(key);
        flatMetadata[`meta_${key}`] = serializeFeatureProperty(value);
    }

    return {
        ...feature,
        properties: {
            source: properties.source || '',
            entity_type: properties.entity_type || '',
            identifier: properties.identifier || '',
            timestamp: properties.timestamp || '',
            popup_title: properties.popup_title || getEntityTitle(properties),
            metadata_keys: Array.from(metadataKeys).join(','),
            ...flatMetadata,
        },
    };
}

function normalizeFeatureProperties(props = {}) {
    return {
        ...props,
        metadata: parseMetadata(props.metadata),
    };
}

function getPopupMetadataRows(props = {}) {
    const metadataKeys = String(props.metadata_keys || '')
        .split(',')
        .map(key => key.trim())
        .filter(Boolean);

    if (metadataKeys.length > 0) {
        return metadataKeys.map(key => [formatKey(key), props[`meta_${key}`]]);
    }

    return Object.entries(parseMetadata(props.metadata))
        .map(([key, value]) => [formatKey(key), value]);
}

function parseMetadata(metadata) {
    if (!metadata) return {};
    if (typeof metadata === 'object' && !Array.isArray(metadata)) return metadata;

    if (typeof metadata === 'string') {
        try {
            const parsed = JSON.parse(metadata);
            if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
                return parsed;
            }
        } catch (error) {}
    }

    return {};
}

function formatDisplayValue(value) {
    if (value === null || value === undefined || value === '') {
        return '';
    }

    if (typeof value === 'boolean') {
        return value ? 'Yes' : 'No';
    }

    if (Array.isArray(value)) {
        return value.join(', ');
    }

    if (typeof value === 'object') {
        return JSON.stringify(value);
    }

    return String(value);
}

function serializeFeatureProperty(value) {
    if (Array.isArray(value) || (typeof value === 'object' && value !== null)) {
        return JSON.stringify(value);
    }

    return value;
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Fetch initial data
async function fetchInitialData() {
    await fetchData();
    // Set up auto-refresh every 60 seconds
    refreshInterval = setInterval(fetchData, 60000);
}

// Fetch data from API
async function fetchData() {
    if (isRefreshing) return;

    isRefreshing = true;
    const refreshBtn = document.getElementById('refresh-btn');
    refreshBtn.disabled = true;
    refreshBtn.innerHTML = 'Refreshing...';

    try {
        // Get current viewport bounds
        const bounds = map.getBounds();
        const lamin = bounds.getSouth();
        const lomin = bounds.getWest();
        const lamax = bounds.getNorth();
        const lomax = bounds.getEast();

        // Build URL with parameters
        const params = new URLSearchParams({
            lamin: lamin.toFixed(4),
            lomin: lomin.toFixed(4),
            lamax: lamax.toFixed(4),
            lomax: lomax.toFixed(4),
        });

        // Add entity type filters based on layer toggles
        const entityTypes = [];
        const sources = [];
        
        if (document.getElementById('toggle-aircraft').checked) {
            entityTypes.push('aircraft');
            sources.push('opensky');
        }
        if (document.getElementById('toggle-vessel').checked) {
            entityTypes.push('vessel');
            sources.push('aisstream');
        }
        if (document.getElementById('toggle-thermal').checked) {
            entityTypes.push('thermal_event');
            sources.push('firms');
        }
        if (document.getElementById('toggle-satellite').checked) {
            entityTypes.push('satellite');
            sources.push('celestrak');
        }
        if (document.getElementById('toggle-radio').checked) {
            entityTypes.push('radio_station');
            sources.push('radio_api');
        }
        if (document.getElementById('toggle-oilrig').checked) {
            entityTypes.push('oil_rig');
            sources.push('oil_rig_api');
        }
        if (document.getElementById('toggle-powergrid').checked) {
            entityTypes.push('power_grid');
            sources.push('power_grid_api');
        }
        if (document.getElementById('toggle-substation').checked) {
            entityTypes.push('power_substation');
            sources.push('power_grid_api');
        }
        if (document.getElementById('toggle-fir').checked) {
            entityTypes.push('fir');
            sources.push('fir_api');
        }
        if (document.getElementById('toggle-maritime').checked) {
            entityTypes.push('maritime_boundary');
            sources.push('maritime_api');
        }

        if (entityTypes.length > 0) {
            params.append('entity_types', entityTypes.join(','));
        }
        
        if (sources.length > 0) {
            params.append('sources', sources.join(','));
        }

        const response = await fetch(`${API_BASE}/unified?${params}`);
        const data = await response.json();

        // Update layers
        updateLayers(data.features);

        // Update stats
        updateStats(data.metadata);

        console.log(`Fetched ${data.features.length} entities`);

    } catch (error) {
        console.error('Error fetching data:', error);
    } finally {
        isRefreshing = false;
        refreshBtn.disabled = false;
        refreshBtn.innerHTML = 'Refresh Data';
    }
}

// Update map layers with new data
function updateLayers(features) {
    const normalizedFeatures = features.map(normalizeFeatureForMap);
    const aircraft = normalizedFeatures.filter(f => f.properties.entity_type === 'aircraft');
    const vessels = normalizedFeatures.filter(f => f.properties.entity_type === 'vessel');
    const thermal = normalizedFeatures.filter(f => f.properties.entity_type === 'thermal_event');
    const satellites = normalizedFeatures.filter(f => f.properties.entity_type === 'satellite');
    const radios = normalizedFeatures.filter(f => f.properties.entity_type === 'radio_station');
    const oilrigs = normalizedFeatures.filter(f => f.properties.entity_type === 'oil_rig');
    const powergrids = normalizedFeatures.filter(f => f.properties.entity_type === 'power_grid');
    const substations = normalizedFeatures.filter(f => f.properties.entity_type === 'power_substation');
    const firs = normalizedFeatures.filter(f => f.properties.entity_type === 'fir');
    const maritime = normalizedFeatures.filter(f => f.properties.entity_type === 'maritime_boundary');

    map.getSource('aircraft').setData({
        type: 'FeatureCollection',
        features: aircraft
    });

    map.getSource('vessel').setData({
        type: 'FeatureCollection',
        features: vessels
    });

    map.getSource('thermal').setData({
        type: 'FeatureCollection',
        features: thermal
    });

    map.getSource('satellite').setData({
        type: 'FeatureCollection',
        features: satellites
    });

    map.getSource('radio').setData({
        type: 'FeatureCollection',
        features: radios
    });

    map.getSource('oilrig').setData({
        type: 'FeatureCollection',
        features: oilrigs
    });

    map.getSource('powergrid').setData({
        type: 'FeatureCollection',
        features: powergrids
    });

    map.getSource('substation').setData({
        type: 'FeatureCollection',
        features: substations
    });

    map.getSource('fir').setData({
        type: 'FeatureCollection',
        features: firs
    });

    map.getSource('maritime').setData({
        type: 'FeatureCollection',
        features: maritime
    });
}

// Update statistics display
function updateStats(metadata) {
    if (!metadata) return;

    document.getElementById('total-count').textContent = metadata.count || 0;
    document.getElementById('aircraft-count').textContent = metadata.entity_types?.aircraft || 0;
    document.getElementById('vessel-count').textContent = metadata.entity_types?.vessel || 0;
    document.getElementById('thermal-count').textContent = metadata.entity_types?.thermal_event || 0;
    document.getElementById('satellite-count').textContent = metadata.entity_types?.satellite || 0;
    document.getElementById('radio-count').textContent = metadata.entity_types?.radio_station || 0;
    document.getElementById('oilrig-count').textContent = metadata.entity_types?.oil_rig || 0;
    document.getElementById('powergrid-count').textContent = metadata.entity_types?.power_grid || 0;
    document.getElementById('substation-count').textContent = metadata.entity_types?.power_substation || 0;
    document.getElementById('fir-count').textContent = metadata.entity_types?.fir || 0;
    document.getElementById('maritime-count').textContent = metadata.entity_types?.maritime_boundary || 0;
    document.getElementById('last-update').textContent = formatTimestamp(metadata.timestamp);
}

// Setup event listeners
function setupEventListeners() {
    // Layer toggles
    document.getElementById('toggle-aircraft').addEventListener('change', (e) => {
        map.setLayoutProperty('aircraft', 'visibility', e.target.checked ? 'visible' : 'none');
    });

    document.getElementById('toggle-vessel').addEventListener('change', (e) => {
        map.setLayoutProperty('vessel', 'visibility', e.target.checked ? 'visible' : 'none');
    });

    document.getElementById('toggle-thermal').addEventListener('change', (e) => {
        map.setLayoutProperty('thermal', 'visibility', e.target.checked ? 'visible' : 'none');
    });

    document.getElementById('toggle-satellite').addEventListener('change', (e) => {
        map.setLayoutProperty('satellite', 'visibility', e.target.checked ? 'visible' : 'none');
    });

    document.getElementById('toggle-radio').addEventListener('change', (e) => {
        map.setLayoutProperty('radio', 'visibility', e.target.checked ? 'visible' : 'none');
    });

    document.getElementById('toggle-oilrig').addEventListener('change', (e) => {
        map.setLayoutProperty('oilrig', 'visibility', e.target.checked ? 'visible' : 'none');
    });

    document.getElementById('toggle-powergrid').addEventListener('change', (e) => {
        map.setLayoutProperty('powergrid', 'visibility', e.target.checked ? 'visible' : 'none');
    });

    document.getElementById('toggle-substation').addEventListener('change', (e) => {
        map.setLayoutProperty('substation', 'visibility', e.target.checked ? 'visible' : 'none');
    });

    document.getElementById('toggle-fir').addEventListener('change', (e) => {
        map.setLayoutProperty('fir', 'visibility', e.target.checked ? 'visible' : 'none');
    });

    document.getElementById('toggle-maritime').addEventListener('change', (e) => {
        map.setLayoutProperty('maritime', 'visibility', e.target.checked ? 'visible' : 'none');
    });

    // Refresh button
    document.getElementById('refresh-btn').addEventListener('click', fetchData);
}

// Start health check
async function startHealthCheck() {
    await checkHealth();
    // Check health every 30 seconds
    setInterval(checkHealth, 30000);
}

// Check system health
async function checkHealth() {
    try {
        const response = await fetch('/health');
        const data = await response.json();

        // Update health status for each source
        data.sources.forEach(source => {
            const elementId = `health-${source.source}`;
            const element = document.getElementById(elementId);
            if (element) {
                const statusSpan = element.querySelector('span:last-child');
                if (source.healthy) {
                    element.className = 'health-item healthy';
                    statusSpan.textContent = '✓ OK';
                } else {
                    element.className = 'health-item unhealthy';
                    statusSpan.textContent = '✗ Error';
                }
            }
        });

    } catch (error) {
        console.error('Error checking health:', error);
    }
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initMap);
