/**
 * 
 */
$(document).ready(function(){
	$.ajax({
		url: window.location.pathname,
		type: 'POST',
		contentType: 'application/json',
		success: function(data){
			var labels = [];
			var walltimeChart = new Chart($('#walltime').get(0).getContext('2d'));
			for(i = 0; i < data.experiments.length; i ++){
				var m = new Date(data.experiments[i]);
				labels.push(m.getUTCFullYear() 
						+"/"+ (m.getUTCMonth()+1) 
						+"/"+ m.getUTCDate() 
						+ " " + m.getUTCHours() 
						+ ":" + m.getUTCMinutes() 
						+ ":" + m.getUTCSeconds());
			}
			
			plotLine(walltimeChart, labels, 'Walltime', data.walltime, document.getElementById('walltime_legend'));
		}
	});
});

function plotLine(chart, labels, label, data, lengend_area){
	var color = 'rgba(151, 187, 205';
	var lineData = {
			labels: labels,
			datasets: [
			   {
				   label: label,
				   fillColor: color +',0.2)',
		           strokeColor: color + ',1)',
		           pointColor: color + ',1)',
		           pointStrokeColor: '#fff',
		           pointHighlightFill: '#fff',
		           pointHighlightStroke: color + ',1)',
		           data: data
			   }
			]
	};
	
	chart.Line(data, {bezierCurve: false});
	legend(legend_area, lineData);
}