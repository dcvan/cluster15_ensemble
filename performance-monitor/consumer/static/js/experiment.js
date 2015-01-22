/**
 * 
 */
$(document).ready(function(){
	if($('#walltime').length){
		$.ajax({
			url: window.location.pathname + '/runs',
			type: 'POST',
			contentType: 'application/json',
			success: function(data){
				plotLine($('#walltime canvas').get(0), 
						data.label,
						 [{'label': 'Walltime', 'data': data.walltime, 'color': '151,187,205'}],
						 $('#walltime div').get(0));
			}
		});
	}
});