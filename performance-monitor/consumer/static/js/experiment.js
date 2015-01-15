/**
 * 
 */
var Chartjs = Chart.noConflict()
$(document).ready(function(){
	$.ajax({
		url: window.location.pathname,
		type: 'POST',
		contentType: 'application/json',
		success: function(data){
			var labels = [], cpuUsage = {}, memUsage = {}, 
				   readCount = {}, writeCount = {},
				   readBytes = {}, writeBytes = {},
				   runtime = {};
			var cpuChart = new Chart($('#cpu_usage').get(0).getContext('2d')),
				   memChart = new Chart($('#mem_usage').get(0).getContext('2d')),
				   readCountChart = new Chart($('#read_count').get(0).getContext('2d')),
				   writeCountChart = new Chart($('#write_count').get(0).getContext('2d')),
				   readBytesChart = new Chart($('#read_bytes').get(0).getContext('2d')),
				   writeBytesChart = new Chart($('#write_count').get(0).getContext('2d')),
				   runtimeChart = new Chart($('#runtime').get(0).getContext('2d'));
			for(i = 0; i < data.length; i ++){
				labels.push(new Date(data[i].expid).toString());
				var step = data[i].step;
				if(!(step in cpuUsage))
					cpuUsage[step] = [];
				cpuUsage[step].push(data[i].avg_cpu_percent);
				if(!(step in memUsage))
					memUsage[step] = [];
				memUsage[step].push(data[i].avg_mem_percent);
				if(!(step in readCount))
					readCount[step] = [];
				readCount[step].push(data[i].total_read_count);
				if(!(step in writeCount))
					writeCount[step] = [];
				writeCount[step].push(data[i].total_write_count);
				if(!(step in readBytes))
					readBytes[step] = [];
				readBytes[step].push(data[i].total_read_bytes);
				if(!(step in writeBytes))
					writeBytes[step] = [];
				writeBytes[step].push(data[i].total_write_bytes);
				if(!(step in runtime))
					runtime[step] = [];
				runtime[step].push(data[i].runtime);
			}
			var cpuData = {
					labels : labels,
					datasets : []
			}
			for(s in cpuUsage){
				cpuData.datasets.push({
					label: s,
					data: cpuUsage[s]
				});
			}
			cpuChart.Line(cpuData, {bezierCurve: false});
		}
	});
});