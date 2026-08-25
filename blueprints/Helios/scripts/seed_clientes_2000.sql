/*
  Helios — Seed de 2,000 clientes dummy (SQL Server)
  Ejecutar en BD Helios. Idempotente: omite identificaciones ya existentes.

  Estrategia:
  - Identificaciones únicas 001-1XXXXXX-C (cédula sintética)
  - Índices esperados: UK Identificacion, IX Nombre_Completo, IX Correo, IX Telefono
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

IF OBJECT_ID('tempdb..#Nombres') IS NOT NULL DROP TABLE #Nombres;
IF OBJECT_ID('tempdb..#Apellidos') IS NOT NULL DROP TABLE #Apellidos;

CREATE TABLE #Nombres (n INT IDENTITY(1,1), Nombre NVARCHAR(40));
INSERT INTO #Nombres (Nombre) VALUES
(N'Juan'),(N'José'),(N'Carlos'),(N'Luis'),(N'Miguel'),(N'Pedro'),(N'Rafael'),(N'Andrés'),
(N'María'),(N'Ana'),(N'Carmen'),(N'Laura'),(N'Patricia'),(N'Sofía'),(N'Valeria'),(N'Elena'),
(N'Daniel'),(N'David'),(N'Jorge'),(N'Alejandro'),(N'Ricardo'),(N'Fernando'),(N'Gabriela'),(N'Camila');

CREATE TABLE #Apellidos (n INT IDENTITY(1,1), Apellido NVARCHAR(40));
INSERT INTO #Apellidos (Apellido) VALUES
(N'García'),(N'Rodríguez'),(N'Martínez'),(N'Pérez'),(N'González'),(N'Sánchez'),(N'Ramírez'),
(N'Torres'),(N'Flores'),(N'Rivera'),(N'Gómez'),(N'Díaz'),(N'Cruz'),(N'Morales'),(N'Reyes'),
(N'Ortiz'),(N'Vargas'),(N'Castillo'),(N'Mendoza'),(N'Romero');

DECLARE @i INT = 1;
DECLARE @max INT = 2000;
DECLARE @nom NVARCHAR(40), @ap1 NVARCHAR(40), @ap2 NVARCHAR(40);
DECLARE @nombre NVARCHAR(200), @iden NVARCHAR(30), @tel NVARCHAR(20), @correo NVARCHAR(100);
DECLARE @nCount INT = (SELECT COUNT(*) FROM #Nombres);
DECLARE @aCount INT = (SELECT COUNT(*) FROM #Apellidos);
DECLARE @pref CHAR(3);

BEGIN TRAN;
WHILE @i <= @max
BEGIN
    SELECT @nom = Nombre FROM #Nombres WHERE n = ((@i - 1) % @nCount) + 1;
    SELECT @ap1 = Apellido FROM #Apellidos WHERE n = ((@i * 3) % @aCount) + 1;
    SELECT @ap2 = Apellido FROM #Apellidos WHERE n = ((@i * 7) % @aCount) + 1;
    SET @nombre = @nom + N' ' + @ap1 + N' ' + @ap2;
    SET @iden = CONCAT('001-', RIGHT(CONCAT('0000000', 1000000 + @i), 7), '-', ((1000000 + @i) % 9) + 1);
    SET @pref = CASE (@i % 3) WHEN 0 THEN '809' WHEN 1 THEN '829' ELSE '849' END;
    SET @tel = CONCAT(@pref, '-', 500 + (@i % 400), '-', RIGHT(CONCAT('0000', 1000 + (@i % 9000)), 4));
    SET @correo = LOWER(@nom) + '.' + LOWER(@ap1) + '.' + CAST(@i AS VARCHAR(10)) + '@cliente.test';

    IF NOT EXISTS (SELECT 1 FROM Clientes WHERE Identificacion = @iden)
    BEGIN
        INSERT INTO Clientes (Nombre_Completo, Tipo_Id, Identificacion, Telefono, Correo)
        VALUES (@nombre, N'Cedula', @iden, @tel, @correo);
    END
    SET @i += 1;
END
COMMIT;

SELECT COUNT(*) AS TotalClientes FROM Clientes;
SELECT TOP 5 * FROM Clientes ORDER BY Cod_CL DESC;
