/**
 * 
 */
$(document).ready(function(){
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
	
	$(document).on('click', '#search', function(){
		data = get_values();
		console.log(JSON.stringify(data));
		update_table(data);
		get_walltime(data);
	});
	
});

function get_values(){
	var data = {};
	$('#analysis div .dropdown, #analysis.form-control').each(function(){
		var k = $(this).get(0).id.replace('-', '_'), v = $(this).val();
		if(v != null && v.length){
			data[k] = v;
		}
	});
	data['worker_sites'] = [];
	$('select option:selected').each(function(index, brand){
		data['worker_sites'].push($(this).val());
	});
	
	return data;
}

function update_table(data){
	$('tbody tr').each(function(){
		$(this).show();
	});
	data.aspect = 'experiment'
	$.ajax({
		uri: window.location.pathname,
		type: 'POST',
		data: JSON.stringify(data),
		contentType: 'application/json',
		success: function(data){
			var exp_ids = {};
			for(i = 0; i < data.exp_ids.length; i ++){
				exp_ids[data.exp_ids[i]] = null;
			}
			$('tbody tr').each(function(){
				var exp_id = $(this).find('td:first').get(0).id;
				if(!(exp_id in exp_ids)){
					$(this).hide();
				}
			});
		}
	});
}

function get_walltime(data){
	var color1 = '151,187,205', color2 = '170,57,57', color3='102,255,51'
	data.aspect = 'run';
	$.ajax({
		uri: window.location.pathname,
		type: 'POST',
		data: JSON.stringify(data),
		contentType: 'application/json',
		success: function(data){
			console.log(JSON.stringify(data));
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