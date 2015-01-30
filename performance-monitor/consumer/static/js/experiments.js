/**
 * 
 */
var color1 = '151,187,205', color2 = '170,57,57', color3='255,211,0';
$(document).ready(function(){
	refresh_figures();
	var clip = new ZeroClipboard($('.copy'), {
		moviePath: '/static/ZeroClipboard.swf'
	});

	$('#worker-sites').multiselect({
		nonSelectedText: 'Worker Sites',
	});
	
	$(document).on('click', '.noshow', function(){
		$(this).parent().parent().hide();
		refresh_figures();
	});
	
	$('.del-experiment').click(function(){
		var exp_id = $(this).closest('tr').children('td.exp-id').text();
		$.ajax({
			url: window.location.pathname + '/experiments/' + exp_id,
			type: 'DELETE',
			data: JSON.stringify({'action': 'remove'}),
			contentType: 'application/json',
			success: function(data){
				location.reload();
			}
		});
	});
	
	$('.sort').click(function(){
		var params = window.location.search.substring(1).split('&'),
			val = $(this).text().toLowerCase().split(' ').join('_'),
			pairs = {};
		for(var p in params){
			if(params[p].length == 0) continue;
			var fs = params[p].split('=');
			pairs[fs[0]] = fs[1];
		}
		pairs['sort'] = val;
		var query = [];
		for(var p in pairs){
			query.push(p + '=' + pairs[p]);
		}
		$(location).attr('href', window.location.pathname + '?' + query.join('&'));
		
	});
	
	$('.clear').click(function(){
		var dropdown = $(this).parent().parent();
		dropdown.find('button').text($(this).data('title'));
		dropdown.val('');
	});
	
	$('.entry').click(function(){
		var dropdown = $(this).parent().parent();
		dropdown.find('button').text($(this).text());
		dropdown.val($(this).text().toLowerCase());
	});
	
	$('.copy').click(function(){
		clip = new ZeroClipboard($('.copy'), {
			moviePath: '/static/ZeroClipboard.swf'
		});
	});
	
	$(document).on('click', '#search', function(){
		query = get_query();
		console.log(JSON.stringify(query));
		if(query.length)
			$(location).attr('href', window.location.pathname + '?' + query);
	});
	
});

function get_query(){
	var data = [];
	$('#analysis div .dropdown, #analysis .form-group input').each(function(){
		var k = $(this).get(0).id.replace('-', '_'), v = $(this).val();
		if(v != null && k.length && v.length){
			data.push(k + '=' + v);
		}
	});
	$('select option:selected').each(function(index, brand){
		data.push('worker_site=' + $(this).val());
	});
	
	return data.join('&');
}

function refresh_figures(){
	var exp = [];
	$('tbody tr:visible').each(function(){
		exp.push($(this).find('td.exp-id').text());
	});
	get_walltime(exp);
	get_sys_usage(exp, 'sys_cpu');
	get_sys_usage(exp, 'sys_mem');
	get_sys_usage(exp, 'sys_read');
	get_sys_usage(exp, 'sys_write');
	get_sys_usage(exp, 'sys_send');
	get_sys_usage(exp, 'sys_recv');
}

function get_walltime(exp){
	if(!exp.length) return;
	$.ajax({
		uri: window.location.pathname,
		type: 'POST',
		data: JSON.stringify({
			'aspect': 'walltime',
			'experiments': exp,
			'type': 'chart'
		}),
		contentType: 'application/json',
		success: function(data){
			if(data.length == 0) return;
			//draw figure
			$('#walltime').empty();
			$('#walltime').append('<canvas></canvas><div></div><div class="std-dev">Standard Deviation: <span></span></div>');
			$('#walltime .std-dev span').text(data.std_dev);
			plotLine($('#walltime canvas').get(0), 
					data.timestamp,
					[{'label': 'Walltime', 'data': data.values, 'color': color1},],
					$('#walltime div').get(0));
		}
	});
}

function get_sys_usage(exp, aspect){
	if(!exp.length) return;
	$.ajax({
		uri: window.location.pathname,
		type: 'POST',
		data: JSON.stringify({
			'aspect': aspect,
			'experiments': exp,
			'type': 'chart'
		}),
		contentType: 'application/json',
		success: function(data){
				if(data.length == 0) return
				if(aspect == 'sys_cpu')
					get_sys_figure(data, $('#sys-cpu'));
				if(aspect == 'sys_mem')
					get_sys_figure(data, $('#sys-mem'));
				if(aspect == 'sys_read')
					get_sys_figure(data, $('#sys-read'));
				if(aspect == 'sys_write')
					get_sys_figure(data, $('#sys-write'));
				if(aspect == 'sys_send')
					get_sys_figure(data, $('#sys-send'));
				if(aspect == 'sys_recv')
					get_sys_figure(data, $('#sys-recv'));
			}
	});
}



function get_sys_figure(data, area){
	area.empty();
	area.append('<canvas></canvas>'
			+ '<div></div>'
			+ '<div class="std-dev">'
			+ '<div>Max Standard Deviation: <span class="max"></span></div>'
			+ '<div>Min Standard Deviation: <span class="min"></span></div>'
			+ '<div>Avg Standard Deviation: <span class="avg"></span></div>'
			+ '</div>');
	area.find('.std-dev div .max').text(data.max_std_dev);
	area.find('.std-dev div .min').text(data.min_std_dev);
	area.find('.std-dev div .avg').text(data.avg_std_dev);
	plotLine(area.find('canvas').get(0),
			data.timestamp,
			[
			 {'label': 'Avg.', 'data':data.max, 'color': color1},
			 {'label': 'Max.', 'data':data.min, 'color': color2},
			 {'label': 'Min.', 'data':data.avg, 'color': color3},
			 ],
			 area.find('div').get(0));
}
