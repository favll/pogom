"use strict"

var $numThreads = $(".num-threads");
var $numAccounts = $(".num-accounts");
var $lastRequestLabel = $(".last-request");
var $fullScanLabel = $(".full-scan");
var $scanPercentLabel = $(".current-scan-percent");

var $selectExclude = $("#exclude-pokemon");
var excludedPokemon = [];

var map;
var scanLocations = new Map();
var coverCircles = [];
var newLocationMarker;

var $heatMapMons = $("#heat-map-mons");
var heatMapData = {};
var pokeList = [];  // contains all 150 pokemon in form { id: id, text: name}


try {
    excludedPokemon = JSON.parse(localStorage.excludedPokemon);
} catch (e) {}


function getFromStorage(keyName, default_value) {
    var res = localStorage.getItem(keyName);
    if(res){
        return res === "true";
    } else {
        return default_value;
    }
}

function pad(num, size) {
    var s = num+"";
    if (s.length < 2) s = "0" + s;
    return s;
}

document.getElementById('pokemon-checkbox').checked = getFromStorage("displayPokemons", "true");
document.getElementById('gyms-checkbox').checked = getFromStorage("displayGyms", "true");
document.getElementById('coverage-checkbox').checked = getFromStorage("displayCoverage", "true");


$.getJSON("locale").done(function(data) {

    $.each(data, function(key, value) {
        pokeList.push( { id: key, text: value } );
    });

    $selectExclude.select2({
        placeholder: "Type to exclude Pokemon",
        data: pokeList
    });
    $selectExclude.val(excludedPokemon).trigger("change");

    $heatMapMons.select2({
      placeholder: "Type to add a heatmap filter",
      data: pokeList
    });
});

// exclude multi-select listener
$selectExclude.on("change", function (e) {
    excludedPokemon = $selectExclude.val().map(Number);
    localStorage.excludedPokemon = JSON.stringify(excludedPokemon);
    clearStaleMarkers();
});

$heatMapMons.on("change", function (e){
    var heatMapMons = $heatMapMons.val().map(Number);

    $.each(pokeList, function(i, poke) {
        if (typeof google === 'undefined') return;
        if (!heatMapData[poke.id]) return;

        if (heatMapMons.indexOf(parseInt(poke.id)) != -1) {
            heatMapData[poke.id]['map'].setMap(map);
        } else {
            heatMapData[poke.id]['map'].setMap(null);
        }
    });
});

// Stolen from http://www.quirksmode.org/js/cookies.html
function readCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for(var i=0;i < ca.length;i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1,c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
    }
    return null;
}

function is_logged_in(){
    if ($(".auth-status")[0].classList.contains("label-success")) {
        return true
    } else {
        return false
    }
}

function drawHeatMap(index, item) {
    heatMapData[index]['map'] =  new google.maps.visualization.HeatmapLayer({
        data: item.data,
        dissipating: true,
        map: null
    })
}


function updateHeatMap() {
    $.ajax({
        url: "heatmap-data",
        type: 'GET',
        data: {'pokemon': localStorage.displayPokemons},
        dataType: "json"
    }).done(function(pokemons) {
        // Google's heatmap example
        $.each(pokemons, function(i, item){
            if (item.count == 0 ) {
                return false;
            }
            var latLng = new google.maps.LatLng(item.latitude, item.longitude);
            var magnitude = item.count;
            var weightedLoc = {
                location: latLng,
                weight: magnitude
            }
            if(heatMapData[item.pokemon_id]) {
                heatMapData[item.pokemon_id]['data'].push(weightedLoc);
            } else {
                heatMapData[item.pokemon_id] = {
                    name: item.name,
                    data: [weightedLoc]
                };
            }
        });
        $.each(heatMapData, function (i, item) {
            drawHeatMap(i, item);
        })

    });
}

function initMap() {
    var initLat = 40.782850;  // NYC Central Park
    var initLng = -73.965288;

    if (initialScanLocations.length !== 0) {
        initLat = initialScanLocations[0].latitude;
        initLng = initialScanLocations[0].longitude;
    }

    map = new google.maps.Map(document.getElementById('map'), {
        // Change this to geolocation?
        center: {lat: initLat, lng: initLng},
        zoom: 13,
        mapTypeControl: false,
        streetViewControl: false,
        disableAutoPan: true
    });

    updateScanLocations(initialScanLocations);
    updateMap();
    updateHeatMap();

    if(is_logged_in()) {
        // on click listener for
        google.maps.event.addListener(map, 'click', function(event) {
            if (newLocationMarker) {
                newLocationMarker.setMap(null);
            }
            newLocationMarker = new google.maps.Marker({
                position: event.latLng,
                map: map
            });
            newLocationMarker.infoWindow = new google.maps.InfoWindow({
                content: "<button id=\"new-loc-btn\">Add new Location</button><input style=\"width: 75px;\" id=\"new-loc-radius\" type=\"number\" placeholder=\"Radius (meters)\">",
                disableAutoPan: true
            });
            newLocationMarker.infoWindow.open(map, newLocationMarker);
            google.maps.event.addListener(newLocationMarker.infoWindow,'closeclick',function(){
                newLocationMarker.setMap(null); //removes the marker
            });
        });

        // change-location button listener
        $('#map').on('click', '#new-loc-btn', function () {
            var radius = parseInt($('#new-loc-radius').val(), 10);
            newLocationMarker.setMap(null);
            if (isNaN(radius) || radius < 100) {
                alert("Radius not valid. Please note that the radius' unit is in meters and must be a whole number. It also should be >100m.")
                return;
            }

            $.post("location",
                {
                    'lat': newLocationMarker.getPosition().lat(),
                    'lng': newLocationMarker.getPosition().lng(),
                    'radius': radius
                },
                function(data) {
                    updateMap();
                },
            "json");
        });
    }

    initGeoLocation();
};

function initGeoLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function(position) {
            map.setCenter({lat: position.coords.latitude, lng: position.coords.longitude});
        });
    }
}

function pokemonLabel(name, id, disappear_time, latitude, longitude) {
    var disappear_date = new Date(disappear_time);

    var label = "<div>\
            <b>" +name+ "</b>\
            <span> - </span>\
            <small>\
                <a href='http://www.pokemon.com/us/pokedex/" +id+ "' target='_blank' title='View in Pokedex'>#"+id+"</a>\
            </small>\
        </div>\
        <div>\
            Disappears at " +pad(disappear_date.getHours())+ ":"+pad(disappear_date.getMinutes())+":"+pad(disappear_date.getSeconds())+"\
            <span class='label-countdown' disappears-at='"+disappear_time+"'>(00m00s)</span></div>\
        <div>\
            <a href='https://www.google.com/maps/dir/Current+Location/"+latitude+","+longitude+"'\
                    target='_blank' title='View in Maps'>Get Directions</a>\
            <a href='#' onclick='removePokemon(\"" + id + "\")')>Hide " + name + "s</a>\
            <a href='#' onclick='addToNotify(\"" + id + "\")')>Notify</a>\
        </div>";
    return label;
};

function removePokemon(id) {
    var selected=$selectExclude.val();
    selected.push(id.toString());
    $selectExclude.val(selected);

    $selectExclude.change();
}

function gymLabel(team_name, team_id, gym_points) {
    var gym_color = [ "0, 0, 0, .4", "74, 138, 202, .6", "240, 68, 58, .6", "254, 217, 40, .6" ];
    var str;
    if (team_name == 0) {
        str = "<div><center>\
            <div>\
                <b style='color:rgba(" + gym_color[team_id] + ")'>" + team_name + "</b><br>\
            </div>\
            </center></div>";
    } else {
        str = "<div><center>\
            <div style='padding-bottom: 2px'>Gym owned by:</div>\
            <div>\
                <b style='color:rgba("+ gym_color[team_id] + ")'>Team " + team_name + "</b><br>\
                <img height='70px' style='padding: 5px;' src='static/forts/" + team_name + "_large.png'> \
            </div>\
            <div>Prestige: " + gym_points + "</div>\
            </center></div>";
    }

    return str;
}


var map_pokemons = {}; // dict containing all pokemons on the map.
var map_gyms = {};
var gym_types = [ "Uncontested", "Mystic", "Valor", "Instinct" ];

function setupPokemonMarker(item) {
    var myIcon = new google.maps.MarkerImage('static/icons/'+item.pokemon_id+'.png', null, null, null, new google.maps.Size(30,30));

    var marker = new google.maps.Marker({
        position: {lat: item.latitude, lng: item.longitude},
        map: map,
        icon: myIcon
    });

    var label = pokemonLabel(item.pokemon_name, item.pokemon_id, item.disappear_time, item.latitude, item.longitude);

    marker.infoWindow = new google.maps.InfoWindow({
        content: label,
        disableAutoPan: true
    });

    addListeners(marker);

    return marker;
}

function setupGymMarker(item) {
    var marker = new google.maps.Marker({
        position: {lat: item.latitude, lng: item.longitude},
        map: map,
        icon: 'static/forts/'+gym_types[item.team_id]+'.png'
    });

    marker.infoWindow = new google.maps.InfoWindow({
        content: gymLabel(gym_types[item.team_id], item.team_id, item.gym_points),
        disableAutoPan: true
    });

    addListeners(marker);
    return marker;
}

function addListeners(marker){
    marker.addListener('click', function() {
        marker.infoWindow.open(map, marker);
        updateLabelDiffTime();
        marker.persist = true;
        marker.setAnimation(null);
    });

    google.maps.event.addListener(marker.infoWindow,'closeclick',function(){
        marker.persist = null;
    });

    var isMobile = (/iphone|ipod|android|ie|blackberry|fennec/).test(navigator.userAgent.toLowerCase());

    if (!isMobile){
        marker.addListener('mouseover', function() {
            marker.infoWindow.open(map, marker);
            updateLabelDiffTime();
        });

        marker.addListener('mouseout', function() {
            if (!marker.persist) {
                marker.infoWindow.close();
            }
        });
    }
    return marker
}

function clearStaleMarkers(){
    $.each(map_pokemons, function(key, value) {
        if (map_pokemons[key]['disappear_time'] < new Date().getTime() ||
                excludedPokemon.indexOf(map_pokemons[key]['pokemon_id']) >= 0) {
            map_pokemons[key].marker.setMap(null);
            console.log("removing marker with key "+key);
            delete map_pokemons[key];
        }
    });
}


function newMarker(latitude, longitude) {
    var marker = new google.maps.Marker({
        position: {lat: latitude, lng: longitude},
        map: map,
        animation: google.maps.Animation.DROP
    });
    marker.setVisible(document.getElementById('coverage-checkbox').checked);

    // This is soooo ugly...
    if (is_logged_in()) {
        var latStr = latitude.toString().replace('.', '');
        var lngStr = longitude.toString().replace('.', '');
        var buttonId = "del-loc-btn-" + latStr + lngStr;

        marker.infoWindow = new google.maps.InfoWindow({
            content: "<button id=\"" + buttonId + "\">Delete Location</button>",
            disableAutoPan: true
        });

        marker.addListener('click', function () {
            marker.infoWindow.open(map, marker);
        });

        // This is not a very beautiful solution
        $('#map').on('click', '#' + buttonId, function () {
            $.ajax({
                url: 'location',
                method: 'DELETE',
                data: {
                    'lat': latitude,
                    'lng': longitude
                },
                success: function(data) {
                    updateMap();
                }
            });

            removeScanLocation(latitude + "," + longitude);
        });
    }


    return marker;
}

function newCircle(latitude, longitude, radius) {
    var coverCircle = new google.maps.Circle({
        strokeColor: '#FF0000',
        strokeOpacity: 0.6,
        strokeWeight: 1,
        fillColor: '#FF0000',
        fillOpacity: 0.08,
        clickable: false,
        map: map,
        center: {lat: latitude, lng: longitude},
        radius: radius
    });
    coverCircle.setVisible(document.getElementById('coverage-checkbox').checked);

    return coverCircle;
}


function removeScanLocation(key) {
    if (scanLocations.has(key)) {
        var loc = scanLocations.get(key);
        loc.marker.setMap(null);
        loc.circle.setVisible(false);
        scanLocations.delete(key);
    }
    return false;
}


function updateScanLocations(updatedScanLocations) {
    var helperMap = new Map();

    // Add new scan locations
    $.each(updatedScanLocations, function (i, scanLocation) {
        var key = scanLocation.latitude + "," + scanLocation.longitude;
        helperMap.set(key, scanLocation);
        if (!scanLocations.has(key)) {
            scanLocations.set(key, {
                location: scanLocation,
                marker: newMarker(scanLocation.latitude, scanLocation.longitude),
                circle: newCircle(scanLocation.latitude, scanLocation.longitude, scanLocation.radius)
            });
        }
    });

    // Remove old scan locations
    $.each(scanLocations.keys(), function(i, key) {
        if (!helperMap.has(key)) {
            removeScanLocation(key);
        }
    });
}

//               'pokestops': document.getElementById('pokestops-checkbox').checked,
//               'pokestops-lured': document.getElementById('pokestops-lured-checkbox').checked,
function updateMap() {
    $.ajax({
        url: "map-data",
        type: 'GET',
        data: {'pokemon': localStorage.displayPokemons,
               'gyms': localStorage.displayGyms},
        dataType: "json"
    }).done(function(result) {
        statusLabels(result["server_status"]);

        updateScanLocations(result['scan_locations']);

        $.each(result.pokemons, function(i, item){
            if (!document.getElementById('pokemon-checkbox').checked) {
                return false; // in case the checkbox was unchecked in the meantime.
            }

            if (!(item.encounter_id in map_pokemons) &&
                    excludedPokemon.indexOf(item.pokemon_id) < 0) {
                // add marker to map and item to dict
                if (item.marker) item.marker.setMap(null);
                item.marker = setupPokemonMarker(item);
                map_pokemons[item.encounter_id] = item;
                notify(item);
            } else if (item.encounter_id in map_pokemons  && 
                    map_pokemons[item.encounter_id].disappear_time != item.disappear_time) {
                //update label
                map_pokemons[item.encounter_id].disappear_time = item.disappear_time;
                var label = pokemonLabel(item.pokemon_name, item.pokemon_id, item.disappear_time, item.latitude, item.longitude);
                map_pokemons[item.encounter_id].marker.infoWindow.setContent(label);
            }
        });

        $.each(result.gyms, function(i, item){
            if (!document.getElementById('gyms-checkbox').checked) {
                return false; // in case the checkbox was unchecked in the meantime.
            }

            if (item.gym_id in map_gyms) {
                // if team has changed, create new marker (new icon)
                if (map_gyms[item.gym_id].team_id != item.team_id) {
                    map_gyms[item.gym_id].marker.setMap(null);
                    map_gyms[item.gym_id].marker = setupGymMarker(item);
                } else { // if it hasn't changed generate new label only (in case prestige has changed)
                    map_gyms[item.gym_id].marker.infoWindow = new google.maps.InfoWindow({
                        content: gymLabel(gym_types[item.team_id], item.team_id, item.gym_points),
                        disableAutoPan: true
                    });
                }
            }
            else { // add marker to map and item to dict
                if (item.marker) item.marker.setMap(null);
                item.marker = setupGymMarker(item);
                map_gyms[item.gym_id] = item;
            }
        });

        clearStaleMarkers();
    }).fail(function() {
        $lastRequestLabel.removeClass('label-success label-warning');
        $lastRequestLabel.addClass('label-danger');
        $lastRequestLabel.html("Disconnected from Server")
    });
}

window.setInterval(updateMap, 10000);

$('#gyms-checkbox').change(function() {
    localStorage.displayGyms = this.checked;
    if(this.checked) {
        updateMap();
    } else {
        $.each(map_gyms, function(key, value) {
            map_gyms[key].marker.setMap(null);
        });
        map_gyms = {}
    }
});

$('#pokemon-checkbox').change(function() {
    localStorage.displayPokemons = this.checked;
    if(this.checked) {
        updateMap();
    } else {
        $.each(map_pokemons, function(key, value) {
            map_pokemons[key].marker.setMap(null);
        });
        map_pokemons = {}
    }
});

$('#coverage-checkbox').change(function() {
    localStorage.displayCoverage = this.checked;

    scanLocations.forEach(function (scanLocation, key) {
        scanLocation.circle.setVisible(this.checked);
    }, this);
    scanLocations.forEach(function (scanLocation, key) {
        scanLocation.marker.setVisible(this.checked);
    }, this);
});


// function displayCoverage() {
//     // if (currentLocationMarker) currentLocationMarker.setMap(null);

//     $.each(coverCircles, function(i, circle) {
//         circle.setMap(null);
//     });

//     $.getJSON("cover", {format: "json"}).done(function(data) {
//         // currentLocationMarker = new google.maps.Marker({
//         //     position: {lat: data['center']['lat'], lng: data['center']['lng']},
//         //     map: map,
//         //     animation: google.maps.Animation.DROP
//         // });

//         $.each(data['cover'], function(i, point) {
//             coverCircles.push(new google.maps.Circle({
//                 strokeColor: '#FF0000',
//                 strokeOpacity: 0.6,
//                 strokeWeight: 1,
//                 fillColor: '#FF0000',
//                 fillOpacity: 0.08,
//                 clickable: false,
//                 map: map,
//                 center: point,
//                 radius: 70
//             }));
//         });
//     });
// }

function statusLabels(status) {
    $numThreads.html(status['num-threads'] + " Threads");
    $numAccounts.html(status['num-accounts'] + " Accounts");

    var difference = status['last-successful-request'];

    if (difference == 'na') {

    } else if (difference == 'sleep') {
        $lastRequestLabel.removeClass('label-danger label-warning');
        $lastRequestLabel.addClass('label-success');
        $lastRequestLabel.html("Sleeping");
    } else {
        var timestring = formatTimeDiff(difference);
        if (difference <= 2) {
            $lastRequestLabel.removeClass('label-danger label-warning');
            $lastRequestLabel.addClass('label-success');
        } if (difference > 2 && difference <= 30) {
            $lastRequestLabel.removeClass('label-success label-danger');
            $lastRequestLabel.addClass('label-warning');
        } if (difference > 30) {
            $lastRequestLabel.removeClass('label-success label-warning');
            $lastRequestLabel.addClass('label-danger');
        }
        $lastRequestLabel.html("Last scan: "+timestring+ " ago");
    }

    var timeSinceScan = status['complete-scan-time'];
    if (timeSinceScan)
        $fullScanLabel.html("Last scan in "+ formatTimeDiff(timeSinceScan))

    var currentScanPercentString = status['current-scan-percent'] ? Number((status['current-scan-percent']).toFixed(2)).toString() : 0;
    $scanPercentLabel.html("Current Scan: "+currentScanPercentString+"%");

}

function formatTimeDiff(difference) {
    var hours = Math.floor(difference / 3600);
    var minutes = Math.floor(difference % 3600 / 60);
    var seconds = Math.floor(difference % 3600 % 60);
    var milli = Math.floor((difference % 3600 % 60 - seconds)*100);

    var timestring = "";
    if(hours > 0) timestring += hours + "h";
    if(minutes > 0) timestring += pad(minutes) + "m";
    if (hours == 0) {
        timestring += pad(seconds);

        if (hours > 0 || minutes > 0) {
            timestring += "s"
        } else {
             timestring += "." + pad(milli) + "s"
        }
    }
    return timestring;
}

var updateLabelDiffTime = function() {
    $('.label-countdown').each(function (index, element) {
        var disappearsAt = new Date(parseInt(element.getAttribute("disappears-at")));
        var now = new Date();

        var difference = Math.abs(disappearsAt - now);
        var hours = Math.floor(difference / 36e5);
        var minutes = Math.floor((difference - (hours * 36e5)) / 6e4);
        var seconds = Math.floor((difference - (hours * 36e5) - (minutes * 6e4)) / 1e3);

        var timestring = "";
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
