/**
 * 
 */
$(document).ready(function(){
	get_walltime();
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
		$(location).attr('href', window.location.pathname + '?' + query)
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
			if(data['std_dev'])
				$('#std-dev').text('Standard Deviation: ' + data['std_dev']);
			plotLine($('#walltime canvas').get(0), 
					data['label'],
					[{'label': 'Walltime', 'data': data['walltime'], 'color': color1},],
					$('#walltime div').get(0));
		}
	});
}