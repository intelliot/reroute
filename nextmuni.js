function nextmuni(main) {
// var host = "http://localhost:8888";
var host = "http://ec2-54-241-123-169.us-west-1.compute.amazonaws.com";
var routes = [
	{pat: /^$/, fun: loadRouteList},
	{pat: /^prediction\/([^\/]+)\/([^\/]+)$/, fun: loadPrediction},
	{pat: /^([^\/]+)$/, fun: loadRoute},
	{pat: /^([^\/]+)\/([^\/]+)$/, fun: loadStops},
	{pat: /^([^\/]+)\/([^\/]+)\/([^\/]+)$/, fun: loadStops},
];
function path() {
	if (!location.hash) return "";
	if (location.hash.charAt(0) === "#") return location.hash.substr(1);
	return location.hash;
}
function pathstillsame(args) {
	var p = path();
	var m;
	if ((m = this.pat.exec(p))) {
		for (var i = 0; i < args.length; i++) {
			if (m[i + 1] !== args[i])
				return false;
		}
	}
	return true;
}
function loadRouteList() {
	var args = arguments;
	$.ajax(host + "/routelist", {dataType: "json", context: this}).done(function(routeList) {
		if (! pathstillsame.call(this, args))  // canceled
			return;
		var top = $("<div>");
		for (var i = 0; i < routeList.length; i++) {
			var route = routeList[i];
			var div = $("<div>").appendTo(top);
			$("<a>").text(route.title).attr("href", "#" + route.tag).appendTo(div).data("route", route).click(function(e) {
				go(e.target.getAttribute("href"));
				e.preventDefault();
			});
		}
		$(main).empty().append(top);
	});
}
function loadRoute(tag) {
	var args = arguments;
	$.ajax(host + "/routeconfig/" + tag, {dataType: "json", context: this}).done(function(routeConfig) {
		if (! pathstillsame.call(this, args))  // canceled
			return;
		var div = $("<div>");
		for (var i = 0; i < routeConfig.directions.length; i++) {
			var dir = routeConfig.directions[i];
			$("<a>").text(dir.title).attr("href", "#" + tag + "/" + dir.tag).data("direction", dir).appendTo($("<div>").appendTo(div));
		}
		$(main).empty().append(div);
	});
}
function loadStops(routeTag, dirTag) {
	var args = arguments;
	$.ajax(host + "/routeconfig/" + routeTag, {dataType: "json", context: this}).done(function(routeConfig) {
		if (! pathstillsame.call(this, args))  // canceled
			return;
		var div = $("<div>");
		for (var i = 0; i < routeConfig.directions.length; i++) {
			var dir = routeConfig.directions[i];
			if (dir.tag !== dirTag)
				continue;
			for (var j = 0; j < dir.stops.length; j++) {
				var stop = dir.stops[j];
				$("<a>").text(stop.title).attr("href", "#prediction/" + stop.stopId + "/" + routeTag).data("stop", stop).appendTo($("<div>").appendTo(div));
			}
		}
		$(main).empty().append(div);
	});
}
function pad2(s) {
	s = "" + s;
	if (s.length < 2) return "0" + s;
	else return s;
}
function loadPrediction(stopId, routeTag) {
	var args = arguments;
	$.ajax(host + "/routeconfig/" + routeTag, {dataType: "json", context: this}).done(function(routeConfig) {
		$.ajax(host + "/prediction/" + stopId + "/" + routeTag, {dataType: "json", context: this}).done(function(directions) {
			if (! pathstillsame.call(this, args))  // canceled
				return;
			var div = $("<div>");
			function rerender() {
				if (0 === div.closest("html").length) {
					return;
				}
				div.empty();
				$("<h2>").appendTo(div).text(routeConfig.title)
				for (var i = 0; i < directions.length; i++) {
					var dir = directions[i];
					$("<h3>").appendTo(div).text(dir.title)
					var lastPredictionIdx;
					for (var j = 0; j < dir.predictions.length; j++) {
						if (dir.predictions[j].epochTime != null) lastPredictionIdx = j;
					}
					var nowSeconds = Math.floor(+new Date/1000);
					for (var j = 0; j <= lastPredictionIdx; j++) {
						var pred = dir.predictions[j];
						var timediv = $("<div class=timediv>");
						var predSpan = null, schedSpan = null;
						var isInPast = true;
						if (pred.epochTime != null) {
							var predSecs = pred.epochTime/1000 - nowSeconds;
							if (predSecs > 0)
								isInPast = false;
							predSpan = $("<span>");
							$("<span class='pred minutes'>").text(Math.floor(predSecs/60)).appendTo(predSpan);
							$("<span class='pred seconds'>").text(":" + pad2(Math.floor(predSecs%60))).appendTo(predSpan);
							predSpan.append(" minutes");
						}
						if (pred.scheduledTime != null) {
							var schedSecs = pred.scheduledTime/1000 - nowSeconds;
							if (schedSecs > 0)
								isInPast = false;
							schedSpan = $("<span>");
							schedSpan.append(" ");
							$("<span class='sched minutes'>").text(Math.floor(schedSecs/60)).appendTo(schedSpan);
							$("<span class='sched seconds'>").text(":" + pad2(Math.floor(schedSecs%60))).appendTo(schedSpan);
							schedSpan.append(" minutes");
						}
						if (isInPast)
							continue;
						if (pred.epochTime != null && pred.scheduledTime != null) {
							timediv.append(predSpan);
							// timediv.append(schedSpan);
							if (pred.epochTime - pred.scheduledTime > 3 * 60 * 1000) {
								// late
								timediv.addClass("late");
								if (pred.epochTime - pred.scheduledTime > 3 * 60 * 1000) {
									timediv.addClass("verylate");
								}
								var minutesLate = Math.round((pred.epochTime - pred.scheduledTime) / 1000 / 60);
								timediv.append(" (" + minutesLate + " minutes late!)");
							} else if (pred.epochTime - pred.scheduledTime < - 1 * 60 * 1000) {
								timediv.addClass("early");
								var minutesEarly = -Math.round((pred.epochTime - pred.scheduledTime) / 1000 / 60);
								timediv.append(" (" + minutesEarly + " minutes early!)");
							} else {
								timediv.addClass("ontime");
							}
						} else if (pred.epochTime == null) {
							timediv.append(schedSpan);
							timediv.append(" (scheduled) bus missing!");
							timediv.addClass("missing");
						} else if (pred.scheduledTime == null) {
							timediv.append(predSpan);
							timediv.append(" (unscheduled)");
							timediv.addClass("unscheduled");
						}
						timediv.appendTo(div);
					}
				}
				setTimeout(rerender, 1000);
			}
			$(main).empty().append(div);
			rerender();
		});
	});
}

var currentPage = "invalid";
function go(hash) {
	if (hash.charAt(0) == "#") hash = hash.substr(1);
	for (var i = 0; i < routes.length; i++) {
		var route = routes[i];
		var m;
		if (m = route.pat.exec(hash)) {
			var args = Array.prototype.slice.call(m, 1);
			route.fun.apply(route, args);
			break;
		}
	}
	location.hash = currentPage = hash;
}
function checkhash() {
	var currentHash = path();
	if (currentHash.charAt(0) == '#') currentHash = currentHash.substr(1); 
	if (currentPage != currentHash) {
		currentPage = currentHash;
		go(currentHash);
	}
}
document.addEventListener("click", function(e) {
	var href = e.target.getAttribute("href");
	if (href && href.charAt(0) == "#") {
		go(href.substr(1));
		e.preventDefault();
		e.stopPropagation();
	}
}, false)
checkhash();
setInterval(checkhash, 1000);
}