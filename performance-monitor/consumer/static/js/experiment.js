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
			
			var cr = 151, cg = 187, cb = 205;
			
			var walltimeData = {
					labels: labels,
					datasets: [
					   {
						   label: 'Walltime',
						   fillColor: 'rgba('+ cr + ',' + cg + ',' + cb +',0.2)',
				            strokeColor: 'rgba('+ cr + ',' + cg + ',' + cb + ',1)',
				            pointColor: 'rgba(' + cr + ',' + cg + ',' + cb + ',1)',
				            pointStrokeColor: '#fff',
				            pointHighlightFill: '#fff',
				            pointHighlightStroke: 'rgba(' + cr + ',' + cg + ',' + cb + ',1)',
							data: data.walltime
					   }
					]
				};
			/*
			for(s in cpuUsage){
				var cnt = +s;
				color = '' + (cr + cnt * 40)%255 + ',' + Math.abs(cg - cnt * 30)%255 + ',' + (cg + cnt * 75)%255
				cpuData.datasets.push({
					label: s,
		            fillColor: 'rgba('+ color +',0.2)',
		            strokeColor: 'rgba('+ color + ',1)',
		            pointColor: 'rgba(' + color + ',1)',
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: 'rgba('+ color +',1)',
					data: cpuUsage[s]
				});
				memData.datasets.push({
					label: s,
		            fillColor: 'rgba('+ color +',0.2)',
		            strokeColor: 'rgba('+ color + ',1)',
		            pointColor: 'rgba(' + color + ',1)',
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: 'rgba('+ color +',1)',
					data: memUsage[s]
				});
				readCountData.datasets.push({
					label: s,
		            fillColor: 'rgba('+ color +',0.2)',
		            strokeColor: 'rgba('+ color + ',1)',
		            pointColor: 'rgba(' + color + ',1)',
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: 'rgba('+ color +',1)',
					data: readCount[s]
				});
				writeCountData.datasets.push({
					label: s,
		            fillColor: 'rgba('+ color +',0.2)',
		            strokeColor: 'rgba('+ color + ',1)',
		            pointColor: 'rgba(' + color + ',1)',
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: 'rgba('+ color +',1)',
					data: writeCount[s]
				});
				readBytesData.datasets.push({
					label: s,
		            fillColor: 'rgba('+ color +',0.2)',
		            strokeColor: 'rgba('+ color + ',1)',
		            pointColor: 'rgba(' + color + ',1)',
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: 'rgba('+ color +',1)',
					data: readBytes[s]
				});
				writeBytesData.datasets.push({
					label: s,
		            fillColor: 'rgba('+ color +',0.2)',
		            strokeColor: 'rgba('+ color + ',1)',
		            pointColor: 'rgba(' + color + ',1)',
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: 'rgba('+ color +',1)',
					data: writeBytes[s]
				});
				readRateData.datasets.push({
					label: s,
		            fillColor: 'rgba('+ color +',0.2)',
		            strokeColor: 'rgba('+ color + ',1)',
		            pointColor: 'rgba(' + color + ',1)',
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: 'rgba('+ color +',1)',
					data: readRate[s]
				});
				writeRateData.datasets.push({
					label: s,
		            fillColor: 'rgba('+ color +',0.2)',
		            strokeColor: 'rgba('+ color + ',1)',
		            pointColor: 'rgba(' + color + ',1)',
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: 'rgba('+ color +',1)',
					data: writeRate[s]
				});
				runtimeData.datasets.push({
					label: s,
		            fillColor: 'rgba('+ color +',0.2)',
		            strokeColor: 'rgba('+ color + ',1)',
		            pointColor: 'rgba(' + color + ',1)',
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: 'rgba('+ color +',1)',
					data: runtime[s]
				});
			}
			*/
			walltimeChart.Line(walltimeData, {bezierCurve: false});
			legend(document.getElementById('walltime_legend'), walltimeData);
		}
	});
});