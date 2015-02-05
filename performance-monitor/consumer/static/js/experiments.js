/**
 * 
 */
var color1 = '151,187,205', color2 = '170,57,57', color3='255,211,0';
$(document).ready(function(){
	var clip = new ZeroClipboard($('.copy'), {
		moviePath: '/static/ZeroClipboard.swf'
	});
	
	$('.nav li a').click(function(){
		activate_tab($(this));
	})
	
	$(document).on('click', '#experiments .nav li a', function(){
		var status = $(this).attr('id');
		if(status == 'finished'){
			$('#sys-analysis').show();
		}else{
			$('#sys-analysis').hide();
		}
		$.ajaxSetup({
			url: window.location.pathname + form_query('status=' + status)
		});
		$.ajax({
			type: 'GET',
			contentType: 'application/json',
			success: function(data){
				if(data.length == 0 || !'result' in data) return;
				var tbody = $('#experiments #table-content tbody'),
					experiments = data['result'];
				tbody.empty();
				for(var i in experiments){
					var row = $('<tr>'), e = experiments[i];
					row.append($('<td class="create-time" data-id="'+ e.exp_id +'"><a href="' + window.location.pathname + '/experiments/' + e.exp_id +'">'+ e.create_time+'</a></td>'));
					row.append($('<td class="topology">' + e.topology + '</td>'));
					row.append($('<td class="deployment">' + e.deployment + '</td>'));
					row.append($('<td class="master-site">' + e.master_site.toUpperCase() + '</td>'));
					var worker_sites = [];
					for(var s in e.worker_sites){
						worker_sites.push(e.worker_sites[s].site.toUpperCase());
					}
					row.append($('<td class="worker-sites">' + worker_sites.join(',') + '</td>'));
					row.append($('<td class="worker-num">' + e.num_of_workers + '</td>'));
					row.append($('<td class="worker-size">' + e.worker_size + '</td>'));
					row.append($('<td class="workload">' + e.workload + '</td>'));
					row.append($('<td class="bandwidth">' + (('bandwidth' in e)?e.bandwidth/(1000 * 1000): '-') + '</td>'));
					var ops = $('<td class="ops">');
					ops.append($('<button></button>', {
						'class': 'btn btn-warning glyphicon glyphicon-repeat redo'
					}));
					ops.append($('<button></button>', {
						'class': 'btn btn-danger glyphicon glyphicon-remove del-experiment'
					}));
					ops.append($('<button></button>', {
						'class': 'btn btn-default glyphicon glyphicon-minus noshow'
					}));
					row.append(ops);
					tbody.append(row);
				}
				$('#sys-analysis .nav li #walltime').trigger('click');
			}
		});
	});
	
	$(document).on('click', '#sys-analysis .nav li a', function(){
		var aspect = $(this).attr('id').replace('-', '_');
		get_sys_chart(aspect, $('#sys-analysis #chart'));
	});

	$('#experiments .nav li #finished').trigger('click');

	$('#worker-sites').multiselect({
		nonSelectedText: 'Worker Sites',
	});
	
	$(document).on('click', '.noshow', function(){
		$(this).parent().parent().hide();
		aspect = $('#sys-analysis .nav .active').find('a').attr('id').replace('-', '_');
		get_sys_chart(aspect, $('#sys-analysis #chart'));
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
	
	$(document).on('click', '.download-image', function(){
		render_image($('#sys-analysis #chart'), 900, 300);
	});
	
	$('.sort').click(function(){
		var params = window.location.search.substring(1).split('&'),
			val = $(this).data('key');
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

function activate_tab(e){
	var tab = e.parent();
	tab.addClass('active');
	tab.siblings().each(function(){
		$(this).removeClass('active');
	});
}

function get_query(){
	var data = [];
	$('#filter div .dropdown, #filter .form-group input').each(function(){
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

function get_sys_chart(aspect, area){
	var exp = [];
	$('#experiments #table-content table tbody tr:visible').each(function(){
		var id = $(this).find('td.create-time').data('id');
		exp.push(id);
	});
	if(aspect == "walltime"){
		get_walltime(exp, area);
	}else if($.inArray(aspect, ['sys_cpu', 'sys_mem', 'sys_read', 'sys_write', 'sys_send', 'sys_recv']) > -1){
		get_sys_usage(exp, aspect, area);
	}else{
		console.log('Unknown aspect: ' + aspect);
	}
}

function get_walltime(exp, area){
	if(!exp.length) return;
	$.ajaxSetup({
		url: window.location.pathname + '/analysis'
	});
	$.ajax({
		type: 'POST',
		data: JSON.stringify({
			exp_ids: exp,
			aspect: 'walltime',
			use: 'chart'
		}),
		contentType: 'application/json',
		success: function(data){
			if(data == null || data.length == 0) return;
			area.empty();
			area.append('<canvas></canvas>'
						+ '<div></div>'
						+ '<div class="analysis">'
						+ '<div>Max: <span class="max"></span></div>'
						+ '<div>Min: <span class="min"></span></div>'
						+ '<div>Avg: <span class="avg"></span></div>'
						+ '<div>Standard Deviation: <span class="avg-std-dev"></span></div>'
						+ '</div>');
			area.find(' .analysis div .max').text(data.overall_max + 'mins');
			area.find(' .analysis div .min').text(data.overall_min + 'mins');
			area.find(' .analysis div .avg').text(data.overall_avg + 'mins');
			area.find(' .analysis div .avg-std-dev').text(data.std_dev + 'mins');
			plotLine(area, 
					data.timestamp,
					[{'label': 'Walltime', 'data': data.values, 'color': color1},]);
		}
	});
}

function get_sys_usage(exp, aspect, area){
	if(!exp.length) return;
	$.ajaxSetup({
		url: window.location.pathname + '/analysis'
	});
	$.ajax({
		type: 'POST	',
		data: JSON.stringify({
			exp_ids: exp,
			aspect: aspect,
			use: 'chart'
		}),
		contentType: 'application/json',
		success: function(data){
				if(data == null || data.length == 0) return;
				if(aspect == 'sys_cpu')
					get_sys_figure(data, area, '%');
				if(aspect == 'sys_mem')
					get_sys_figure(data, area, '%');
				if(aspect == 'sys_read')
					get_sys_figure(data, area, ' MB/s');
				if(aspect == 'sys_write')
					get_sys_figure(data, area, ' MB/s');
				if(aspect == 'sys_send')
					get_sys_figure(data, area, ' MB/s');
				if(aspect == 'sys_recv')
					get_sys_figure(data, area, ' MB/s');
			}
	});
}

function get_sys_figure(data, area, unit){
	area.empty();
	area.append('<canvas></canvas>'
			+ '<div></div>'
			+ '<div class="analysis">'
			+ '<div>Max: <span class="max"></span></div>'
			+ '<div>Min: <span class="min"></span></div>'
			+ '<div>Avg: <span class="avg"></span></div>'
			+ '<div>Max Standard Deviation: <span class="max-std-dev"></span></div>'
			+ '<div>Min Standard Deviation: <span class="min-std-dev"></span></div>'
			+ '<div>Avg Standard Deviation: <span class="avg-std-dev"></span></div>'
			+ '</div>');
	area.find('.analysis div .max').text(data.overall_max + unit);
	area.find('.analysis div .min').text(data.overall_min + unit);
	area.find('.analysis div .avg').text(data.overall_avg + unit);
	area.find('.analysis div .max-std-dev').text(data.max_std_dev + unit);
	area.find('.analysis div .min-std-dev').text(data.min_std_dev + unit);
	area.find('.analysis div .avg-std-dev').text(data.avg_std_dev + unit);
	plotLine(area,
			data.timestamp,
			[
			 {'label': 'Max.', 'data':data.max, 'color': color1},
			 {'label': 'Min.', 'data':data.min, 'color': color3},
			 {'label': 'Avg.', 'data':data.avg, 'color': color2},
			 ]);
}
