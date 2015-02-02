/**
 * 
 */
$(document).ready(function(){
	var clip = new ZeroClipboard($('#copy-id'), {
		moviePath: '/static/ZeroClipboard.swf'
	});
	get_manifest();
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
	
	$("#replicate").click(function(){
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

function get_manifest(){
	$.ajaxSetup({
		url: window.location.pathname + '/manifest',
	});
	$.ajax({
		type: 'GET',
		contentType:'application/json',
		success:function(data){
			if(data.length == 0 || !'manifest' in data) return;
			$('#manifest').text(data['manifest']);
			prettyPrint();
		}
	});
}