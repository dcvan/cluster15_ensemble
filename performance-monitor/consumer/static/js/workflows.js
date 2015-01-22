/**
 * New node file
 */
$(document).ready(function(){
	$('#submit').click(function(){
		var data = {
				'type': $('#types option:selected').val(),
				'topology': $('#topology option:selected').val(),
				'mode': $('#mode option:selected').val(),
				'master_site': $('#master-site option:selected').val(),
				'worker_site': $('#topology option:selected').val() == 'intra-rack'?$('#master-site option:selected').val():$('#worker-site option:selected').val(),
				'worker_size': $('#worker-size option:selected').val(),
				'storage_site': $('#storage-site option:selected').val(),
				'storage_type': $('#storage-type option:selected').val(),
				'run_num': $('#run-num input').val(),
				'worker_num': $('#worker-num input').val(),
				'reservation': $('#reservation input').val(),
				'bandwidth': $('#bandwidth input').val() * 1000 * 1000,
				'storage_size': $('#storage-size input').val(),
			};
		
		console.log(JSON.stringify(data));
		$.ajax({
			url: window.location.pathname,
			type: 'POST',
			data: JSON.stringify(data),
			contentType: 'application/json',
			success: function(data){
				window.location.replace(get_url('workflows/' + data.type + '/experiments/' + data.exp_id));
			}
		});
	});
});