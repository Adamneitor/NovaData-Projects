"""Migraciones ligeras para columnas nuevas sin borrar datos."""

from sqlalchemy import text

from app.config import DATABASE_URL
from app.database import engine


def migrate() -> None:
    # Solo aplica a SQL Server; en SQLite/Postgres create_all + seed bastan.
    if not str(DATABASE_URL).startswith("mssql"):
        print("migrate: omitido (motor no-MSSQL).")
        return
    _migrate_mssql()


def _add_column_if_missing(cn, table: str, column: str, ddl: str) -> None:
    existe = cn.execute(
        text(
            f"""
            SELECT 1 FROM sys.columns
            WHERE object_id = OBJECT_ID('{table}') AND name = '{column}'
            """
        )
    ).scalar()
    if not existe:
        cn.execute(text(ddl))
        print(f"Columna {table}.{column} agregada.")


def _migrate_mssql() -> None:
    with engine.begin() as cn:
        _add_column_if_missing(
            cn,
            "Usuarios",
            "Tipo_Autenticacion",
            """
            ALTER TABLE Usuarios
            ADD Tipo_Autenticacion NVARCHAR(10) NOT NULL
                CONSTRAINT DF_Usuarios_TipoAuth DEFAULT 'APP'
            """,
        )

        nullable = cn.execute(
            text(
                """
                SELECT is_nullable FROM sys.columns
                WHERE object_id = OBJECT_ID('Usuarios') AND name = 'password_hash'
                """
            )
        ).scalar()
        if nullable == 0:
            cn.execute(text("ALTER TABLE Usuarios ALTER COLUMN password_hash NVARCHAR(300) NULL"))
            print("Columna Usuarios.password_hash ahora admite NULL.")

        _add_column_if_missing(
            cn,
            "Usuarios",
            "Debe_Cambiar_Password",
            """
            ALTER TABLE Usuarios
            ADD Debe_Cambiar_Password BIT NOT NULL
                CONSTRAINT DF_Usuarios_DebeCambiarPwd DEFAULT 0
            """,
        )
        _add_column_if_missing(
            cn,
            "Usuarios",
            "Dias_Vigencia_Password",
            "ALTER TABLE Usuarios ADD Dias_Vigencia_Password INT NULL",
        )
        _add_column_if_missing(
            cn,
            "Usuarios",
            "Password_Fecha_Cambio",
            "ALTER TABLE Usuarios ADD Password_Fecha_Cambio DATETIME2 NULL",
        )

        # Índices de búsqueda de clientes (idempotente)
        cn.execute(
            text(
                """
                IF NOT EXISTS (
                    SELECT 1 FROM sys.indexes
                    WHERE name = 'IX_Clientes_Nombre_Completo' AND object_id = OBJECT_ID('Clientes')
                )
                CREATE NONCLUSTERED INDEX IX_Clientes_Nombre_Completo
                    ON Clientes (Nombre_Completo)
                    INCLUDE (Identificacion, Tipo_Id, Telefono, Correo);
                """
            )
        )
        cn.execute(
            text(
                """
                IF NOT EXISTS (
                    SELECT 1 FROM sys.indexes
                    WHERE name = 'IX_Clientes_Correo' AND object_id = OBJECT_ID('Clientes')
                )
                CREATE NONCLUSTERED INDEX IX_Clientes_Correo
                    ON Clientes (Correo)
                    WHERE Correo IS NOT NULL;
                """
            )
        )
        cn.execute(
            text(
                """
                IF NOT EXISTS (
                    SELECT 1 FROM sys.indexes
                    WHERE name = 'IX_Clientes_Telefono' AND object_id = OBJECT_ID('Clientes')
                )
                CREATE NONCLUSTERED INDEX IX_Clientes_Telefono
                    ON Clientes (Telefono)
                    WHERE Telefono IS NOT NULL;
                """
            )
        )
        # Casos por cliente (ficha CRM)
        cn.execute(
            text(
                """
                IF NOT EXISTS (
                    SELECT 1 FROM sys.indexes
                    WHERE name = 'IX_Casos_Cod_CL_Fecha' AND object_id = OBJECT_ID('Casos')
                )
                CREATE NONCLUSTERED INDEX IX_Casos_Cod_CL_Fecha
                    ON Casos (Cod_CL, fecha_creacion DESC)
                    INCLUDE (IdFlujo, IdEtapaActual, IdEstadoActual, EstadoGeneral, key_usuario_creador)
                    WHERE Cod_CL IS NOT NULL;
                """
            )
        )
        # Full-Text Search opcional (si el servicio FTS está disponible)
        try:
            fts = cn.execute(
                text("SELECT FULLTEXTSERVICEPROPERTY('IsFullTextInstalled')")
            ).scalar()
            if fts == 1:
                cn.execute(
                    text(
                        """
                        IF NOT EXISTS (SELECT 1 FROM sys.fulltext_catalogs WHERE name = 'FTC_Helios')
                            CREATE FULLTEXT CATALOG FTC_Helios AS DEFAULT;
                        """
                    )
                )
                cn.execute(
                    text(
                        """
                        IF NOT EXISTS (
                            SELECT 1 FROM sys.fulltext_indexes
                            WHERE object_id = OBJECT_ID('Clientes')
                        )
                        BEGIN
                            -- Requiere índice unique clave; Identificacion ya es unique
                            DECLARE @uk sysname;
                            SELECT TOP 1 @uk = i.name
                            FROM sys.indexes i
                            WHERE i.object_id = OBJECT_ID('Clientes') AND i.is_unique = 1 AND i.is_primary_key = 1;
                            IF @uk IS NOT NULL
                            BEGIN
                                DECLARE @sql nvarchar(400);
                                SET @sql = N'CREATE FULLTEXT INDEX ON Clientes (Nombre_Completo, Correo)
                                    KEY INDEX [' + @uk + N'] ON FTC_Helios WITH CHANGE_TRACKING AUTO';';
                                EXEC sp_executesql @sql;
                            END
                        END
                        """
                    )
                )
                print("Full-Text Search de Clientes verificado/creado (si aplicable).")
        except Exception as exc:  # noqa: BLE001
            print(f"FTS omitido: {exc}")

        # --- Datos complementarios: formato visual + precisión ---
        # Ampliar Tipo_Dato si aún es corto
        try:
            cn.execute(
                text(
                    """
                    IF EXISTS (
                        SELECT 1 FROM sys.columns
                        WHERE object_id = OBJECT_ID('Tipos_Datos_Complementarios')
                          AND name = 'Tipo_Dato'
                          AND max_length < 80
                    )
                    ALTER TABLE Tipos_Datos_Complementarios ALTER COLUMN Tipo_Dato NVARCHAR(40) NOT NULL
                    """
                )
            )
        except Exception as exc:  # noqa: BLE001
            print(f"Alter Tipo_Dato omitido: {exc}")

        _add_column_if_missing(
            cn,
            "Tipos_Datos_Complementarios",
            "Codigo",
            "ALTER TABLE Tipos_Datos_Complementarios ADD Codigo NVARCHAR(30) NULL",
        )
        _add_column_if_missing(
            cn,
            "Datos_Complementarios",
            "Formato_Visualizacion",
            "ALTER TABLE Datos_Complementarios ADD Formato_Visualizacion NVARCHAR(30) NULL",
        )
        _add_column_if_missing(
            cn,
            "Datos_Complementarios",
            "Decimales",
            "ALTER TABLE Datos_Complementarios ADD Decimales INT NULL",
        )

        # Semilla de tipos nuevos + códigos (idempotente)
        for tid, nombre, input_html, codigo in [
            (1, "Texto", "text", "texto"),
            (2, "Numero", "number", "numero"),
            (3, "Fecha", "date", "fecha"),
            (4, "Booleano", "checkbox", "booleano"),
            (5, "Lista", "select", "lista"),
            (6, "Numero decimal", "text", "numero_decimal"),
            (7, "Telefono", "tel", "telefono"),
            (8, "Moneda", "text", "moneda"),
            (9, "Moneda decimal", "text", "moneda_decimal"),
        ]:
            existe = cn.execute(
                text(
                    "SELECT 1 FROM Tipos_Datos_Complementarios WHERE key_tipo_dato = :id OR Tipo_Dato = :nombre"
                ),
                {"id": tid, "nombre": nombre},
            ).scalar()
            if not existe:
                cn.execute(text("SET IDENTITY_INSERT Tipos_Datos_Complementarios ON"))
                try:
                    cn.execute(
                        text(
                            """
                            INSERT INTO Tipos_Datos_Complementarios (key_tipo_dato, Tipo_Dato, input_html, Codigo)
                            VALUES (:id, :nombre, :input_html, :codigo)
                            """
                        ),
                        {"id": tid, "nombre": nombre, "input_html": input_html, "codigo": codigo},
                    )
                    print(f"Tipo de dato {tid} ({nombre}) insertado.")
                finally:
                    cn.execute(text("SET IDENTITY_INSERT Tipos_Datos_Complementarios OFF"))
            else:
                cn.execute(
                    text(
                        """
                        UPDATE Tipos_Datos_Complementarios
                        SET input_html = :input_html, Codigo = :codigo
                        WHERE key_tipo_dato = :id OR Tipo_Dato = :nombre
                        """
                    ),
                    {"id": tid, "nombre": nombre, "input_html": input_html, "codigo": codigo},
                )

        # Orden de datos por etapa + etapa de captura en casos
        _add_column_if_missing(
            cn,
            "Etapas_X_Dato",
            "Orden",
            "ALTER TABLE Etapas_X_Dato ADD Orden INT NOT NULL CONSTRAINT DF_EtapasXDato_Orden DEFAULT 1",
        )
        # Orden opcional: NULL = sin índice asignado por el usuario
        orden_nullable = cn.execute(
            text(
                """
                SELECT is_nullable FROM sys.columns
                WHERE object_id = OBJECT_ID('Etapas_X_Dato') AND name = 'Orden'
                """
            )
        ).scalar()
        if str(orden_nullable).upper() in ("0", "NO", "FALSE"):
            cn.execute(
                text(
                    """
                    DECLARE @df sysname;
                    SELECT @df = dc.name
                    FROM sys.default_constraints dc
                    INNER JOIN sys.columns c
                      ON c.default_object_id = dc.object_id
                    WHERE dc.parent_object_id = OBJECT_ID('Etapas_X_Dato')
                      AND c.name = 'Orden';
                    IF @df IS NOT NULL
                      EXEC('ALTER TABLE Etapas_X_Dato DROP CONSTRAINT [' + @df + ']');
                    """
                )
            )
            cn.execute(text("ALTER TABLE Etapas_X_Dato ALTER COLUMN Orden INT NULL"))
            print("Columna Etapas_X_Dato.Orden ahora admite NULL (sin índice automático).")

        _add_column_if_missing(
            cn,
            "Etapas_X_Dato",
            "Depende_De_Dato",
            "ALTER TABLE Etapas_X_Dato ADD Depende_De_Dato INT NULL",
        )
        _add_column_if_missing(
            cn,
            "Etapas_X_Dato",
            "Condicion_Valor",
            "ALTER TABLE Etapas_X_Dato ADD Condicion_Valor NVARCHAR(20) NULL",
        )
        _add_column_if_missing(
            cn,
            "Etapas_X_Dato",
            "Requerido_Si_Cumple",
            "ALTER TABLE Etapas_X_Dato ADD Requerido_Si_Cumple BIT NOT NULL CONSTRAINT DF_EtapasXDato_ReqSiCumple DEFAULT 0",
        )
        _add_column_if_missing(
            cn,
            "Etapas_X_Dato",
            "Deshabilitar_Si_No_Cumple",
            "ALTER TABLE Etapas_X_Dato ADD Deshabilitar_Si_No_Cumple BIT NOT NULL CONSTRAINT DF_EtapasXDato_DisSiNoCumple DEFAULT 0",
        )

        _add_column_if_missing(
            cn,
            "Casos_Datos_Complementarios",
            "IdEtapa",
            "ALTER TABLE Casos_Datos_Complementarios ADD IdEtapa INT NULL",
        )

        # Tablas de reglas de transición por datos adicionales
        cn.execute(
            text(
                """
                IF OBJECT_ID('Dato_Reglas', 'U') IS NULL
                CREATE TABLE Dato_Reglas (
                    IdDatoRegla INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                    IdEstado INT NOT NULL,
                    Nombre NVARCHAR(120) NULL,
                    Logica NVARCHAR(10) NOT NULL CONSTRAINT DF_DatoReglas_Logica DEFAULT 'AND',
                    Prioridad INT NOT NULL CONSTRAINT DF_DatoReglas_Pri DEFAULT 1,
                    EsDefault BIT NOT NULL CONSTRAINT DF_DatoReglas_Default DEFAULT 0,
                    IdEtapaDestino INT NOT NULL,
                    IdEstadoDestino INT NOT NULL,
                    CONSTRAINT FK_DatoReglas_Estado FOREIGN KEY (IdEstado) REFERENCES Estados(IdEstado),
                    CONSTRAINT FK_DatoReglas_EtapaDest FOREIGN KEY (IdEtapaDestino) REFERENCES Etapas(IdEtapa),
                    CONSTRAINT FK_DatoReglas_EstadoDest FOREIGN KEY (IdEstadoDestino) REFERENCES Estados(IdEstado)
                );
                """
            )
        )
        cn.execute(
            text(
                """
                IF OBJECT_ID('Dato_Regla_Condiciones', 'U') IS NULL
                CREATE TABLE Dato_Regla_Condiciones (
                    IdCondicion INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                    IdDatoRegla INT NOT NULL,
                    key_dato INT NOT NULL,
                    Operador NVARCHAR(20) NOT NULL,
                    Valor NVARCHAR(300) NOT NULL CONSTRAINT DF_DatoReglaCond_Valor DEFAULT '',
                    ValorHasta NVARCHAR(300) NULL,
                    CONSTRAINT FK_DatoReglaCond_Regla FOREIGN KEY (IdDatoRegla)
                        REFERENCES Dato_Reglas(IdDatoRegla) ON DELETE CASCADE,
                    CONSTRAINT FK_DatoReglaCond_Dato FOREIGN KEY (key_dato)
                        REFERENCES Datos_Complementarios(key_dato)
                );
                """
            )
        )
        print("Tablas Dato_Reglas / Dato_Regla_Condiciones verificadas.")

        # Mapeos de input/output de API por estado
        cn.execute(
            text(
                """
                IF OBJECT_ID('Estado_Api_Inputs', 'U') IS NULL
                CREATE TABLE Estado_Api_Inputs (
                    IdEstadoApiInput INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                    IdEstado INT NOT NULL,
                    IdParametro INT NOT NULL,
                    Origen NVARCHAR(15) NOT NULL CONSTRAINT DF_EstadoApiIn_Origen DEFAULT 'fijo',
                    ValorFijo NVARCHAR(500) NULL,
                    key_dato INT NULL,
                    CampoCaso NVARCHAR(50) NULL,
                    CONSTRAINT UQ_EstadoApiIn UNIQUE (IdEstado, IdParametro),
                    CONSTRAINT FK_EstadoApiIn_Estado FOREIGN KEY (IdEstado) REFERENCES Estados(IdEstado),
                    CONSTRAINT FK_EstadoApiIn_Param FOREIGN KEY (IdParametro) REFERENCES Api_Parametros(IdParametro),
                    CONSTRAINT FK_EstadoApiIn_Dato FOREIGN KEY (key_dato) REFERENCES Datos_Complementarios(key_dato)
                );
                """
            )
        )
        cn.execute(
            text(
                """
                IF OBJECT_ID('Estado_Api_Outputs', 'U') IS NULL
                CREATE TABLE Estado_Api_Outputs (
                    IdEstadoApiOutput INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                    IdEstado INT NOT NULL,
                    IdOutput INT NOT NULL,
                    key_dato INT NOT NULL,
                    CONSTRAINT UQ_EstadoApiOut UNIQUE (IdEstado, IdOutput),
                    CONSTRAINT FK_EstadoApiOut_Estado FOREIGN KEY (IdEstado) REFERENCES Estados(IdEstado),
                    CONSTRAINT FK_EstadoApiOut_Output FOREIGN KEY (IdOutput) REFERENCES Api_Outputs(IdOutput),
                    CONSTRAINT FK_EstadoApiOut_Dato FOREIGN KEY (key_dato) REFERENCES Datos_Complementarios(key_dato)
                );
                """
            )
        )
        print("Tablas Estado_Api_Inputs / Estado_Api_Outputs verificadas.")

        # Reglas API: lógica AND/OR, modo AUTO/MANUAL y condiciones múltiples
        _add_column_if_missing(
            cn,
            "Api_Reglas",
            "Logica",
            "ALTER TABLE Api_Reglas ADD Logica NVARCHAR(10) NOT NULL CONSTRAINT DF_ApiReglas_Logica DEFAULT 'AND'",
        )
        _add_column_if_missing(
            cn,
            "Api_Reglas",
            "ModoEjecucion",
            "ALTER TABLE Api_Reglas ADD ModoEjecucion NVARCHAR(10) NOT NULL CONSTRAINT DF_ApiReglas_Modo DEFAULT 'AUTO'",
        )
        _add_column_if_missing(
            cn,
            "Api_Reglas",
            "Nombre",
            "ALTER TABLE Api_Reglas ADD Nombre NVARCHAR(120) NULL",
        )
        # Permitir output legado nullable (condiciones nuevas)
        try:
            cn.execute(
                text(
                    """
                    IF EXISTS (
                        SELECT 1 FROM sys.columns
                        WHERE object_id = OBJECT_ID('Api_Reglas') AND name = 'IdOutput' AND is_nullable = 0
                    )
                    ALTER TABLE Api_Reglas ALTER COLUMN IdOutput INT NULL
                    """
                )
            )
        except Exception as exc:  # noqa: BLE001
            print(f"Alter Api_Reglas.IdOutput omitido: {exc}")

        cn.execute(
            text(
                """
                IF OBJECT_ID('Api_Regla_Condiciones', 'U') IS NULL
                CREATE TABLE Api_Regla_Condiciones (
                    IdCondicion INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                    IdRegla INT NOT NULL,
                    IdOutput INT NOT NULL,
                    Operador NVARCHAR(15) NOT NULL,
                    Valor NVARCHAR(200) NOT NULL CONSTRAINT DF_ApiReglaCond_Valor DEFAULT '',
                    CONSTRAINT FK_ApiReglaCond_Regla FOREIGN KEY (IdRegla)
                        REFERENCES Api_Reglas(IdRegla) ON DELETE CASCADE,
                    CONSTRAINT FK_ApiReglaCond_Output FOREIGN KEY (IdOutput)
                        REFERENCES Api_Outputs(IdOutput)
                );
                """
            )
        )
        # Migrar reglas legacy (una condición en columnas) → tabla de condiciones
        cn.execute(
            text(
                """
                INSERT INTO Api_Regla_Condiciones (IdRegla, IdOutput, Operador, Valor)
                SELECT r.IdRegla, r.IdOutput, ISNULL(r.Operador, '='), ISNULL(r.Valor, '')
                FROM Api_Reglas r
                WHERE r.IdOutput IS NOT NULL
                  AND NOT EXISTS (
                    SELECT 1 FROM Api_Regla_Condiciones c WHERE c.IdRegla = r.IdRegla
                  );
                """
            )
        )
        print("Api_Reglas / Api_Regla_Condiciones verificadas.")


if __name__ == "__main__":
    migrate()
    print("Migración completada.")

