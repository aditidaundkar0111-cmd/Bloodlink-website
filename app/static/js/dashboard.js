const API_BASE = '';

document.addEventListener('DOMContentLoaded', function() {
    loadDashboard();
});

async function loadDashboard() {
    try {
        const response = await fetch(`${API_BASE}/api/current-user`);
        
        if (!response.ok) {
            window.location.href = '/login';
            return;
        }
        
        const user = await response.json();
        document.getElementById('user-name').textContent = user.name;
        document.getElementById('user-email').textContent = user.email;
        if (user.donor) {
            const donorSection = document.getElementById('donor-section');
            donorSection.style.display = 'block';
            
            document.getElementById('donor-blood-group').textContent = user.donor.blood_group;
            document.getElementById('donor-location').textContent = user.donor.city || user.donor.address || 'N/A';
            document.getElementById('donor-availability').textContent = user.donor.is_available ? 'Available' : 'Unavailable';
            document.getElementById('donor-count').textContent = user.donor.donation_count;
            document.getElementById('last-donation').textContent = user.donor.last_donation_date || 'Never';
            document.getElementById('toggle-availability-btn').addEventListener('click', toggleAvailability);
        }
        loadDonorStats();
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
        window.location.href = '/login';
    }
}

async function toggleAvailability() {
    try {
        const user = await fetch(`${API_BASE}/api/current-user`).then(r => r.json());
        const donorId = user.donor.donor_id;
        const newStatus = !user.donor.is_available;
        
        const response = await fetch(`${API_BASE}/api/donors/${donorId}/availability`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ is_available: newStatus })
        });
        
        if (response.ok) {
            loadDashboard();
        } else {
            alert('Failed to update availability');
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

async function loadDonorStats() {
    try {
        const donorsResponse = await fetch(`${API_BASE}/api/donors?page=1`);
        const donorsData = await donorsResponse.json();
        
        document.getElementById('stat-donors').textContent = donorsData.total;
        
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

const logoutBtn = document.getElementById('logout-btn');
if (logoutBtn) {
    logoutBtn.addEventListener('click', async function() {
        try {
            await fetch(`${API_BASE}/api/logout`, { method: 'POST' });
            window.location.href = '/';
        } catch (error) {
            console.error('Logout error:', error);
        }
    });
}

const createRequestBtn = document.getElementById('create-request-btn');
const requestModal = document.getElementById('request-modal');
const closeBtn = document.querySelector('.close');

if (createRequestBtn) {
    createRequestBtn.addEventListener('click', function() {
        requestModal.style.display = 'block';
    });
}

if (closeBtn) {
    closeBtn.addEventListener('click', function() {
        requestModal.style.display = 'none';
    });
}

window.addEventListener('click', function(event) {
    if (event.target === requestModal) {
        requestModal.style.display = 'none';
    }
});

const getCurrentLocationBtn = document.getElementById('get-current-location-btn');
if (getCurrentLocationBtn) {
    getCurrentLocationBtn.addEventListener('click', function(e) {
        e.preventDefault();
        
        if (!navigator.geolocation) {
            alert('Geolocation is not supported by your browser');
            return;
        }
        
        this.textContent = '⏳ Getting location...';
        this.disabled = true;
        
        navigator.geolocation.getCurrentPosition(
            function(position) {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                
                document.getElementById('request-coords').value = `${lat}, ${lng}`;
                document.getElementById('coordinates-group').style.display = 'block';

                fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`)
                    .then(r => r.json())
                    .then(data => {
                        if (data.address) {
                            const address = `${data.address.road || ''} ${data.address.neighbourhood || ''}, ${data.address.city || data.address.town || ''}`.trim();
                            document.getElementById('request-location').value = address;
                        }
                        
                        const locationStatus = document.getElementById('location-status');
                        locationStatus.textContent = '✓ Location captured (Lat: ' + lat.toFixed(4) + ', Lng: ' + lng.toFixed(4) + ')';
                        locationStatus.style.color = '#90ee90';
                        locationStatus.style.display = 'block';
                        
                        getCurrentLocationBtn.textContent = '📍 Location obtained ✓';
                        getCurrentLocationBtn.disabled = false;
                    })
                    .catch(e => {
                        console.error('Geolocation error:', e);
                        const locationStatus = document.getElementById('location-status');
                        locationStatus.textContent = '✓ Coordinates captured (address lookup failed)';
                        locationStatus.style.display = 'block';
                        getCurrentLocationBtn.textContent = '📍 Location obtained ✓';
                        getCurrentLocationBtn.disabled = false;
                    });
            },
            function(error) {
                let errorMsg = '';
                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        errorMsg = 'Permission to access location denied';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMsg = 'Location information unavailable';
                        break;
                    case error.TIMEOUT:
                        errorMsg = 'Location request timed out';
                        break;
                    default:
                        errorMsg = 'Error getting location: ' + error.message;
                }
                
                const locationStatus = document.getElementById('location-status');
                locationStatus.textContent = '✗ ' + errorMsg;
                locationStatus.style.color = '#ffb6c1';
                locationStatus.style.display = 'block';
                
                getCurrentLocationBtn.textContent = '📍 Use Live Location';
                getCurrentLocationBtn.disabled = false;
            }
        );
    });
}

const createRequestForm = document.getElementById('create-request-form');
if (createRequestForm) {
    createRequestForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const bloodGroup = document.getElementById('request-blood-group').value;
        const location = document.getElementById('request-location').value;
        const urgencyLevel = document.getElementById('request-urgency').value;
        const coords = document.getElementById('request-coords').value;
        
        if (!bloodGroup || !location) {
            alert('Please select blood group and enter location');
            return;
        }
        
        let lat, lng;
        
        try {
            if (coords) {
                const [latStr, lngStr] = coords.split(',').map(v => v.trim());
                lat = parseFloat(latStr);
                lng = parseFloat(lngStr);
            } else if (navigator.geolocation) {
                const position = await new Promise((resolve, reject) => {
                    navigator.geolocation.getCurrentPosition(resolve, reject);
                });
                lat = position.coords.latitude;
                lng = position.coords.longitude;
            }
            
            const response = await fetch(`${API_BASE}/api/requests`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    blood_group: bloodGroup,
                    location: location,
                    urgency_level: urgencyLevel,
                    latitude: lat,
                    longitude: lng
                })
            });
            
            if (response.ok) {
                alert('Blood request created successfully!');
                requestModal.style.display = 'none';
                createRequestForm.reset();
                document.getElementById('coordinates-group').style.display = 'none';
                document.getElementById('location-status').style.display = 'none';
                document.getElementById('get-current-location-btn').textContent = '📍 Use Live Location';
                loadDashboard();
            } else {
                const error = await response.json();
                alert('Error: ' + (error.error || 'Failed to create request'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error: ' + error.message);
        }
    });
}

function showMessage(element, message, type = 'success') {
    if (!element) return;
    
    element.textContent = message;
    element.className = `message ${type}`;
    element.style.display = 'block';
    
    if (type === 'success') {
        setTimeout(() => {
            element.style.display = 'none';
        }, 3000);
    }
}