<?php
header('Content-Type: application/json');

// Uso de CPU y RAM (simplificado)
$cpu = intval(exec("top -bn1 | grep 'Cpu(s)' | awk '{print 100 - $8}'")); // uso CPU
$ram = intval(exec("free | grep Mem | awk '{print $3/$2 * 100.0}'")); // uso RAM

// Canales activos IVR
$ivr_channels = intval(exec("asterisk -rx 'core show channels concise' | grep '^Local/' | wc -l"));

// Agentes conectados en Issabel
$agents = intval(exec("asterisk -rx 'queue show' | grep 'Agent/' | grep -c ' (Not in use)'")); // o ajusta según necesidad

echo json_encode([
  'cpu' => $cpu,
  'ram' => $ram,
  'ivr_channels' => $ivr_channels,
  'agents' => $agents
]);
