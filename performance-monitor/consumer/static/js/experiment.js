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
			for(i = 0; i < data.experiments.length; i ++){
				var m = new Date(data.experiments[i]);
				labels.push(m.getUTCFullYear() 
						+"/"+ (m.getUTCMonth()+1) 
						+"/"+ m.getUTCDate() 
						+ " " + m.getUTCHours() 
						+ ":" + m.getUTCMinutes() 
						+ ":" + m.getUTCSeconds());
			}
			
			plotLine($('#walltime').get(0), labels, [{'label': 'Walltime', 'data': data.walltime, 'color': '151,187,205'}], $('#walltime_legend').get(0));
		}
	});
	
	$('.nav li a').click(function(e){
		e.preventDefault();
		var job = $(this).data('cmdline'),
			aspect = $(this).data('aspect');
		$(this).tab('show');
		$.ajax({
			url: '/types/genomic/jobs/' + job,
			type: 'POST',
			contentType: 'application/json',
			success: function(data){
				// create labels
				var labels = [];
				for(i = 0; i < data.length; i ++){
					var m = new Date(data[i].start_time)
					labels.push(m.getUTCFullYear() 
						+"/"+ (m.getUTCMonth()+1) 
						+"/"+ m.getUTCDate() 
						+ " " + m.getUTCHours() 
						+ ":" + m.getUTCMinutes() 
						+ ":" + m.getUTCSeconds());
				}
				if(aspect == 'runtime'){
					var runtime = {
							'label': 'Runtime',
							'color': '151,187,205',
							'data': []
						};
					for(i = 0; i < data.length; i ++){
						runtime.data.push(data[i].runtime);
					}
					console.log(JSON.stringify(runtime));
					plotLine($('#runtime_paint canvas').get(0), labels, [runtime], $('#runtime_paint div').get(0));
				}else if(aspect == 'cpu_mem'){
					var cpuData = {
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
						cpuData.data.push(data[i].avg_cpu_percent);
						memData.data.push(data[i].avg_mem_percent);
					}
					plotLine($('#cpu_mem_paint canvas').get(0), labels, [cpuData, memData], $('#cpu_mem_paint div').get(0));
				}else if(aspect == 'rw_rate'){
					var readRate = {
							'label': 'Read Rate',
							'color': '170,57,57',
							'data': []
					},
						writeRate = {
							'label': 'Write Rate',
							'color': '151,187,205',
							'data': []	
					};
					for(i = 0; i < data.length; i ++){
						readRate.data.push(data[i].read_rate / 1024 / 1024);
						writeRate.data.push(data[i].write_rate / 1024 / 1024);
					}
					console.log(JSON.stringify([readRate, writeRate]));
					plotLine($('#rw_rate_paint canvas').get(0), labels, [readRate, writeRate], $('#rw_rate_paint div').get(0));
				}
			}
		});
	});
	
	$('.nav').each(function(){
		var firstTab = $(this).find('li').first();
		firstTab.addClass('active');
		firstTab.find('a').click();
	});
});