# Documentación de Integración: Bots y APIs

## 1. Variables que van hacia los Bots de Aseguradora (Payload Mapping)

Los bots de aseguradoras reciben datos mapeados desde el contexto de cotización. Cada aseguradora tiene su propio mapeo de campos.

### Estructura del Contexto (QuoteContext)

El contexto contiene la siguiente estructura de datos:

```typescript
{
  meta: {
    solicitudAseguradoraId: string,
    solicitudCotizacionId: string,
    aseguradora: string,
    endpind: string  // endpoint del bot
  },
  asesor: {
    tipoIdentificacionAsesor: string,
    usuarioAsesor: string,
    contrasenaAsesor: string
  },
  solicitante: {
    tipoDocumento: string,
    numeroDocumento: string,
    primerNombre: string,
    segundoNombre: string,
    primerApellido: string,
    segundoApellido: string,
    nombres: string,  // combinación de nombres
    apellidos: string,  // combinación de apellidos
    generoNombre: string,
    fechaNacimiento: string,  // formato: año/mes/dia
    diaNacimiento: string,
    mesNacimiento: string,
    anioNacimiento: string,
    email: string,
    telefono: string,
    direccion: string,
    ciudadResidenciaId: string
  },
  vehiculo: {
    placa: string,
    claseVehiculoNombre: string,
    modelo: string,  // año como string
    codigoFasecolda: string,
    marca: string,
    linea: string,
    version: string,
    tipoServicioNombre: string,
    ciudadMovilizacionNombre: string,
    departamentoMovilizacion: string,
    tipoPlaca: string,
    esCeroKilometros: string,  // "si" o "no"
    valorFactura: string,  // valor como string
    color: string
  }
}
```

### Ejemplo de Payload para HDI

**Mapeo:**
```json
{
  "in_strIDSolicitudAseguradora": "meta.solicitudAseguradoraId",
  "in_strTipoIdentificacionAsesorUsuario": "asesor.tipoIdentificacionAsesor",
  "in_strUsuarioAsesor": "asesor.usuarioAsesor",
  "in_strContrasenaAsesor": "asesor.contrasenaAsesor",
  "in_strTipoDoc": "solicitante.tipoDocumento",
  "in_strNumDoc": "solicitante.numeroDocumento",
  "in_strNombre": "solicitante.primerNombre",
  "in_strApellido": "solicitante.primerApellido",
  "in_strGenero": "solicitante.generoNombre",
  "in_strDiaNacimiento": "solicitante.diaNacimiento",
  "in_strMesNacimiento": "solicitante.mesNacimiento",
  "in_strAnioNacimiento": "solicitante.anioNacimiento",
  "in_strPlaca": "vehiculo.placa",
  "in_strUsoVehiculo": "vehiculo.claseVehiculoNombre",
  "in_strModelo": "vehiculo.modelo",
  "in_strCodFasecolda": "vehiculo.codigoFasecolda",
  "in_strMarca": "vehiculo.marca",
  "in_strVersion": "vehiculo.version",
  "in_strTipo": "vehiculo.tipoServicioNombre",
  "in_strCiudadMovilidad": "vehiculo.ciudadMovilizacionNombre",
  "in_strTipoPlaca": "vehiculo.tipoPlaca",
  "in_strKmVehiculo": "vehiculo.esCeroKilometros",
  "in_strValorFactura": "vehiculo.valorFactura"
}
```

**Payload resultante enviado al bot:**
```json
{
  "in_strIDSolicitudAseguradora": "abc123xyz",
  "in_strTipoIdentificacionAsesorUsuario": "CC",
  "in_strUsuarioAsesor": "usuario_hdi",
  "in_strContrasenaAsesor": "password123",
  "in_strTipoDoc": "CC",
  "in_strNumDoc": "1234567890",
  "in_strNombre": "Juan",
  "in_strApellido": "Pérez",
  "in_strGenero": "Masculino",
  "in_strDiaNacimiento": "15",
  "in_strMesNacimiento": "06",
  "in_strAnioNacimiento": "1990",
  "in_strPlaca": "ABC123",
  "in_strUsoVehiculo": "Particular",
  "in_strModelo": "2020",
  "in_strCodFasecolda": "12345678",
  "in_strMarca": "CHEVROLET",
  "in_strVersion": "LT",
  "in_strTipo": "Automóvil",
  "in_strCiudadMovilidad": "Bogotá",
  "in_strTipoPlaca": "Particular",
  "in_strKmVehiculo": "no",
  "in_strValorFactura": "50000000"
}
```

**Ejemplo cURL:**
```bash
curl -X POST "http://localhost:4000/api/hdi/cotizar" \
  -H "Authorization: Bearer YOUR_BOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "in_strIDSolicitudAseguradora": "abc123xyz",
    "in_strTipoIdentificacionAsesorUsuario": "CC",
    "in_strUsuarioAsesor": "usuario_hdi",
    "in_strContrasenaAsesor": "password123",
    "in_strTipoDoc": "CC",
    "in_strNumDoc": "1234567890",
    "in_strNombre": "Juan",
    "in_strApellido": "Pérez",
    "in_strGenero": "Masculino",
    "in_strDiaNacimiento": "15",
    "in_strMesNacimiento": "06",
    "in_strAnioNacimiento": "1990",
    "in_strPlaca": "ABC123",
    "in_strUsoVehiculo": "Particular",
    "in_strModelo": 2020,
    "in_strCodFasecolda": "12345678",
    "in_strMarca": "CHEVROLET",
    "in_strVersion": "LT",
    "in_strTipo": "Automóvil",
    "in_strCiudadMovilidad": "Bogotá",
    "in_strTipoPlaca": "Particular",
    "in_strKmVehiculo": "no",
    "in_strValorFactura": 50000000
  }'
```

### Ejemplos de Payload por Aseguradora

---

#### RUNT

**Payload:**
```json
{
  "in_strIDSolicitudAseguradora": "abc123xyz",
  "in_strIDSolicitudCotizadora": "solicitud_123",
  "in_strPlaca": "ABC123",
  "in_strTipoDoc": "CC",
  "in_strNumDoc": "1234567890"
}
```

**cURL:**
```bash
curl -X POST "http://localhost:4000/api/runt/consultar" \
  -H "Authorization: Bearer YOUR_BOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "in_strIDSolicitudAseguradora": "abc123xyz",
    "in_strIDSolicitudCotizadora": "solicitud_123",
    "in_strPlaca": "ABC123",
    "in_strTipoDoc": "CC",
    "in_strNumDoc": "1234567890"
  }'
```

---

#### AXA COLPATRIA

**Payload:**
```json
{
  "in_strIDSolicitudAseguradora": "abc123xyz",
  "in_strTipoIdentificacionAsesorUsuario": "CC",
  "in_strUsuarioAsesor": "usuario_axa",
  "in_strContrasenaAsesor": "password123",
  "in_strNumDoc": "1234567890",
  "in_strGenero": "Masculino",
  "in_strFechaNacimiento": "1990/06/15",
  "in_strPlaca": "ABC123",
  "in_strTipoServicio": "Particular",
  "in_strColorVehiculo": "ROJO",
  "in_strDepartamentoCirculacion": "Cundinamarca",
  "in_strKmVehiculo": "no",
  "in_strValorFactura": "50000000",
  "in_strCodigoFasecolda": "12345678",
  "in_strModelo": "2020"
}
```

**cURL:**
```bash
curl -X POST "http://localhost:4000/api/axa/cotizar" \
  -H "Authorization: Bearer YOUR_BOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "in_strIDSolicitudAseguradora": "abc123xyz",
    "in_strTipoIdentificacionAsesorUsuario": "CC",
    "in_strUsuarioAsesor": "usuario_axa",
    "in_strContrasenaAsesor": "password123",
    "in_strNumDoc": "1234567890",
    "in_strGenero": "Masculino",
    "in_strFechaNacimiento": "1990/06/15",
    "in_strPlaca": "ABC123",
    "in_strTipoServicio": "Particular",
    "in_strColorVehiculo": "ROJO",
    "in_strDepartamentoCirculacion": "Cundinamarca",
    "in_strKmVehiculo": "no",
    "in_strValorFactura": "50000000",
    "in_strCodigoFasecolda": "12345678",
    "in_strModelo": "2020"
  }'
```

---

#### SOLIDARIA

**Payload:**
```json
{
  "in_strIDSolicitudAseguradora": "abc123xyz",
  "in_strTipoIdentificacionAsesorUsuario": "CC",
  "in_strUsuarioAsesor": "usuario_solidaria",
  "in_strContrasenaAsesor": "password123",
  "in_strTipoDoc": "CC",
  "in_strNumDoc": "CC",
  "in_strApellido": "Pérez",
  "in_strGenero": "Masculino",
  "in_strEmail": "juan.perez@email.com",
  "in_strCelular": "3001234567",
  "in_strPlaca": "ABC123",
  "in_strCiudadMovilidad": "Bogotá",
  "in_strClaseVehiculo": "Automóvil"
}
```

**cURL:**
```bash
curl -X POST "http://localhost:4000/api/solidaria/cotizar" \
  -H "Authorization: Bearer YOUR_BOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "in_strIDSolicitudAseguradora": "abc123xyz",
    "in_strTipoIdentificacionAsesorUsuario": "CC",
    "in_strUsuarioAsesor": "usuario_solidaria",
    "in_strContrasenaAsesor": "password123",
    "in_strTipoDoc": "CC",
    "in_strNumDoc": "CC",
    "in_strApellido": "Pérez",
    "in_strGenero": "Masculino",
    "in_strEmail": "juan.perez@email.com",
    "in_strCelular": "3001234567",
    "in_strPlaca": "ABC123",
    "in_strCiudadMovilidad": "Bogotá",
    "in_strClaseVehiculo": "Automóvil"
  }'
```

---

#### SBS

**Payload:**
```json
{
  "in_strIDSolicitudAseguradora": "abc123xyz",
  "in_strTipoIdentificacionAsesorUsuario": "CC",
  "in_strUsuarioAsesor": "usuario_sbs",
  "in_strContrasenaAsesor": "password123",
  "in_strTipoDoc": "CC",
  "in_strNumDoc": "1234567890",
  "in_strEmail": "juan.perez@email.com",
  "in_strCelular": "3001234567",
  "in_strPlaca": "ABC123",
  "in_strKmVehiculo": "no",
  "in_strCodigoFasecolda": "12345678",
  "in_strModelo": "2020"
}
```

**cURL:**
```bash
curl -X POST "http://localhost:4000/api/sbs/cotizar" \
  -H "Authorization: Bearer YOUR_BOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "in_strIDSolicitudAseguradora": "abc123xyz",
    "in_strTipoIdentificacionAsesorUsuario": "CC",
    "in_strUsuarioAsesor": "usuario_sbs",
    "in_strContrasenaAsesor": "password123",
    "in_strTipoDoc": "CC",
    "in_strNumDoc": "1234567890",
    "in_strEmail": "juan.perez@email.com",
    "in_strCelular": "3001234567",
    "in_strPlaca": "ABC123",
    "in_strKmVehiculo": "no",
    "in_strCodigoFasecolda": "12345678",
    "in_strModelo": "2020"
  }'
```

---

#### EQUIDAD

**Payload:**
```json
{
  "in_strIDSolicitudAseguradora": "abc123xyz",
  "in_strTipoIdentificacionAsesorUsuario": "CC",
  "in_strUsuarioAsesor": "usuario_equidad",
  "in_strContrasenaAsesor": "password123",
  "in_strTipoDoc": "CC",
  "in_strNumDoc": "1234567890",
  "in_strNombre": "Juan",
  "in_strSegundoNombre": "Carlos",
  "in_strApellido": "Pérez",
  "in_strSegundoApellido": "García",
  "in_strGenero": "Masculino",
  "in_strDiaNacimiento": "15",
  "in_strMesNacimiento": "06",
  "in_strAnioNacimiento": "1990",
  "in_strClaseVehiculo": "Automóvil",
  "in_strPlaca": "ABC123",
  "in_strCiudadMovilidad": "Bogotá",
  "in_strKmVehiculo": "no",
  "in_strValorFactura": "50000000"
}
```

**cURL:**
```bash
curl -X POST "http://localhost:4000/api/equidad/cotizar" \
  -H "Authorization: Bearer YOUR_BOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "in_strIDSolicitudAseguradora": "abc123xyz",
    "in_strTipoIdentificacionAsesorUsuario": "CC",
    "in_strUsuarioAsesor": "usuario_equidad",
    "in_strContrasenaAsesor": "password123",
    "in_strTipoDoc": "CC",
    "in_strNumDoc": "1234567890",
    "in_strNombre": "Juan",
    "in_strSegundoNombre": "Carlos",
    "in_strApellido": "Pérez",
    "in_strSegundoApellido": "García",
    "in_strGenero": "Masculino",
    "in_strDiaNacimiento": "15",
    "in_strMesNacimiento": "06",
    "in_strAnioNacimiento": "1990",
    "in_strClaseVehiculo": "Automóvil",
    "in_strPlaca": "ABC123",
    "in_strCiudadMovilidad": "Bogotá",
    "in_strKmVehiculo": "no",
    "in_strValorFactura": "50000000"
  }'
```

---

#### SURA

**Mapeo:**
```json
{
  "in_strIDSolicitudAseguradora": "meta.solicitudAseguradoraId",
  "in_strTipoIdentificacionAsesorUsuario": "asesor.tipoIdentificacionAsesor",
  "in_strUsuarioAsesor": "asesor.usuarioAsesor",
  "in_strContrasenaAsesor": "asesor.contrasenaAsesor",
  "in_strNumDoc": "solicitante.numeroDocumento",
  "in_strGenero": "solicitante.generoNombre",
  "in_strFechaNacimiento": "solicitante.fechaNacimiento",
  "in_strNombreCompleto": "solicitante.nombres",
  "in_strApellidoCompleto": "solicitante.apellidos",
  "in_strDireccion": "solicitante.direccion",
  "in_strPlaca": "vehiculo.placa",
  "in_strTipoServicio": "vehiculo.tipoServicioNombre",
  "in_strModelo": "vehiculo.modelo",
  "in_strColorVehiculo": "vehiculo.color",
  "in_strCiudadMovilidad": "vehiculo.ciudadMovilizacionNombre",
  "in_strCodigoFasecolda": "vehiculo.codigoFasecolda",
  "in_strKmVehiculo": "vehiculo.esCeroKilometros",
  "in_strClaseVehiculo": "vehiculo.claseVehiculoNombre"
}
```

**Payload:**
```json
{
  "in_strIDSolicitudAseguradora": "abc123xyz",
  "in_strTipoIdentificacionAsesorUsuario": "CC",
  "in_strUsuarioAsesor": "usuario_sura",
  "in_strContrasenaAsesor": "password123",
  "in_strNumDoc": "1234567890",
  "in_strGenero": "Masculino",
  "in_strFechaNacimiento": "1990/06/15",
  "in_strNombreCompleto": "Juan Carlos",
  "in_strApellidoCompleto": "Pérez García",
  "in_strDireccion": "Calle 123 #45-67",
  "in_strPlaca": "ABC123",
  "in_strTipoServicio": "Particular",
  "in_strModelo": "2020",
  "in_strColorVehiculo": "ROJO",
  "in_strCiudadMovilidad": "Bogotá",
  "in_strCodigoFasecolda": "12345678",
  "in_strKmVehiculo": "no",
  "in_strClaseVehiculo": "Automóvil"
}
```

**cURL:**
```bash
curl -X POST "http://localhost:4000/api/sura/cotizar" \
  -H "Authorization: Bearer YOUR_BOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "in_strIDSolicitudAseguradora": "abc123xyz",
    "in_strTipoIdentificacionAsesorUsuario": "CC",
    "in_strUsuarioAsesor": "usuario_sura",
    "in_strContrasenaAsesor": "password123",
    "in_strNumDoc": "1234567890",
    "in_strGenero": "Masculino",
    "in_strFechaNacimiento": "1990/06/15",
    "in_strNombreCompleto": "Juan Carlos",
    "in_strApellidoCompleto": "Pérez García",
    "in_strDireccion": "Calle 123 #45-67",
    "in_strPlaca": "ABC123",
    "in_strTipoServicio": "Particular",
    "in_strModelo": "2020",
    "in_strColorVehiculo": "ROJO",
    "in_strCiudadMovilidad": "Bogotá",
    "in_strCodigoFasecolda": "12345678",
    "in_strKmVehiculo": "no",
    "in_strClaseVehiculo": "Automóvil"
  }'
```

---

#### MUNDIAL

**Payload:**
```json
{
  "in_strIDSolicitudAseguradora": "abc123xyz",
  "in_strTipoIdentificacionAsesorUsuario": "CC",
  "in_strUsuarioAsesor": "usuario_mundial",
  "in_strContrasenaAsesor": "password123",
  "in_strTipoDoc": "CC",
  "in_strNumDoc": "1234567890",
  "in_strGenero": "Masculino",
  "in_strDiaNacimiento": "15",
  "in_strMesNacimiento": "06",
  "in_strAnioNacimiento": "1990",
  "in_strEmail": "juan.perez@email.com",
  "in_strCelular": "3001234567",
  "in_strDireccion": "Calle 123 #45-67",
  "in_strCiudadResidencia": "ciudad_id_123",
  "in_strPlaca": "ABC123",
  "in_strModelo": "2020",
  "in_strCiudadMovilidad": "Bogotá"
}
```

**cURL:**
```bash
curl -X POST "http://localhost:4000/api/mundial/cotizar" \
  -H "Authorization: Bearer YOUR_BOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "in_strIDSolicitudAseguradora": "abc123xyz",
    "in_strTipoIdentificacionAsesorUsuario": "CC",
    "in_strUsuarioAsesor": "usuario_mundial",
    "in_strContrasenaAsesor": "password123",
    "in_strTipoDoc": "CC",
    "in_strNumDoc": "1234567890",
    "in_strGenero": "Masculino",
    "in_strDiaNacimiento": "15",
    "in_strMesNacimiento": "06",
    "in_strAnioNacimiento": "1990",
    "in_strEmail": "juan.perez@email.com",
    "in_strCelular": "3001234567",
    "in_strDireccion": "Calle 123 #45-67",
    "in_strCiudadResidencia": "ciudad_id_123",
    "in_strPlaca": "ABC123",
    "in_strModelo": "2020",
    "in_strCiudadMovilidad": "Bogotá"
  }'
```

---

#### ALLIANZ

**Mapeo:**
```json
{
  "in_strIDSolicitudAseguradora": "meta.solicitudAseguradoraId",
  "in_strUsuarioAsesor": "asesor.usuarioAsesor",
  "in_strContrasenaAsesor": "asesor.contrasenaAsesor",
  "in_strTipoDoc": "solicitante.tipoDocumento",
  "in_strNumDoc": "solicitante.numeroDocumento",
  "in_strNombreCompleto": "solicitante.nombres",
  "in_strApellidoCompleto": "solicitante.apellidos",
  "in_strFechaNacimiento": "solicitante.fechaNacimiento",
  "in_strGenero": "solicitante.generoNombre",
  "in_strEmail": "solicitante.email",
  "in_strCelular": "solicitante.telefono",
  "in_strPlaca": "vehiculo.placa",
  "in_strModelo": "vehiculo.modelo",
  "in_strMarca": "vehiculo.marca",
  "in_strClaseVehiculo": "vehiculo.claseVehiculoNombre",
  "in_strDepartamentoCirculacion": "vehiculo.departamentoMovilizacion",
  "in_strCiudadMovilidad": "vehiculo.ciudadMovilizacionNombre",
  "in_strCodigoFasecolda": "vehiculo.codigoFasecoldaCF",
  "in_strKmVehiculo": "vehiculo.esCeroKilometros"
}
```

**Payload:**
```json
{
  "in_strIDSolicitudAseguradora": "abc123xyz",
  "in_strUsuarioAsesor": "usuario_allianz",
  "in_strContrasenaAsesor": "password123",
  "in_strTipoDoc": "CC",
  "in_strNumDoc": "1234567890",
  "in_strNombreCompleto": "Juan Carlos",
  "in_strApellidoCompleto": "Pérez García",
  "in_strFechaNacimiento": "1990/06/15",
  "in_strGenero": "Masculino",
  "in_strEmail": "juan.perez@email.com",
  "in_strCelular": "3001234567",
  "in_strPlaca": "ABC123",
  "in_strModelo": "2020",
  "in_strMarca": "CHEVROLET",
  "in_strClaseVehiculo": "Automóvil",
  "in_strDepartamentoCirculacion": "Cundinamarca",
  "in_strCiudadMovilidad": "Bogotá",
  "in_strCodigoFasecolda": "12345678",
  "in_strKmVehiculo": "no"
}
```

**cURL:**
```bash
curl -X POST "http://localhost:4000/api/allianz/cotizar" \
  -H "Authorization: Bearer YOUR_BOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "in_strIDSolicitudAseguradora": "abc123xyz",
    "in_strUsuarioAsesor": "usuario_allianz",
    "in_strContrasenaAsesor": "password123",
    "in_strTipoDoc": "CC",
    "in_strNumDoc": "1234567890",
    "in_strNombreCompleto": "Juan Carlos",
    "in_strApellidoCompleto": "Pérez García",
    "in_strFechaNacimiento": "1990/06/15",
    "in_strGenero": "Masculino",
    "in_strEmail": "juan.perez@email.com",
    "in_strCelular": "3001234567",
    "in_strPlaca": "ABC123",
    "in_strModelo": "2020",
    "in_strMarca": "CHEVROLET",
    "in_strClaseVehiculo": "Automóvil",
    "in_strDepartamentoCirculacion": "Cundinamarca",
    "in_strCiudadMovilidad": "Bogotá",
    "in_strCodigoFasecolda": "12345678",
    "in_strKmVehiculo": "no"
  }'
```

---

#### BOLIVAR

**Payload:**
```json
{
  "in_strIDSolicitudAseguradora": "abc123xyz",
  "in_strUsuarioAsesor": "usuario_bolivar",
  "in_strContrasenaAsesor": "password123",
  "in_strTipoDoc": "CC",
  "in_strNumDoc": "1234567890",
  "in_strGenero": "Masculino",
  "in_strNombreCompleto": "Juan Carlos",
  "in_strApellidoCompleto": "Pérez García",
  "in_strFechaNacimiento": "1990/06/15",
  "in_strEmail": "juan.perez@email.com",
  "in_strCelular": "3001234567",
  "in_strPlaca": "ABC123",
  "in_strModelo": "2020",
  "in_strMarca": "CHEVROLET",
  "in_strCodigoFasecolda": "12345678",
  "in_strKmVehiculo": "no"
}
```

**cURL:**
```bash
curl -X POST "http://localhost:4000/api/bolivar/cotizar" \
  -H "Authorization: Bearer YOUR_BOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "in_strIDSolicitudAseguradora": "abc123xyz",
    "in_strUsuarioAsesor": "usuario_bolivar",
    "in_strContrasenaAsesor": "password123",
    "in_strTipoDoc": "CC",
    "in_strNumDoc": "1234567890",
    "in_strGenero": "Masculino",
    "in_strNombreCompleto": "Juan Carlos",
    "in_strApellidoCompleto": "Pérez García",
    "in_strFechaNacimiento": "1990/06/15",
    "in_strEmail": "juan.perez@email.com",
    "in_strCelular": "3001234567",
    "in_strPlaca": "ABC123",
    "in_strModelo": "2020",
    "in_strMarca": "CHEVROLET",
    "in_strCodigoFasecolda": "12345678",
    "in_strKmVehiculo": "no"
  }'
```

---

## 2. JSON para Subir Archivos

### Endpoint: `POST /archivos-cotizacion`

**Método:** `POST`  
**Content-Type:** `multipart/form-data`

### Campos del formulario:

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `archivo` | File | ✅ Sí | Archivo PDF, JPEG o PNG (máx 10MB) |
| `idSolicitudAseguradora` | String | ✅ Sí | ID de la solicitud de aseguradora |
| `tipoSubida` | String | ❌ No | `"bot"` (default) o `"manual"` |

### Tipos de archivo permitidos:
- `application/pdf`
- `image/jpeg`
- `image/png`

### Respuesta exitosa (201):

```json
{
  "success": true,
  "message": "Archivo subido exitosamente",
  "data": {
    "id": "archivo_id_123",
    "nombre": "cotizacion_hdi_20231128.pdf",
    "nombreOriginal": "cotizacion.pdf",
    "ruta": "/uploads/archivos-cotizacion/archivo_id_123.pdf",
    "solicitudCotizacionId": "solicitud_123",
    "aseguradora": "HDI",
    "tipoSubida": "bot"
  }
}
```

### Ejemplo con cURL:

```bash
curl -X POST "http://localhost:3000/archivos-cotizacion" \
  -F "archivo=@/ruta/al/archivo.pdf" \
  -F "idSolicitudAseguradora=abc123xyz" \
  -F "tipoSubida=manual"
```

### Ejemplo con Postman:

1. **Método:** POST
2. **URL:** `http://localhost:3000/archivos-cotizacion`
3. **Body:** Seleccionar `form-data`
4. **Agregar campos:**
   - Key: `archivo` | Type: `File` | Value: Seleccionar archivo
   - Key: `idSolicitudAseguradora` | Type: `Text` | Value: `abc123xyz`
   - Key: `tipoSubida` | Type: `Text` | Value: `manual`

---

## 3. JSON para POST/PATCH `/solicitudes-aseguradoras/datos-vehiculo-adicionales`

### Endpoint: `POST` o `PATCH /solicitudes-aseguradoras/datos-vehiculo-adicionales`

**Método:** `POST` o `PATCH`  
**Content-Type:** `application/json`

### Campos del JSON:

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `solicitudCotizacionId` | String | ✅ Sí | ID de la solicitud de cotización (1-25 caracteres) |
| `solicitudAseguradoraId` | String | ❌ No | ID de la solicitud de aseguradora (1-25 caracteres) |
| `marca` | String | ❌ No | Marca del vehículo (1-100 caracteres) |
| `modelo` | Number | ❌ No | Año del modelo (1900 - año actual + 1) |
| `linea` | String | ❌ No | Línea del vehículo (1-100 caracteres) |
| `color` | String | ❌ No | Color del vehículo (2-50 caracteres) |
| `codigoFasecolda` | String | ❌ No | Código Fasecolda (1-10 caracteres) |
| `codigo_fasecolda` | String | ❌ No | Alias de codigoFasecolda |
| `version` | String | ❌ No | Versión del vehículo (1-50 caracteres) |

**Nota:** Debe enviar al menos un campo a actualizar (además del `solicitudCotizacionId`).

### Ejemplo de JSON:

```json
{
  "solicitudCotizacionId": "solicitud_123",
  "marca": "CHEVROLET",
  "modelo": 2020,
  "linea": "SPARK GT",
  "color": "ROJO",
  "codigoFasecolda": "12345678",
  "version": "LT 1.2"
}
```

### Respuesta exitosa (200):

```json
{
  "success": true,
  "message": "Datos del vehículo actualizados correctamente"
}
```

### Ejemplo con cURL:

```bash
curl -X POST "http://localhost:3000/solicitudes-aseguradoras/datos-vehiculo-adicionales" \
  -H "Content-Type: application/json" \
  -d '{
    "solicitudCotizacionId": "solicitud_123",
    "marca": "CHEVROLET",
    "modelo": 2020,
    "linea": "SPARK GT",
    "color": "ROJO",
    "codigoFasecolda": "12345678",
    "version": "LT 1.2"
  }'
```

### Ejemplo con PATCH:

```bash
curl -X PATCH "http://localhost:3000/solicitudes-aseguradoras/datos-vehiculo-adicionales" \
  -H "Content-Type: application/json" \
  -d '{
    "solicitudCotizacionId": "solicitud_123",
    "color": "AZUL"
  }'
```

### Ejemplo con Postman:

1. **Método:** POST o PATCH
2. **URL:** `http://localhost:3000/solicitudes-aseguradoras/datos-vehiculo-adicionales`
3. **Headers:**
   - Key: `Content-Type` | Value: `application/json`
4. **Body:** Seleccionar `raw` y `JSON`
5. **Contenido:**
```json
{
  "solicitudCotizacionId": "solicitud_123",
  "marca": "CHEVROLET",
  "modelo": 2020,
  "linea": "SPARK GT",
  "color": "ROJO",
  "codigoFasecolda": "12345678",
  "version": "LT 1.2"
}
```

---

## 4. JSON que se envía a CORE-services (http-procesador)

### Endpoint: `POST {CORE_SERVICES_URL}/api/v1/solicitudes/aseguradora`

**URL Base:** Configurada en variable de entorno `CORE_SERVICES_URL` (default: `http://localhost:8002`)  
**Método:** `POST`  
**Content-Type:** `application/json`  
**Timeout:** 30 segundos

### Estructura del JSON:

```json
{
  "idSolicitudAseguradora": "string",
  "idArchivoCotizacion": "string",
  "codigoAseguradora": "string"
}
```

### Campos:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `idSolicitudAseguradora` | String | ID de la solicitud de aseguradora |
| `idArchivoCotizacion` | String | ID del archivo de cotización subido |
| `codigoAseguradora` | String | ID numérico de la aseguradora (mapeado desde código) |

### Mapeo de Códigos de Aseguradora:

El sistema convierte códigos de aseguradora a IDs numéricos usando `aseguradora-id-mapper.ts`:

| Código | ID Numérico |
|--------|-------------|
| HDI | 1 |
| SURA | 2 |
| AXA_COLPATRIA | 3 |
| SBS | 4 |
| SOLIDARIA | 5 |
| EQUIDAD | 6 |
| MUNDIAL | 7 |
| ALLIANZ | 8 |
| BOLIVAR | 9 |

### Ejemplo de JSON enviado:

```json
{
  "idSolicitudAseguradora": "abc123xyz",
  "idArchivoCotizacion": "archivo_id_456",
  "codigoAseguradora": "1"
}
```

### Ejemplo con cURL:

```bash
curl -X POST "http://localhost:8002/api/v1/solicitudes/aseguradora" \
  -H "Content-Type: application/json" \
  -d '{
    "idSolicitudAseguradora": "abc123xyz",
    "idArchivoCotizacion": "archivo_id_456",
    "codigoAseguradora": "1"
  }'
```

### Ejemplo con Postman:

1. **Método:** POST
2. **URL:** `http://localhost:8002/api/v1/solicitudes/aseguradora`
3. **Headers:**
   - Key: `Content-Type` | Value: `application/json`
4. **Body:** Seleccionar `raw` y `JSON`
5. **Contenido:**
```json
{
  "idSolicitudAseguradora": "abc123xyz",
  "idArchivoCotizacion": "archivo_id_456",
  "codigoAseguradora": "1"
}
```

### Respuesta exitosa (200):

```json
{
  "success": true,
  "message": "Solicitud procesada correctamente"
}
```

### Errores comunes:

**422 - Error de validación:**
```json
{
  "message": "Datos inválidos",
  "errors": [...]
}
```

**Error de mapeo de aseguradora:**
```
Código de aseguradora no válido: "CODIGO_INVALIDO". 
Por favor, agregue este código al mapeo en aseguradora-id-mapper.ts
```

---

## Variables de Entorno

### Para Bots:
```env
BOT_BASE_URL=http://localhost:4000
BOT_API_KEY=your_bot_api_key
```

### Para CORE-services:
```env
CORE_SERVICES_URL=http://localhost:8002
```

---

## Notas Importantes

1. **Timeout de Bots:** 15 segundos
2. **Timeout de CORE-services:** 30 segundos
3. **Tamaño máximo de archivo:** 10MB
4. **Formatos de archivo permitidos:** PDF, JPEG, PNG
5. **Todos los endpoints usan JSON** excepto la subida de archivos que usa `multipart/form-data`
