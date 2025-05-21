import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, CallbackQueryHandler
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os

# Configuración de logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Estados de la conversación
ELEGIR_ACCION, ELEGIR_TIPO, ELEGIR_CATEGORIA, ELEGIR_CONCEPTO, INGRESAR_MONTO, CONFIRMAR = range(6)

# Listas predefinidas
CONCEPTOS_INGRESOS = [
    "SUELDO DE ESPOSA",
    "SUELDO DE ESPOSO",
    "VENTA DE PRODUCTOS",
    "EXTRAS",
    "COBRO DE DEUDAS",
    "OTROS"
]

CONCEPTOS_GASTOS = [
    "ALQUILER",
    "TARJETA DE CREDITO",
    "PLAN DE CELULAR",
    "INTERNET",
    "LUZ",
    "AGUA",
    "GAS",
    "RECARGA DE TELEFONOS",
    "PASAJES",
    "GASOLINA/COMBUSTIBLE",
    "DIEZMO",
    "OFRENDA",
    "MENSUALIDAD DE COLEGIO",
    "AHORRO FIJO EN BANCO",
    "ALIMENTOS (DESAYUNO, ALMUERZO, CENA)",
    "ROPA",
    "CALZADO / ZAPATILLA",
    "ARTICULOS DE COCINA",
    "UTENSILIOS DE LIMPIEZA",
    "ARTICULO PARA EL HOGAR",
    "COSAS NO NECESARIAS",
    "ARTICULOS DE ASEO PERSONAL",
    "ARTICULOS DE LIMPIEZA",
    "REGALOS",
    "TECNOLOGICOS",
    "ELECTRODOMESTICOS",
    "CITA MEDICA",
    "GASTOS MEDICOS",
    "MEDICINA / PASTILLAS",
    "SALIDAS",
    "TARJETA X",
    "LIBROS",
    "COMIDA DE MASCOTAS",
    "VETERINARIO",
    "ANIVERSARIO",
    "DONACION",
    "DENTISTA",
    "VIAJES INTERPROVINCIALES",
    "COLEGIO DE LOS NIÑOS",
    "PRESTAMOS"
]

CATEGORIAS = ["FIJO", "VARIABLE"]
TIPOS = ["INGRESO", "GASTO"]

# Variables para almacenar temporalmente la información del registro
usuario_data = {}

# Función para conectar con Google Sheets
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive.file",
             "https://www.googleapis.com/auth/drive"]
    
    # Ruta al archivo de credenciales
    credentials_path = "credenciales_google.json"
    
    try:
        # Verificar si el archivo existe
        import os
        if not os.path.exists(credentials_path):
            logger.error(f"¡El archivo de credenciales no existe en la ruta: {os.path.abspath(credentials_path)}!")
            return None
            
        logger.info(f"Intentando conectar con el archivo de credenciales: {os.path.abspath(credentials_path)}")
        
        # Intentar leer el archivo
        with open(credentials_path, 'r') as f:
            logger.info("Archivo de credenciales encontrado y leído correctamente")
        
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
        logger.info("Credenciales cargadas correctamente")
        
        client = gspread.authorize(creds)
        logger.info("Cliente autorizado correctamente")
        
        # Nombre de tu hoja de Google Sheets
        nombre_spreadsheet = "ECONOMIA DE LA CASA"
        logger.info(f"Intentando abrir la hoja: {nombre_spreadsheet}")
        
        # Listar todas las hojas a las que tenemos acceso
        disponibles = [sheet.title for sheet in client.openall()]
        logger.info(f"Hojas disponibles: {disponibles}")
        
        spreadsheet = client.open(nombre_spreadsheet)
        logger.info(f"Hoja de cálculo abierta correctamente. Hojas: {[ws.title for ws in spreadsheet.worksheets()]}")
        
        sheet = spreadsheet.worksheet("Registro")
        logger.info("Hoja 'Registro' abierta correctamente")
        
        return sheet
    except Exception as e:
        logger.error(f"Error al conectar con Google Sheets: {str(e)}")
        logger.error(f"Tipo de error: {type(e).__name__}")
        import traceback
        logger.error(f"Detalles: {traceback.format_exc()}")
        return None

# Comandos
def start(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("Registrar movimiento", callback_data='registrar')],
        [InlineKeyboardButton("Ver último registro", callback_data='ver_ultimo')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        f'Hola {user.first_name}! Soy el bot de economía familiar.\n\n'
        f'¿Qué deseas hacer?',
        reply_markup=reply_markup
    )
    
    return ELEGIR_ACCION

def elegir_accion(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    if query.data == 'registrar':
        # Inicializar datos del usuario
        usuario_data[query.from_user.id] = {
            'usuario': query.from_user.first_name
        }
        
        keyboard = [[InlineKeyboardButton(tipo, callback_data=tipo)] for tipo in TIPOS]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            text="¿Qué tipo de movimiento quieres registrar?",
            reply_markup=reply_markup
        )
        return ELEGIR_TIPO
    
    elif query.data == 'ver_ultimo':
        # Implementar la visualización del último registro
        try:
            sheet = conectar_google_sheets()
            if sheet:
                # Obtener la última fila
                records = sheet.get_all_records()
                if records:
                    last_record = records[-1]
                    query.edit_message_text(
                        f"📝 *Último registro*\n\n"
                        f"📅 Fecha: {last_record.get('Fecha', 'N/A')}\n"
                        f"👤 Usuario: {last_record.get('Usuario', 'N/A')}\n"
                        f"📊 Tipo: {last_record.get('Tipo', 'N/A')}\n"
                        f"🏷️ Categoría: {last_record.get('Categoría', 'N/A')}\n"
                        f"🔖 Concepto: {last_record.get('Concepto', 'N/A')}\n"
                        f"💰 Monto: S/. {last_record.get('Monto', 'N/A')}\n",
                        parse_mode='Markdown'
                    )
                else:
                    query.edit_message_text("No hay registros disponibles.")
            else:
                query.edit_message_text("No se pudo conectar con la hoja de cálculo.")
        except Exception as e:
            query.edit_message_text(f"Error al obtener el último registro: {e}")
        
        return ConversationHandler.END

def elegir_tipo(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    tipo = query.data
    usuario_data[query.from_user.id]['tipo'] = tipo
    
    keyboard = [[InlineKeyboardButton(categoria, callback_data=categoria)] for categoria in CATEGORIAS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        text=f"Has seleccionado: {tipo}\n\n¿Es un {tipo.lower()} fijo o variable?",
        reply_markup=reply_markup
    )
    
    return ELEGIR_CATEGORIA

def elegir_categoria(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    categoria = query.data
    usuario_data[query.from_user.id]['categoria'] = categoria
    
    # Seleccionar la lista adecuada según el tipo
    conceptos = CONCEPTOS_INGRESOS if usuario_data[query.from_user.id]['tipo'] == "INGRESO" else CONCEPTOS_GASTOS
    
    # Crear botones en filas de 2
    keyboard = []
    row = []
    for i, concepto in enumerate(conceptos):
        row.append(InlineKeyboardButton(concepto, callback_data=concepto))
        if i % 2 == 1 or i == len(conceptos) - 1:
            keyboard.append(row)
            row = []
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        text=f"Has seleccionado: {categoria}\n\nSelecciona el concepto:",
        reply_markup=reply_markup
    )
    
    return ELEGIR_CONCEPTO

def elegir_concepto(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    concepto = query.data
    usuario_data[query.from_user.id]['concepto'] = concepto
    
    query.edit_message_text(
        text=f"Has seleccionado: {concepto}\n\nPor favor, ingresa el monto (solo números):"
    )
    
    return INGRESAR_MONTO

def ingresar_monto(update: Update, context: CallbackContext) -> int:
    try:
        monto = float(update.message.text.replace(',', '.'))
        user_id = update.effective_user.id
        
        if monto <= 0:
            update.message.reply_text("El monto debe ser mayor que cero. Por favor, ingresa un monto válido:")
            return INGRESAR_MONTO
        
        usuario_data[user_id]['monto'] = monto
        
        # Mostrar resumen para confirmación
        keyboard = [
            [InlineKeyboardButton("✅ Confirmar", callback_data='confirmar')],
            [InlineKeyboardButton("❌ Cancelar", callback_data='cancelar')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            f"📝 *Resumen del registro*\n\n"
            f"👤 Usuario: {usuario_data[user_id]['usuario']}\n"
            f"📊 Tipo: {usuario_data[user_id]['tipo']}\n"
            f"🏷️ Categoría: {usuario_data[user_id]['categoria']}\n"
            f"🔖 Concepto: {usuario_data[user_id]['concepto']}\n"
            f"💰 Monto: S/. {monto}\n\n"
            f"¿Confirmas este registro?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return CONFIRMAR
    
    except ValueError:
        update.message.reply_text("Por favor, ingresa solo números (usa punto o coma para decimales):")
        return INGRESAR_MONTO

def confirmar(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    if query.data == 'confirmar':
        user_id = query.from_user.id
        
        try:
            sheet = conectar_google_sheets()
            if sheet:
                # Datos a registrar
                fecha = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                mes = datetime.now().strftime("%B %Y")  # Mes y año
                
                # Añadir a Google Sheets
                sheet.append_row([
                    fecha,
                    usuario_data[user_id]['usuario'],
                    usuario_data[user_id]['tipo'],
                    usuario_data[user_id]['categoria'],
                    usuario_data[user_id]['concepto'],
                    usuario_data[user_id]['monto'],
                    mes
                ])
                
                query.edit_message_text("✅ Registro completado con éxito.")
            else:
                query.edit_message_text("❌ No se pudo conectar con la hoja de cálculo.")
        
        except Exception as e:
            query.edit_message_text(f"❌ Error al guardar el registro: {e}")
    
    else:  # cancelar
        query.edit_message_text("❌ Registro cancelado.")
    
    # Limpiar datos
    if user_id in usuario_data:
        del usuario_data[user_id]
    
    return ConversationHandler.END

def registrar_por_texto(update: Update, context: CallbackContext) -> None:
    """Procesa mensajes de texto con formato: TIPO MONTO CONCEPTO"""
    text = update.message.text.upper()
    user = update.effective_user
    
    try:
        parts = text.split()
        
        # Verificar si el formato es correcto
        if len(parts) < 3:
            update.message.reply_text(
                "❌ Formato incorrecto. Usa: TIPO MONTO CONCEPTO\n"
                "Ejemplo: GASTO 50 ALIMENTOS"
            )
            return
        
        tipo = parts[0]
        if tipo not in TIPOS:
            update.message.reply_text(f"❌ El tipo debe ser INGRESO o GASTO. Recibido: {tipo}")
            return
        
        try:
            monto = float(parts[1].replace(',', '.'))
            if monto <= 0:
                update.message.reply_text("❌ El monto debe ser mayor que cero.")
                return
        except ValueError:
            update.message.reply_text("❌ El monto debe ser un número válido.")
            return
        
        # Unir el resto como concepto
        concepto_texto = " ".join(parts[2:])
        
        # Verificar si el concepto existe en las listas predefinidas
        lista_conceptos = CONCEPTOS_INGRESOS if tipo == "INGRESO" else CONCEPTOS_GASTOS
        
        # Buscar el mejor concepto que coincida
        concepto_encontrado = None
        for concepto in lista_conceptos:
            if concepto_texto in concepto or concepto in concepto_texto:
                concepto_encontrado = concepto
                break
        
        if not concepto_encontrado:
            # Si no se encuentra una coincidencia exacta, mostrar opciones
            update.message.reply_text(
                f"❌ No se encontró el concepto '{concepto_texto}'. Por favor, usa el comando /start para registrar."
            )
            return
        
        # Categoría por defecto (se puede mejorar con un algoritmo más inteligente)
        categoria = "VARIABLE"  # Por defecto
        
        # Algunos conceptos que suelen ser fijos
        conceptos_fijos = ["ALQUILER", "INTERNET", "LUZ", "AGUA", "GAS", "PLAN DE CELULAR", 
                         "SUELDO", "MENSUALIDAD", "AHORRO FIJO"]
        
        for cf in conceptos_fijos:
            if cf in concepto_encontrado:
                categoria = "FIJO"
                break
        
        # Registrar en Google Sheets
        sheet = conectar_google_sheets()
        if sheet:
            fecha = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            mes = datetime.now().strftime("%B %Y")
            
            sheet.append_row([
                fecha,
                user.first_name,
                tipo,
                categoria,
                concepto_encontrado,
                monto,
                mes
            ])
            
            update.message.reply_text(
                f"✅ Registro rápido completado:\n\n"
                f"👤 Usuario: {user.first_name}\n"
                f"📊 Tipo: {tipo}\n"
                f"🏷️ Categoría: {categoria}\n"
                f"🔖 Concepto: {concepto_encontrado}\n"
                f"💰 Monto: S/. {monto}\n"
            )
        else:
            update.message.reply_text("❌ No se pudo conectar con la hoja de cálculo.")
    
    except Exception as e:
        update.message.reply_text(f"❌ Error: {e}")

def cancelar(update: Update, context: CallbackContext) -> int:
    """Cancela la conversación"""
    user = update.message.from_user
    logger.info(f"Usuario {user.first_name} canceló la conversación.")
    update.message.reply_text('Operación cancelada. ¡Hasta pronto!')
    
    # Limpiar datos
    if update.effective_user.id in usuario_data:
        del usuario_data[update.effective_user.id]
    
    return ConversationHandler.END

def ayuda(update: Update, context: CallbackContext) -> None:
    """Envía un mensaje de ayuda"""
    update.message.reply_text(
        "🤖 *Bot de Economía Familiar* 🏡\n\n"
        "*Comandos disponibles:*\n"
        "/start - Iniciar el bot y registrar un movimiento\n"
        "/ayuda - Mostrar este mensaje de ayuda\n\n"
        "*Registro rápido por texto:*\n"
        "Puedes escribir directamente en este formato:\n"
        "TIPO MONTO CONCEPTO\n\n"
        "*Ejemplos:*\n"
        "• INGRESO 1500 SUELDO DE ESPOSO\n"
        "• GASTO 50 ALIMENTOS\n",
        parse_mode='Markdown'
    )

def error(update: Update, context: CallbackContext) -> None:
    """Maneja errores"""
    logger.warning(f'Update {update} causó el error {context.error}')
    if update.message:
        update.message.reply_text("Ocurrió un error. Por favor, intenta de nuevo o contacta al administrador.")

def main() -> None:
    """Función principal"""
    # Configura el token de tu bot
    TOKEN = "TU_TOKEN_DE_TELEGRAM"
    
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher
    
    # Manejador de conversación para el registro de movimientos
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ELEGIR_ACCION: [CallbackQueryHandler(elegir_accion)],
            ELEGIR_TIPO: [CallbackQueryHandler(elegir_tipo)],
            ELEGIR_CATEGORIA: [CallbackQueryHandler(elegir_categoria)],
            ELEGIR_CONCEPTO: [CallbackQueryHandler(elegir_concepto)],
            INGRESAR_MONTO: [MessageHandler(Filters.text & ~Filters.command, ingresar_monto)],
            CONFIRMAR: [CallbackQueryHandler(confirmar)]
        },
        fallbacks=[CommandHandler('cancelar', cancelar)]
    )
    
    dispatcher.add_handler(conv_handler)
    
    # Manejador para registro por texto
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, registrar_por_texto))
    
    # Otros comandos
    dispatcher.add_handler(CommandHandler("ayuda", ayuda))
    
    # Manejador de errores
    dispatcher.add_error_handler(error)
    
    # Iniciar el bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
