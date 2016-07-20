

var map;
function initMap() {
    map = new google.maps.Map(document.getElementById('map'), {
        center: {lat: center_lat, lng: center_lng},
        zoom: 16
    });
    
    marker = new google.maps.Marker({
        position: {lat: center_lat, lng: center_lng},
        map: map,
        animation: google.maps.Animation.DROP
    });

};


function pokemonLabel(name, disappear_time, id, disappear_time, latitude, longitude) {
    disappear_date = new Date(disappear_time)
    let pad = number => number <= 99 ? ("0"+number).slice(-2) : number;
    
    var label = `
        <div>
            <b>${name}</b>
            <span> - </span>
            <small>
                <a href='http://www.pokemon.com/us/pokedex/${id}' target='_blank' title='View in Pokedex'>#${id}</a>
            </small>
        </div>
        <div>
            Disappears at ${pad(disappear_date.getHours())}:${pad(disappear_date.getMinutes())}:${pad(disappear_date.getSeconds())} 
            <span class='label-countdown' disappears-at='${disappear_time}'>(00m00s)</span></div>
        <div>
            <a href='https://www.google.com/maps/dir/Current+Location/${latitude},${longitude}' 
                    target='_blank' title='View in Maps'>Get Directions</a>
        </div>`;
    return label;
};



map_objects = {} // dict containing all markers (pokemon, stops, gyms) on the map.


function setupPokemonMarker(item) {
    var marker = new google.maps.Marker({
        position: {lat: item.latitude, lng: item.longitude},
        map: map,
        icon: 'static/icons/'+item.pokemon_id+'.png'
    });
    
    marker.infoWindow = new google.maps.InfoWindow({
        content: pokemonLabel(item.pokemon_name, item.disappear_time, item.pokemon_id, item.disappear_time, item.latitude, item.longitude)
    });
    
    marker.addListener('click', function() {
        marker.infoWindow.open(map, marker);
        updateLabelDiffTime();
        marker.persist = true;
    });
    
    google.maps.event.addListener(marker.infoWindow,'closeclick',function(){
        marker.persist = null;
    });

    marker.addListener('mouseover', function() {
        marker.infoWindow.open(map, marker);
        updateLabelDiffTime();
    });
    
    marker.addListener('mouseout', function() {
        if (!marker.persist) {
            marker.infoWindow.close();
        }
    });

    return marker;
};

function clearStaleMarkers(){
    $.each(map_objects, function(key, value) {
        
        if (map_objects[key]['disappear_time'] < new Date().getTime()) {
            map_objects[key].marker.setMap(null);
            console.log("removing marker with key "+key);
            delete map_objects[key];
        }
    });
};

function updateMap() {
    $.ajax({
        url: "/map-data",
        type: 'GET',
        data: {'pokemon': document.getElementById('pokemon-checkbox').checked,
               'pokestops': document.getElementById('pokestops-checkbox').checked,
               'pokestops-lured': document.getElementById('pokestops-lured-checkbox').checked,
               'gyms': document.getElementById('gyms-checkbox').checked},
        dataType: "json"
    }).done(function(result){
        $.each(result, function(i, item){
            
            if (item.encounter_id in map_objects) {
                // do nothing 
            }
            else { // add marker to map and item to dict
                item.marker = setupPokemonMarker(item);
                map_objects[item.encounter_id] = item;
            }
            
        });
        clearStaleMarkers();
    });
};

window.setInterval(updateMap, 5000);
updateMap();

var coverage;
function displayCoverage() {
    $.getJSON("/cover", {format: "json"}).done(function(data) {        
        var coverage = new google.maps.Polygon({
            paths: data,
            strokeColor: '#FF0000',
            strokeOpacity: 0.6,
            strokeWeight: 1,
            fillColor: '#FF0000',
            fillOpacity: 0.08,
            clickable: false
        });
        coverage.setMap(map);
    });
}
displayCoverage();

var updateLabelDiffTime = function() {
    $('.label-countdown').each(function (index, element) {
        var disappearsAt = new Date(parseInt(element.getAttribute("disappears-at")));
        var now = new Date();
        
        var difference = Math.abs(disappearsAt - now);
        var hours = Math.floor(difference / 36e5);
        var minutes = Math.floor((difference - (hours * 36e5)) / 6e4);
        var seconds = Math.floor((difference - (hours * 36e5) - (minutes * 6e4)) / 1e3);
        
        if(disappearsAt < now){
            timestring = "(expired)";
        } 
        else {
            timestring = "(";
            if(hours > 0)
                timestring = hours + "h";
            
            timestring += ("0" + minutes).slice(-2) + "m";
            timestring += ("0" + seconds).slice(-2) + "s";
            timestring += ")";
        }

        $(element).text(timestring)
    });
};

window.setInterval(updateLabelDiffTime, 1000);
