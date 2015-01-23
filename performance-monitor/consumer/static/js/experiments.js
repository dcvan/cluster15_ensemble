/**
 * 
 */
$(document).ready(function(){
	$('button').click(function(){
		var expId = $(this).closest('tr').children('td.exp-id').text();
		$.ajax({
			url: window.location.pathname + '/experiments/' + expId,
			type: 'DELETE',
			contentType: 'application/json',
			success: function(data){
				location.reload();
			}
		});
	});
});