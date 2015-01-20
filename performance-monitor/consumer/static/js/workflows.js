/**
 * New node file
 */
$(document).ready(function(){
	$('#submit').click(function(){
		var data = {
				'type': $('#types input:checked').val(),
				'topology': $('#topology input:checked').val(),
				'mode': $('#mode input:checked').val(),
				'node_num': $('#node-num input').val(), 
				'reserve_days': $('#reserve-days input').val()
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