<?php 
header('Content-Type: text/html; charset=UTF-8');
include '/var/www/html/ivr_adminlte/includes/db.php';
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL & ~E_NOTICE);
if (!ini_get('date.timezone')) {
    date_default_timezone_set('America/Guayaquil');
}
?>
<body class="hold-transition sidebar-mini">
<div class="wrapper">
  <section class="content pt-3">
    <div class="container-fluid">
<div class="row">
  <div class="col-md-3">
    <div class="small-box bg-info">
      <div class="inner">
        <h3><?php echo obtenerConteo("PENDIENTE"); ?></h3>
        <p>Números Activos</p>
      </div>
      <div class="icon"><i class="fas fa-broadcast-tower"></i></div>
    </div>
  </div>
  <div class="col-md-3">
    <div class="small-box bg-success">
      <div class="inner">
        <h3><?php echo obtenerConteo("ENVIADO"); ?></h3>
        <p>Llamadas en Cola</p>
      </div>
      <div class="icon"><i class="fas fa-phone-volume"></i></div>
    </div>
  </div>
  <div class="col-md-3">
    <div class="small-box bg-warning">
      <div class="inner">
        <h3><?php echo obtenerConteo("CONTESTADA"); ?></h3>
        <p>Contestadas</p>
      </div>
      <div class="icon"><i class="fas fa-headset"></i></div>
    </div>
  </div>
  <div class="col-md-3">
    <div class="small-box bg-danger">
      <div class="inner">
        <h3><?php echo obtenerConteo("NO CONTESTADA"); ?></h3>
        <p>No Contestadas</p>
      </div>
      <div class="icon"><i class="fas fa-times-circle"></i></div>
    </div>
  </div>
</div>

    </div>
  </section>
</div>
</body>


<script src="assets/plugins/jquery/jquery.min.js"></script>

<script>
  setInterval(() => {
    fetch('modulos/live_log_ajax.php')
      .then(res => res.text())
      .then(data => {
        document.getElementById('liveLogs').textContent = data;
      });
  }, 5000);
</script>


<?php
function obtenerConteo($estado) {
  global $pdo;
  try {
    $hoy = date('Y-m-d'); // Fecha de hoy
    $stmt = $pdo->prepare("
      SELECT COUNT(*) as total
      FROM detalle_campana
      WHERE DATE(fecha_envio) = ? AND estado = ?
    ");
    $stmt->execute([$hoy, $estado]);
    $row = $stmt->fetch(PDO::FETCH_ASSOC);
    return $row ? $row['total'] : 0;
  } catch (PDOException $e) {
    error_log("Error en obtenerConteoDesdeDetalle: " . $e->getMessage());
    return 0;
  }
}
?>