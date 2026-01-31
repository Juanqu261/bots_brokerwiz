"""
Insurance payload validation schemas.

This module defines Pydantic models for validating insurance-specific payloads
before queueing tasks to MQTT. Each insurance company has its own schema
defining required and optional fields.
"""

from pydantic import BaseModel, ConfigDict
from typing import Dict, Type
from app.models.job import Aseguradora


class InsurancePayloadBase(BaseModel):
    """
    Base model for all insurance payloads.
    
    Allows extra fields to be preserved in the payload.
    """
    model_config = ConfigDict(extra="allow")



class HDIPayload(InsurancePayloadBase):
    """Payload schema for HDI insurance."""
    # Asesor fields
    in_strTipoIdentificacionAsesorUsuario: str
    in_strUsuarioAsesor: str
    in_strContrasenaAsesor: str
    
    # Solicitante fields
    in_strTipoDoc: str
    in_strNumDoc: str
    in_strNombre: str
    in_strApellido: str
    in_strGenero: str
    in_strDiaNacimiento: str
    in_strMesNacimiento: str
    in_strAnioNacimiento: str
    
    # Vehiculo fields
    in_strPlaca: str
    in_strUsoVehiculo: str
    in_strModelo: str
    in_strCodFasecolda: str
    in_strMarca: str
    in_strVersion: str
    in_strTipo: str
    in_strCiudadMovilidad: str
    in_strTipoPlaca: str
    in_strKmVehiculo: str
    in_strValorFactura: str


class SBSPayload(InsurancePayloadBase):
    """Payload schema for SBS insurance."""
    in_strTipoIdentificacionAsesorUsuario: str
    in_strUsuarioAsesor: str
    in_strContrasenaAsesor: str
    in_strTipoDoc: str
    in_strNumDoc: str
    in_strEmail: str
    in_strCelular: str
    in_strPlaca: str
    in_strKmVehiculo: str
    in_strCodigoFasecolda: str
    in_strModelo: str


class RUNTPayload(InsurancePayloadBase):
    """Payload schema for RUNT."""
    in_strIDSolicitudCotizadora: str
    in_strPlaca: str
    in_strTipoDoc: str
    in_strNumDoc: str


class SURAPayload(InsurancePayloadBase):
    """Payload schema for SURA insurance."""
    in_strTipoIdentificacionAsesorUsuario: str
    in_strUsuarioAsesor: str
    in_strContrasenaAsesor: str
    in_strNumDoc: str
    in_strGenero: str
    in_strFechaNacimiento: str
    in_strNombreCompleto: str
    in_strApellidoCompleto: str
    in_strDireccion: str
    in_strPlaca: str
    in_strTipoServicio: str
    in_strModelo: str
    in_strColorVehiculo: str
    in_strCiudadMovilidad: str
    in_strCodigoFasecolda: str
    in_strKmVehiculo: str
    in_strClaseVehiculo: str


class AXAPayload(InsurancePayloadBase):
    """Payload schema for AXA COLPATRIA insurance."""
    in_strTipoIdentificacionAsesorUsuario: str
    in_strUsuarioAsesor: str
    in_strContrasenaAsesor: str
    in_strNumDoc: str
    in_strGenero: str
    in_strFechaNacimiento: str
    in_strPlaca: str
    in_strTipoServicio: str
    in_strColorVehiculo: str
    in_strDepartamentoCirculacion: str
    in_strKmVehiculo: str
    in_strValorFactura: str
    in_strCodigoFasecolda: str
    in_strModelo: str


class ALLIANZPayload(InsurancePayloadBase):
    """Payload schema for ALLIANZ insurance."""
    in_strUsuarioAsesor: str
    in_strContrasenaAsesor: str
    in_strTipoDoc: str
    in_strNumDoc: str
    in_strNombreCompleto: str
    in_strApellidoCompleto: str
    in_strFechaNacimiento: str
    in_strGenero: str
    in_strEmail: str
    in_strCelular: str
    in_strPlaca: str
    in_strModelo: str
    in_strMarca: str
    in_strClaseVehiculo: str
    in_strDepartamentoCirculacion: str
    in_strCiudadMovilidad: str
    in_strCodigoFasecolda: str
    in_strKmVehiculo: str


class BOLIVARPayload(InsurancePayloadBase):
    """Payload schema for BOLIVAR insurance."""
    in_strUsuarioAsesor: str
    in_strContrasenaAsesor: str
    in_strTipoDoc: str
    in_strNumDoc: str
    in_strGenero: str
    in_strNombreCompleto: str
    in_strApellidoCompleto: str
    in_strFechaNacimiento: str
    in_strEmail: str
    in_strCelular: str
    in_strPlaca: str
    in_strModelo: str
    in_strMarca: str
    in_strCodigoFasecolda: str
    in_strKmVehiculo: str


class EQUIDADPayload(InsurancePayloadBase):
    """Payload schema for EQUIDAD insurance."""
    in_strTipoIdentificacionAsesorUsuario: str
    in_strUsuarioAsesor: str
    in_strContrasenaAsesor: str
    in_strTipoDoc: str
    in_strNumDoc: str
    in_strNombre: str
    in_strSegundoNombre: str
    in_strApellido: str
    in_strSegundoApellido: str
    in_strGenero: str
    in_strDiaNacimiento: str
    in_strMesNacimiento: str
    in_strAnioNacimiento: str
    in_strClaseVehiculo: str
    in_strPlaca: str
    in_strCiudadMovilidad: str
    in_strKmVehiculo: str
    in_strValorFactura: str


class MUNDIALPayload(InsurancePayloadBase):
    """Payload schema for MUNDIAL insurance."""
    in_strTipoIdentificacionAsesorUsuario: str
    in_strUsuarioAsesor: str
    in_strContrasenaAsesor: str
    in_strTipoDoc: str
    in_strNumDoc: str
    in_strGenero: str
    in_strDiaNacimiento: str
    in_strMesNacimiento: str
    in_strAnioNacimiento: str
    in_strEmail: str
    in_strCelular: str
    in_strDireccion: str
    in_strCiudadResidencia: str
    in_strPlaca: str
    in_strModelo: str
    in_strCiudadMovilidad: str


class SOLIDARIAPayload(InsurancePayloadBase):
    """Payload schema for SOLIDARIA insurance."""
    in_strTipoIdentificacionAsesorUsuario: str
    in_strUsuarioAsesor: str
    in_strContrasenaAsesor: str
    in_strTipoDoc: str
    in_strNumDoc: str
    in_strApellido: str
    in_strGenero: str
    in_strEmail: str
    in_strCelular: str
    in_strPlaca: str
    in_strCiudadMovilidad: str
    in_strClaseVehiculo: str


# Schema registry mapping insurance companies to their validation schemas
INSURANCE_SCHEMAS: Dict[Aseguradora, Type[InsurancePayloadBase]] = {
    Aseguradora.HDI: HDIPayload,
    Aseguradora.SBS: SBSPayload,
    Aseguradora.RUNT: RUNTPayload,
    Aseguradora.SURA: SURAPayload,
    Aseguradora.AXA: AXAPayload,
    Aseguradora.ALLIANZ: ALLIANZPayload,
    Aseguradora.BOLIVAR: BOLIVARPayload,
    Aseguradora.EQUIDAD: EQUIDADPayload,
    Aseguradora.MUNDIAL: MUNDIALPayload,
    Aseguradora.SOLIDARIA: SOLIDARIAPayload,
}
