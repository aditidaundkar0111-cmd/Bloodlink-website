const API_BASE = "";

let map = null;
let markers = [];


function applyQuickAccessBloodGroup() {
    const params = new URLSearchParams(window.location.search);
    const bg = params.get("blood_group")?.replace(" ", "+");

    if (bg) {
        const select = document.getElementById("blood-group");
        if (select) select.value = bg;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    initializeMap();
    attachSearchHandlers();
    applyQuickAccessBloodGroup();  
});

function initializeMap() {
    const mapElement = document.getElementById('map');

    if (mapElement && map === null) {
        map = L.map('map').setView([18.5204, 73.8567], 12);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);

        setTimeout(() => {
            map.invalidateSize();
        }, 200);
    }
}

window.addEventListener("load", function () {
    if (map) {
        map.invalidateSize();
    }
});

function attachSearchHandlers() {
    const searchBtn = document.getElementById('search-btn');
    const currentLocBtn = document.getElementById('current-location-btn');

    if (searchBtn) {
        searchBtn.addEventListener('click', performSearch);
    }

    if (currentLocBtn) {
        currentLocBtn.addEventListener('click', getCurrentLocation);
    }
}

function getCurrentLocation() {
    if (navigator.geolocation) {
        document.getElementById('current-location-btn').textContent = 'Getting location...';

        navigator.geolocation.getCurrentPosition(function (position) {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;

            map.setView([lat, lng], 13);

            L.circleMarker([lat, lng], {
                radius: 10,
                color: '#3498db',
                fillColor: '#3498db',
                fillOpacity: 0.8
            }).addTo(map).bindPopup('Your Location');

            window.currentLocation = { lat, lng };

            document.getElementById('current-location-btn').textContent = 'Location obtained ✓';
            performSearch();
        }, function (error) {
            alert('Could not get your location: ' + error.message);
        });
    } else {
        alert('Geolocation is not supported by your browser');
    }
}

async function performSearch() {
    let bloodGroup = document.getElementById('blood-group')?.value;
    if (!bloodGroup) {
        const params = new URLSearchParams(window.location.search);
        bloodGroup = params.get("blood_group")?.replace(" ", "+");
    }

    const radius = parseInt(document.getElementById('radius')?.value || 10);
    const urgency = document.getElementById('urgency')?.value || 2;

    if (!bloodGroup) {
        alert('Please select a blood group');
        return;
    }

    if (!window.currentLocation) {
        alert('Please select your location first');
        return;
    }

    const userLat = window.currentLocation.lat;
    const userLng = window.currentLocation.lng;

    try {
        const response = await fetch(`${API_BASE}/api/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                blood_group: bloodGroup,
                latitude: userLat,
                longitude: userLng,
                radius_km: radius,
                urgency: urgency
            })
        });

        const data = await response.json();

        if (response.ok) {
            displayDonors(data.donors || []);
        } else {
            alert('Search failed: ' + (data.error || 'Unknown error'));
        }

    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function displayDonors(donors) {
    const donorsList = document.getElementById('donors-list');

    if (donors.length === 0) {
        donorsList.innerHTML = '<div class="no-results"><p>No donors found in this area</p></div>';
        return;
    }
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];

    let html = '';
    donors.forEach(donor => {
        html += `
        ${(() => {
            let urgencyClass = "low";
            if (donor.ai_score >= 8) urgencyClass = "high";
            else if (donor.ai_score >= 5) urgencyClass = "medium";
            return `<div class="donor-card ${urgencyClass}">`;
        })()}
            <h3>${donor.name}</h3>
            <div class="donor-info">
                <p><span class="donor-badge badge-blood">${donor.blood_group}</span></p>
                <p><strong>Distance:</strong> <span class="donor-badge badge-distance">${donor.distance_km} km</span></p>
                <p><strong>City:</strong> ${donor.city || 'N/A'}</p>
                <p><strong>Status:</strong>
                    <span class="donor-badge ${donor.is_available ? 'badge-available' : 'badge-unavailable'}">
                        ${donor.is_available ? 'Available' : 'Unavailable'}
                    </span>
                </p>
                <p><strong>Donations:</strong> ${donor.donation_count}</p>
                ${donor.is_verified ? '<p><i class="fas fa-check-circle"></i> Verified Donor</p>' : ''}
            </div>

            <div class="donor-buttons">
                <a href="tel:${donor.phone}" class="btn btn-primary">Call</a>
                <a href="mailto:${donor.email}" class="btn btn-secondary">Email</a>
            </div>
        </div>
        `;

        if (donor.latitude && donor.longitude) {
            const marker = L.marker([donor.latitude, donor.longitude])
                .bindPopup(`
                    <b>${donor.name}</b><br>
                    Blood: ${donor.blood_group}<br>
                    Distance: ${donor.distance_km} km<br>
                    <a href="tel:${donor.phone}">Call</a>
                `)
                .addTo(map);
            markers.push(marker);
        }
    });

    donorsList.innerHTML = html;
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