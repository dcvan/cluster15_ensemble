/**
 * 
 */
$(document).ready(function(){
	$('canvas').each(function(){
		$(this).width = 1300;
		$(this).height = 500;
	});
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
			
			plotLine(walltimeChart, labels, [{'label': 'Walltime', 'data': data.walltime, 'color': '151,187,205'}], $('#walltime_legend').get(0));
		}
	});
	
	$('.nav li a').click(function(e){
		e.preventDefault();
		var job = $(this).data('cmdline');
		$(this).tab('show');
		$.ajax({
			url: '/types/genomic/jobs/' + job,
			type: 'POST',
			contentType: 'application/json',
			success: function(data){
				var labels = [],  
					cpuData = {
						'label': 'CPU Usage',
						'color': '170,57,57',
						'data': []
					},
					memData = {
						'label': 'Memory Usage',
						'color': '151,187,205',
						'data': []
					};
				for(i = 0; i < data.length; i ++){
					var m = new Date(data[i].start_time)
					labels.push(m.getUTCFullYear() 
						+"/"+ (m.getUTCMonth()+1) 
						+"/"+ m.getUTCDate() 
						+ " " + m.getUTCHours() 
						+ ":" + m.getUTCMinutes() 
						+ ":" + m.getUTCSeconds());
					cpuData.data.push(data[i].avg_cpu_percent);
					memData.data.push(data[i].avg_mem_percent);
				}
				
				plotLine(new Chart($('#cpu_mem_paint canvas').get(0).getContext('2d')), labels, [cpuData, memData], $('#cpu_mem_paint div').get(0));
			}
		})
	});
	
	var firstTab = $('.nav li').first();
	firstTab.addClass('active');
	firstTab.find('a').click();
});

function plotLine(chart, labels, ds, legend_area){
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
	
	chart.Line(lineData, {bezierCurve: false});
	legend(legend_area, lineData);
}