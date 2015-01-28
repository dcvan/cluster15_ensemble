/**
 * 
 */
$(document).ready(function(){
	get_walltime();
	get_figure('sys_cpu', $('#sys-cpu'));
	get_figure('sys_mem', $('#sys-mem'));
	var clip = new ZeroClipboard($('.copy'), {
		moviePath: '/static/ZeroClipboard.swf'
	});

	$('#worker-sites').multiselect({
		nonSelectedText: 'Worker Sites',
	});
	
	
	$('.del-experiment').click(function(){
		var expId = $(this).closest('tr').children('td.exp-id').text();
		$.ajax({
			url: window.location.pathname + '/experiments/' + expId,
			type: 'DELETE',
			data: JSON.stringify({'action': 'remove'}),
			contentType: 'application/json',
			success: function(data){
				location.reload();
			}
		});
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
			$(location).attr('href', document.URL + '?' + query);
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


function get_walltime(){
	var color1 = '151,187,205', color2 = '170,57,57', color3='102,255,51';
	$.ajaxSetup({url: (window.location.search.substring(0).length)?document.URL + '&aspect=run':document.URL + '?aspect=run'});
	$.ajax({
		type: 'GET',
		contentType: 'application/json',
		success: function(data){
			$('#walltime').empty();
			$('#walltime').append('<canvas></canvas><div></div><div id="std-dev"></div>');
			$('#walltime #std-dev').text('Standard Deviation: ' + data['std_dev']);
			plotLine($('#walltime canvas').get(0), 
					data['label'],
					[{'label': 'Walltime', 'data': data['walltime'], 'color': color1},],
					$('#walltime div').get(0));
		}
	});
}

function get_sys_cpu(){
	var color1 = '151,187,205', color2 = '170,57,57', color3='102,255,51';
	$.ajaxSetup({url: (window.location.search.substring(0).length)?document.URL + '&aspect=sys_cpu':document.URL + '?aspect=sys_cpu'});
	$.ajax({
		type: 'GET',
		contentType: 'application/json',
		success: function(data){
//			console.log(JSON.stringify(data));
			$('#sys-cpu').empty();
			$('#sys-cpu').append('<canvas></canvas><div></div><div id="std-dev"></div>');
			$('#sys-cpu #std-dev').append('<span>Max Standard Deviation: ' + data['max_std_dev'] + '</span>');
			$('#sys-cpu #std-dev').append('<span>Min Standard Deviation: ' + data['min_std_dev'] + '</span>');
			$('#sys-cpu #std-dev').append('<span>Avg Standard Deviation: ' + data['avg_std_dev'] + '</span>');
			
			plotLine($('#sys-cpu canvas').get(0),
					data['label'],
					[
					 {'label': 'Avg.', 'data':data['avg'], 'color': color1},
					 {'label': 'Max.', 'data':data['max'], 'color': color2},
					 {'label': 'Min.', 'data':data['min'], 'color': color3},
					 ],
					 $('#sys-cpu div').get(0));
		}
	});
}

function get_figure(aspect, area){
	var color1 = '151,187,205', color2 = '170,57,57', color3='102,255,51';
	$.ajaxSetup({url: document.URL + ((window.location.search.substring(0).length)?'&aspect=':'?aspect=') + aspect});
	$.ajax({
		type: 'GET',
		contentType: 'application/json',
		success: function(data){
			area.empty();
			area.append('<canvas></canvas><div></div><div id="std-dev"></div>');
			area.find('#std-dev').append('<span>Max Standard Deviation: ' + data['max_std_dev'] + '</span>');
			area.find('#std-dev').append('<span>Min Standard Deviation: ' + data['min_std_dev'] + '</span>');
			area.find('#std-dev').append('<span>Avg Standard Deviation: ' + data['avg_std_dev'] + '</span>');
			
			plotLine(area.find('canvas').get(0),
					data['label'],
					[
					 {'label': 'Avg.', 'data':data['avg'], 'color': color1},
					 {'label': 'Max.', 'data':data['max'], 'color': color2},
					 {'label': 'Min.', 'data':data['min'], 'color': color3},
					 ],
					 area.find('div').get(0));
		}
	});
}
