/**
 * 
 */
$(document).ready(function(){
	var color1 = '151,187,205', color2 = '170,57,57', color3='51,255,102'
	$.ajax({
		url: window.location.path,
		type: 'POST',
		contentType: 'application/json',
		data: JSON.stringify({'aspect': 'system'}),
		success: function(data){
			console.log(JSON.stringify(data));
			plotLine($('#sys-cpu canvas').get(0), 
					data['label'],
					[{'label': 'Avg.', 'data': data['sys_cpu_percent'], 'color': color1},
					 {'label': 'Max.', 'data': data['sys_max_cpu_percent'], 'color': color2},
					 {'label': 'Min.', 'data': data['sys_min_cpu_percent'], 'color': color3},
					],
					$('#sys-cpu div').get(0));
			plotLine($('#sys-mem canvas').get(0), 
					data['label'],
					[{'label': 'Avg.', 'data': data['sys_mem_percent'], 'color': color1},
					 {'label': 'Max.', 'data': data['sys_max_mem_percent'], 'color': color2},
					 {'label': 'Min.', 'data': data['sys_min_mem_percent'], 'color': color3},
					],
					$('#sys-mem div').get(0));
			plotLine($('#sys-rw canvas').get(0), 
					data['label'],
					[{'label': 'Read Rate', 'data': data['sys_read_rate'], 'color': color1},
					 {'label': 'Write Rate', 'data': data['sys_write_rate'], 'color': color2}
					],
					$('#sys-rw div').get(0));
			plotLine($('#sys-sr canvas').get(0), 
					data['label'],
					[{'label': 'Send Rate', 'data': data['sys_send_rate'], 'color': color1},
					 {'label': 'Recv Rate', 'data': data['sys_recv_rate'], 'color': color2}
					],
					$('#sys-sr div').get(0));
		}
	});
	
	$.ajax({
		url: window.location.path,
		type: 'POST',
		contentType: 'application/json',
		data: JSON.stringify({'aspect': 'job'}),
		success: function(data){
			console.log(JSON.stringify(data));
			plotLine($('#cpu-line canvas').get(0), 
					data['label'],
					[{'label': 'Avg.', 'data': data['avg_cpu_percent'], 'color': color1},
					 {'label': 'Max.', 'data': data['max_cpu_percent'], 'color': color2},
					 {'label': 'Min.', 'data': data['min_cpu_percent'], 'color': color3}
					],
					$('#cpu-line div').get(0));
			plotLine($('#mem-line canvas').get(0), 
					data['label'],
					[{'label': 'Avg.', 'data': data['avg_mem_percent'], 'color': color1},
					 {'label': 'Max.', 'data': data['max_mem_percent'], 'color': color2},
					 {'label': 'Min.', 'data': data['min_mem_percent'], 'color': color3}
					],
					$('#mem-line div').get(0));
			plotBar($('#rw-line canvas').get(0), 
					data['label'],
					[{'label': 'Read Rate', 'data': data['read_rate'], 'color': color1},
					 {'label': 'Write Rate', 'data': data['write_rate'], 'color': color2}
					],
					$('#rw-line div').get(0));
			plotBar($('#runtime-bar canvas').get(0), 
					data['label'],
					[{'label': 'Runtime', 'data': data['runtime'], 'color': color1},
					],
					$('#runtime-bar div').get(0));
		}
	});
});