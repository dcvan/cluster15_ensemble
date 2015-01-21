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
						 [for (r of data.runs) 'run-' + r.run_id],
						 [{'label': 'Walltime', 'data': [for (r of data.runs) r.walltimes], 'color': '151,187,205'}],
						 $('#walltime div').get(0));
			}
		});
	}
});