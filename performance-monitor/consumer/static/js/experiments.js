/**
 * 
 */
$(document).ready(function(){
	$('.del-experiment').click(function(){
		var expId = $(this).closest('tr').children('td.exp-id').text();
		$.ajax({
			url: window.location.pathname + '/experiments/' + expId,
			type: 'DELETE',
			data: JSON.stringify({'action': 'remove'}),
			contentType: 'application/json',
			success: function(data){
				location.reload();
			}
		});
	});
	
	$('.clear').click(function(){
		var dropdown = $(this).parent().parent();
		dropdown.find('button:first-child').text($(this).data('title'));
		dropdown.val('');
		data = get_values();
		console.log(JSON.stringify(data));
	});
	
	$('.entry').click(function(){
		var dropdown = $(this).parent().parent();
		dropdown.find('button:first-child').text($(this).text());
		dropdown.val($(this).text());
		data = get_values();
		console.log(JSON.stringify(data));
	});
	
	$('input').focusout(function(){
		data = get_values();
		console.log(JSON.stringify(data));
	});
	
});

function get_values(){
	var data = {};
	$('#analysis div, input').each(function(){
		var k = $(this).get(0).id.replace('-', '_'), v = $(this).val();
		if(v.length){
			data[k] = v;
		}
	});
	return data;
}