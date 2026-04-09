-- =========================================================
-- PANALOGIS — Script SQL para TiDB Cloud / MySQL 8.x Cloud
-- Diferencias vs panalogis.sql (XAMPP local):
--   • Sin DROP/CREATE DATABASE (la BD ya existe en TiDB Cloud)
--   • Sin DELIMITER // (no soportado en SQL Editor cloud)
--   • Sin CREATE USER / GRANT (manejado por TiDB Cloud UI)
-- Autores: Bundy, Herrera, De León — ITSE BD1 2026
-- =========================================================

USE panalogis_db;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ─── TABLAS MAESTRAS ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS TIPO_VEHICULO (
  id_tipo_vehiculo  INT AUTO_INCREMENT PRIMARY KEY,
  descripcion       VARCHAR(100) NOT NULL,
  capacidad_ton     DECIMAL(8,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS VEHICULO (
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

CREATE TABLE IF NOT EXISTS CONDUCTOR (
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

CREATE TABLE IF NOT EXISTS CLIENTE (
  id_cliente       INT AUTO_INCREMENT PRIMARY KEY,
  ruc              VARCHAR(30)  NOT NULL UNIQUE,
  razon_social     VARCHAR(200) NOT NULL,
  contacto_nombre  VARCHAR(150),
  contacto_tel     VARCHAR(20),
  contacto_email   VARCHAR(150),
  direccion        TEXT,
  estado           ENUM('ACTIVO','INACTIVO') DEFAULT 'ACTIVO'
);

CREATE TABLE IF NOT EXISTS TIPO_CARGA (
  id_tipo_carga  INT AUTO_INCREMENT PRIMARY KEY,
  nombre         VARCHAR(100) NOT NULL,
  refrigeracion  TINYINT(1)  DEFAULT 0,
  es_peligrosa   TINYINT(1)  DEFAULT 0,
  observaciones  TEXT
);

CREATE TABLE IF NOT EXISTS RUTA (
  id_ruta           INT AUTO_INCREMENT PRIMARY KEY,
  nombre            VARCHAR(150) NOT NULL,
  origen            VARCHAR(200) NOT NULL,
  destino           VARCHAR(200) NOT NULL,
  distancia_km      DECIMAL(8,2),
  tiempo_est_horas  DECIMAL(5,2),
  tarifa_base       DECIMAL(10,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS ROL_USUARIO (
  id_rol      INT AUTO_INCREMENT PRIMARY KEY,
  nombre      VARCHAR(80) NOT NULL UNIQUE,
  descripcion TEXT
);

CREATE TABLE IF NOT EXISTS USUARIO (
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

CREATE TABLE IF NOT EXISTS ORDEN_SERVICIO (
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

CREATE TABLE IF NOT EXISTS MANTENIMIENTO (
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

CREATE TABLE IF NOT EXISTS FACTURA (
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

CREATE TABLE IF NOT EXISTS BITACORA (
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
-- INSTRUCCIÓN: En TiDB Cloud SQL Editor, ejecuta cada trigger por separado.
-- Selecciona el bloque de un trigger (desde CREATE hasta END;) y presiona Run.

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
END;

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
END;

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
END;

CREATE TRIGGER trg_bitacora_orden
AFTER UPDATE ON ORDEN_SERVICIO
FOR EACH ROW
BEGIN
  IF OLD.estado != NEW.estado THEN
    INSERT INTO BITACORA (tabla_afectada, operacion, id_registro, descripcion)
    VALUES ('ORDEN_SERVICIO', 'UPDATE', NEW.id_orden,
      CONCAT('Estado cambio de [', OLD.estado, '] a [', NEW.estado, ']'));
  END IF;
END;

CREATE TRIGGER trg_vehiculo_a_mantenimiento
AFTER INSERT ON MANTENIMIENTO
FOR EACH ROW
BEGIN
  IF NEW.estado = 'EN_PROCESO' THEN
    UPDATE VEHICULO SET estado = 'MANTENIMIENTO'
    WHERE id_vehiculo = NEW.id_vehiculo;
  END IF;
END;

CREATE TRIGGER trg_vehiculo_liberado
AFTER UPDATE ON MANTENIMIENTO
FOR EACH ROW
BEGIN
  IF NEW.estado = 'COMPLETADO' AND OLD.estado = 'EN_PROCESO' THEN
    UPDATE VEHICULO SET estado = 'ACTIVO'
    WHERE id_vehiculo = NEW.id_vehiculo;
  END IF;
END;

-- ─── STORED PROCEDURES ────────────────────────────────────────────────────────
-- INSTRUCCIÓN: Igual que los triggers — ejecuta cada procedimiento por separado.

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
END;

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
END;

-- ─── ROLES Y DATOS BASE ────────────────────────────────────────────────────────

INSERT INTO ROL_USUARIO (nombre, descripcion) VALUES
  ('ADMINISTRADOR', 'Acceso total al sistema'),
  ('OPERADOR',      'Lectura y escritura en tablas operativas'),
  ('CONSULTOR',     'Solo lectura para reportes');

-- ─── DATOS DE PRUEBA ──────────────────────────────────────────────────────────

INSERT INTO TIPO_VEHICULO (descripcion, capacidad_ton) VALUES
  ('Camión liviano',          3.50),
  ('Camión mediano',         10.00),
  ('Trailer / Semirremolque',30.00),
  ('Furgón refrigerado',      8.00);

INSERT INTO VEHICULO (placa, marca, modelo, anio, id_tipo_vehiculo) VALUES
  ('AB-1234', 'Mercedes-Benz', 'Actros 1845',  2020, 3),
  ('CD-5678', 'Hino',          '300 Series',   2021, 2),
  ('EF-9012', 'Isuzu',         'NQR 75L',      2019, 2),
  ('GH-3456', 'Volkswagen',    'Constellation',2022, 3),
  ('IJ-7890', 'Hyundai',       'HD78',         2020, 2),
  ('KL-1122', 'Mitsubishi',    'Canter FE84',  2021, 1),
  ('MN-3344', 'Volvo',         'FH16 750',     2023, 3);

INSERT INTO CONDUCTOR (cedula, nombre, apellido, licencia, categoria_licencia, vences_licencia, telefono) VALUES
  ('8-123-456', 'Carlos',  'Mendoza',   'LIC-001', 'C3', '2027-06-30', '6700-1111'),
  ('8-234-567', 'Roberto', 'Flores',    'LIC-002', 'C3', '2026-12-15', '6700-2222'),
  ('8-345-678', 'Luis',    'Samaniego', 'LIC-003', 'C2', '2027-03-22', '6700-3333'),
  ('8-456-789', 'Ana',     'Reyes',     'LIC-004', 'C2', '2026-08-10', '6700-4444'),
  ('8-567-890', 'Pedro',   'Castillo',  'LIC-005', 'C3', '2027-11-05', '6700-5555');

INSERT INTO CLIENTE (ruc, razon_social, contacto_nombre, contacto_tel, contacto_email) VALUES
  ('123-456-1-2026', 'Constructora Panamá S.A.',      'Ana Rodríguez', '6800-1234', 'ana@constructora.pa'),
  ('789-012-1-2026', 'Supermercados Central S.A.',    'Marcos León',   '6800-5678', 'marcos@central.pa'),
  ('345-678-1-2026', 'Farmacéutica Istmo S.A.',       'Rosa Díaz',     '6800-9012', 'rosa@farmistmo.pa'),
  ('901-234-1-2026', 'Cementos Nacionales S.A.',      'Jorge Pérez',   '6800-3456', 'jorge@cementos.pa'),
  ('567-890-1-2026', 'Distribuidora Tech Panama S.A.','Karla Mora',    '6800-7890', 'karla@techpanama.pa');

INSERT INTO TIPO_CARGA (nombre, refrigeracion, es_peligrosa) VALUES
  ('Materiales de construcción', 0, 0),
  ('Alimentos perecederos',      1, 0),
  ('Medicamentos',               1, 0),
  ('Carga general seca',         0, 0),
  ('Maquinaria industrial',      0, 0);

INSERT INTO RUTA (nombre, origen, destino, distancia_km, tiempo_est_horas, tarifa_base) VALUES
  ('Ciudad - Colon',    'Ciudad de Panama', 'Colon',          76,  1.5, 150.00),
  ('Ciudad - Chiriqui', 'Ciudad de Panama', 'David, Chiriqui',480, 6.0, 850.00),
  ('Ciudad - Penonome', 'Ciudad de Panama', 'Penonome',       148, 2.5, 280.00),
  ('Ciudad - Santiago', 'Ciudad de Panama', 'Santiago',       250, 3.5, 420.00),
  ('Ciudad - Azuero',   'Ciudad de Panama', 'Los Santos',     310, 4.5, 520.00);

INSERT INTO USUARIO (username, nombre_completo, email, id_rol) VALUES
  ('admin', 'Administrador PanaLogis', 'admin@panalogis.pa', 1);

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
  WHEN 1 THEN 'Parque Logistico Este, Panama'
  WHEN 2 THEN 'Zona Comercial Colon 2000, Colon'
  WHEN 3 THEN 'Ciudad de la Salud, Panama'
  WHEN 4 THEN 'Parque Industrial La Chorrera, Panama Oeste'
  WHEN 5 THEN 'Area Bancaria, Ciudad de Panama'
END;

-- ─── ÓRDENES DE DEMO (insert directo, sin SP para evitar restricciones del editor) ──

INSERT INTO ORDEN_SERVICIO
  (numero_orden, fecha_programada, id_cliente, id_ruta, id_vehiculo, id_conductor, id_tipo_carga, peso_kg, descripcion, estado, observaciones)
VALUES
  ('ORD-2026-000001', '2026-04-10', 1, 1, 1, 1, 1, 12000.00, 'Traslado de acero estructural',                 'ENTREGADO',   'Entrega completada y cerrada sin incidencias operativas.'),
  ('ORD-2026-000002', '2026-04-09', 2, 2, 2, 2, 2,  8500.00, 'Carga refrigerada para cadena de supermercados','EN_TRANSITO', 'Unidad salio a las 06:30 y reporto paso por Capira.'),
  ('ORD-2026-000003', '2026-04-05', 3, 3, 3, 3, 3,  2400.00, 'Medicamentos con cadena de frio',              'ENTREGADO',   'Entrega hospitalaria completada sin incidencias.'),
  ('ORD-2026-000004', '2026-04-06', 4, 4, 4, 4, 5, 18000.00, 'Maquinaria para planta de cemento',            'ENTREGADO',   'Entrega cerrada, pero la factura quedo anulada por ajuste comercial.'),
  ('ORD-2026-000005', '2026-04-04', 1, 5, 5, 3, 4,  4300.00, 'Carga seca para distribucion regional',        'CANCELADO',   'Cliente reprogramo la descarga para la proxima semana.');

-- Facturas manuales (normalmente las genera el trigger trg_generar_factura)
INSERT INTO FACTURA (numero_factura, id_orden, subtotal, impuesto, total, estado, fecha_pago) VALUES
  ('FAC-2026-000001', 1,  1800.00, 126.00,  1926.00, 'PAGADA',   '2026-04-11'),
  ('FAC-2026-000003', 3,   672.00,  47.04,   719.04, 'PENDIENTE', NULL),
  ('FAC-2026-000004', 4, 15300.00,1071.00, 16371.00, 'ANULADA',   NULL);

-- Mantenimientos
INSERT INTO MANTENIMIENTO (id_vehiculo, tipo, fecha_inicio, fecha_fin, descripcion, costo, taller, estado) VALUES
  (5, 'CORRECTIVO', '2026-04-08', NULL,         'Reemplazo del sistema de frenos neumaticos',       1850.00, 'Taller Industrial Pacifico', 'EN_PROCESO'),
  (7, 'PREVENTIVO', '2026-03-18', '2026-03-19', 'Cambio de filtros, fluidos y calibracion general',  420.00, 'Centro Tecnico Norte',       'COMPLETADO');

-- Estado final de vehículo 7 (trigger no actua en insert directo, forzamos)
UPDATE VEHICULO SET estado = 'INACTIVO'   WHERE id_vehiculo = 7;
UPDATE VEHICULO SET estado = 'MANTENIMIENTO' WHERE id_vehiculo = 5;
UPDATE CONDUCTOR SET estado = 'SUSPENDIDO' WHERE id_conductor = 5;
UPDATE CLIENTE   SET estado = 'INACTIVO'   WHERE id_cliente   = 5;

-- Bitácora de demo
INSERT INTO BITACORA (tabla_afectada, operacion, id_registro, descripcion) VALUES
  ('ORDEN_SERVICIO', 'UPDATE', 1, 'Estado cambio de [PENDIENTE] a [EN_TRANSITO]'),
  ('ORDEN_SERVICIO', 'UPDATE', 1, 'Estado cambio de [EN_TRANSITO] a [ENTREGADO]'),
  ('ORDEN_SERVICIO', 'UPDATE', 2, 'Estado cambio de [PENDIENTE] a [EN_TRANSITO]'),
  ('ORDEN_SERVICIO', 'UPDATE', 3, 'Estado cambio de [PENDIENTE] a [ENTREGADO]'),
  ('ORDEN_SERVICIO', 'UPDATE', 4, 'Estado cambio de [PENDIENTE] a [ENTREGADO]');

-- =========================================================
-- FIN — panalogis_db lista en TiDB Cloud
-- =========================================================
