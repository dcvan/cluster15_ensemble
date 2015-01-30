/**
 * New node file
 */
$(document).ready(function(){
	display_topology();
	display_worker_sites();
	$('#mode option[value="standalone"]').prop('selected', true);
	display_storage_type();
	
	$('#mode').change(function(){
		display_topology();
		display_worker_sites();
		display_storage_type();
	});
	
	$('#topology').change(function(){
		display_worker_sites();
	});
	
	$('#master-site').change(function(){
		if($('#topology option:selected').val() == 'intra-rack'){
			$('#workers .worker .site').val($('#master-site option:selected').val());
		}
	});
	
	$('#storage-location').change(function(){
		if($(this).find('option:selected').val() == 'local'){
			$('#storage-size').hide();
		}else{
			$('#storage-size').show();
		}
	});
	
	$(document).on('click', '#submit', function(){
		var data = {
				'action': 'new_experiment',
				'type': $('#types option:selected').val(),
				'topology': $('#topology option:selected').val(),
				'mode': $('#mode option:selected').val(),
				'master_site': $('#master-site option:selected').val(),
				'worker_size': $('#worker-size option:selected').val(),
				'storage_location': $('#storage-location option:selected').val(),
				'storage_type': $('#storage-type option:selected').val(),
				'run_num': $('#run-num input').val(),
				'reservation': $('#reservation input').val(),
				'bandwidth': $('#bandwidth input').val() * 1000 * 1000,
				'storage_size': $('#storage-size input').val(),
			};
		if($('#worker-sites').is(':visible')){
			data['worker_sites'] = [];
			$('.worker').each(function(){
				data['worker_sites'].push({
					'site': $(this).find('option:selected').val(),
					'num': $(this).find('input').val()
				});	
			});
		}else{
			data['worker_sites'] = [{'site': data['master_site'], 'num': 1}];
		}
		
		$.ajax({
			url: window.location.pathname,
			type: 'POST',
			data: JSON.stringify(data),
			contentType: 'application/json',
			success: function(data){
				window.location.replace(get_url('/workflows/' + data.type + '/experiments/' + data.exp_id));
			}
		});
	});
	
	$('#add').click(function(){
		$('#workers').append($('#workers div:first').clone());
	});
	
	$(document).on('click', '.remove', function(){
		if($('#workers').children().length > 1)
			$(this).parent().remove();
	});
});

function display_topology(){
	if($('#mode option:selected').val() == 'standalone'){
		$('#topology option[value="intra-rack"]').prop('selected', true);
		$('#topology').prop('disabled', true);
	}else{
		$('#topology').prop('disabled', false);
	}
}

function display_worker_sites(){
	if ($('#mode option:selected').val() == 'multinode'){
		$('#worker-sites').show();
	}else{
		$('#worker-sites').hide();
	}
	
	if($('#topology option:selected').val() == 'intra-rack'){
		$('#workers .worker .site').prop('disabled', true);
		$('#workers .worker .site').val($('#master-site option:selected').val());
		$('#workers .worker .remove').hide();
		$('#add').hide();
	}else{
		$('#workers.worker.remove').show();
		$('#workers .worker .site').prop('disabled', false);
		$('#add').show();
	}
}

function display_storage_type(){
	$('#storage-type').empty();
	var mode = $('#mode option:selected').val();
	$.ajax({
		uri: window.location.pathname,
		type: 'POST',
		data: JSON.stringify({'action': 'query_mode', 'mode': mode}),
		contentType: 'application/json',
		success:function(data){
			if(data.length == 0 || !'storage_type' in data) return;
			for(var i in data['storage_type']){
				$('#storage-type').append($('<option>'+ data['storage_type'][i] +'</option>', {
							value: data['storage_type'][i]
						}));
			}
		}
	});
}






