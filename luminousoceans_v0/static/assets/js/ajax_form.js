$(document).ready(function() {
    $('#nivelForm').on('submit', function(event) {
      event.preventDefault(); // Evita el comportamiento de envío predeterminado del formulario
  
      // Realiza una solicitud AJAX al servidor
      $.ajax({
        url: 'http://127.0.0.1:5000', // Reemplaza esto con la URL de tu servidor
        method: 'POST',
        data: $(this).serialize(),
        success: function(response) {
          // Procesa la respuesta del servidor (por ejemplo, mostrar el output)
          $('.output').html(response.output);
          $('#loader').hide(); // Oculta el elemento "loader"
        },
        beforeSend: function() {
          // Muestra el elemento "loader" antes de enviar la solicitud
          showLoader();
        },
        error: function() {
          // Maneja errores en la solicitud AJAX
          alert('Ocurrió un error al enviar el formulario.');
        },
      });
    });
  });
  