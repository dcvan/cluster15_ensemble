/**
 * 
 */

function plotLine(canvas, labels, ds, legend_area){
	resize(canvas);
	var lineData = {
			labels: labels,
			datasets: []
	};
	
	for(i = 0; i < ds.length; i ++){
		lineData.datasets.push({
				   label: ds[i].label,
				   fillColor: 'rgba(' + ds[i].color +',0.2)',
		           strokeColor: 'rgba(' + ds[i].color + ',1)',
		           pointColor: 'rgba(' + ds[i].color + ',1)',
		           pointStrokeColor: '#fff',
		           pointHighlightFill: '#fff',
		           pointHighlightStroke: 'rgba(' + ds[i].color + ',1)',
		           data: ds[i].data
		});
	}
	var context = canvas.getContext('2d');
	var chart = new Chart(context).Line(lineData, {bezierCurve: true});
	legend(legend_area, lineData);
	return chart;
}

function plotBar(canvas, labels, ds, legend_area){
	resize(canvas);
	var barData = {
			labels: labels,
			datasets: []
	};
	
	for(i = 0; i < ds.length; i ++){
		barData.datasets.push({
			label: ds[i].label,
            fillColor: 'rgba(' + ds[i].color + ',0.5)',
            strokeColor: 'rgba('+ ds[i].color + ',0.8)',
            highlightFill: 'rgba(' + ds[i].color + ',0.75)',
            highlightStroke: 'rgba(' + ds[i].color + ',1)',
			data: ds[i].data
		});
	}
	var chart = new Chart(canvas.getContext('2d')).Bar(barData, {barShowStroke: true});
	legend(legend_area, barData);
	return chart;
}

function resize(canvas){
	canvas.width = 1050;
	canvas.height = 500;
}

function get_url(path){
	return "http://" + document.location.host + path; 
}