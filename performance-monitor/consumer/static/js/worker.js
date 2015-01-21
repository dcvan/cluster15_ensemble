/**
 * 
 */
$(document).ready(function(){
	var color1 = '151,187,205', color2 = '170,57,57';
	$.ajax({
		url: window.location.path,
		type: 'POST',
		contentType: 'application/json',
		data: JSON.stringify({'aspect': 'system'}),
		success: function(data){
			plotLine($('#sys-cpu-mem canvas').get(0), 
					data['label'],
					[{'label': 'CPU Usage', 'data': data['sys_cpu_percent'], 'color': color1},
					 {'label': 'Memory Usage', 'data': data['sys_mem_percent'], 'color': color2}
					],
					$('#sys-cpu-mem div').get(0));
			plotLine($('#sys-rw canvas').get(0), 
					data['label'],
					[{'label': 'Bytes Read', 'data': data['sys_read_bytes'], 'color': color1},
					 {'label': 'Bytes Written', 'data': data['sys_write_bytes'], 'color': color2}
					],
					$('#sys-rw div').get(0));
			plotLine($('#sys-sr canvas').get(0), 
					data['label'],
					[{'label': 'Bytes Sent', 'data': data['sys_net_bytes_sent'], 'color': color1},
					 {'label': 'Bytes Received', 'data': data['sys_net_bytes_recv'], 'color': color2}
					],
					$('#sys-sr div').get(0));
		}
	});
	
	$.ajax({
		url: window.location.path,
		type: 'POST',
		contentType: 'application/json',
		data: JSON.stringify({'aspect': 'process'}),
		success: function(data){
			plotLine($('#cpu-mem-line canvas').get(0), 
					data['label_running'],
					[{'label': 'CPU Usage', 'data': data['cpu_percent'], 'color': color1},
					 {'label': 'Memory Usage', 'data': data['mem_percent'], 'color': color2}
					],
					$('#cpu-mem-line div').get(0));
			plotLine($('#rw-line canvas').get(0), 
					data['label_running'],
					[{'label': 'Bytes Read', 'data': data['total_read_bytes'], 'color': color1},
					 {'label': 'Bytes Written', 'data': data['total_write_bytes'], 'color': color2}
					],
					$('#rw-line div').get(0));
			plotBar($('#cpu-mem-bar canvas').get(0), 
					data['label_terminated'],
					[{'label': 'Avg. CPU Usage', 'data': data['avg_cpu_percent'], 'color': color1},
					 {'label': 'Avg. Memory Usage', 'data': data['avg_mem_percent'], 'color': color2}
					],
					$('#cpu-mem-bar div').get(0));
			plotBar($('#rw-bar canvas').get(0), 
					data['label_terminated'],
					[{'label': 'Read Rate', 'data': data['read_rate'], 'color': color1},
					 {'label': 'Write Rate', 'data': data['write_rate'], 'color': color2}
					],
					$('#rw-bar div').get(0));
			plotBar($('#runtime-bar canvas').get(0), 
					data['label_terminated'],
					[{'label': 'Runtime', 'data': data['runtime'], 'color': color1},
					],
					$('#runtime-bar div').get(0));
		}
	});
});