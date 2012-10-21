$(document).ready( function() {


	$('#select-route').click( function() {
		// When clicked on, then put route container on top and shift it over.
		$('#time-container').addClass('none');
		$('#route-container').removeClass('none');
		$('.carousel').carousel('next');

		google.maps.event.addDomListener(window, 'load', initialize());
	});

    initTableView();
    initTimeSelector();
});

function initTableView() {
	$('.carousel').carousel({interval:false});


	$('.back-button').click( function() {
		$('.carousel').carousel('prev');
	});

	$('#select-time').click( function() {
		// When clicked on, then put time container on top and shift it over.
		$('#route-container').addClass('none');
		$('#time-container').removeClass('none');
		$('.carousel').carousel('next');
	});
}

function initTimeSelector() {
	// If select 'day' class, toggle blue color.
	$('.day').click( function() {
		$(this).toggleClass('btn-info');
	});

	$('#set-time-button').click( function() {
		// see what 'day' classes have the class 'btn-info'. Be smart about it.
		var dayString = "";
		$('.day').each( function() {
			if ($(this).hasClass('btn-info')) {
				dayString = dayString + $(this).html() + ", ";
			}
		});
		if (dayString.length > 0) {
			// Remove the last space and comma
			dayString = dayString.substring(0, dayString.length - 2);
		}
		if (dayString == "M, T, W, Th, F") {
			dayString = "Weekdays";
		} else if (dayString == "M, T, W, Th, F, Sat, Sun") {
			dayString = "Everyday";
		}
		$('#time-message').html(dayString);
		$('#select-time .subtitle').html(dayString);
	});
}


function initialize() {
var mapOptions = {
  zoom: 14,
  center: new google.maps.LatLng(37.775, -122.4183),
  mapTypeId: google.maps.MapTypeId.ROADMAP
};

map = new google.maps.Map(document.getElementById('map_canvas'),
    mapOptions);

  var transitLayer = new google.maps.TransitLayer();
  transitLayer.setMap(map);

  var directionsDisplay = new google.maps.DirectionsRenderer();
  directionsDisplay.setMap(map);

  var markerOptions = {
  	draggable: true,
  	flat: false,
  	position: new google.maps.LatLng(37.775, -122.4183)
  }
  var startMarker = new google.maps.Marker( markerOptions );
  var endMarker = new google.maps.Marker( markerOptions );

  startMarker.setMap(map);
  endMarker.setMap(map);


  $('#set-route-button').click( function() {
  	// Query google maps with both end points LatLng.
  	var startLatLng = startMarker.getPosition();
  	var endLatLng = endMarker.getPosition();

  	var directionsService = new google.maps.DirectionsService();
  	
	var request = {
		origin:startLatLng,
		destination:endLatLng,
		travelMode: google.maps.TravelMode.TRANSIT
	};

	directionsService.route(request, function(response, status) {
		if (status == google.maps.DirectionsStatus.OK) {
			directionsDisplay.setDirections(response);
			var transitInfo = "";
			// Loop until a transit object is found, and then save that information.
			for ( var i = 0; i < response.routes.length; i++ ) {
				for ( var j = 0; j < response.routes[i].legs.length; j++ ) {
					for ( var k = 0; k < response.routes[i].legs[j].steps.length; k++ ) {
						if ( typeof response.routes[i].legs[j].steps[k].transit === "undefined" ) {
							console.log("no transit data yet");
						} else {
							transitInfo = transitInfo + response.routes[i].legs[j].steps[k].transit.line.short_name + "-"
											  + response.routes[i].legs[j].steps[k].transit.line.name + ", ";
						}
					}
				}
			}
			if (transitInfo.length > 0) {
				transitInfo = transitInfo.substring(0, transitInfo.length - 2);
			}
			$('#route-message').html("You have selected " + transitInfo + ".");
			$('#select-route .subtitle').html(transitInfo);
		}
	});

  })

}