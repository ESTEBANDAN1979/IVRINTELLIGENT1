DROP PROCEDURE IF EXISTS obtener_varias_campanas_activas;
DROP PROCEDURE IF EXISTS obtener_detalle_campana_para_marcar;
DROP PROCEDURE IF EXISTS obtener_campana_activa;
DROP PROCEDURE IF EXISTS marcar_detalle_enviado;
DROP PROCEDURE IF EXISTS marcar_campana_ejecucion;
DROP PROCEDURE IF EXISTS liberar_campana;

DROP TABLE IF EXISTS mensajes;
DROP TABLE IF EXISTS grupo_subida;
DROP TABLE IF EXISTS estadisticas;
DROP TABLE IF EXISTS detalle_campana;
DROP TABLE IF EXISTS campanas;
DROP TABLE IF EXISTS audios;

CREATE TABLE audios (
	id INT(11) AUTO_INCREMENT PRIMARY KEY,
	campana_id INT(11) NULL,
	nombre_audio VARCHAR(100),
	ruta_audio VARCHAR(255),
	nombre VARCHAR(255)
);

CREATE TABLE campanas (
	id INT(11) AUTO_INCREMENT PRIMARY KEY,
	nombre VARCHAR(100) NOT NULL,
	fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	max_canales INT(11) DEFAULT 5,
	estado VARCHAR(20) DEFAULT 'ACTIVA',
	intensidad INT(11) DEFAULT 1,
	fecha_inicio DATETIME NULL,
	ejecutando TINYINT(4) DEFAULT 0
);

CREATE TABLE detalle_campana (
	id INT(11) AUTO_INCREMENT PRIMARY KEY,
	campana_id INT(11),
	cedula VARCHAR(20),
	nombre VARCHAR(100),
	telefono VARCHAR(20),
	texto TEXT,
	reintentos_actuales INT(11) DEFAULT 0,
	reintentos_max INT(11),
	fecha_ultima_llamada TIMESTAMP NULL,
	estado ENUM('PENDIENTE','ENVIADO','CONTESTADA','NO CONTESTADA','EN LLAMADA','BUZON','FALLIDA','ERROR','REINTENTAR','ELIMINADO') DEFAULT 'PENDIENTE',
	uidnew CHAR(36),
	fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	grupo_id INT(11),
	ruta VARCHAR(100),
	audio_ivr BIT(1),
	activo VARCHAR(25) DEFAULT 'PAUSADA'
);

CREATE TABLE estadisticas (
	tipo VARCHAR(50) NOT NULL PRIMARY KEY,
	valor INT(11) DEFAULT 0
);

CREATE TABLE grupo_subida (
	id INT(11) AUTO_INCREMENT PRIMARY KEY,
	campana_id INT(11) NOT NULL,
	fecha_subida TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	descripcion VARCHAR(255),
	activo INT(11) DEFAULT 1
);

CREATE TABLE mensajes (
	id INT(11) AUTO_INCREMENT PRIMARY KEY,
	campana_id INT(11),
	texto TEXT,
	archivo_audio VARCHAR(255),
	ruta_audio VARCHAR(255),
	titulo VARCHAR(255),
	nombreaudio VARCHAR(255),
	audio BIT(1) DEFAULT b'0',
	orden INT(11) DEFAULT 1,
	en_proceso TINYINT(4) DEFAULT 0,
	activo BIT(1) NOT NULL DEFAULT b'1'
);

-- PROCEDIMIENTOS

DELIMITER //

CREATE PROCEDURE liberar_campana (IN id_campana INT)
BEGIN
	UPDATE ivr.campanas
	SET ejecutando = 0
	WHERE id NOT IN (
		SELECT campana_id FROM ivr.detalle_campana WHERE campana_id = id_campana GROUP BY campana_id
	);
END;
//

CREATE PROCEDURE marcar_campana_ejecucion (IN p_campana_id INT)
BEGIN
	UPDATE ivr.campanas
	SET ejecutando = 1
	WHERE id IN (
		SELECT campana_id FROM ivr.detalle_campana WHERE grupo_id = p_campana_id GROUP BY campana_id
	);
END;
//

CREATE PROCEDURE marcar_detalle_enviado (IN id_detalle INT)
BEGIN
	UPDATE detalle_campana
	SET estado = 'ENVIADO',
		reintentos_actuales = reintentos_actuales + 1
	WHERE id = id_detalle;
END;
//

CREATE PROCEDURE obtener_campana_activa ()
BEGIN
	SELECT t1.id, t1.max_canales, t1.intensidad, t.grupo_id
	FROM detalle_campana t
	LEFT JOIN (
		SELECT id, max_canales, intensidad, estado, ejecutando
		FROM campanas
	) t1 ON t1.id = t.campana_id
	WHERE t.activo = 'ACTIVA'
	  AND t.estado = 'PENDIENTE'
	LIMIT 1;
END;
//

CREATE PROCEDURE obtener_detalle_campana_para_marcar (IN p_grupo_id INT, IN p_intensidad INT, IN p_max_canales INT)
BEGIN
	SELECT t.id, t.telefono, t.texto, t.uidnew, c.nombre, t.ruta AS ruta_audio, audio_ivr, t.grupo_id
	FROM detalle_campana t
	JOIN campanas c ON c.id = t.campana_id
	WHERE t.grupo_id = p_grupo_id
	  AND t.estado IN ('PENDIENTE', 'REINTENTAR')
	  AND t.reintentos_actuales < p_intensidad
	ORDER BY t.id ASC
	LIMIT p_max_canales;
END;
//

CREATE PROCEDURE obtener_varias_campanas_activas ()
BEGIN
	SELECT t1.id, t1.max_canales, t1.intensidad, t.grupo_id
	FROM detalle_campana t
	LEFT JOIN (
		SELECT id, max_canales, intensidad, estado, ejecutando
		FROM campanas
	) t1 ON t1.id = t.campana_id
	WHERE t.activo = 'ACTIVA'
	  AND t.estado IN ('PENDIENTE')
	GROUP BY t1.id, t1.max_canales, t1.intensidad, t.grupo_id
	LIMIT 5;
END;
//

DELIMITER ;

-- LLAVES FORÁNEAS

ALTER TABLE audios
	ADD CONSTRAINT audios_ibfk_1
	FOREIGN KEY (campana_id)
	REFERENCES campanas(id)
	ON DELETE RESTRICT ON UPDATE RESTRICT;

ALTER TABLE detalle_campana
	ADD CONSTRAINT detalle_campana_ibfk_1
	FOREIGN KEY (campana_id)
	REFERENCES campanas(id)
	ON DELETE CASCADE ON UPDATE RESTRICT;

ALTER TABLE detalle_campana
	ADD CONSTRAINT detalle_campana_ibfk_2
	FOREIGN KEY (grupo_id)
	REFERENCES grupo_subida(id)
	ON DELETE RESTRICT ON UPDATE RESTRICT;

ALTER TABLE grupo_subida
	ADD CONSTRAINT grupo_subida_ibfk_1
	FOREIGN KEY (campana_id)
	REFERENCES campanas(id)
	ON DELETE RESTRICT ON UPDATE RESTRICT;

ALTER TABLE mensajes
	ADD CONSTRAINT mensajes_ibfk_1
	FOREIGN KEY (campana_id)
	REFERENCES campanas(id)
	ON DELETE RESTRICT ON UPDATE RESTRICT;