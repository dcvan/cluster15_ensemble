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
			var runtimeLabels = [], sumLabels = [], 
				  cpuPct = [], memPct = [], 
				  readCount = [], writeCount = [], 
				  readBytes = [], writeBytes = [], 
				  runtime = [], 
				  readRates = [], writeRates = [],
				  totalReadBytes = [], totalWriteBytes = [],
				  totalReadCount = [], totalWriteCount = [],
				  avgCpuPct = [], avgMemPct = [];
			for(i = 0; i < data.length; i ++){
				if(data[i].status == 'terminated'){
					runtimeLabels[runtimeLabels.length - 1] = data[i].executable;
					sumLabels.push(data[i].executable);
					runtime.push(data[i].runtime);
					avgCpuPct.push(data[i].avg_cpu_percent);
					avgMemPct.push(data[i].avg_mem_percent);
					//readRates.push(data[i].read_rate);
					//writeRates.push(data[i].write_rate);
					totalReadCount.push(data[i].total_read_count / 1000);
					totalWriteCount.push(data[i].total_write_count / 1000);
					totalReadBytes.push(data[i].total_read_bytes / 1024 / 1024)	;
					totalWriteBytes.push(data[i].total_write_bytes / 1024 / 1024);
				}
				else{
					runtimeLabels.push('');
					cpuPct.push(data[i].cpu_percent);
					memPct.push(data[i].memory_percent);
					readCount.push(data[i].total_read_count / 1000);
					writeCount.push(data[i].total_write_count / 1000);
					readBytes.push(data[i].total_read_bytes / 1024 / 1024);
					writeBytes.push(data[i].total_write_bytes / 1024 / 1024);
				}
			}
			var cpuMemChart = new Chart($('#cpu_mem_pct').get(0).getContext('2d')),
				   ioCountChart = new Chart($('#io_count').get(0).getContext('2d')),
				   ioBytesChart = new Chart($('#io_bytes').get(0).getContext('2d')),
				   sumCpuMemChart = new Chart($('#sum_cpu_mem_pct').get(0).getContext('2d')),
				   sumRwCountChart = new Chart($('#sum_rw_count').get(0).getContext('2d')),
				   sumRwBytesChart = new Chart($('#sum_rw_bytes').get(0).getContext('2d')),
				   sumRuntimeChart = new Chart($('#sum_runtime').get(0).getContext('2d'));
			
			var dataTemplate = {
					labels: null,
					datasets: null, 
			};
			
			var datasetTemplate1 = {
		            label: null,
		            fillColor: "rgba(170,57,57,0.2)",
		            strokeColor: "rgba(170,57,57,1)",
		            pointColor: "rgba(170,57,57,1)",
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: "rgba(170,57,57, 1)",
		            data: null
			};
			
			var datasetTemplate2 = {
		            label: null,
		            fillColor: 'rgba(151,187,205,0.2)',
		            strokeColor: 'rgba(151,187,205,1)',
		            pointColor: 'rgba(151,187,205,1)',
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: 'rgba(151,187,205,1)',
		            data: null
			};
			
			// CPU and memory runtime usage data
			var cpuMemData = $.extend({}, dataTemplate);
			cpuMemData.labels = runtimeLabels;
			cpuMemData.datasets = [];
			var cpuDs = $.extend({}, datasetTemplate1);
			cpuDs.label = 'CPU Usage at Runtime';
			cpuDs.data = cpuPct;
			cpuMemData.datasets.push(cpuDs);
			var memDs= $.extend({}, datasetTemplate2);
			memDs.label = 'Memory Usage at Runtime';
			memDs.data = memPct;
			cpuMemData.datasets.push(memDs);
			
			// read/write count at runtime
			var rwCountData = $.extend({}, dataTemplate);
			rwCountData.labels = runtimeLabels;
			rwCountData.datasets = [];
			var readCountDs = $.extend({}, datasetTemplate1);
			readCountDs.label = 'Read Count at Runtime';
			readCountDs.data = readCount
			rwCountData.datasets.push(readCountDs);
			var writeCountDs = $.extend({}, datasetTemplate2);
			writeCountDs.label = 'Write Count at Runtime';
			writeCountDs.data = writeCount;
			rwCountData.datasets.push(writeCountDs);
			
			// read/write bytes at runtime
			var rwBytesData = $.extend({}, dataTemplate);
			rwBytesData.labels = runtimeLabels;
			rwBytesData.datasets = [];
			var readBytesDs = $.extend({}, datasetTemplate1);
			readBytesDs.label = 'Read Bytes at Runtime';
			readBytesDs.data = readBytes;
			rwBytesData.datasets.push(readBytesDs);
			var writeBytesDs = $.extend({}, datasetTemplate2);
			writeBytesDs.label = 'Write Bytes at Runtime';
			writeBytesDs.data = writeBytes;
			rwBytesData.datasets.push(writeBytesDs);
			
			// runtime summary
			var sumRuntimeData = $.extend({}, dataTemplate);
			sumRuntimeData.labels = sumLabels;
			sumRuntimeData.datasets = [];
			var runtimeDs = $.extend({}, datasetTemplate1);
			runtimeDs.label = 'Runtime'
			runtimeDs.data = runtime;
			sumRuntimeData.datasets.push(runtimeDs);
			
			// average CPU and memory usage
			var sumCpuMemData = $.extend({}, dataTemplate);
			sumCpuMemData.labels = sumLabels;
			sumCpuMemData.datasets = [];
			var avgCpuDs = $.extend({}, datasetTemplate1);
			avgCpuDs.label = 'Avg. CPU Usage';
			avgCpuDs.data = avgCpuPct;
			sumCpuMemData.datasets.push(avgCpuDs);
			var avgMemDs = $.extend({}, datasetTemplate2);
			avgMemDs.label = 'Avg. Memory Usage';
			avgMemDs.data = avgMemPct;
			sumCpuMemData.datasets.push(avgMemDs);
			
			// total read/write count summary
			var sumRwCountData = $.extend({}, dataTemplate);
			sumRwCountData.labels = sumLabels;
			sumRwCountData.datasets = [];
			var sumReadCountDs = $.extend({}, datasetTemplate1);
			sumReadCountDs.label = 'Total Read Count'
			sumReadCountDs.data = totalReadCount;
			sumRwCountData.datasets.push(sumReadCountDs);
			var sumWriteCountDs = $.extend({}, datasetTemplate2);
			sumWriteCountDs.label = 'Total Write Count';
			sumWriteCountDs.data = totalWriteBytes;
			sumRwCountData.datasets.push(sumWriteCountDs);
			
			// total read/write bytes summary
			var sumRwBytesData = $.extend({}, dataTemplate);
			sumRwBytesData.labels = sumLabels;
			sumRwBytesData.datasets = [];
			var sumReadBytesDs = $.extend({}, datasetTemplate1);
			sumReadBytesDs.label = 'Total Read Bytes';
			sumReadBytesDs.data = totalReadBytes;
			sumRwBytesData.datasets.push(sumReadBytesDs);
			var sumWriteBytesDs = $.extend({}, datasetTemplate2);
			sumWriteBytesDs.label = 'Total Write Bytes';
			sumWriteBytesDs.data = totalWriteBytes;
			sumRwBytesData.datasets.push(sumWriteBytesDs);
			
			var cpuMemLine = cpuMemChart.Line(cpuMemData, {bezierCurve: false});
			var ioCountLine = ioCountChart.Line(rwCountData, {bezierCurve: false});
			var ioBytesLine = ioBytesChart.Line(rwBytesData, {bezierCurve: false});
			var sumCpuMemLine = sumCpuMemChart.Bar(sumCpuMemData, {barShowStroke: false});
			var sumRwCountLine = sumRwCountChart.Bar(sumRwCountData, {barShowStroke: false});
			var sumRwBytesLine = sumRwBytesChart.Bar(sumRwBytesData, {barShowStroke: false});
			var sumRuntimeLine = sumRuntimeChart.Bar(sumRuntimeData, {barShowStroke: false});
		}
	});
});