/**
 * 
 */
$(document).ready(function(){
	var clip = new ZeroClipboard($('#copy-id'), {
		moviePath: '/static/ZeroClipboard.swf'
	});
	
	$("#redo").click(function(){
		$.ajax({
			url: window.location.pathname,
			type: 'DELETE',
			contentType: 'application/json',
			data: JSON.stringify({'action': 'redo'}),
			success:function(data){
				location.reload();
			}
		});
	});
	
	$("#copy").click(function(){
		$.ajax({
			url: window.location.pathname,
			type: 'GET',
			contentType: 'application/json',
			success: function(data){
				console.log(JSON.stringify(data));
				$.ajax({
					url: '/',
					type: 'POST',
					contentType: 'application/json',
					data: JSON.stringify(data),
					success: function(data){
						window.location.replace(get_url('/workflows/' + data.type));
					}
				});
			}
		});
	});
	
	$('#del').click(function(){
		$.ajax({
			url: window.location.pathname,
			type: 'DELETE',
			contentType: 'application/json',
			data: JSON.stringify({'action': 'remove'}),
			success: function(data){
				window.location.replace(get_url('/'))
			}
		});
	});
});