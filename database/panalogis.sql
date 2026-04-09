-- =========================================================
-- PANALOGIS — Script SQL Completo
-- Base de Datos: panalogis_db
-- SGBD: MariaDB 10.x / MySQL 8.x (via XAMPP)
-- Autores: Bundy, Herrera, De León — ITSE BD1 2026
-- =========================================================

DROP DATABASE IF EXISTS panalogis_db;
CREATE DATABASE panalogis_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE panalogis_db;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ─── TABLAS MAESTRAS ──────────────────────────────────────────────────────────

CREATE TABLE TIPO_VEHICULO (
  id_tipo_vehiculo  INT AUTO_INCREMENT PRIMARY KEY,
  descripcion       VARCHAR(100) NOT NULL,
  capacidad_ton     DECIMAL(8,2) NOT NULL
);

CREATE TABLE VEHICULO (
  id_vehiculo       INT AUTO_INCREMENT PRIMARY KEY,
  placa             VARCHAR(20)  NOT NULL UNIQUE,
  marca             VARCHAR(80)  NOT NULL,
  modelo            VARCHAR(80)  NOT NULL,
  anio              YEAR         NOT NULL,
  id_tipo_vehiculo  INT          NOT NULL,
  estado            ENUM('ACTIVO','MANTENIMIENTO','INACTIVO') DEFAULT 'ACTIVO',
  kilometraje       DECIMAL(10,2) DEFAULT 0,
  CONSTRAINT fk_veh_tipo FOREIGN KEY (id_tipo_vehiculo)
    REFERENCES TIPO_VEHICULO(id_tipo_vehiculo)
);

CREATE TABLE CONDUCTOR (
  id_conductor        INT AUTO_INCREMENT PRIMARY KEY,
  cedula              VARCHAR(20)  NOT NULL UNIQUE,
  nombre              VARCHAR(100) NOT NULL,
  apellido            VARCHAR(100) NOT NULL,
  telefono            VARCHAR(20),
  email               VARCHAR(150),
  licencia            VARCHAR(50)  NOT NULL UNIQUE,
  categoria_licencia  VARCHAR(10)  NOT NULL,
  vences_licencia     DATE         NOT NULL,
  estado              ENUM('ACTIVO','INACTIVO','SUSPENDIDO') DEFAULT 'ACTIVO'
);

CREATE TABLE CLIENTE (
  id_cliente       INT AUTO_INCREMENT PRIMARY KEY,
  ruc              VARCHAR(30)  NOT NULL UNIQUE,
  razon_social     VARCHAR(200) NOT NULL,
  contacto_nombre  VARCHAR(150),
  contacto_tel     VARCHAR(20),
  contacto_email   VARCHAR(150),
  direccion        TEXT,
  estado           ENUM('ACTIVO','INACTIVO') DEFAULT 'ACTIVO'
);

CREATE TABLE TIPO_CARGA (
  id_tipo_carga  INT AUTO_INCREMENT PRIMARY KEY,
  nombre         VARCHAR(100) NOT NULL,
  refrigeracion  TINYINT(1)  DEFAULT 0,
  es_peligrosa   TINYINT(1)  DEFAULT 0,
  observaciones  TEXT
);

CREATE TABLE RUTA (
  id_ruta           INT AUTO_INCREMENT PRIMARY KEY,
  nombre            VARCHAR(150) NOT NULL,
  origen            VARCHAR(200) NOT NULL,
  destino           VARCHAR(200) NOT NULL,
  distancia_km      DECIMAL(8,2),
  tiempo_est_horas  DECIMAL(5,2),
  tarifa_base       DECIMAL(10,2) NOT NULL
);

CREATE TABLE ROL_USUARIO (
  id_rol      INT AUTO_INCREMENT PRIMARY KEY,
  nombre      VARCHAR(80) NOT NULL UNIQUE,
  descripcion TEXT
);

CREATE TABLE USUARIO (
  id_usuario      INT AUTO_INCREMENT PRIMARY KEY,
  username        VARCHAR(80)  NOT NULL UNIQUE,
  nombre_completo VARCHAR(200) NOT NULL,
  email           VARCHAR(150) NOT NULL UNIQUE,
  id_rol          INT          NOT NULL,
  estado          ENUM('ACTIVO','INACTIVO') DEFAULT 'ACTIVO',
  fecha_creacion  DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_usr_rol FOREIGN KEY (id_rol)
    REFERENCES ROL_USUARIO(id_rol)
);

-- ─── TABLA CENTRAL ────────────────────────────────────────────────────────────

CREATE TABLE ORDEN_SERVICIO (
  id_orden         INT AUTO_INCREMENT PRIMARY KEY,
  numero_orden     VARCHAR(30)  NOT NULL UNIQUE,
  fecha_creacion   DATETIME     DEFAULT CURRENT_TIMESTAMP,
  fecha_programada DATE         NOT NULL,
  id_cliente       INT          NOT NULL,
  id_ruta          INT          NOT NULL,
  id_vehiculo      INT          NOT NULL,
  id_conductor     INT          NOT NULL,
  id_tipo_carga    INT          NOT NULL,
  peso_kg          DECIMAL(10,2) NOT NULL,
  descripcion      TEXT,
  estado           ENUM('PENDIENTE','EN_TRANSITO','ENTREGADO','CANCELADO') DEFAULT 'PENDIENTE',
  observaciones    TEXT,
  CONSTRAINT fk_ord_cli FOREIGN KEY (id_cliente)    REFERENCES CLIENTE(id_cliente),
  CONSTRAINT fk_ord_rut FOREIGN KEY (id_ruta)       REFERENCES RUTA(id_ruta),
  CONSTRAINT fk_ord_veh FOREIGN KEY (id_vehiculo)   REFERENCES VEHICULO(id_vehiculo),
  CONSTRAINT fk_ord_con FOREIGN KEY (id_conductor)  REFERENCES CONDUCTOR(id_conductor),
  CONSTRAINT fk_ord_car FOREIGN KEY (id_tipo_carga) REFERENCES TIPO_CARGA(id_tipo_carga)
);

CREATE TABLE MANTENIMIENTO (
  id_mantenimiento  INT AUTO_INCREMENT PRIMARY KEY,
  id_vehiculo       INT          NOT NULL,
  tipo              ENUM('PREVENTIVO','CORRECTIVO','REVISION') NOT NULL,
  fecha_inicio      DATE         NOT NULL,
  fecha_fin         DATE,
  descripcion       TEXT         NOT NULL,
  costo             DECIMAL(10,2),
  taller            VARCHAR(200),
  estado            ENUM('EN_PROCESO','COMPLETADO') DEFAULT 'EN_PROCESO',
  CONSTRAINT fk_mant_veh FOREIGN KEY (id_vehiculo)
    REFERENCES VEHICULO(id_vehiculo)
);

CREATE TABLE FACTURA (
  id_factura      INT AUTO_INCREMENT PRIMARY KEY,
  numero_factura  VARCHAR(30)   NOT NULL UNIQUE,
  id_orden        INT           NOT NULL UNIQUE,
  fecha_emision   DATETIME      DEFAULT CURRENT_TIMESTAMP,
  subtotal        DECIMAL(12,2) NOT NULL,
  impuesto        DECIMAL(12,2) NOT NULL,
  total           DECIMAL(12,2) NOT NULL,
  estado          ENUM('PENDIENTE','PAGADA','ANULADA') DEFAULT 'PENDIENTE',
  fecha_pago      DATE,
  CONSTRAINT fk_fac_ord FOREIGN KEY (id_orden)
    REFERENCES ORDEN_SERVICIO(id_orden)
);

CREATE TABLE BITACORA (
  id_bitacora      INT AUTO_INCREMENT PRIMARY KEY,
  tabla_afectada   VARCHAR(100) NOT NULL,
  operacion        ENUM('INSERT','UPDATE','DELETE') NOT NULL,
  id_registro      INT          NOT NULL,
  descripcion      TEXT,
  fecha_operacion  DATETIME     DEFAULT CURRENT_TIMESTAMP,
  id_usuario       INT,
  CONSTRAINT fk_bit_usr FOREIGN KEY (id_usuario)
    REFERENCES USUARIO(id_usuario)
);

-- ─── TRIGGERS ─────────────────────────────────────────────────────────────────

DELIMITER //

-- Bloquea asignar conductor que ya tiene una orden activa
CREATE TRIGGER trg_check_conductor_libre
BEFORE INSERT ON ORDEN_SERVICIO
FOR EACH ROW
BEGIN
  DECLARE activas INT;
  SELECT COUNT(*) INTO activas
  FROM ORDEN_SERVICIO
  WHERE id_conductor = NEW.id_conductor
    AND estado IN ('PENDIENTE','EN_TRANSITO');
  IF activas > 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'El conductor ya tiene una orden activa asignada.';
  END IF;
END//

-- Bloquea asignar vehículo que está en mantenimiento
CREATE TRIGGER trg_check_vehiculo_disponible
BEFORE INSERT ON ORDEN_SERVICIO
FOR EACH ROW
BEGIN
  DECLARE en_mant INT;
  SELECT COUNT(*) INTO en_mant
  FROM VEHICULO
  WHERE id_vehiculo = NEW.id_vehiculo
    AND estado = 'MANTENIMIENTO';
  IF en_mant > 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'El vehículo está en mantenimiento y no puede operar.';
  END IF;
END//

-- Genera factura automáticamente al entregar una orden
CREATE TRIGGER trg_generar_factura
AFTER UPDATE ON ORDEN_SERVICIO
FOR EACH ROW
BEGIN
  DECLARE v_tarifa   DECIMAL(10,2);
  DECLARE v_subtotal DECIMAL(12,2);
  DECLARE v_num      VARCHAR(30);
  IF NEW.estado = 'ENTREGADO' AND OLD.estado != 'ENTREGADO' THEN
    SELECT tarifa_base INTO v_tarifa
    FROM RUTA WHERE id_ruta = NEW.id_ruta;
    SET v_subtotal = v_tarifa * (NEW.peso_kg / 1000);
    SET v_num = CONCAT('FAC-', YEAR(NOW()), '-', LPAD(NEW.id_orden, 6, '0'));
    INSERT INTO FACTURA (numero_factura, id_orden, subtotal, impuesto, total)
    VALUES (v_num, NEW.id_orden, v_subtotal, v_subtotal * 0.07, v_subtotal * 1.07);
  END IF;
END//

-- Registra en bitácora cada cambio de estado de una orden
CREATE TRIGGER trg_bitacora_orden
AFTER UPDATE ON ORDEN_SERVICIO
FOR EACH ROW
BEGIN
  IF OLD.estado != NEW.estado THEN
    INSERT INTO BITACORA (tabla_afectada, operacion, id_registro, descripcion)
    VALUES ('ORDEN_SERVICIO', 'UPDATE', NEW.id_orden,
      CONCAT('Estado cambio de [', OLD.estado, '] a [', NEW.estado, ']'));
  END IF;
END//

-- Cambia estado del vehículo a MANTENIMIENTO al registrar uno activo
CREATE TRIGGER trg_vehiculo_a_mantenimiento
AFTER INSERT ON MANTENIMIENTO
FOR EACH ROW
BEGIN
  IF NEW.estado = 'EN_PROCESO' THEN
    UPDATE VEHICULO SET estado = 'MANTENIMIENTO'
    WHERE id_vehiculo = NEW.id_vehiculo;
  END IF;
END//

-- Restaura el vehículo a ACTIVO al completar el mantenimiento
CREATE TRIGGER trg_vehiculo_liberado
AFTER UPDATE ON MANTENIMIENTO
FOR EACH ROW
BEGIN
  IF NEW.estado = 'COMPLETADO' AND OLD.estado = 'EN_PROCESO' THEN
    UPDATE VEHICULO SET estado = 'ACTIVO'
    WHERE id_vehiculo = NEW.id_vehiculo;
  END IF;
END//

DELIMITER ;

-- ─── STORED PROCEDURES ────────────────────────────────────────────────────────

DELIMITER //

-- Crea una orden completa dentro de una transacción con manejo de errores
CREATE PROCEDURE sp_crear_orden(
  IN  p_fecha_prog    DATE,
  IN  p_id_cliente    INT,
  IN  p_id_ruta       INT,
  IN  p_id_vehiculo   INT,
  IN  p_id_conductor  INT,
  IN  p_id_tipo_carga INT,
  IN  p_peso_kg       DECIMAL(10,2),
  IN  p_descripcion   TEXT,
  OUT p_numero_orden  VARCHAR(30),
  OUT p_mensaje       VARCHAR(200)
)
BEGIN
  DECLARE v_num VARCHAR(30);
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    GET DIAGNOSTICS CONDITION 1 @msg = MESSAGE_TEXT;
    SET p_mensaje = @msg;
    SET p_numero_orden = NULL;
    ROLLBACK;
  END;

  START TRANSACTION;
    SET v_num = CONCAT('ORD-', YEAR(NOW()), '-',
      LPAD((SELECT IFNULL(MAX(id_orden), 0) + 1 FROM ORDEN_SERVICIO), 6, '0'));

    INSERT INTO ORDEN_SERVICIO
      (numero_orden, fecha_programada, id_cliente, id_ruta,
       id_vehiculo, id_conductor, id_tipo_carga, peso_kg, descripcion)
    VALUES
      (v_num, p_fecha_prog, p_id_cliente, p_id_ruta,
       p_id_vehiculo, p_id_conductor, p_id_tipo_carga, p_peso_kg, p_descripcion);

    SET p_numero_orden = v_num;
    SET p_mensaje = CONCAT('Orden creada exitosamente: ', v_num);
  COMMIT;
END//

-- Reporte de rentabilidad por ruta para un mes/año dado
CREATE PROCEDURE sp_rentabilidad_ruta(
  IN p_anio INT,
  IN p_mes  INT
)
BEGIN
  SELECT
    r.nombre        AS ruta,
    r.origen,
    r.destino,
    COUNT(o.id_orden)  AS total_servicios,
    SUM(f.subtotal)    AS ingresos_netos,
    SUM(f.impuesto)    AS itbms_cobrado,
    SUM(f.total)       AS ingresos_totales,
    AVG(f.total)       AS promedio_por_servicio
  FROM RUTA r
  JOIN ORDEN_SERVICIO o ON o.id_ruta = r.id_ruta
  JOIN FACTURA f        ON f.id_orden = o.id_orden
                        AND f.estado <> 'ANULADA'
  WHERE o.estado = 'ENTREGADO'
    AND (p_anio IS NULL OR YEAR(o.fecha_programada)  = p_anio)
    AND (p_mes  IS NULL OR MONTH(o.fecha_programada) = p_mes)
  GROUP BY r.id_ruta, r.nombre, r.origen, r.destino
  ORDER BY ingresos_totales DESC;
END//

DELIMITER ;

-- ─── ROLES Y PERMISOS ─────────────────────────────────────────────────────────

INSERT INTO ROL_USUARIO (nombre, descripcion) VALUES
  ('ADMINISTRADOR', 'Acceso total al sistema'),
  ('OPERADOR',      'Lectura y escritura en tablas operativas'),
  ('CONSULTOR',     'Solo lectura para reportes');

-- Usuarios de base de datos (ejecutar como root en XAMPP)
CREATE USER IF NOT EXISTS 'pana_admin'@'localhost'    IDENTIFIED BY 'Admin2026!';
CREATE USER IF NOT EXISTS 'pana_operador'@'localhost' IDENTIFIED BY 'Oper2026!';
CREATE USER IF NOT EXISTS 'pana_consultor'@'localhost' IDENTIFIED BY 'Cons2026!';

GRANT ALL PRIVILEGES  ON panalogis_db.* TO 'pana_admin'@'localhost';
GRANT SELECT, INSERT, UPDATE ON panalogis_db.* TO 'pana_operador'@'localhost';
GRANT SELECT ON panalogis_db.* TO 'pana_consultor'@'localhost';
FLUSH PRIVILEGES;

-- ─── DATOS DE PRUEBA ──────────────────────────────────────────────────────────

INSERT INTO TIPO_VEHICULO (descripcion, capacidad_ton) VALUES
  ('Camión liviano',          3.50),
  ('Camión mediano',         10.00),
  ('Trailer / Semirremolque',30.00),
  ('Furgón refrigerado',      8.00);

INSERT INTO VEHICULO (placa, marca, modelo, anio, id_tipo_vehiculo) VALUES
  ('AB-1234', 'Mercedes-Benz', 'Actros 1845',     2020, 3),
  ('CD-5678', 'Hino',          '300 Series',       2021, 2),
  ('EF-9012', 'Isuzu',         'NQR 75L',          2019, 2),
  ('GH-3456', 'Volkswagen',    'Constellation',     2022, 3),
  ('IJ-7890', 'Hyundai',       'HD78',             2020, 2),
  ('KL-1122', 'Mitsubishi',    'Canter FE84',      2021, 1),
  ('MN-3344', 'Volvo',         'FH16 750',         2023, 3);

INSERT INTO CONDUCTOR (cedula, nombre, apellido, licencia, categoria_licencia, vences_licencia, telefono) VALUES
  ('8-123-456', 'Carlos',  'Mendoza',   'LIC-001', 'C3', '2027-06-30', '6700-1111'),
  ('8-234-567', 'Roberto', 'Flores',    'LIC-002', 'C3', '2026-12-15', '6700-2222'),
  ('8-345-678', 'Luis',    'Samaniego', 'LIC-003', 'C2', '2027-03-22', '6700-3333'),
  ('8-456-789', 'Ana',     'Reyes',     'LIC-004', 'C2', '2026-08-10', '6700-4444'),
  ('8-567-890', 'Pedro',   'Castillo',  'LIC-005', 'C3', '2027-11-05', '6700-5555');

INSERT INTO CLIENTE (ruc, razon_social, contacto_nombre, contacto_tel, contacto_email) VALUES
  ('123-456-1-2026', 'Constructora Panamá S.A.',     'Ana Rodríguez', '6800-1234', 'ana@constructora.pa'),
  ('789-012-1-2026', 'Supermercados Central S.A.',   'Marcos León',   '6800-5678', 'marcos@central.pa'),
  ('345-678-1-2026', 'Farmacéutica Istmo S.A.',      'Rosa Díaz',     '6800-9012', 'rosa@farmistmo.pa'),
  ('901-234-1-2026', 'Cementos Nacionales S.A.',     'Jorge Pérez',   '6800-3456', 'jorge@cementos.pa'),
  ('567-890-1-2026', 'Distribuidora Tech Panama S.A.','Karla Mora',   '6800-7890', 'karla@techpanama.pa');

INSERT INTO TIPO_CARGA (nombre, refrigeracion, es_peligrosa) VALUES
  ('Materiales de construcción', 0, 0),
  ('Alimentos perecederos',      1, 0),
  ('Medicamentos',               1, 0),
  ('Carga general seca',         0, 0),
  ('Maquinaria industrial',      0, 0);

INSERT INTO RUTA (nombre, origen, destino, distancia_km, tiempo_est_horas, tarifa_base) VALUES
  ('Ciudad – Colón',    'Ciudad de Panamá', 'Colón',          76,  1.5, 150.00),
  ('Ciudad – Chiriquí', 'Ciudad de Panamá', 'David, Chiriquí',480, 6.0, 850.00),
  ('Ciudad – Penonomé', 'Ciudad de Panamá', 'Penonomé',       148, 2.5, 280.00),
  ('Ciudad – Santiago', 'Ciudad de Panamá', 'Santiago',       250, 3.5, 420.00),
  ('Ciudad – Azuero',   'Ciudad de Panamá', 'Los Santos',     310, 4.5, 520.00);

-- Usuario admin inicial
INSERT INTO USUARIO (username, nombre_completo, email, id_rol) VALUES
  ('admin', 'Administrador PanaLogis', 'admin@panalogis.pa', 1);

-- Dataset demo con cobertura suficiente para dashboard, CRUD y reportes
UPDATE VEHICULO
SET kilometraje = CASE id_vehiculo
  WHEN 1 THEN 185420.50
  WHEN 2 THEN 94215.20
  WHEN 3 THEN 131880.75
  WHEN 4 THEN 68240.10
  WHEN 5 THEN 118995.40
  WHEN 6 THEN 156700.00
  WHEN 7 THEN 213450.90
END;

UPDATE CONDUCTOR
SET email = CASE id_conductor
  WHEN 1 THEN 'carlos.mendoza@panalogis.pa'
  WHEN 2 THEN 'roberto.flores@panalogis.pa'
  WHEN 3 THEN 'luis.samaniego@panalogis.pa'
  WHEN 4 THEN 'ana.reyes@panalogis.pa'
  WHEN 5 THEN 'pedro.castillo@panalogis.pa'
END;

UPDATE CLIENTE
SET direccion = CASE id_cliente
  WHEN 1 THEN 'Parque Logístico Este, Panamá'
  WHEN 2 THEN 'Zona Comercial Colón 2000, Colón'
  WHEN 3 THEN 'Ciudad de la Salud, Panamá'
  WHEN 4 THEN 'Parque Industrial La Chorrera, Panamá Oeste'
  WHEN 5 THEN 'Área Bancaria, Ciudad de Panamá'
END;

SET @orden_1 = NULL; SET @msg_1 = NULL;
CALL sp_crear_orden('2026-04-10', 1, 1, 1, 1, 1, 12000.00, 'Traslado de acero estructural', @orden_1, @msg_1);
UPDATE ORDEN_SERVICIO
SET estado = 'ENTREGADO',
    observaciones = 'Entrega completada y cerrada sin incidencias operativas.'
WHERE numero_orden = @orden_1;
UPDATE FACTURA
SET estado = 'PAGADA',
    fecha_pago = '2026-04-11'
WHERE id_orden = (SELECT id_orden FROM ORDEN_SERVICIO WHERE numero_orden = @orden_1);

SET @orden_2 = NULL; SET @msg_2 = NULL;
CALL sp_crear_orden('2026-04-09', 2, 2, 2, 2, 2, 8500.00, 'Carga refrigerada para cadena de supermercados', @orden_2, @msg_2);
UPDATE ORDEN_SERVICIO
SET estado = 'EN_TRANSITO',
    observaciones = 'Unidad salió a las 06:30 y reportó paso por Capira.'
WHERE numero_orden = @orden_2;

SET @orden_3 = NULL; SET @msg_3 = NULL;
CALL sp_crear_orden('2026-04-05', 3, 3, 3, 3, 3, 2400.00, 'Medicamentos con cadena de frío', @orden_3, @msg_3);
UPDATE ORDEN_SERVICIO
SET estado = 'ENTREGADO',
    observaciones = 'Entrega hospitalaria completada sin incidencias.'
WHERE numero_orden = @orden_3;

SET @orden_4 = NULL; SET @msg_4 = NULL;
CALL sp_crear_orden('2026-04-06', 4, 4, 4, 4, 5, 18000.00, 'Maquinaria para planta de cemento', @orden_4, @msg_4);
UPDATE ORDEN_SERVICIO
SET estado = 'ENTREGADO',
    observaciones = 'Entrega cerrada, pero la factura quedó anulada por ajuste comercial.'
WHERE numero_orden = @orden_4;
UPDATE FACTURA
SET estado = 'ANULADA',
    fecha_pago = NULL
WHERE id_orden = (SELECT id_orden FROM ORDEN_SERVICIO WHERE numero_orden = @orden_4);

SET @orden_5 = NULL; SET @msg_5 = NULL;
CALL sp_crear_orden('2026-04-04', 1, 5, 5, 3, 4, 4300.00, 'Carga seca para distribución regional', @orden_5, @msg_5);
UPDATE ORDEN_SERVICIO
SET estado = 'CANCELADO',
    observaciones = 'Cliente reprogramó la descarga para la próxima semana.'
WHERE numero_orden = @orden_5;

SET @orden_6 = NULL; SET @msg_6 = NULL;
CALL sp_crear_orden('2026-04-03', 2, 1, 4, 4, 4, 3600.00, 'Reposición urgente de mercancía seca', @orden_6, @msg_6);
UPDATE ORDEN_SERVICIO
SET observaciones = 'Pendiente de salida en cuanto se libere la ventana de carga.'
WHERE numero_orden = @orden_6;

INSERT INTO MANTENIMIENTO (
  id_vehiculo, tipo, fecha_inicio, fecha_fin, descripcion, costo, taller, estado
) VALUES
  (5, 'CORRECTIVO', '2026-04-08', NULL, 'Reemplazo del sistema de frenos neumáticos', 1850.00, 'Taller Industrial Pacífico', 'EN_PROCESO'),
  (7, 'PREVENTIVO', '2026-03-18', '2026-03-19', 'Cambio de filtros, fluidos y calibración general', 420.00, 'Centro Técnico Norte', 'COMPLETADO');

UPDATE VEHICULO SET estado = 'INACTIVO' WHERE id_vehiculo = 7;
UPDATE CONDUCTOR SET estado = 'SUSPENDIDO' WHERE id_conductor = 5;
UPDATE CLIENTE SET estado = 'INACTIVO' WHERE id_cliente = 5;

-- ─── CONSULTAS FUNCIONALES ────────────────────────────────────────────────────

-- Q1: Estado actual de la flota
-- SELECT v.placa, v.marca, v.modelo, tv.descripcion, v.estado, v.kilometraje
-- FROM VEHICULO v JOIN TIPO_VEHICULO tv ON tv.id_tipo_vehiculo = v.id_tipo_vehiculo
-- ORDER BY v.estado, v.placa;

-- Q2: Conductores disponibles (sin orden activa)
-- SELECT c.cedula, CONCAT(c.nombre,' ',c.apellido) AS conductor,
--        c.categoria_licencia, c.vences_licencia
-- FROM CONDUCTOR c
-- WHERE c.estado = 'ACTIVO'
--   AND c.id_conductor NOT IN (
--     SELECT id_conductor FROM ORDEN_SERVICIO
--     WHERE estado IN ('PENDIENTE','EN_TRANSITO'));

-- Q3: Historial de servicios por cliente
-- SELECT cl.razon_social, o.numero_orden, r.nombre AS ruta,
--        o.fecha_programada, o.estado, IFNULL(f.total, 0) AS monto_facturado
-- FROM CLIENTE cl
-- JOIN ORDEN_SERVICIO o ON o.id_cliente = cl.id_cliente
-- JOIN RUTA r ON r.id_ruta = o.id_ruta
-- LEFT JOIN FACTURA f ON f.id_orden = o.id_orden
-- ORDER BY cl.razon_social, o.fecha_programada DESC;

-- Q4: Rentabilidad por ruta (mes actual)
-- CALL sp_rentabilidad_ruta(YEAR(CURDATE()), MONTH(CURDATE()));

-- Q5: Alertas de mantenimiento activo
-- SELECT v.placa, v.marca, v.modelo, m.tipo, m.fecha_inicio, m.descripcion, m.taller
-- FROM MANTENIMIENTO m JOIN VEHICULO v ON v.id_vehiculo = m.id_vehiculo
-- WHERE m.estado = 'EN_PROCESO' ORDER BY m.fecha_inicio;

-- Q6: Conductores con más entregas completadas
-- SELECT CONCAT(c.nombre,' ',c.apellido) AS conductor,
--        COUNT(o.id_orden) AS entregas, SUM(f.total) AS valor_transportado
-- FROM CONDUCTOR c
-- JOIN ORDEN_SERVICIO o ON o.id_conductor = c.id_conductor AND o.estado = 'ENTREGADO'
-- JOIN FACTURA f ON f.id_orden = o.id_orden
-- GROUP BY c.id_conductor ORDER BY entregas DESC;

-- Q7: Consolidado de facturación mensual
-- SELECT YEAR(f.fecha_emision) AS anio, MONTH(f.fecha_emision) AS mes,
--        COUNT(f.id_factura) AS total_facturas,
--        SUM(f.subtotal) AS ingresos_netos, SUM(f.impuesto) AS itbms,
--        SUM(f.total) AS ingresos_totales,
--        SUM(CASE WHEN f.estado='PAGADA'   THEN f.total ELSE 0 END) AS cobrado,
--        SUM(CASE WHEN f.estado='PENDIENTE' THEN f.total ELSE 0 END) AS por_cobrar
-- FROM FACTURA f GROUP BY anio, mes ORDER BY anio DESC, mes DESC;

-- Q8: Bitácora de operaciones (últimas 50)
-- SELECT b.fecha_operacion, b.tabla_afectada, b.operacion, b.id_registro, b.descripcion
-- FROM BITACORA b ORDER BY b.fecha_operacion DESC LIMIT 50;

-- =========================================================
-- FIN DEL SCRIPT — panalogis_db lista para usar
-- Ejecutar en XAMPP: mysql -u root -p < panalogis.sql
-- =========================================================
