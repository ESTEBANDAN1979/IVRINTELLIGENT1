<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Panel de Recursos del Sistema IVR</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/admin-lte@3.2/dist/css/adminlte.min.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free/css/all.min.css">
  <script src="https://cdn.jsdelivr.net/npm/jquery@3.6.0/dist/jquery.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.6.2/dist/js/bootstrap.bundle.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="hold-transition sidebar-mini">
<div class="wrapper">
  <section class="content pt-3">
    <div class="container-fluid">
      <div class="row">
        <!-- CPU -->
        <div class="col-md-3">
          <div class="small-box bg-info">
            <div class="inner">
              <h3 id="cpu">4%</h3>
              <p>Uso de CPU</p>
            </div>
            <div class="icon">
              <i class="fas fa-microchip"></i>
            </div>
          </div>
        </div>

        <!-- RAM -->
        <div class="col-md-3">
          <div class="small-box bg-success">
            <div class="inner">
              <h3 id="ram">12%</h3>
              <p>Uso de RAM</p>
            </div>
            <div class="icon">
              <i class="fas fa-memory"></i>
            </div>
          </div>
        </div>

        <!-- Canales activos IVR -->
        <div class="col-md-3">
          <div class="small-box bg-warning">
            <div class="inner">
              <h3 id="ivr_channels">0</h3>
              <p>Canales IVR activos</p>
            </div>
            <div class="icon">
              <i class="fas fa-phone-volume"></i>
            </div>
          </div>
        </div>

        <!-- Agentes conectados -->
        <div class="col-md-3">
          <div class="small-box bg-danger">
            <div class="inner">
              <h3 id="agents">0</h3>
              <p>Agentes conectados</p>
            </div>
            <div class="icon">
              <i class="fas fa-headset"></i>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</div>

<script>
  function cargarDatos() {
    $.getJSON('datos_recursos.php', function (data) {
      $('#cpu').text(data.cpu + '%');
      $('#ram').text(data.ram + '%');
      $('#ivr_channels').text(data.ivr_channels);
      $('#agents').text(data.agents);
    });
  }

  $(function () {
    cargarDatos();
    setInterval(cargarDatos, 10000); // actualizar cada 10 segundos
  });
</script>
</body>
</html>
