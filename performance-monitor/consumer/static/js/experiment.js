/**
 * 
 */
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
			for(i = 0; i < data.experiments.length; i ++){
				var m = new Date(data.experiments[i]);
				labels.push(m.getUTCFullYear() 
						+"/"+ (m.getUTCMonth()+1) 
						+"/"+ m.getUTCDate() 
						+ " " + m.getUTCHours() 
						+ ":" + m.getUTCMinutes() 
						+ ":" + m.getUTCSeconds());
			}
			
			for(i = 0; i < data.updates.length; i ++){
				var step = data.updates[i].step;
				if(!(step in cpuUsage))
					cpuUsage[step] = [];
				cpuUsage[step].push(data.updates[i].avg_cpu_percent);
				if(!(step in memUsage))
					memUsage[step] = [];
				memUsage[step].push(data.updates[i].avg_mem_percent);
				if(!(step in readCount))
					readCount[step] = [];
				readCount[step].push(data.updates[i].total_read_count);
				if(!(step in writeCount))
					writeCount[step] = [];
				writeCount[step].push(data.updates[i].total_write_count);
				if(!(step in readBytes))
					readBytes[step] = [];
				readBytes[step].push(data.updates[i].total_read_bytes);
				if(!(step in writeBytes))
					writeBytes[step] = [];
				writeBytes[step].push(data.updates[i].total_write_bytes);
				if(!(step in runtime))
					runtime[step] = [];
				runtime[step].push(data.updates[i].runtime);
			}
			var cr = 151, cg = 187, cb = 205;
			var cpuData = {labels: labels, datasets: []},
				memData = {labels: labels, datasets: []},
				readCountData = {labels: labels, datasets: []},
				writeCountData = {labels: labels, datasets: []},
				readBytesData = {labels: labels, datasets: []},
				writeBytesData = {labels: labels, datasets: []},
				runtimeData = {labels: labels, datasets: []};
			for(s in cpuUsage){
				var cnt = +s;
				color = '' + (cr + cnt * 10) + ',' + (cg - cnt * 10) + ',' + (cg - cnt * 15)
				cpuData.datasets.push({
					label: s,
		            fillColor: 'rgba('+ color +',0.2)',
		            strokeColor: 'rgba('+ color + ',1)',
		            pointColor: 'rgba(' + color ',1)',
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: 'rgba('+ color +',1)',
					data: cpuUsage[s]
				});
				memData.datasets.push({
					label: s,
		            fillColor: 'rgba('+ color +',0.2)',
		            strokeColor: 'rgba('+ color + ',1)',
		            pointColor: 'rgba(' + color ',1)',
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: 'rgba('+ color +',1)',
					data: memUsage[s]
				});
				readCountData.datasets.push({
					label: s,
		            fillColor: 'rgba('+ color +',0.2)',
		            strokeColor: 'rgba('+ color + ',1)',
		            pointColor: 'rgba(' + color ',1)',
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: 'rgba('+ color +',1)',
					data: readCount[s]
				});
				writeCountData.datasets.push({
					label: s,
		            fillColor: 'rgba('+ color +',0.2)',
		            strokeColor: 'rgba('+ color + ',1)',
		            pointColor: 'rgba(' + color ',1)',
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: 'rgba('+ color +',1)',
					data: writeCount[s]
				});
				readBytesData.datasets.push({
					label: s,
		            fillColor: 'rgba('+ color +',0.2)',
		            strokeColor: 'rgba('+ color + ',1)',
		            pointColor: 'rgba(' + color ',1)',
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: 'rgba('+ color +',1)',
					data: readBytes[s]
				});
				writeBytesData.datasets.push({
					label: s,
		            fillColor: 'rgba('+ color +',0.2)',
		            strokeColor: 'rgba('+ color + ',1)',
		            pointColor: 'rgba(' + color ',1)',
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: 'rgba('+ color +',1)',
					data: writeBytes[s]
				});
				runtimeData.datasets.push({
					label: s,
		            fillColor: 'rgba('+ color +',0.2)',
		            strokeColor: 'rgba('+ color + ',1)',
		            pointColor: 'rgba(' + color ',1)',
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: 'rgba('+ color +',1)',
					data: runtime[s]
				});
				
			}
			console.log(JSON.stringify(cpuData));
			cpuChart.Line(cpuData, {bezierCurve: false});
			memChart.Line(memData, {bezierCurve: false});
			readCountChart.Line(readCountData, {bezierCurve: false});
			writeCountChart.Line(writeCountData, {bezierCurve: false});
			readBytesChart.Line(readBytesData, {bezierCurve: false});
			writeBytesChart.Line(writeBytesData, {bezierCurve: false});
			runtimeChart.Line(runtimeData, {bezierCurve: false});
		}
	});
});