/**
 * 
 */
$(document).ready(function(){
	$('.nav li').first().addClass('active');
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
			
			plotLine(walltimeChart, labels, 'Walltime', data.walltime, $('#walltime_legend').get(0));
		}
	});
	
	$('.nav li a').click(function(e){
		e.preventDefault();
		var job = $(this).text();
		$.ajax({
			url: '/types/genomic/jobs/' + job,
			type: 'POST',
			contentType: 'application/json',
			success: function(data){
				var labels = [], cpuUsage = [];
				for(i = 0; i < data.length; i ++){
					var m = new Date(data[i].start_time)
					labels.push(m.getUTCFullYear() 
						+"/"+ (m.getUTCMonth()+1) 
						+"/"+ m.getUTCDate() 
						+ " " + m.getUTCHours() 
						+ ":" + m.getUTCMinutes() 
						+ ":" + m.getUTCSeconds());
					cpuUsage.push(data.avg_cpu_percent);
					plotLine(new Chart($('#cpu_mem_paint canvas').get(0).getContext('2d')), labels, 'CPU Usage', cpuUsage, $('#cpu_mem_paint div').get(0));
				}
			}
		})
	});
});

function plotLine(chart, labels, label, data, legend_area){
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
	
	chart.Line(lineData, {bezierCurve: false});
	legend(legend_area, lineData);
}