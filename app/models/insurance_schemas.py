"""
Schemas para los payloads por aseguradora.
"""

from typing import Dict, Type
from app.models.job import Aseguradora
from pydantic import BaseModel, ConfigDict


class InsurancePayloadBase(BaseModel):
    """
    Modelo base para permitir campos adicionales.
    """
    model_config = ConfigDict(extra="allow")



class HDIPayload(InsurancePayloadBase):
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
    in_strIDSolicitudCotizadora: str
    in_strPlaca: str
    in_strTipoDoc: str
    in_strNumDoc: str


class SURAPayload(InsurancePayloadBase):
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


# Schema registry
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
