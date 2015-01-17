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
					sumLabels.push(data[i].executable);
					runtime.push(data[i].runtime);
					avgCpuPct.push(data[i].avg_cpu_percent);
					avgMemPct.push(data[i].avg_mem_percent);
					readRates.push(data[i].read_rate / 1024 / 1024);
					writeRates.push(data[i].write_rate / 1024 / 1024);
					totalReadCount.push(data[i].total_read_count / 1000);
					totalWriteCount.push(data[i].total_write_count / 1000);
					totalReadBytes.push(data[i].total_read_bytes / 1024 / 1024)	;
					totalWriteBytes.push(data[i].total_write_bytes / 1024 / 1024);
				}
				else{
					if(data[i].status == 'started'){
						runtimeLabels.push(data[i].executable);
					}else{
						runtimeLabels.push('');
					}
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
				   sumRwRatesChart = new Chart($('#sum_rw_rates').get(0).getContext('2d')),
				   sumRuntimeChart = new Chart($('#sum_runtime').get(0).getContext('2d'));
			
			var dataTemplate = {
					labels: null,
					datasets: null, 
			};
			
			var lineTemp1 = {
		            label: null,
		            fillColor: 'rgba(170,57,57,0.2)',
		            strokeColor: 'rgba(170,57,57,1)',
		            pointColor: 'rgba(170,57,57,1)',
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: 'rgba(170,57,57,1)',
		            data: null
			}, 
			lineTemp2 = {
		            label: null,
		            fillColor: 'rgba(151,187,205,0.2)',
		            strokeColor: 'rgba(151,187,205,1)',
		            pointColor: 'rgba(151,187,205,1)',
		            pointStrokeColor: '#fff',
		            pointHighlightFill: '#fff',
		            pointHighlightStroke: 'rgba(151,187,205,1)',
		            data: null
			},
			barTemp1 = {
		            label: null,
		            fillColor: 'rgba(170,57,57,0.5)',
		            strokeColor: 'rgba(170,57,57,0.8)',
		            highlightFill: 'rgba(170,57,57,0.75)',
		            highlightStroke: 'rgba(170,57,57,1)',
		            data: null
			},
			barTemp2 = {
		            label: null,
		            fillColor: 'rgba(151,187,205,0.5)',
		            strokeColor: 'rgba(151,187,205,0.8)',
		            highlightFill: 'rgba(151,187,205,0.75)',
		            highlightStroke: 'rgba(151,187,205,1)',
		            data: null	
			};
			
			var lineOpts = {
				bezierCurve: false,
			},
				barOpts = {
				barShowStroke: true,
			};
			
			// CPU and memory runtime usage data
			var cpuMemData = $.extend({}, dataTemplate);
			cpuMemData.labels = runtimeLabels;
			cpuMemData.datasets = [];
			var cpuDs = $.extend({}, lineTemp1);
			cpuDs.label = 'CPU Usage';
			cpuDs.data = cpuPct;
			cpuMemData.datasets.push(cpuDs);
			var memDs= $.extend({}, lineTemp2);
			memDs.label = 'Memory Usage';
			memDs.data = memPct;
			cpuMemData.datasets.push(memDs);
			
			// read/write count at runtime
			var rwCountData = $.extend({}, dataTemplate);
			rwCountData.labels = runtimeLabels;
			rwCountData.datasets = [];
			var readCountDs = $.extend({}, lineTemp1);
			readCountDs.label = 'Read Count';
			readCountDs.data = readCount
			rwCountData.datasets.push(readCountDs);
			var writeCountDs = $.extend({}, lineTemp2);
			writeCountDs.label = 'Write Count';
			writeCountDs.data = writeCount;
			rwCountData.datasets.push(writeCountDs);
			
			// read/write bytes at runtime
			var rwBytesData = $.extend({}, dataTemplate);
			rwBytesData.labels = runtimeLabels;
			rwBytesData.datasets = [];
			var readBytesDs = $.extend({}, lineTemp1);
			readBytesDs.label = 'Read Bytes';
			readBytesDs.data = readBytes;
			rwBytesData.datasets.push(readBytesDs);
			var writeBytesDs = $.extend({}, lineTemp2);
			writeBytesDs.label = 'Write Bytes';
			writeBytesDs.data = writeBytes;
			rwBytesData.datasets.push(writeBytesDs);
			
			// runtime summary
			var sumRuntimeData = $.extend({}, dataTemplate);
			sumRuntimeData.labels = sumLabels;
			sumRuntimeData.datasets = [];
			var runtimeDs = $.extend({}, barTemp1);
			runtimeDs.label = 'Runtime'
			runtimeDs.data = runtime;
			sumRuntimeData.datasets.push(runtimeDs);
			
			// average CPU and memory usage
			var sumCpuMemData = $.extend({}, dataTemplate);
			sumCpuMemData.labels = sumLabels;
			sumCpuMemData.datasets = [];
			var avgCpuDs = $.extend({}, barTemp1);
			avgCpuDs.label = 'Avg. CPU Usage';
			avgCpuDs.data = avgCpuPct;
			sumCpuMemData.datasets.push(avgCpuDs);
			var avgMemDs = $.extend({}, barTemp2);
			avgMemDs.label = 'Avg. Memory Usage';
			avgMemDs.data = avgMemPct;
			sumCpuMemData.datasets.push(avgMemDs);
			
			// total read/write count summary
			var sumRwCountData = $.extend({}, dataTemplate);
			sumRwCountData.labels = sumLabels;
			sumRwCountData.datasets = [];
			var sumReadCountDs = $.extend({}, barTemp1);
			sumReadCountDs.label = 'Total Read Count'
			sumReadCountDs.data = totalReadCount;
			sumRwCountData.datasets.push(sumReadCountDs);
			var sumWriteCountDs = $.extend({}, barTemp2);
			sumWriteCountDs.label = 'Total Write Count';
			sumWriteCountDs.data = totalWriteBytes;
			sumRwCountData.datasets.push(sumWriteCountDs);
			
			// total read/write bytes summary
			var sumRwBytesData = $.extend({}, dataTemplate);
			sumRwBytesData.labels = sumLabels;
			sumRwBytesData.datasets = [];
			var sumReadBytesDs = $.extend({}, barTemp1);
			sumReadBytesDs.label = 'Total Read Bytes';
			sumReadBytesDs.data = totalReadBytes;
			sumRwBytesData.datasets.push(sumReadBytesDs);
			var sumWriteBytesDs = $.extend({}, barTemp2);
			sumWriteBytesDs.label = 'Total Write Bytes';
			sumWriteBytesDs.data = totalWriteBytes;
			sumRwBytesData.datasets.push(sumWriteBytesDs);
			
			// read/write bytes
			var sumRwRatesData = $.extend({}, dataTemplate);
			sumRwRatesData.labels = sumLabels;
			sumRwRatesData.datasets = [];
			var sumReadRatesDs = $.extend({}, barTemp1);
			sumReadRatesDs.label = 'Read Rate';
			sumReadRatesDs.data = readRates;
			sumRwRatesData.datasets.push(sumReadRatesDs);
			var sumWriteRatesDs = $.extend({}, barTemp2);
			sumWriteRatesDs.label = 'Write Rate';
			sumWriteRatesDs.data = writeRates;
			sumRwRatesData.datasets.push(sumWriteRatesDs);
			
			var cpuMemLine = cpuMemChart.Line(cpuMemData, lineOpts);
			var ioCountLine = ioCountChart.Line(rwCountData, lineOpts);
			var ioBytesLine = ioBytesChart.Line(rwBytesData, lineOpts);
			var sumCpuMemLine = sumCpuMemChart.Bar(sumCpuMemData, barOpts);
			var sumRwCountLine = sumRwCountChart.Bar(sumRwCountData, barOpts);
			var sumRwBytesLine = sumRwBytesChart.Bar(sumRwBytesData, barOpts);
			var sumRuntimeLine = sumRuntimeChart.Bar(sumRuntimeData, barOpts);
			var sumRwRatesLine = sumRwRatesChart.Bar(sumRwRatesData, barOpts);
			
			legend(document.getElementById('cpu_mem_pct_legend'), cpuMemData);
			legend(document.getElementById('io_count_legend'), rwCountData);
			legend(document.getElementById('io_bytes_legend'), rwBytesData);
			legend(document.getElementById('sum_cpu_mem_pct_legend'), sumCpuMemData);
			legend(document.getElementById('sum_rw_count_legend'), sumRwCountData);
			legend(document.getElementById('sum_rw_bytes_legend'), sumRwBytesData);
			legend(document.getElementById('runtime_legend'), sumRuntimeData);
			legend(document.getElementById('sum_rw_rates_legend'), sumRwRatesData);
		}
	});
});
