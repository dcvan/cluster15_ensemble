/**
 * New node file
 */
$(document).ready(function(){
	$('#submit').click(function(){
		var data = {
				'type': $('#types input:checked').val(),
				'topology': $('#topology input:checked').val(),
				'mode': $('#mode input:checked').val(),
				'worker_size': $('#worker-size input:checked').val(),
				'storage_site': $('#storage-site input:checked').val(),
				'storage_type': $('#storage-type input:checked').val(),
				'run_num': $('#run-num input').val(),
				'worker_num': $('#worker-num input').val(),
				'reservation': $('#reservation input').val(),
				'bandwidth': $('#bandwidth input').val() * 1000 * 1000,
				'storage_size': $('#storage-size input').val()
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