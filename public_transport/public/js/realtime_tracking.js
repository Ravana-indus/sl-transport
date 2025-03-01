frappe.provide('public_transport.realtime');

public_transport.realtime.BusTracker = class BusTracker {
    constructor(busId, mapElement) {
        this.busId = busId;
        this.map = null;
        this.marker = null;
        this.path = [];
        this.mapElement = mapElement;
        this.subscribers = new Set();
        
        this.initialize();
    }
    
    initialize() {
        this.initializeMap();
        this.subscribeToUpdates();
        this.stopMarkers = new Map();
        this.routePath = null;
        this.deviationPath = null;
        this.loadRouteData();
    }
    
    async loadRouteData() {
        try {
            const result = await frappe.call({
                method: 'public_transport.public_transport.api.get_route_data',
                args: { 
                    bus_id: this.busId,
                    include_deviations: true
                }
            });
            
            if (result.message && result.message.status === 'success') {
                this.renderRoute(result.message.route);
                this.renderStops(result.message.stops);
                
                if (result.message.active_deviation) {
                    this.handleDeviation(result.message.active_deviation);
                }
            }
        } catch (error) {
            console.error('Failed to load route data:', error);
        }
    }
    
    renderRoute(routeData) {
        // Clear existing route
        if (this.routePath) {
            this.routePath.setMap(null);
        }
        
        // Create route path
        const coordinates = routeData.coordinates.map(coord => ({
            lat: parseFloat(coord.lat),
            lng: parseFloat(coord.lng)
        }));
        
        this.routePath = new google.maps.Polyline({
            path: coordinates,
            geodesic: true,
            strokeColor: '#4A90E2',
            strokeOpacity: 0.8,
            strokeWeight: 3,
            map: this.map
        });
        
        // Fit map bounds to show entire route
        const bounds = new google.maps.LatLngBounds();
        coordinates.forEach(coord => bounds.extend(coord));
        this.map.fitBounds(bounds);
    }
    
    renderStops(stops) {
        // Clear existing stop markers
        this.stopMarkers.forEach(marker => marker.setMap(null));
        this.stopMarkers.clear();
        
        stops.forEach(stop => {
            const marker = new google.maps.Marker({
                position: {
                    lat: parseFloat(stop.latitude),
                    lng: parseFloat(stop.longitude)
                },
                map: this.map,
                icon: {
                    url: '/assets/public_transport/images/bus-stop-icon.svg',
                    scaledSize: new google.maps.Size(24, 24)
                },
                title: stop.stop_name
            });
            
            // Add info window
            const infoWindow = new google.maps.InfoWindow({
                content: this.createStopInfoContent(stop)
            });
            
            marker.addListener('click', () => {
                infoWindow.open(this.map, marker);
            });
            
            this.stopMarkers.set(stop.name, {
                marker,
                infoWindow,
                data: stop
            });
        });
    }
    
    createStopInfoContent(stop) {
        return `
            <div class="stop-info ${stop.isDeviation ? 'deviation' : ''}">
                <h5>${stop.stop_name}</h5>
                <p>${stop.address}</p>
                ${stop.isDeviation ? '<p class="deviation-badge">Alternate Stop</p>' : ''}
                ${stop.eta ? `<p><strong>ETA:</strong> ${stop.eta}</p>` : ''}
                ${this.createFacilitiesHtml(stop.facilities)}
            </div>
        `;
    }
    
    createFacilitiesHtml(facilities) {
        if (!facilities || !facilities.length) return '';
        
        return `
            <div class="facilities">
                <strong>Facilities:</strong>
                <ul>
                    ${facilities.map(f => `
                        <li>${f.facility_type} 
                            ${f.status !== 'Working' ? `(${f.status})` : ''}
                        </li>
                    `).join('')}
                </ul>
            </div>
        `;
    }
    
    initializeMap() {
        this.map = new google.maps.Map(this.mapElement, {
            zoom: 12,
            center: { lat: 6.9271, lng: 79.8612 }  // Default to Colombo
        });
        
        this.marker = new google.maps.Marker({
            map: this.map,
            icon: {
                url: '/assets/public_transport/images/bus-icon.svg',
                scaledSize: new google.maps.Size(32, 32)
            }
        });
        
        this.path = new google.maps.Polyline({
            map: this.map,
            path: [],
            strokeColor: '#4A90E2',
            strokeOpacity: 1.0,
            strokeWeight: 2
        });
    }
    
    subscribeToUpdates() {
        frappe.realtime.on(`bus_location_${this.busId}`, (data) => {
            this.handleLocationUpdate(data);
        });
        
        // Subscribe to bus updates
        frappe.call({
            method: 'public_transport.public_transport.realtime.subscribe_to_bus',
            args: { bus_id: this.busId }
        });
    }
    
    handleLocationUpdate(data) {
        const position = {
            lat: parseFloat(data.location.lat),
            lng: parseFloat(data.location.lng)
        };
        
        // Update marker position
        this.marker.setPosition(position);
        
        // Update path
        const pathCoords = this.path.getPath();
        pathCoords.push(position);
        
        // Center map if following
        if (this.isFollowing) {
            this.map.panTo(position);
        }
        
        // Notify subscribers
        this.notifySubscribers(data);
        
        // Update ETAs for upcoming stops
        if (data.upcoming_stops) {
            data.upcoming_stops.forEach(stop => {
                const stopMarker = this.stopMarkers.get(stop.stop);
                if (stopMarker) {
                    stopMarker.data.eta = stop.eta;
                    stopMarker.infoWindow.setContent(
                        this.createStopInfoContent(stopMarker.data)
                    );
                }
            });
        }
    }
    
    handleDeviation(deviation) {
        // Clear existing deviation path
        if (this.deviationPath) {
            this.deviationPath.setMap(null);
        }
        
        // Create deviation path
        const coordinates = deviation.stops.map(stop => ({
            lat: parseFloat(stop.latitude),
            lng: parseFloat(stop.longitude)
        }));
        
        this.deviationPath = new google.maps.Polyline({
            path: coordinates,
            geodesic: true,
            strokeColor: '#FF4B4B',
            strokeOpacity: 0.8,
            strokeWeight: 3,
            strokePattern: [10, 5],
            map: this.map
        });
        
        // Add deviation info window
        const infoWindow = new google.maps.InfoWindow({
            content: this.createDeviationInfoContent(deviation)
        });
        
        // Show deviation info when clicking the path
        this.deviationPath.addListener('click', (e) => {
            infoWindow.setPosition(e.latLng);
            infoWindow.open(this.map);
        });
        
        // Update affected stops
        this.updateStopsForDeviation(deviation);
    }
    
    createDeviationInfoContent(deviation) {
        return `
            <div class="deviation-info">
                <h5>Route Deviation</h5>
                <p><strong>Reason:</strong> ${deviation.reason}</p>
                <p><strong>Description:</strong> ${deviation.description}</p>
                <p><strong>Active until:</strong> ${deviation.end_time}</p>
                <p><strong>Expected delay:</strong> ${deviation.delay_minutes} minutes</p>
            </div>
        `;
    }
    
    updateStopsForDeviation(deviation) {
        // Update stop markers for deviated route
        deviation.stops.forEach(stop => {
            const marker = this.stopMarkers.get(stop.name);
            if (marker) {
                marker.marker.setIcon({
                    url: '/assets/public_transport/images/bus-stop-icon-alt.svg',
                    scaledSize: new google.maps.Size(24, 24)
                });
                
                // Update info window content
                marker.data.isDeviation = true;
                marker.infoWindow.setContent(this.createStopInfoContent(marker.data));
            }
        });
    }
    
    startFollowing() {
        this.isFollowing = true;
        if (this.marker) {
            this.map.panTo(this.marker.getPosition());
        }
    }
    
    stopFollowing() {
        this.isFollowing = false;
    }
    
    addSubscriber(callback) {
        this.subscribers.add(callback);
    }
    
    removeSubscriber(callback) {
        this.subscribers.delete(callback);
    }
    
    notifySubscribers(data) {
        this.subscribers.forEach(callback => {
            try {
                callback(data);
            } catch (e) {
                console.error('Subscriber callback failed:', e);
            }
        });
    }
    
    destroy() {
        // Unsubscribe from updates
        frappe.call({
            method: 'public_transport.public_transport.realtime.unsubscribe_from_bus',
            args: { bus_id: this.busId }
        });
        
        frappe.realtime.off(`bus_location_${this.busId}`);
        
        // Clear map elements
        if (this.marker) {
            this.marker.setMap(null);
        }
        if (this.path) {
            this.path.setMap(null);
        }
        
        this.subscribers.clear();
    }
};