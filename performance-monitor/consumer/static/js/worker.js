/**
 *  
 */
$(document).ready(function(){
	$.ajax({
		url: window.location.pathname,
		type: 'POST',
		contentType: 'application/json',
		success: function(data){
			var rtLabels = [], sumLabels = [];
			var color1 = '170,57,57', color2 = '151,187,205';
			var cpu = get_dataset('CPU Usage', [], color1),
				  mem = get_dataset('Memory Usage', [], color2),
				  readCount = get_dataset('Read Count', [], color1),
				  writeCount = get_dataset('Write Count', [], color2),
				  readBytes = get_dataset('Read Bytes', [], color1),
				  writeBytes = get_dataset('Write Bytes', [], color2),
				  sumCpu = get_dataset('CPU Usage', [], color1),
				  sumMem = get_dataset('Memory Usage', [], color2),
				  sumReadCount = get_dataset('Read Count', [], color1),
				  sumWriteCount = get_dataset('Write Count', [], color2),
				  sumReadBytes = get_dataset('Read Bytes', [], color1),
				  sumWriteBytes = get_dataset('Write Bytes', [], color2),
				  sumReadRate = get_dataset('Read Rate', [], color1),
				  sumWriteRate = get_dataset('Write Rate', [], color2),
				  sumRuntime = get_dataset('Runtime', [], color1);
		
			for(i = 0; i < data.length; i ++){
				if(data[i].status == 'terminated'){
					sumLabels.push(data[i].executable);
					sumRuntime.data.push(data[i].runtime);
					sumCpu.data.push(data[i].avg_cpu_percent);
					sumMem.data.push(data[i].avg_mem_percent);
					sumReadRate.data.push(data[i].read_rate / 1024 / 1024);
					sumWriteRate.data.push(data[i].write_rate / 1024 / 1024);
					sumReadCount.data.push(data[i].total_read_count / 1000);
					sumWriteCount.data.push(data[i].total_write_count / 1000);
					sumReadBytes.data.push(data[i].total_read_bytes / 1024 / 1024)	;
					sumWriteBytes.data.push(data[i].total_write_bytes / 1024 / 1024);
				}
				else{
					if(data[i].status == 'started'){
						rtLabels.push(data[i].executable);
					}else{
						rtLabels.push('');
					}
					cpu.data.push(data[i].cpu_percent);
					mem.data.push(data[i].memory_percent);
					readCount.data.push(data[i].total_read_count / 1000);
					writeCount.data.push(data[i].total_write_count / 1000);
					readBytes.data.push(data[i].total_read_bytes / 1024 / 1024);
					writeBytes.data.push(data[i].total_write_bytes / 1024 / 1024);
				}
			}
			plotLine($('#cpu_mem_usage').get(0), rtLabels, [cpu, mem], $('#cpu_mem_usage_legend').get(0));
			plotLine($('#rw_count').get(0), rtLabels, [readCount, writeCount], $('#rw_count_legend').get(0));
			plotLine($('#rw_bytes').get(0), rtLabels, [readBytes, writeBytes], $('#rw_bytes_legend').get(0));
			plotBar($('#sum_cpu_mem').get(0), sumLabels, [sumCpu, sumMem], $('#sum_cpu_mem_legend').get(0));
			plotBar($('#sum_rw_count').get(0), sumLabels, [sumReadCount, sumWriteCount], $('#sum_rw_count_legend').get(0));
			plotBar($('#sum_rw_bytes').get(0), sumLabels, [sumReadBytes, sumWriteBytes], $('#sum_rw_bytes_legend').get(0));
			plotBar($('#sum_rw_rate').get(0), sumLabels, [sumReadRate, sumWriteRate], $('#sum_rw_rate_legend').get(0));
			plotBar($('#sum_runtime').get(0), sumLabels, [sumRuntime], $('#runtime_legend').get(0));
	});
});

function get_dataset(label, data, color){
	return {
		'label': label,
		'data': data,
		'color': color
	};
}
