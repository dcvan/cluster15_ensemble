/**
 * Workflow Page
 */
$(document).ready(function(){
	display_topology();
	display_worker_sites();
	$('#deployment option[value="standalone"]').prop('selected', true);
	display_storage_type();
	display_storage_config();
	
	$('#deployment').change(function(){
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
	
	$('#storage-type').change(function(){
		display_storage_config();
	})
	
	$(document).on('click', '#submit', function(){
		var data = {
				'type': $('#types option:selected').val(),
				'topology': $('#topology option:selected').val(),
				'deployment': $('#deployment option:selected').val(),
				'master_site': $('#master-site option:selected').val(),
				'worker_size': $('#worker-size option:selected').val(),
				'storage_type': $('#storage-type option:selected').val(),
				'filesystem': $('#filesystem option:selected').val(),
				'workload': parseInt($('#workload input').val()),
				'reservation': parseInt($('#reservation input').val()),
			};
		
		if($('#worker-sites').is(':visible')){
			var worker_sites = [], num_of_workers = 0;
			$('.worker').each(function(){
				data['worker_sites'].push({
					'site': $(this).find('option:selected').val(),
					'num': parseInt($(this).find('input').val())
				});	
				data['num_of_workers'] += parseInt($(this).find('input').val());
			});
		}else{
			data['worker_sites'] = [{'site': data['master_site'], 'num': 1}];
			data['num_of_workers'] = 1;
		}
		
		if($('#storage-config').is(':visible')){
			data['storage_site'] = $('#storage-config #detail .site select option:selected').val();
			data['storage_bw'] = parseInt($('#storage_config #detail #storage-bw input').val()) * 1000 * 1000;
			data['storage_size'] = parseInt($('#storage_config #detail #storage-size input').val()); 
		}
		console.log(JSON.stringify(data));
		$.ajax({
			url: window.location.pathname,
			type: 'POST',
			data: JSON.stringify(data),
			contentType: 'application/json',
			success: function(data){
				console.log(JSON.stringify(data));
				$(location).attr('href', get_url('/workflows/' + data.type + '/experiments/' + data.exp_id));
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
	if($('#deployment option:selected').val() == 'standalone'){
		$('#topology option[value="intra-rack"]').prop('selected', true);
		$('#topology').prop('disabled', true);
	}else{
		$('#topology').prop('disabled', false);
	}
}

function display_worker_sites(){
	if ($('#deployment option:selected').val() == 'multinode'){
		$('#worker-sites').show();
		$('#bandwidth').show();
	}else{
		$('#worker-sites').hide();
		$('#bandwidth').hide();
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
	$('#filesystem').empty();
	var deployment = $('#deployment option:selected').val();
	$.ajaxSetup({
		url: '/deployments/' + deployment
	});
	$.ajax({
		type: 'GET',
		contentType: 'application/json',
		success:function(data){
			if(data.length == 0 || !'fs' in data) return;
			for(var i in data['fs']){
				$('#filesystem').append($('<option>'+ data['fs'][i] +'</option>', {
							value: data['fs'][i]
						}));
			}
		}
	});
}

function display_storage_config(){
	if($('#storage-type option:selected').val() == 'native'){
		$('#storage-config').hide();
	}else{
		$('#storage-config').show();
	}
}

