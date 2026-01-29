"""
Selectores CSS para el portal SBS Seguros.

Estos selectores se extraen del portal original y se mantienen sincronizados
con la estructura HTML del portal de SBS.
"""

from enum import StrEnum


class SBSUIElements(StrEnum):
    """Selectores CSS para el portal SBS Seguros."""
    
    # === Login Page ===
    INPUT_USERNAME = "#username"
    INPUT_PASSWORD = "#password"
    CAPTCHA_IMAGE = "#captcha"
    INPUT_CAPTCHA = "#captchaInput"
    BUTTON_LOGIN = "#loginButton"
    BUTTON_REFRESH_CAPTCHA = "#captchaContainer > div > button"
    PANTALLA_ERROR_CREDENCIALES = "div.bg-red-100.border-red-500 div.text-red-700"
    
    # === Main Menu ===
    BUTTON_CERRAR_VENTANA = "#app > div > div > div.z-\\[999\\].fixed.w-full.h-full.left-0.top-0.bg-\\[\\#344054b3\\].flex.items-center.justify-center.transition-opacity.duration-300.ease-in-out.opacity-100 > div > button"
    TEXTO_BIENVENIDA = "//div[normalize-space()='Todo en un solo lugar']"
    MENU_SEGUROS = "div.flex.flex-row.gap-\\[32px\\] > div.cursor-pointer:first-of-type"
    LINK_AUTOS_MOTOS = "#app > div > div > div:nth-child(3) > div > div > div:nth-child(1) > div.relative.flex.flex-col.items-start.justify-start.gap-2.shrink-0 > a:nth-child(1) > div.relative.flex.flex-col.items-start.justify-start.gap-0.shrink-0 > span"
    BUTTON_COTIZAR = "a[href*='cotizadoresgenerales.com/AutenticacionSSO']"
    
    # === Quotation Form ===
    INPUT_IDENTIFICACION = "#ctl00_ContentPlaceHolder1_LoginViewCotizacionWeb_txtNumDocAseg"
    INPUT_PLACA = "#ctl00_ContentPlaceHolder1_LoginViewCotizacionWeb_tbPlacas"
    BUTTON_CONSULTAR = "#ctl00_ContentPlaceHolder1_LoginViewCotizacionWeb_BtnConsultar"
    INPUT_CELULAR = "#ctl00_ContentPlaceHolder1_LoginViewCotizacionWeb_tbCelularContacto"
    INPUT_EMAIL = "#ctl00_ContentPlaceHolder1_LoginViewCotizacionWeb_tbEmailContacto"
    
    # === Coverage Options ===
    BUTTON_RESPONSABILIDAD_CIVIL_NO = "#ctl00_ContentPlaceHolder1_LoginViewCotizacionWeb_rbExtenderCoberturaNO"
    BUTTON_BICICLETA_NO = "#ctl00_ContentPlaceHolder1_LoginViewCotizacionWeb_rbAsegVehAdicionalNO"
    
    # === Additional Coverage Checkboxes ===
    BUTTON_GASTOS = "#ctl00_ContentPlaceHolder1_LoginViewCotizacionWeb_Adic_26_chkSelCob"
    BUTTON_LLANTAS_ESTALLADAS = "#ctl00_ContentPlaceHolder1_LoginViewCotizacionWeb_Adic_28_chkSelCob"
    BUTTON_PEQUEÑOS_ACCESORIOS = "#ctl00_ContentPlaceHolder1_LoginViewCotizacionWeb_Adic_29_chkSelCob"
    BUTTON_ACCIDENTES_PERSONALES = "#ctl00_ContentPlaceHolder1_LoginViewCotizacionWeb_Adic_50_chkSelCob"
    BUTTON_REMPLAZO_LLAVES = "#ctl00_ContentPlaceHolder1_LoginViewCotizacionWeb_Adic_36_chkSelCob"
    
    # === Plan Selection ===
    BUTTON_PREMIUM = "#ctl00_ContentPlaceHolder1_LoginViewCotizacionWeb_rbSelPaq_34"
    BUTTON_ESTANDAR = "#ctl00_ContentPlaceHolder1_LoginViewCotizacionWeb_rbSelPaq_36"
    BUTTON_BASICO = "#ctl00_ContentPlaceHolder1_LoginViewCotizacionWeb_rbSelPaq_38"
    
    # === Finalization ===
    BUTTON_COTIZAR2 = "#ctl00_ContentPlaceHolder1_LoginViewCotizacionWeb_btnCotizar"
    BUTTON_DESCARGAR_PDF = "#ctl00_ContentPlaceHolder1_LoginViewCotizacionWeb_btnGetPDF"
    
    # === Quotation Table ===
    TABLE_COTIZACION = "#ctl00_ContentPlaceHolder1_LoginViewCotizacionWeb_tblValoresPlanCoti"
