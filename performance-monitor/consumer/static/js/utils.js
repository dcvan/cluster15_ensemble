/**
 * 
 */

function form_query(arg){
	if(arg == null || arg.length == 0) return null;
	if(window.location.search.substring(1).length == 0)
		return '?' + arg;
	var params = window.location.search.substring(1).split('&');
	params.push(arg);
	return '?' + params.join('&');
}

function plotLine(container, labels, ds){
	var canvas = container.find('canvas').get(0),
		legend_area = container.find('div').get(0),
		analysis = container.find('.analysis'),
		opers = container.find('.opers');
	resize(canvas);
	
	var lineData = {
			labels: labels,
			datasets: []
	}, 
	opts = {
			bezierCurve: false,
			onAnimationComplete: function(){
				opers.append($('<button class="btn btn-default chartjs">Chart.js</button>'));
				opers.append($('<button class="btn btn-default matplotlib">Matplotlib</button>'))
			}
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
		           data: ds[i].data,
		});
	}
	var context = canvas.getContext('2d');
	var chart = new Chart(context).Line(lineData, opts);
	legend(legend_area, lineData);
	return chart;
}

function plotBar(canvas, labels, ds, legend_area){
	resize(canvas);
	var barData = {
			labels: labels,
			datasets: []
	},
	opts = {
			bezierCurve: false,
	};
	
	for(i = 0; i < ds.length; i ++){
		barData.datasets.push({
			label: ds[i].label,
            fillColor: 'rgba(' + ds[i].color + ',0.5)',
            strokeColor: 'rgba('+ ds[i].color + ',0.8)',
            highlightFill: 'rgba(' + ds[i].color + ',0.75)',
            highlightStroke: 'rgba(' + ds[i].color + ',1)',
			data: ds[i].data
		});
	}
	var chart = new Chart(canvas.getContext('2d')).Bar(barData, opts);
	legend(legend_area, barData);
	return chart;
}

function resize(canvas){
	canvas.width = 1050;
	canvas.height = 500;
}


function get_url(path){
	return "http://" + document.location.host + path; 
}

function format_date(d){
	return moment(d, 'X').format('YYYY-MM-DD HH:mm:ss');
}

function render_image(container, height, width){
	var canvas = container.find('canvas').get(0),
		legend_area = container.find('div').get(0),
		analysis = container.find('.analysis'),
		paint = document.createElement('canvas');
	paint.width = canvas.width + 5;
	paint.height = canvas.height + 300;
	var ctx = paint.getContext('2d');
	ctx.drawImage(canvas, 5, 5);
	html2canvas(legend_area, {
		onrendered: function(l){
			ctx.drawImage(l, 5, canvas.height);
			html2canvas(analysis, {
				onrendered: function(a){
					ctx.drawImage(a, 10 + l.width, canvas.height);
					var pdf = new jsPDF('l', 'mm', [280, 155]);
					pdf.addImage(paint.toDataURL('image/png'), 'PNG', 0, 0);
					pdf.save('download.pdf');
				}
			});
			
		}
	});
}

